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

from logger import get_logger

log = get_logger(__name__)


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

    def _record_first(self, store, year, band, key, qso_date):
        existing = store[year][band].get(key)
        if existing is None or (qso_date and qso_date < existing):
            store[year][band][key] = qso_date

    def add_qso(self, year, band, entity_code, cq_zone, qso_date):
        if not year or not band:
            return
        if entity_code:
            self._record_first(self.entities, year, band, entity_code, qso_date)
        if cq_zone:
            self._record_first(self.zones, year, band, cq_zone, qso_date)

    """
        Parsing
    """
    def parse_files(self, adif_file_paths, lookup, ignore_sat_entries=False, progress_callback=None):
        if lookup and hasattr(lookup, 'clear_entity_session_cache'):
            lookup.clear_entity_session_cache()

        files = [p for p in (adif_file_paths or []) if p and os.path.exists(p)]
        total_files = len(files)

        for file_index, file_path in enumerate(files):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            except OSError as e:
                log.error(f"Marathon score: cannot read {file_path} -> {e}")
                continue

            records = re.split(r"<EOR>", content, flags=re.IGNORECASE)
            for record in records:
                record = record.strip()
                if not record:
                    continue
                record = " ".join(record.split())
                (year, qso_date, band, grid, call, freq, mode,
                 rst_sent, rst_rcvd, qsl_status, prop_mode, info) = parse_adif_record(record, lookup)

                if ignore_sat_entries and prop_mode == 'SAT':
                    continue
                if not info:
                    continue

                self.add_qso(
                    year,
                    band,
                    info.get('entity_code'),
                    info.get('cqz'),
                    qso_date,
                )

            if progress_callback:
                progress_callback(file_index + 1, total_files)

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
        """Bands (in AMATEUR_BANDS order) that have any entity or zone for year."""
        result = []
        for band in AMATEUR_BANDS.keys():
            n_ent, n_zone = self.band_counts(year, band, cutoff)
            if n_ent or n_zone:
                result.append(band)
        return result

    def band_counts(self, year, band, cutoff=None):
        """(entities, zones) worked on `band` in `year`, filtered by cutoff."""
        ent = self.entities.get(year, {}).get(band, {})
        zon = self.zones.get(year, {}).get(band, {})
        n_ent  = sum(1 for d in ent.values() if self._passes_cutoff(d, cutoff))
        n_zone = sum(1 for d in zon.values() if self._passes_cutoff(d, cutoff))
        return n_ent, n_zone

    def overall_score(self, year, cutoff=None):
        """
        Official DX Marathon score for the year: unique entities across all
        bands + unique zones across all bands. Returns (entities, zones, total).
        """
        entity_dates = {}
        for band_map in self.entities.get(year, {}).values():
            for code, date in band_map.items():
                if code not in entity_dates or (date and date < entity_dates[code]):
                    entity_dates[code] = date

        zone_dates = {}
        for band_map in self.zones.get(year, {}).values():
            for zone, date in band_map.items():
                if zone not in zone_dates or (date and date < zone_dates[zone]):
                    zone_dates[zone] = date

        n_ent  = sum(1 for d in entity_dates.values() if self._passes_cutoff(d, cutoff))
        n_zone = sum(1 for d in zone_dates.values() if self._passes_cutoff(d, cutoff))
        return n_ent, n_zone, n_ent + n_zone


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
