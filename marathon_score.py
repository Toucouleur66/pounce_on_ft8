# marathon_score.py
#
# Standalone DX Marathon scorer (no Qt). Parses the operator's ADIF logbook and
# computes, per year and per band, the DXCC entities and CQ zones worked, keeping
# the earliest QSO date of each so a year-to-date comparison is possible.
#
# DX Marathon scoring: 1 point per unique DXCC entity worked in the year + 1
# point per unique CQ zone worked in the year. Each counts once, no multipliers.
# A single QSO may score both a country and a zone.

import os
import re

from collections import defaultdict

from utils import parse_adif_record, AMATEUR_BANDS
from callsign_lookup import CallsignLookup
from marathon_entities import marathon_entity, marathon_entity_name
from marathon_wae import resolve_wae, wae_record

from logger import get_logger

log = get_logger(__name__)

# DX Marathon covers HF plus 6 m only; bands above 6 m (4 m, 2 m, 70 cm, …) do
# not count. Kept in AMATEUR_BANDS display order.
MARATHON_BANDS = [b for b in AMATEUR_BANDS.keys() if b not in ('4m', '2m', '70cm', '13cm', '3cm')]
_MARATHON_BANDS_SET = set(MARATHON_BANDS)


class MarathonScorer:
    """
    Holds the parsed Marathon data:
      entities[year][band] -> {entity_code: earliest_qso_date}
      zones[year][band]    -> {cq_zone:     earliest_qso_date}
    `year` is a string ("2026"), `band` a lowercase string ("20m"), the date the
    ADIF QSO_DATE string ("YYYYMMDD"). Entity/zone are ints.
    """

    def __init__(self):
        self.entities = defaultdict(lambda: defaultdict(dict))
        self.zones    = defaultdict(lambda: defaultdict(dict))
        # entity_code -> country name, for display in the difference window.
        self.entity_names = {}

    def _record_first(self, store, year, band, key, qso_date, callsign):
        # Value is (earliest_qso_date, callsign of that earliest QSO).
        existing = store[year][band].get(key)
        if existing is None or (qso_date and qso_date < existing[0]):
            store[year][band][key] = (qso_date, callsign)

    def add_qso(self, year, band, entity_code, cq_zone, qso_date, callsign=None, entity_name=None):
        # Ignore QSOs outside the DX Marathon bands (above 6 m).
        if not year or not band or band not in _MARATHON_BANDS_SET:
            return
        if entity_code:
            self._record_first(self.entities, year, band, entity_code, qso_date, callsign)
            if entity_name and entity_code not in self.entity_names:
                self.entity_names[entity_code] = entity_name
        if cq_zone:
            self._record_first(self.zones, year, band, cq_zone, qso_date, callsign)

    def entity_name(self, entity_code):
        return self.entity_record(entity_code)["name"]

    def entity_record(self, entity_code):
        """
        {prefix, name, continent, cq_zones} for an entity. WAE entities (internal
        codes 901-906) use their DX Marathon record; the rest resolve against the
        official CSV via the captured ClubLog name (avoids ADIF-code collisions),
        falling back to the parsed name.
        """
        wae = wae_record(entity_code)
        if wae:
            return {
                "prefix"   : wae["prefix"],
                "name"     : wae["name"],
                "continent": wae["continent"],
                "cq_zones" : wae["cq_zones"],
            }

        lookup_name = self.entity_names.get(entity_code)
        record = marathon_entity(entity_code, lookup_name)
        if record:
            return record
        return {
            "prefix"   : "",
            "name"     : lookup_name or str(entity_code),
            "continent": "",
            "cq_zones" : "",
        }

    """
        Parsing
    """
    def parse_files(self, adif_file_paths, lookup, ignore_sat_entries=False, progress_callback=None):
        """
        progress_callback(records_done, records_total) is called periodically so
        the UI can show a real progress bar across all files.
        """
        if lookup and hasattr(lookup, 'clear_entity_session_cache'):
            lookup.clear_entity_session_cache()

        files = [p for p in (adif_file_paths or []) if p and os.path.exists(p)]

        # Read every file up front and split into records to get an accurate
        # total (reading 10+ MB is instant; the cost is the per-record lookup).
        file_records = []
        total_records = 0
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            except OSError as e:
                log.error(f"Marathon score: cannot read {file_path} -> {e}")
                continue
            records = [r for r in re.split(r"<EOR>", content, flags=re.IGNORECASE) if r.strip()]
            file_records.append(records)
            total_records += len(records)

        done = 0
        if progress_callback:
            progress_callback(0, total_records)

        for records in file_records:
            for record in records:
                record = " ".join(record.split())
                (year, qso_date, band, grid, call, freq, mode,
                 rst_sent, rst_rcvd, qsl_status, prop_mode, info) = parse_adif_record(record, lookup)

                done += 1

                if not (ignore_sat_entries and prop_mode == 'SAT') and info:
                    entity_code = info.get('entity_code')
                    entity_name = info.get('entity')
                    # DX Marathon WAE entities (Shetland, Sicily, ITU Vienna…) are
                    # remapped to their internal code (901-906) so they score and
                    # display as distinct entities.
                    wae = resolve_wae(call, entity_name)
                    if wae:
                        entity_code = wae['code']
                        entity_name = wae['name']

                    self.add_qso(
                        year,
                        band,
                        entity_code,
                        info.get('cqz'),
                        qso_date,
                        callsign=call,
                        entity_name=entity_name,
                    )

                # Report progress every 200 records (and on the last one).
                if progress_callback and (done % 200 == 0 or done == total_records):
                    progress_callback(done, total_records)

    """
        Queries
    """
    @staticmethod
    def _passes_cutoff(qso_date, cutoff):
        """
        cutoff is None (no filter) or a (month, day) tuple. Keep the QSO only if
        its month/day is on or before the cutoff, so "to date" compares like for
        like across years. Records with no parseable date are kept.
        """
        if cutoff is None:
            return True
        if not qso_date or len(qso_date) < 8:
            return True
        try:
            month = int(qso_date[4:6])
            day   = int(qso_date[6:8])
        except ValueError:
            return True
        return (month, day) <= cutoff

    def years(self):
        return sorted(set(self.entities.keys()) | set(self.zones.keys()))

    def bands_worked(self, year, cutoff=None):
        """DX Marathon bands (160 m - 6 m) that have any entity or zone for year."""
        result = []
        for band in MARATHON_BANDS:
            n_ent, n_zone = self.band_counts(year, band, cutoff)
            if n_ent or n_zone:
                result.append(band)
        return result

    def band_counts(self, year, band, cutoff=None):
        """(entities, zones) worked on `band` in `year`, filtered by cutoff."""
        n_ent  = len(self._worked_info(self.entities, year, band, cutoff))
        n_zone = len(self._worked_info(self.zones, year, band, cutoff))
        return n_ent, n_zone

    def overall_score(self, year, cutoff=None):
        """
        Official DX Marathon score for the year: unique entities across all
        bands + unique zones across all bands. Returns (entities, zones, total).
        """
        n_ent  = len(self._worked_info(self.entities, year, None, cutoff))
        n_zone = len(self._worked_info(self.zones, year, None, cutoff))
        return n_ent, n_zone, n_ent + n_zone

    def _worked_info(self, store, year, band, cutoff):
        """{key: (earliest_qso_date, callsign)} worked, filtered by cutoff.
        band=None -> union across all bands (each key's earliest QSO wins)."""
        earliest = {}
        if band is None:
            band_maps = store.get(year, {}).values()
        else:
            band_maps = [store.get(year, {}).get(band, {})]
        for band_map in band_maps:
            for key, value in band_map.items():
                date = value[0]
                if key not in earliest or (date and date < earliest[key][0]):
                    earliest[key] = value
        return {key: value for key, value in earliest.items() if self._passes_cutoff(value[0], cutoff)}

    def entity_info(self, year, band=None, cutoff=None):
        """{entity_code: (date, callsign)} filtered by cutoff."""
        return self._worked_info(self.entities, year, band, cutoff)

    def zone_info(self, year, band=None, cutoff=None):
        """{cq_zone: (date, callsign)} filtered by cutoff."""
        return self._worked_info(self.zones, year, band, cutoff)

    def entities_worked(self, year, band=None, cutoff=None):
        return set(self._worked_info(self.entities, year, band, cutoff))

    def zones_worked(self, year, band=None, cutoff=None):
        return set(self._worked_info(self.zones, year, band, cutoff))


def build_scorer(adif_file_paths, ignore_sat_entries=False, progress_callback=None):
    """
    Construct a CallsignLookup (self-loading) and parse the given ADIF files into
    a populated MarathonScorer. Runs synchronously; call from a worker thread.
    """
    lookup = CallsignLookup()
    scorer = MarathonScorer()
    scorer.parse_files(
        adif_file_paths,
        lookup,
        ignore_sat_entries=ignore_sat_entries,
        progress_callback=progress_callback,
    )
    return scorer
