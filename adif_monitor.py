import os
import threading
import copy

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

        # Get unique file paths to avoid duplicate processing
        self.unique_file_paths = []
        seen_paths = set()
        
        for file_path in [adif_file_path, adif_worked_callsigns_file]:
            if file_path:
                abs_path = os.path.abspath(file_path)
                if abs_path not in seen_paths:
                    seen_paths.add(abs_path)
                    self.unique_file_paths.append(abs_path)

        self.adif_last_mtime = {path: None for path in self.unique_file_paths}

        self.adif_data_by_file   = {}
        self.callbacks          = []
        self.stop_event         = Event()
        self.data_lock          = threading.RLock()

        self._lookup            = False
        self._running           = False
        self.monitoring_thread  = threading.Thread(target=self.monitor_adif_files, daemon=True)

    def start(self):
        self._running = True
        self.monitoring_thread.start()

    def register_lookup(self, lookup):
        self._lookup = lookup

    def stop(self):
        log.info("Stopping ADIF monitor")
        self._running = False
        self.stop_event.set()
        
        if self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
            if self.monitoring_thread.is_alive():
                log.warning("ADIF monitoring thread did not stop gracefully")
        
        log.info("ADIF monitor stopped")

    def register_callback(self, callback):
        self.callbacks.append(callback)
    
    def notify_callbacks(self):
        try:
            with self.data_lock:
                data_copy = copy.deepcopy(self.get_adif_data())
            
            for callback in self.callbacks:
                try:
                    callback(data_copy)
                except Exception as e:
                    log.error(f"Error in callback ({callback}): {e}\n{traceback.format_exc()}")
                    
        except Exception as e:
            log.error(f"Critical error in notify_callbacks: {e}\n{traceback.format_exc()}")  

    def monitor_adif_files(self):
        log.info("ADIF monitoring thread started")
        try:
            while self._running:    
                self.process_adif_file()
                if self._running: 
                    self.stop_event.wait(15)
        except Exception as e:
            log.error(f"Critical error in ADIF monitoring thread: {e}\n{traceback.format_exc()}")
        finally:
            log.info("ADIF monitoring thread stopped")

    def process_adif_file(self):
        files_processed = []
        
        for file_path in self.unique_file_paths:
            if os.path.exists(file_path):
                try:
                    current_mtime = os.path.getmtime(file_path)
                    last_mtime = self.adif_last_mtime[file_path]                
                    
                    if last_mtime is None or current_mtime != last_mtime:
                        log.info(f"Start processing: {file_path}")
                        self.adif_last_mtime[file_path] = current_mtime
                        processing_time, parsed_data = parse_adif(file_path, self._lookup)
                        
                        with self.data_lock:
                            self.adif_data_by_file[file_path] = parsed_data
                        
                        log.info(f"Processed ({processing_time:.4f}s): {file_path}")
                        files_processed.append(file_path)
                except Exception as e:
                    log.error(f"Error processing {file_path}: {e}\n{traceback.format_exc()}")
        
        if files_processed:
            self.notify_callbacks()

    def get_adif_data(self):
        merged_data = {
            'wkb4'  : defaultdict(lambda: defaultdict(set)),
            'entity': defaultdict(lambda: defaultdict(set)),
            'grid'  : defaultdict(lambda: defaultdict(set)),
        }
        
        # Create a snapshot to avoid iterator invalidation
        data_snapshot = list(self.adif_data_by_file.values())
        for data in data_snapshot:
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
            
            grid_data = data.get('grid')
            if grid_data:
                for band, grids in grid_data.items():
                    if grids is None:
                        continue
                    for grid, calls in grids.items():
                        merged_data['grid'][band][grid].update(calls)
        
        return merged_data
    