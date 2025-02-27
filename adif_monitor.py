import os
import threading

import inspect
import traceback

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
            adif_file_path              : None,
            adif_worked_callsigns_file  : None
        }

        self.adif_data_by_file   = {}
        self.callbacks          = []
        self.stop_event         = Event()

        self._lookup            = False
        self._running           = False
        self.monitoring_thread  = threading.Thread(target=self.monitor_adif_files, daemon=True)

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
                callback(self.get_adif_data())
            except Exception as e:
                log.error(f"Error in callback {callback}: {e}\n{traceback.format_exc()}")  

    def monitor_adif_files(self):
        while self._running:    
            self.process_adif_file()
            self.stop_event.wait(15)

    def process_adif_file(self):
        for file_path in [self.adif_file_path, self.adif_worked_callsigns_file]:
            if os.path.exists(file_path):
                try:
                    current_mtime = os.path.getmtime(file_path)
                    if self.adif_last_mtime[file_path] is None or current_mtime != self.adif_last_mtime[file_path]:
                        self.adif_last_mtime[file_path] = current_mtime
                        processing_time, parsed_data = parse_adif(file_path, self._lookup)
                        
                        self.adif_data_by_file[file_path] = parsed_data
                        
                        log.info(f"Processed ({processing_time:.4f}s): {file_path}")
                        self.notify_callbacks()                            
                except Exception as e:
                    log.error(f"Error processing {file_path}: {e}\n{traceback.format_exc()}")

    def get_adif_data(self):
        merged_data = {
            'wkb4': defaultdict(lambda: defaultdict(set)),
            'entity': defaultdict(lambda: defaultdict(set)),
        }
        for data in self.adif_data_by_file.values():
            if data is None:
                continue  

            wkb4_data = data.get('wkb4')
            if wkb4_data:
                for year, bands in wkb4_data.items():
                    if bands is None:
                        continue
                    for band, calls in bands.items():
                        merged_data['wkb4'][year][band].update(calls)
            
            entity_data = data.get('entity')
            if entity_data:
                for year, bands in entity_data.items():
                    if bands is None:
                        continue
                    for band, entities in bands.items():
                        merged_data['entity'][year][band].update(entities)
        
        return merged_data