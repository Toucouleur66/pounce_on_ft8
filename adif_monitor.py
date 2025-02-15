import os
import time
import threading

from collections import defaultdict
from threading import Event

from utils import parse_adif
from logger import get_logger

log     = get_logger(__name__)

class AdifMonitor:
    def __init__(self, adif_file_path, adif_worked_callsigns_file):

        self.adif_file_path             = adif_file_path
        self.adif_worked_callsigns_file = adif_worked_callsigns_file

        self.adif_last_mtime = {
            adif_file_path: None,
            adif_worked_callsigns_file: None
        }

        self.adif_wkb4_data   = defaultdict(lambda: defaultdict(set))
        self.adif_entity_data = defaultdict(lambda: defaultdict(set))

        self._lookup  = False
        self._running = False

        self.callbacks  = []
        self.stop_event = Event()

        self.monitoring_thread = threading.Thread(target=self.monitor_adif_files, daemon=True)

    def start(self):
        self._running = True
        self.monitoring_thread.start()

    def register_lookup(self, lookup):
        self._lookup = lookup

    def stop(self):
        self._running = False
        self.stop_event.set()
        self.monitoring_thread.join()

    def register_callback(self, callback):
        self.callbacks.append(callback)
    
    def notify_callbacks(self):
        for callback in self.callbacks:
            try:
                callback(self.adif_data)
            except Exception as e:
                log.error(f"Error in callback {callback}: {e}")  

    def monitor_adif_files(self):
        while self._running:    
            for file_path in [
                self.adif_file_path,
                self.adif_worked_callsigns_file
            ]:
                if os.path.exists(file_path):
                    try:
                        current_mtime = os.path.getmtime(file_path)
                        if self.adif_last_mtime[file_path] is None or current_mtime != self.adif_last_mtime[file_path]:
                            self.adif_last_mtime[file_path] = current_mtime
                            processing_time, parsed_wkb4_data, parsed_entity_data = parse_adif(file_path, self._lookup)
                            self.merge_adif_data(parsed_wkb4_data, parsed_entity_data)
                            
                            log.info(f"Processed ({processing_time:.4f}s):{file_path}")                            
                            
                    except Exception as e:
                        log.error(f"Error processing {file_path}: {e}")

            self.stop_event.wait(7.5)

    def merge_adif_data(self, parsed_wkb4_data, parsed_entity_data = None):
        for year, bands in parsed_wkb4_data.items():
            for band, calls in bands.items():
                self.adif_wkb4_data[year][band].update(calls)

        if parsed_entity_data:
            for year, bands in parsed_entity_data.items():
                for band, entities in bands.items():
                    self.adif_entity_data[year][band].update(entities)

        self.notify_callbacks()                

    def get_adif_data(self):
        return {
            'wkb4': self.adif_wkb4_data,
            'entity': self.adif_entity_data
        }
