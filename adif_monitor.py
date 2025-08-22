import os
import threading
import copy

import inspect
import traceback

from collections import defaultdict
from threading import Event

from utils import parse_adif_incremental
from logger import get_logger
from adif_processor import AdifProcessor

log     = get_logger(__name__)

class AdifMonitor:
    def __init__(self, adif_file_path, adif_worked_callsigns_file):
        self.adif_file_path             = adif_file_path
        self.adif_worked_callsigns_file = adif_worked_callsigns_file

        log.error("ADIF monitor initialized with files: \n\t%s,\n\t%s", self.adif_file_path, self.adif_worked_callsigns_file)

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
        self.adif_last_size = {path: None for path in self.unique_file_paths}

        self.adif_data_by_file   = {}
        self.callbacks          = []
        self.stop_event         = Event()
        self.data_lock          = threading.RLock()

        self._lookup            = False
        self._running           = False
        self.monitoring_thread  = threading.Thread(target=self.monitor_adif_files, daemon=True)
        self.adif_processor     = AdifProcessor()
        self.pending_tasks      = {}

    def start(self):
        self._running = True
        self.adif_processor.start()
        self.monitoring_thread.start()

    def register_lookup(self, lookup):
        self._lookup = lookup

    def stop(self):
        log.info("Stopping ADIF monitor")
        self._running = False
        self.stop_event.set()
        
        self.adif_processor.stop()
        
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
                self.check_file_changes()
                self.check_processing_results()
                if self._running: 
                    self.stop_event.wait(5)
        except Exception as e:
            log.error(f"Critical error in ADIF monitoring thread: {e}\n{traceback.format_exc()}")
        finally:
            log.info("ADIF monitoring thread stopped")

    def merge_adif_data(self, existing_data, incremental_data):
        """Merge incremental ADIF data with existing data"""
        merged_data = copy.deepcopy(existing_data)
        
        for data_type in ['wkb4', 'entity', 'grid']:
            if data_type in incremental_data and incremental_data[data_type]:
                if data_type not in merged_data:
                    merged_data[data_type] = {}
                
                for key1, value1 in incremental_data[data_type].items():
                    if key1 not in merged_data[data_type]:
                        merged_data[data_type][key1] = {}
                    
                    for key2, value2 in value1.items():
                        if key2 not in merged_data[data_type][key1]:
                            merged_data[data_type][key1][key2] = set()
                        merged_data[data_type][key1][key2].update(value2)
        
        return merged_data

    def check_file_changes(self):
        for file_path in self.unique_file_paths:
            if os.path.exists(file_path):
                try:
                    current_mtime = os.path.getmtime(file_path)
                    current_size = os.path.getsize(file_path)
                    last_mtime = self.adif_last_mtime[file_path]
                    last_size = self.adif_last_size[file_path]
                    
                    if last_mtime is None or current_mtime != last_mtime:
                        if file_path in self.pending_tasks:
                            log.info(f"File changed while processing, skipping: {file_path}")
                            continue
                        
                        log.info(f"File changed, queuing for processing: {file_path}")
                        self.adif_last_mtime[file_path] = current_mtime
                        
                        if (last_size is not None and 
                            current_size > last_size and 
                            file_path in self.adif_data_by_file):
                            task_id = self.adif_processor.process_file(
                                file_path, last_size, self._lookup, max_lines=10
                            )
                        else:
                            task_id = self.adif_processor.process_file(
                                file_path, 0, self._lookup, max_lines=None
                            )
                        
                        if task_id:
                            self.pending_tasks[task_id] = {
                                'file_path': file_path,
                                'current_size': current_size,
                                'incremental': last_size is not None and current_size > last_size and file_path in self.adif_data_by_file
                            }
                        
                except Exception as e:
                    log.error(f"Error checking file changes for {file_path}: {e}\n{traceback.format_exc()}")
    
    def check_processing_results(self):
        files_processed = []
        
        while True:
            result = self.adif_processor.get_result()
            if result is None:
                break
            
            task_id = result['task_id']
            if task_id not in self.pending_tasks:
                continue
                
            task_info = self.pending_tasks.pop(task_id)
            file_path = task_info['file_path']
            
            if result['success']:
                try:
                    with self.data_lock:
                        if task_info['incremental']:
                            existing_data = self.adif_data_by_file[file_path]
                            self.adif_data_by_file[file_path] = self.merge_adif_data(
                                existing_data, result['parsed_data']
                            )
                            log.info(f"Processed incremental ({result['processing_time']:.4f}s): {file_path}")
                        else:
                            self.adif_data_by_file[file_path] = result['parsed_data']
                            log.info(f"Processed full file ({result['processing_time']:.4f}s): {file_path}")
                    
                    self.adif_last_size[file_path] = task_info['current_size']
                    files_processed.append(file_path)
                    
                except Exception as e:
                    log.error(f"Error updating ADIF data for {file_path}: {e}\n{traceback.format_exc()}")
            else:
                log.error(f"ADIF processing failed for {file_path}: {result['error']}")
        
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
    