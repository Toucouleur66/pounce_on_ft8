import threading

from utils import text_to_array

class MonitoringSettings:
    def __init__(self):
        self.lock                   = threading.Lock()

        self._monitored_callsigns   = set()
        self._wanted_callsigns      = set()
        self._excluded_callsigns    = set()
        self._monitored_cq_zones    = set()

    def get_monitored_callsigns(self):
        with self.lock:
            return self._monitored_callsigns

    def set_monitored_callsigns(self, callsigns):
        with self.lock:
            self._monitored_callsigns = text_to_array(callsigns)

    def get_wanted_callsigns(self):
        with self.lock:
            return self._wanted_callsigns

    def set_wanted_callsigns(self, callsigns):
        with self.lock:
            self._wanted_callsigns = text_to_array(callsigns)

    def get_excluded_callsigns(self):
        with self.lock:
            return self._excluded_callsigns

    def set_excluded_callsigns(self, callsigns):
        with self.lock:
            self._excluded_callsigns = text_to_array(callsigns)

    def get_monitored_cq_zones(self):
        with self.lock:
            return self._monitored_cq_zones

    def set_monitored_cq_zones(self, cq_zones):
        with self.lock:
            self._monitored_cq_zones = text_to_array(cq_zones)
