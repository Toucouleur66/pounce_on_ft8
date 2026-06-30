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
    def __init__(self, adif_file_paths, adif_worked_callsigns_file):
        self.adif_file_paths            = adif_file_paths if adif_file_paths else []
        self.adif_worked_callsigns_file = adif_worked_callsigns_file

        log.debug("ADIF monitor initialized with files: \n\t%s,\n\t%s", self.adif_file_paths, self.adif_worked_callsigns_file)

        # Get unique file paths to avoid duplicate processing
        self.unique_file_paths = []
        seen_paths = set()
        
        # Add all ADIF file paths
        all_file_paths = list(self.adif_file_paths) if self.adif_file_paths else []
        if adif_worked_callsigns_file:
            all_file_paths.append(adif_worked_callsigns_file)
        
        for file_path in all_file_paths:
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
        self.ignore_sat_entries = False
        self._running           = False
        self.monitoring_thread  = threading.Thread(target=self.monitor_adif_files, daemon=True)
        self.adif_processor     = AdifProcessor()
        self.pending_tasks      = {}
        self.processing_callbacks = []

    def start(self):
        self._running = True
        self.adif_processor.start()
        self.monitoring_thread.start()

    def register_lookup(self, lookup):
        self._lookup = lookup

    def set_ignore_sat_entries(self, ignore_sat_entries):
        new_value = bool(ignore_sat_entries)
        # When the SAT filter toggles, force a full rescan of every monitored
        # ADIF file so the change takes effect on already-parsed data (a full
        # rescan replaces the per-file data instead of merging).
        if new_value != self.ignore_sat_entries:
            self.ignore_sat_entries = new_value
            if self._running:
                self.force_full_rescan_all()

    def force_full_rescan_all(self):
        for abs_path in self.adif_last_size:
            self.adif_last_size[abs_path] = None
        log.info("Full rescan scheduled for all ADIF files (SAT filter changed)")

    def update_file_paths(self, updated_adif_file_paths):
        log.info(f"Updating ADIF file paths from {self.adif_file_paths} to {updated_adif_file_paths}")

        if not updated_adif_file_paths:
            updated_adif_file_paths = []

        if self.adif_file_paths == updated_adif_file_paths:
            log.info("ADIF file paths unchanged, no update needed")
            return False

        self.adif_file_paths = updated_adif_file_paths
        
        seen_paths = set()
        self.unique_file_paths = []
        
        all_file_paths = list(self.adif_file_paths) if self.adif_file_paths else []
        if self.adif_worked_callsigns_file:
            all_file_paths.append(self.adif_worked_callsigns_file)
        
        for file_path in all_file_paths:
            if file_path:
                abs_path = os.path.abspath(file_path)
                if abs_path not in seen_paths:
                    seen_paths.add(abs_path)
                    self.unique_file_paths.append(abs_path)
        
        new_paths = set(self.unique_file_paths)
        old_paths = set(self.adif_last_mtime.keys())
        
        # Handle new files - add them and queue for immediate processing
        added_paths = new_paths - old_paths
        for path in added_paths:
            log.info(f"Added new ADIF file for monitoring: {path}")
            
            # Queue new file for immediate processing if it exists
            if os.path.exists(path):
                try:
                    # Set timestamps BEFORE queuing to prevent duplicate processing
                    current_mtime = os.path.getmtime(path)
                    current_size = os.path.getsize(path)
                    self.adif_last_mtime[path] = current_mtime
                    self.adif_last_size[path] = current_size
                    
                    log.info(f"Queuing new file for immediate processing: {path}")
                    task_id = self.adif_processor.process_file(
                        path, 0, self._lookup, max_lines=None,
                        ignore_sat_entries=self.ignore_sat_entries
                    )
                    
                    if task_id:
                        if not self.pending_tasks:
                            self.notify_processing_callbacks({'type': 'adif_processing_started'})
                        
                        self.pending_tasks[task_id] = {
                            'file_path': path,
                            'current_size': current_size,
                            'incremental': False
                        }
                        
                except Exception as e:
                    log.error(f"Error queuing new file {path} for processing: {e}")
            else:
                # File doesn't exist yet, set None to allow future processing
                self.adif_last_mtime[path] = None
                self.adif_last_size[path] = None
        
        # Handle removed files - clean up all associated data
        removed_paths = old_paths - new_paths
        for path in removed_paths:
            self.adif_last_mtime.pop(path, None)
            self.adif_last_size.pop(path, None)
            # Important: Remove the file's data from the merged dataset
            if path in self.adif_data_by_file:
                del self.adif_data_by_file[path]
                log.info(f"Removed ADIF data for file: {path}")
            
            # Cancel any pending tasks for this file
            tasks_to_remove = []
            for task_id, task_info in self.pending_tasks.items():
                if task_info.get('file_path') == path:
                    tasks_to_remove.append(task_id)
                    log.info(f"Cancelled pending task for removed file: {path}")
            
            for task_id in tasks_to_remove:
                self.pending_tasks.pop(task_id, None)
            
            log.info(f"Removed ADIF file from monitoring: {path}")
        
        # If files were added or removed, refresh the callbacks to update UI
        if added_paths or removed_paths:
            log.info("ADIF files were added or removed, refreshing data")
            self.notify_callbacks()
            
            # Log comprehensive statistics after file path changes
            # self._log_adif_statistics()
        
        return True

    def _log_adif_statistics(self):
        try:
            from utils import AMATEUR_BANDS
            
            merged_data = self.get_adif_data()
            report_lines = []
            report_lines.append("Adif Summary:")
            
            # Get sorted amateur bands (by frequency order)
            sorted_bands = sorted(AMATEUR_BANDS.keys(), key=lambda x: AMATEUR_BANDS[x][0])
            
            # WKB4 Statistics Table
            wkb4_data = merged_data.get('wkb4', {})
            if wkb4_data:
                report_lines.append("")
                report_lines.append("Worked Before (Wkb4)")
                
                # Table header
                header = "Year".ljust(6)
                for band in sorted_bands:
                    header += band.rjust(6)
                header += "Total".rjust(8)
                report_lines.append("-" * len(header))
                report_lines.append(header)
                report_lines.append("-" * len(header))
                
                # Table rows by year
                total_by_band = {band: 0 for band in sorted_bands}
                grand_total = 0
                
                for year in sorted(wkb4_data.keys()):
                    row = year.ljust(6)
                    year_total = 0
                    for band in sorted_bands:
                        count = len(wkb4_data[year].get(band, set()))
                        row += str(count).rjust(6) if count > 0 else "".rjust(6)
                        total_by_band[band] += count
                        year_total += count
                    row += str(year_total).rjust(8)
                    grand_total += year_total
                    report_lines.append(row)
                
                # Total row
                total_row = "Total".ljust(6)
                for band in sorted_bands:
                    count = total_by_band[band]
                    total_row += str(count).rjust(6) if count > 0 else "".rjust(6)
                total_row += str(grand_total).rjust(8)
                report_lines.append("-" * len(header))
                report_lines.append(total_row)
            else:
                report_lines.append("")
                report_lines.append("Worked Before (Wkb4): No data available")

            # Entity Statistics Table
            entity_data = merged_data.get('entity', {})
            if entity_data:
                report_lines.append("")
                report_lines.append("Entities:")
                
                # Table header
                header = "Year".ljust(6)
                for band in sorted_bands:
                    header += band.rjust(6)
                header += "Total".rjust(8)
                report_lines.append("-" * len(header))
                report_lines.append(header)
                report_lines.append("-" * len(header))
                
                # Table rows by year
                total_by_band = {band: 0 for band in sorted_bands}
                grand_total = 0
                
                for year in sorted(entity_data.keys()):
                    row = year.ljust(6)
                    year_total = 0
                    for band in sorted_bands:
                        count = len(entity_data[year].get(band, set()))
                        row += str(count).rjust(6) if count > 0 else "".rjust(6)
                        total_by_band[band] += count
                        year_total += count
                    row += str(year_total).rjust(8)
                    grand_total += year_total
                    report_lines.append(row)
                
                # Total row
                total_row = "Total".ljust(6)
                for band in sorted_bands:
                    count = total_by_band[band]
                    total_row += str(count).rjust(6) if count > 0 else "".rjust(6)
                total_row += str(grand_total).rjust(8)
                report_lines.append("-" * len(header))
                report_lines.append(total_row)
            else:
                report_lines.append("")
                report_lines.append("Entities: No data available")

            # Grid Statistics Table (single row)
            grid_data = merged_data.get('grid', {})
            if grid_data:
                report_lines.append("")
                report_lines.append("Grids:")
                
                # Table header
                header = "".ljust(6)  # No year column for grids
                for band in sorted_bands:
                    header += band.rjust(6)
                header += "Total".rjust(8)
                report_lines.append("-" * len(header))
                report_lines.append(header)
                report_lines.append("-" * len(header))
                
                # Single row with grid counts
                row = "Grids".ljust(6)
                total_grids = 0
                for band in sorted_bands:
                    count = len(grid_data.get(band, set()))
                    row += str(count).rjust(6) if count > 0 else "".rjust(6)
                    total_grids += count
                row += str(total_grids).rjust(8)
                report_lines.append(row)
            else:
                report_lines.append("")
                report_lines.append("Grids: No data available")

            # File summary
            report_lines.append("")
            report_lines.append(f"Monitored Files: {len(self.unique_file_paths)}")
            for i, file_path in enumerate(self.unique_file_paths, 1):
                file_name = os.path.basename(file_path)
                status = "✓" if file_path in self.adif_data_by_file else "⏳"
                report_lines.append(f"{i:2d}. {status} {file_name}")
            
            # Output as a single log message with proper formatting
            log.info("\n".join(report_lines))
            
        except Exception as e:
            log.error(f"Error generating ADIF statistics: {e}")

    def log_statistics(self):
        self._log_adif_statistics()

    def force_full_rescan(self, file_path):
        abs_path = os.path.abspath(file_path)
        if abs_path in self.adif_last_size:
            self.adif_last_size[abs_path] = None
            log.info(f"Full rescan scheduled for: {abs_path}")

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
    
    def register_processing_callback(self, callback):
        self.processing_callbacks.append(callback)
    
    def notify_processing_callbacks(self, message):
        for callback in self.processing_callbacks:
            try:
                callback(message)
            except Exception as e:
                log.error(f"Error in processing callback ({callback}): {e}\n{traceback.format_exc()}")
    
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
            file_check_counter = 0
            while self._running:    
                # Check file changes every 5 seconds (50 * 0.1s)
                if file_check_counter % 50 == 0:
                    self.check_file_changes()
                
                # Check processing results and progress every 100ms for smooth updates
                self.check_processing_results()
                self.check_processing_progress()
                
                file_check_counter += 1
                if self._running: 
                    self.stop_event.wait(0.1)  # Check every 100ms for smoother progress updates
        except Exception as e:
            log.error(f"Critical error in ADIF monitoring thread: {e}\n{traceback.format_exc()}")
        finally:
            log.info("ADIF monitoring thread stopped")

    def merge_adif_data(self, existing_data, incremental_data):
        """
            Merge incremental ADIF data with existing data
        """
        merged_data = copy.deepcopy(existing_data)
        
        # 'grid' and 'entity_qsl' store lists of QSO dicts; 'wkb4'/'entity' store sets
        list_data_types = ('grid', 'entity_qsl')

        for data_type in ['wkb4', 'entity', 'entity_qsl', 'grid']:
            if data_type in incremental_data and incremental_data[data_type]:
                if data_type not in merged_data:
                    merged_data[data_type] = {}

                for key1, value1 in incremental_data[data_type].items():
                    if key1 not in merged_data[data_type]:
                        merged_data[data_type][key1] = {}

                    for key2, value2 in value1.items():
                        if key2 not in merged_data[data_type][key1]:
                            if data_type in list_data_types:
                                merged_data[data_type][key1][key2] = []
                            else:
                                merged_data[data_type][key1][key2] = set()

                        if data_type in list_data_types and isinstance(value2, list):
                            merged_data[data_type][key1][key2].extend(value2)
                        elif isinstance(value2, set):
                            merged_data[data_type][key1][key2].update(value2)
                        else:
                            # Handle backward compatibility
                            if data_type in list_data_types:
                                merged_data[data_type][key1][key2].extend(value2 if isinstance(value2, list) else [value2])
                            else:
                                merged_data[data_type][key1][key2].add(value2)
        
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
                            log.debug(f"File changed while processing, skipping: {file_path}")
                            continue
                        
                        log.debug(f"File changed, queuing for processing: {file_path}")
                        self.adif_last_mtime[file_path] = current_mtime
                        
                        if (last_size is not None and 
                            current_size > last_size and 
                            file_path in self.adif_data_by_file):
                            task_id = self.adif_processor.process_file(
                                file_path, last_size, self._lookup, max_lines=10,
                                ignore_sat_entries=self.ignore_sat_entries
                            )
                        else:
                            task_id = self.adif_processor.process_file(
                                file_path, 0, self._lookup, max_lines=None,
                                ignore_sat_entries=self.ignore_sat_entries
                            )
                        
                        if task_id:
                            if not self.pending_tasks:
                                self.notify_processing_callbacks({'type': 'adif_processing_started'})
                            
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
            if not self.pending_tasks:
                self.notify_processing_callbacks({'type': 'adif_processing_finished'})

                self._lookup.force_cache_save()
                # Show statistics after processing is complete
                # self._log_adif_statistics()
    
    def check_processing_progress(self):
        """
            Check for progress updates from ADIF processor
        """
        while True:
            progress = self.adif_processor.get_progress()
            if progress is None:
                break
            
            # Notify callbacks with progress information
            self.notify_processing_callbacks({
                'type': 'adif_processing_progress',
                'task_id': progress['task_id'],
                'processed': progress['processed'],
                'total': progress['total'],
                'file_path': progress['file_path']
            })

    def get_adif_data(self):
        merged_data = {
            'wkb4'      : defaultdict(lambda: defaultdict(set)),
            'entity'    : defaultdict(lambda: defaultdict(set)),
            'entity_qsl': defaultdict(lambda: defaultdict(list)),
            'grid'      : defaultdict(lambda: defaultdict(list)),
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

            entity_qsl_data = data.get('entity_qsl')

            if entity_qsl_data:
                for band, entities in entity_qsl_data.items():
                    if entities is None:
                        continue
                    for entity_code, qso_data in entities.items():
                        merged_data['entity_qsl'][band][entity_code].extend(qso_data)

            grid_data = data.get('grid')
            if grid_data:
                for band, grids in grid_data.items():
                    if grids is None:
                        continue
                    for grid, qso_data in grids.items():
                        merged_data['grid'][band][grid].extend(qso_data)
        
        return merged_data
    