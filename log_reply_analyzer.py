# log_reply_analyzer.py
#
# Reply-decision audit: parse pounce.log to reconstruct, for a station we replied
# to, WHY it was prioritized and WHICH other stations were candidates in the same
# cycle (process_reply_packet_buffer -> "Selected messages" block).
#
# Pure Python, NO PyQt dependency, so the parser is unit-testable standalone.
#
# Log format reminder (logger.py LOG_FORMAT = "[%(asctime)s @%(name)s] %(levelname)s --:\n\t%(message)s"):
# a record spans multiple physical lines. A "Selected messages" block looks like:
#
#   [260707_090959 @wsjtx_listener] INFO --:
#   \tSelected messages (4):
#   \t[ 5 ] 070945 de:JR2ULS    *\tdir:F5UKW\tsnr:-15  \tpid:2028  \twkb4y:      \twhy:wanted_cq_zone
#   \t[ 3 ] 070945 de:JA2FJP    *\tdir:EW8W \tsnr:-7   \tpid:2021  \twkb4y:      \twhy:wanted_cq_zone
#   ...
#
# Candidates are printed sorted by the same tie-break as the winner selection
# (get_sorted_keys), descending, so the FIRST candidate line is the selected one.

import os
import re

# Header of any log record: "[YYMMDD_HHMMSS @name] LEVEL --:"
_HEADER_RE = re.compile(
    r'^\[(?P<ts>\d{6}_\d{6})\s+@(?P<name>[\w.]+)\]\s+(?P<level>\w+)\s+--:\s*$'
)

_SELECTED_RE = re.compile(r'^Selected messages \((?P<count>\d+)\):\s*$')

# One candidate line (leading tab already stripped). Tolerant to spacing and to a
# missing wkb4y / why field (older logs). lotw flag is the char right after the
# padded callsign: "*" when LoTW, else a space.
_CANDIDATE_RE = re.compile(
    r'^\[\s*(?P<priority>-?\d+)\s*\]\s+'
    r'(?P<time>\d{6})\s+'
    r'de:(?P<callsign>[A-Z0-9/]+)\s*(?P<lotw>[*\s])?'
    r'\s*dir:(?P<dir>\S+)?'
    r'\s*snr:(?P<snr>[+-]?\d+)'
    r'\s*pid:(?P<pid>\d+)'
    r'(?:\s*wkb4y:(?P<wkb4y>\d+)?)?'
    r'(?:\s*why:(?P<why>\S+))?'
    r'\s*$'
)

# Neighbouring context lines worth surfacing (eligibility / fate of a callsign).
_CONTEXT_PATTERNS = (
    'for marathon',
    'as wanted',
    'for DXCC',
    'for grid',
    'as it is set as excluded',
    'as it is wkb4',
    'Keeping',
    'Sent ReplyPacket',
    'Watchdog',
    'Focus on',
    'Found',
    'Skipping',
)


def find_log_files(app_data_dir):
    """
        Return the current pounce.log plus rotated backups (pounce.log.YYMMDD),
        most-recent first. A cycle may live in the current file OR a backup
        depending on the day.
    """
    if not app_data_dir or not os.path.isdir(app_data_dir):
        return []

    current = os.path.join(app_data_dir, 'pounce.log')
    backups = []
    for name in os.listdir(app_data_dir):
        if re.fullmatch(r'pounce\.log\.\d{6}', name):
            backups.append(os.path.join(app_data_dir, name))

    # Backups sorted by their YYMMDD suffix descending (newest first).
    backups.sort(key=lambda p: p.rsplit('.', 1)[-1], reverse=True)

    files = []
    if os.path.isfile(current):
        files.append(current)
    files.extend(backups)
    return files


def _read_lines(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read().splitlines()
    except OSError:
        return []


def _parse_candidate(raw_line):
    line = raw_line.strip()
    m = _CANDIDATE_RE.match(line)
    if not m:
        return None
    return {
        'priority'      : int(m.group('priority')),
        'time'          : m.group('time'),
        'callsign'      : m.group('callsign'),
        'lotw'          : m.group('lotw') == '*',
        'directed'      : m.group('dir') or '',
        'snr'           : int(m.group('snr')),
        'packet_id'     : int(m.group('pid')),
        'wkb4_year'     : int(m.group('wkb4y')) if m.group('wkb4y') else None,
        'priority_type' : m.group('why'),  # None on older logs
    }


def parse_selected_blocks(lines):
    """
        Parse all "Selected messages" blocks from a list of log lines.

        Returns a list of dicts:
          { 'header_ts': 'YYMMDD_HHMMSS', 'line_index': int (header line),
            'candidates': [ {priority, time, callsign, lotw, directed, snr,
                             packet_id, wkb4_year, priority_type}, ... ] }
        Candidates keep their logged order (already sorted best-first).
    """
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        header = _HEADER_RE.match(lines[i])
        # The record body is on the following tab-indented line(s).
        if header and i + 1 < n and _SELECTED_RE.match(lines[i + 1].strip()):
            header_ts = header.group('ts')
            candidates = []
            j = i + 2
            # Consume following candidate lines until a non-candidate line.
            while j < n:
                # Stop if a new record header starts.
                if _HEADER_RE.match(lines[j]):
                    break
                cand = _parse_candidate(lines[j])
                if cand is None:
                    # A blank or unrelated indented line ends the block.
                    if lines[j].strip() == '':
                        j += 1
                        continue
                    break
                candidates.append(cand)
                j += 1
            if candidates:
                blocks.append({
                    'header_ts'  : header_ts,
                    'line_index' : i,
                    'candidates' : candidates,
                })
            i = j
            continue
        i += 1
    return blocks


def _tie_break_note(selected, candidates):
    """
        If the selected candidate does NOT have a strictly-max priority (i.e. there
        was a tie on priority), state which field decided, mirroring get_sorted_keys
        order: (priority, -wkb4_year[None=best], lotw, snr, -packet_id).
    """
    if not selected:
        return None
    top = max(c['priority'] for c in candidates)
    tied = [c for c in candidates if c['priority'] == top]
    if len(tied) <= 1:
        return None  # won outright on priority

    # wkb4_year: None ranks best (treated as +inf in get_sorted_keys via -year).
    def wkb4_rank(c):
        return float('inf') if c['wkb4_year'] is None else -c['wkb4_year']

    for field, label, keyfn in (
        ('wkb4_year', 'no/older Worked-Before', wkb4_rank),
        ('lotw',      'LoTW membership',        lambda c: 1 if c['lotw'] else 0),
        ('snr',       'better SNR',             lambda c: c['snr']),
        ('packet_id', 'earlier decode',         lambda c: -c['packet_id']),
    ):
        best = max(tied, key=keyfn)
        if keyfn(best) != keyfn(min(tied, key=keyfn)):
            # This field is the first that separates the tied set.
            if best['callsign'] == selected['callsign']:
                return f"Tie on priority {top}; won on {label}."
            return f"Tie on priority {top}; decided on {label}."
    return f"Tie on priority {top}."


def collect_context(lines, callsign, block_line_index, window=40):
    """
        Best-effort: gather nearby log lines mentioning this callsign that explain
        its eligibility/fate (marathon, wanted, exclusion, Sent ReplyPacket...).
        Searches a window of lines around the block.
    """
    if block_line_index is None:
        lo, hi = 0, len(lines)
    else:
        lo = max(0, block_line_index - window)
        hi = min(len(lines), block_line_index + window)

    hits = []
    for k in range(lo, hi):
        line = lines[k].strip()
        if callsign not in line:
            continue
        if any(pat in line for pat in _CONTEXT_PATTERNS):
            hits.append(line)
    # De-dup while preserving order.
    seen = set()
    out = []
    for h in hits:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


def analyze_reply(callsign, time_hhmmss=None, packet_id=None, lines=None, blocks=None):
    """
        Find the reply-decision cycle for `callsign` and return an analysis dict:

          {
            'found'         : bool,
            'callsign'      : str,
            'selected'      : candidate dict | None,   # the winner of the cycle
            'is_selected'   : bool,   # was OUR callsign the winner?
            'reason'        : str | None,              # selected priority_type
            'candidates'    : [candidate dict, ...],   # full cycle, best-first
            'tie_break_note': str | None,
            'context'       : [str, ...],              # neighbouring log lines
            'message'       : str | None,              # human note when not found
          }

        Matching: prefer a block whose candidates contain `callsign`, disambiguated
        by packet_id (unique per session) then time_hhmmss when several match.
    """
    callsign = (callsign or '').upper()
    # The log records the decode time as HHMMSS; the GUI row carries date_str as
    # "YYYY-MM-DD HH:MM:SS". Normalize to the 6 HHMMSS digits so time matching works.
    norm_time = None
    if time_hhmmss is not None:
        digits = ''.join(ch for ch in str(time_hhmmss) if ch.isdigit())
        norm_time = digits[-6:] if len(digits) >= 6 else digits
    if blocks is None:
        blocks = parse_selected_blocks(lines or [])

    # All blocks where this callsign appears as a candidate.
    matching = []
    for b in blocks:
        for c in b['candidates']:
            if c['callsign'].upper() == callsign:
                score = 0
                if packet_id is not None and c['packet_id'] == packet_id:
                    score += 100
                if norm_time is not None and c['time'] == norm_time:
                    score += 10
                matching.append((score, b, c))
                break

    if not matching:
        context = collect_context(lines or [], callsign, None) if lines else []
        return {
            'found'         : False,
            'callsign'      : callsign,
            'selected'      : None,
            'is_selected'   : False,
            'reason'        : None,
            'candidates'    : [],
            'tie_break_note': None,
            'context'       : context,
            'message'       : f"No reply decision found for {callsign} in the log.",
        }

    # Best-scoring block (exact packet_id/time preferred); ties -> latest block.
    matching.sort(key=lambda t: (t[0], t[1]['line_index']))
    _, block, our_candidate = matching[-1]

    candidates = block['candidates']
    selected = candidates[0] if candidates else None
    is_selected = bool(selected and selected['callsign'].upper() == callsign)
    reason = selected.get('priority_type') if selected else None

    context = collect_context(lines or [], callsign, block['line_index']) if lines else []

    return {
        'found'         : True,
        'callsign'      : callsign,
        'selected'      : selected,
        'is_selected'   : is_selected,
        'reason'        : reason,
        'candidates'    : candidates,
        'tie_break_note': _tie_break_note(selected, candidates),
        'context'       : context,
        'message'       : None,
    }


def analyze_reply_from_files(callsign, time_hhmmss=None, packet_id=None, log_files=None):
    """
        Convenience: read the given log files (current + backups, most-recent
        first) and run analyze_reply against their combined lines. Stops at the
        first file that yields a match so the freshest cycle wins.
    """
    for path in (log_files or []):
        lines = _read_lines(path)
        if not lines:
            continue
        result = analyze_reply(callsign, time_hhmmss, packet_id, lines=lines)
        if result['found']:
            result['log_file'] = path
            return result
    # Nothing matched in any file: return a not-found built from the newest file's
    # context (if any) so the dialog can still show neighbouring lines.
    for path in (log_files or []):
        lines = _read_lines(path)
        if lines:
            result = analyze_reply(callsign, time_hhmmss, packet_id, lines=lines)
            result['log_file'] = path
            return result
    return analyze_reply(callsign, time_hhmmss, packet_id, lines=[])
