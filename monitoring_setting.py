import threading

from utils import text_to_array

from utils import(
    AMATEUR_BANDS
)

class MonitoringSettings:
    def __init__(self):
        self.lock = threading.Lock()
        self._wanted_callsigns = {}
        self._monitored_callsigns = {}
        self._excluded_callsigns = {}
        self._monitored_cq_zones = {}

        for band in AMATEUR_BANDS.keys():
            self._wanted_callsigns[band]    = set()
            self._monitored_callsigns[band] = set()
            self._excluded_callsigns[band]  = set()
            self._monitored_cq_zones[band]  = set()

    def get_wanted_callsigns(self, band):
        with self.lock:
            return self._wanted_callsigns.get(band, set())

    def set_wanted_callsigns(self, band, callsigns):
        with self.lock:
            self._wanted_callsigns[band] = text_to_array(callsigns)

    def get_monitored_callsigns(self, band):
        with self.lock:
            return self._monitored_callsigns.get(band, set())

    def set_monitored_callsigns(self, band, callsigns):
        with self.lock:
            self._monitored_callsigns[band] = text_to_array(callsigns)            

    def get_excluded_callsigns(self, band):
        with self.lock:
            return self._excluded_callsigns.get(band, set())

    def set_excluded_callsigns(self, band, callsigns):
        with self.lock:
            self._excluded_callsigns[band] = text_to_array(callsigns)                        

    def get_monitored_cq_zones(self, band):
        with self.lock:
            return self._monitored_cq_zones.get(band, set())

    def set_monitored_cq_zones(self, band, callsigns):
        with self.lock:
            self._monitored_cq_zones[band] = text_to_array(callsigns)               