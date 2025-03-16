# monitoring_setting.py

import threading

from utils import text_to_array, int_to_array

class MonitoringSettings:
    def __init__(self):
        self.lock                   = threading.Lock()

        self._monitored_callsigns   = set()
        self._wanted_callsigns      = set()
        self._excluded_callsigns    = set()
        self._monitored_cq_zones    = set()
        self._excluded_cq_zones     = set()
        self._operating_band        = None

    def get_monitored_callsigns(self):
        with self.lock:
            return sorted(self._monitored_callsigns)

    def set_monitored_callsigns(self, callsigns):
        with self.lock:
            self._monitored_callsigns = text_to_array(callsigns)

    def get_wanted_callsigns(self):
        with self.lock:
            return sorted(self._wanted_callsigns)

    def set_wanted_callsigns(self, callsigns):
        with self.lock:
            self._wanted_callsigns = text_to_array(callsigns)

    def get_excluded_callsigns(self):
        with self.lock:
            return sorted(self._excluded_callsigns)
        
    def get_excluded_cq_zones(self):
        with self.lock:
            return sorted(self._excluded_cq_zones)     

    def get_operating_band(self):
        with self.lock:
            return self._operating_band               

    def set_excluded_callsigns(self, callsigns):
        with self.lock:
            self._excluded_callsigns = text_to_array(callsigns)

    def get_monitored_cq_zones(self):
        with self.lock:
            return sorted(self._monitored_cq_zones)

    def set_monitored_cq_zones(self, cq_zones):
        with self.lock:
            self._monitored_cq_zones = int_to_array(cq_zones)

    def set_excluded_cq_zones(self, cq_zones):
        with self.lock:
            self._excluded_cq_zones = int_to_array(cq_zones)

    def set_operating_band(self, band):
        with self.lock:
            self._operating_band = band