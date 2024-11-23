import threading

class MonitoringSettings:
    def __init__(self):
        self.lock = threading.Lock()
        self._monitored_callsigns = set()
        self._wanted_callsigns = set()
        self._excluded_callsigns = set()
        self._monitored_cq_zones = set()

    def get_monitored_callsigns(self):
        with self.lock:
            return self._monitored_callsigns.copy()

    def set_monitored_callsigns(self, callsigns):
        with self.lock:
            self._monitored_callsigns = set(callsigns)

    def get_wanted_callsigns(self):
        with self.lock:
            return self._wanted_callsigns.copy()

    def set_wanted_callsigns(self, callsigns):
        with self.lock:
            self._wanted_callsigns = set(callsigns)

    def get_excluded_callsigns(self):
        with self.lock:
            return self._excluded_callsigns.copy()

    def set_excluded_callsigns(self, callsigns):
        with self.lock:
            self._excluded_callsigns = set(callsigns)

    def get_monitored_cq_zones(self):
        with self.lock:
            return self._monitored_cq_zones.copy()

    def set_monitored_cq_zones(self, cq_zones):
        with self.lock:
            self._monitored_cq_zones = set(cq_zones)
