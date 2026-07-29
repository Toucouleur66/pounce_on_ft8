# marathon_entities.py
#
# Official DX Marathon entity list (dxmarathon.com). Resolves an entity to its DX
# Marathon record (prefix, name, continent, CQ zones) so the score/difference
# windows show the official data.
#
# Resolution note: ClubLog cty.xml and the DX Marathon CSV do NOT always agree on
# ADIF DXCC numbers (e.g. ClubLog gives "Shetland Islands" code 241, while the CSV
# uses 241 for "South Shetland Is." and files Shetland under Scotland). So we
# resolve by the ClubLog entity NAME first (matched against several CSV name
# columns, DXCC-source rows winning), and only fall back to the ADIF code.

import csv
import re

from utils import get_data_file_path

from logger import get_logger

log = get_logger(__name__)

_CSV_FILENAME = "dx_marathon_entities.csv"

# CSV name columns to index, in priority order.
_NAME_COLUMNS = [
    "ClubLog Name", "ADIF Name", "LoTW Name", "Name",
    "Short Name", "Long Name", "Alternate Name 1", "Alternate Name 2",
]

_by_code = None   # {adif_code (int): record}
_by_name = None   # {normalized_name (str): record}


def _norm(text):
    text = text.upper().replace("&", " AND ")
    text = text.replace("ST.", "SAINT").replace("IS.", "ISLANDS").replace("I.", "ISLAND")
    return re.sub(r"[^A-Z0-9]", "", text)  # drop accents, punctuation, spaces


def _record(row):
    return {
        "prefix"   : (row.get("Prefix") or "").strip(),
        "name"     : (row.get("Name") or "").strip(),
        "continent": (row.get("Continent") or "").strip(),
        "cq_zones" : (row.get("CQ Zones") or "").strip(),
    }


def _load():
    global _by_code, _by_name
    if _by_code is not None:
        return

    _by_code = {}
    _by_name = {}
    path = get_data_file_path(_CSV_FILENAME)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            rows = list(csv.DictReader(f))
    except OSError as e:
        log.warning(f"DX Marathon entities CSV not available ({e}); using lookup names")
        return

    for row in rows:
        code = (row.get("ADIF DXCC Code") or "").strip()
        if code.isdigit() and (row.get("Name") or "").strip():
            _by_code.setdefault(int(code), _record(row))

    # Name index: DXCC-source rows win over WAE/special rows for the same name.
    for dxcc_first in (True, False):
        for row in rows:
            is_dxcc = (row.get("Source", "").strip() == "DXCC")
            if is_dxcc != dxcc_first:
                continue
            record = _record(row)
            for col in _NAME_COLUMNS:
                value = (row.get(col) or "").strip()
                if value:
                    _by_name.setdefault(_norm(value), record)

    log.debug(f"DX Marathon entities loaded: {len(_by_code)} codes, {len(_by_name)} names from {path}")


def marathon_entity(entity_code, lookup_name=None):
    """
    DX Marathon record {prefix, name, continent, cq_zones} for an entity, or None.
    Resolves by the ClubLog `lookup_name` first (avoids ADIF-code collisions such
    as Shetland/South Shetland), then by ADIF code.
    """
    _load()
    if lookup_name:
        record = _by_name.get(_norm(lookup_name))
        if record:
            return record
    if entity_code is not None:
        try:
            return _by_code.get(int(entity_code))
        except (TypeError, ValueError):
            return None
    return None


def marathon_entity_name(entity_code, lookup_name=None):
    """Official DX Marathon name for an entity, or None if not listed."""
    record = marathon_entity(entity_code, lookup_name)
    return record["name"] if record else None
