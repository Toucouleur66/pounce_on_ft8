import os
import time
import multiprocessing
import queue
import os
import time
import re

from multiprocessing import Process, Queue, Event

from collections import defaultdict
from utils import parse_adif_record, is_valid_grid_format

from logger import get_logger

log = get_logger(__name__)

class AdifProcessor:
    def __init__(self):
        self.process = None
        self.task_queue = Queue()
        self.result_queue = Queue()
        self.stop_event = Event()
        self._running = False
    
    def start(self):
        if not self._running:
            self._running = True
            self.process = Process(
                target=self._worker_process,
                args=(self.task_queue, self.result_queue, self.stop_event),
                daemon=True
            )
            self.process.start()
            log.info("ADIF processor started")
    
    def stop(self):
        if self._running:
            self._running = False
            self.stop_event.set()
            
            if self.process and self.process.is_alive():
                self.process.terminate()
                self.process.join(timeout=5)
                if self.process.is_alive():
                    log.warning("ADIF processor did not stop gracefully")
            
            log.info("ADIF processor stopped")
    
    def process_file(self, file_path, last_size, lookup=None, max_lines=10):
        if not self._running:
            return None
            
        task_id = f"{file_path}_{time.time()}"
        task = {
            'id': task_id,
            'file_path': file_path,
            'last_size': last_size,
            'lookup_data': self._serialize_lookup(lookup) if lookup else None,
            'max_lines': max_lines
        }
        
        try:
            self.task_queue.put(task, timeout=1)
            return task_id
        except queue.Full:
            log.warning("Task queue is full, skipping ADIF processing")
            return None
    
    def get_result(self, timeout=0.1):
        try:
            result = self.result_queue.get(timeout=timeout)
            return result
        except queue.Empty:
            return None
    
    def _serialize_lookup(self, lookup):
        if not lookup:
            return None
        
        return {
            'has_lookup': True
        }
    
    @staticmethod
    def _worker_process(task_queue, result_queue, stop_event):
        log.info("ADIF worker process started")
        
        try:
            while not stop_event.is_set():
                try:
                    task = task_queue.get(timeout=1)
                    if task is None:
                        break
                    
                    # log.info(f"Processing ADIF task: {task['id']}")
                    
                    lookup = AdifProcessor._deserialize_lookup(task.get('lookup_data'))
                    
                    processing_time, parsed_data = AdifProcessor._parse_adif_multiprocess(
                        task['file_path'],
                        task['last_size'],
                        lookup=lookup,
                        max_lines=task['max_lines']
                    )
                    
                    result = {
                        'task_id': task['id'],
                        'file_path': task['file_path'],
                        'processing_time': processing_time,
                        'parsed_data': parsed_data,
                        'success': True,
                        'error': None
                    }
                    
                    result_queue.put(result)
                    # log.info(f"Completed ADIF task: {task['id']} in {processing_time:.4f}s")
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    log.error(f"Error processing ADIF task: {e}")
                    error_result = {
                        'task_id': task.get('id', 'unknown'),
                        'file_path': task.get('file_path', 'unknown'),
                        'processing_time': 0,
                        'parsed_data': None,
                        'success': False,
                        'error': str(e)
                    }
                    result_queue.put(error_result)
                    
        except Exception as e:
            log.error(f"Critical error in ADIF worker process: {e}")
        finally:
            log.info("ADIF worker process stopped")
    
    @staticmethod
    def _deserialize_lookup(lookup_data):
        if not lookup_data or not lookup_data.get('has_lookup'):
            return None
        
        try:
            from callsign_lookup import CallsignLookup
            return CallsignLookup()
        except ImportError:
            log.warning("CallsignLookup not available in worker process")
            return None
    
    @staticmethod
    def _parse_adif_multiprocess(file_path, last_size, lookup=None, max_lines=10):
        """Multiprocess-safe version of parse_adif_incremental"""
        start_time = time.time()
        
        parsed_wkb4_data = {}
        parsed_grid_data = {}
        parsed_entity_data = {} if lookup else None
        
        if not os.path.exists(file_path):
            return time.time() - start_time, {
                'wkb4': parsed_wkb4_data,
                'entity': parsed_entity_data,
                'grid': parsed_grid_data
            }
        
        file_size = os.path.getsize(file_path)
        
        if last_size is not None and last_size > 0 and file_size < last_size:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        elif last_size == 0:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        else:
            if file_size == last_size:
                return time.time() - start_time, {
                    'wkb4': parsed_wkb4_data,
                    'entity': parsed_entity_data,
                    'grid': parsed_grid_data
                }
            
            content = ""
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(last_size)
                content = f.read()
                
                if max_lines and content:
                    lines = content.split('\n')
                    if len(lines) > max_lines:
                        content = '\n'.join(lines[-max_lines:])
        
        if content:
            records = re.split(r"<EOR>", content, flags=re.IGNORECASE)
            
            for record in records:
                record = record.strip()
                if record:
                    record = " ".join(record.split())
                    year, band, grid, call, confirmed, info = parse_adif_record(record, lookup)
                    
                    if lookup and year and band and info and info.get('entity_code'):
                        if year not in parsed_entity_data:
                            parsed_entity_data[year] = {}
                        if band not in parsed_entity_data[year]:
                            parsed_entity_data[year][band] = set()
                        parsed_entity_data[year][band].add(info.get('entity_code'))
                    
                    if year and band and call:
                        if year not in parsed_wkb4_data:
                            parsed_wkb4_data[year] = {}
                        if band not in parsed_wkb4_data[year]:
                            parsed_wkb4_data[year][band] = set()
                        parsed_wkb4_data[year][band].add(call)
                    
                    if band and grid and call and is_valid_grid_format(grid):
                        if band not in parsed_grid_data:
                            parsed_grid_data[band] = {}
                        if grid not in parsed_grid_data[band]:
                            parsed_grid_data[band][grid] = set()
                        parsed_grid_data[band][grid].add(call)
        
        processing_time = time.time() - start_time
        
        return processing_time, {
            'wkb4': parsed_wkb4_data,
            'entity': parsed_entity_data,
            'grid': parsed_grid_data
        }