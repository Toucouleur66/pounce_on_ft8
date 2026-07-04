# pota_spots.py
#
# Parks On The Air (POTA) live-spot provider.
#
# POTA activator status is NOT stored in the local ADIF (unlike DXCC/Marathon):
# an operator activates many different parks and each park reference is a fresh
# catch for a hunter. We therefore look the status up live from the pota.app spot
# API and cross-reference every decoded callsign against the current activator
# spots.
#
# PotaSpotProvider owns:
#   - a cache mapping activator callsign -> park reference (FT8/FT4 spots only),
#     refreshed off the GUI thread by PotaFetchWorker,
#   - an in-memory set of (callsign, reference) pairs already answered TODAY
#     (UTC), so the same operator is re-called when their park reference changes
#     but not spammed for the same park on the same UTC day.
#
# The provider is read from the listener thread (get_reference / already_answered
# / mark_answered) and written from the GUI thread (update_spots), so all shared
# state is guarded by a lock.

import json
import threading
import urllib.request

from datetime import datetime, timezone

from PyQt6.QtCore import QObject, pyqtSignal

from logger import get_logger
from constants import POTA_SPOT_URL

log = get_logger(__name__)

# Modes we can actually decode in this app. POTA spots for other modes (CW/SSB)
# are ignored so we never colour/reply to a station we can't work here.
POTA_DIGITAL_MODES = {"FT8", "FT4"}


class PotaFetchWorker(QObject):
    """Fetches the current POTA activator spots off the GUI thread."""

    # emits { callsign_upper: reference } (already filtered to FT8/FT4)
    finished = pyqtSignal(dict)

    def __init__(self, url=POTA_SPOT_URL, timeout=15):
        super().__init__()
        self._url     = url
        self._timeout = timeout

    def run(self):
        spots = {}
        try:
            req = urllib.request.Request(
                self._url,
                headers={"User-Agent": "Wait-and-Pounce"}
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                payload = resp.read().decode("utf-8")
            data = json.loads(payload)

            for spot in data:
                mode = (spot.get("mode") or "").upper()
                if mode not in POTA_DIGITAL_MODES:
                    continue
                activator = (spot.get("activator") or "").upper().strip()
                reference = (spot.get("reference") or "").upper().strip()
                if activator and reference:
                    # Last spot wins (spots are returned oldest->newest enough
                    # for our purposes; the most recent reference is preferred).
                    spots[activator] = reference

            log.info(f"POTA: fetched {len(spots)} FT8/FT4 activator spot(s)")
        except Exception as e:
            # On failure emit an empty dict; the provider keeps its previous
            # cache so a transient network hiccup does not wipe known spots.
            log.error(f"POTA: spot fetch failed: {e}")
            self.finished.emit({})
            return

        self.finished.emit(spots)


class PotaSpotProvider(QObject):
    """Thread-safe cache of current POTA activator spots + answered-today set."""

    def __init__(self):
        super().__init__()
        self._lock              = threading.Lock()
        self._spots             = {}                  # callsign_upper -> reference
        self._answered          = set()               # (callsign_upper, reference)
        self._answered_utc_date = self._today_utc()

    @staticmethod
    def _today_utc():
        return datetime.now(timezone.utc).date()

    def update_spots(self, spots):
        """Replace the cached spot map (called from the GUI thread on fetch)."""
        if not spots:
            # Keep the previous cache on an empty/failed fetch.
            return
        with self._lock:
            self._spots = dict(spots)

    def get_reference(self, callsign):
        """Return the park reference for a spotted activator, else None."""
        if not callsign:
            return None
        with self._lock:
            return self._spots.get(callsign.upper())

    def _maybe_reset_locked(self):
        """Clear the answered set when the UTC day rolls over. Caller holds lock."""
        today = self._today_utc()
        if today != self._answered_utc_date:
            self._answered.clear()
            self._answered_utc_date = today

    def already_answered(self, callsign, reference):
        """True if this (callsign, reference) was already replied to today (UTC)."""
        if not callsign or not reference:
            return False
        with self._lock:
            self._maybe_reset_locked()
            return (callsign.upper(), reference.upper()) in self._answered

    def mark_answered(self, callsign, reference):
        """Record that we replied to this (callsign, reference) today (UTC)."""
        if not callsign or not reference:
            return
        with self._lock:
            self._maybe_reset_locked()
            self._answered.add((callsign.upper(), reference.upper()))
