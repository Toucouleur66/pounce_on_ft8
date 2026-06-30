import os
import time
import multiprocessing
import queue
import os
import time
import re

from multiprocessing import Process, Queue, Event

from collections import defaultdict
from utils import process_adif_records

from logger import get_logger

log = get_logger(__name__)

class AdifProcessor:
    def __init__(self):
        self.process = None
        self.task_queue = Queue()
        self.result_queue = Queue()
        self.progress_queue = Queue()
        self.stop_event = Event()
        self._running = False
        
        # Fix for Windows 10 multiprocessing
        if hasattr(multiprocessing, 'set_start_method'):
            try:
                multiprocessing.set_start_method('spawn', force=True)
            except RuntimeError:
                pass
    
    def start(self):
        if not self._running:
            self._running = True

            # Clear the stop flag in case the processor was previously stopped
            # and is now being restarted (e.g. Stop/Start monitoring).
            self.stop_event.clear()

            # Drain any leftover sentinel/task from a previous run so the fresh
            # worker doesn't read a stale None and exit immediately.
            while True:
                try:
                    self.task_queue.get_nowait()
                except queue.Empty:
                    break

            # Additional Windows safety check
            if hasattr(multiprocessing, 'freeze_support'):
                multiprocessing.freeze_support()

            self.process = Process(
                target=self._worker_process,
                args=(self.task_queue, self.result_queue, self.progress_queue, self.stop_event),
                daemon=True
            )
            self.process.start()
            log.info("ADIF processor started")
    
    def stop(self):
        if self._running:
            self._running = False

            # Ask the worker to exit on its own so it can release its DLL
            # handles and clean up its PyInstaller _MEIxxxxx temp dir. A brutal
            # terminate() leaves those handles open, which on Windows produces
            # the "Failed to remove temporary directory" warning during use.
            self.stop_event.set()

            # Also push a sentinel in case the worker is blocked in task_queue.get()
            try:
                self.task_queue.put(None, timeout=1)
            except queue.Full:
                pass

            if self.process and self.process.is_alive():
                # Give the worker a chance to leave its loop and shut down cleanly.
                self.process.join(timeout=5)

                # Only as a last resort, force-kill it.
                if self.process.is_alive():
                    log.warning("ADIF processor did not stop gracefully, terminating")
                    self.process.terminate()
                    self.process.join(timeout=5)
                    if self.process.is_alive():
                        log.warning("ADIF processor still alive after terminate")

            self.process = None
            log.info("ADIF processor stopped")
    
    def process_file(self, file_path, last_size, lookup=None, max_lines=10, ignore_sat_entries=False):
        if not self._running:
            return None

        task_id = f"{file_path}_{time.time()}"
        task = {
            'id': task_id,
            'file_path': file_path,
            'last_size': last_size,
            'needs_lookup': lookup is not None,  # Just flag if lookup is needed
            'max_lines': max_lines,
            'ignore_sat_entries': ignore_sat_entries
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
    
    def get_progress(self, timeout=0.01):
        try:
            progress = self.progress_queue.get(timeout=timeout)
            return progress
        except queue.Empty:
            return None
    
    @staticmethod
    def _get_or_create_lookup(needs_lookup):
        """
            Get or create the shared lookup instance for the worker process
        """
        if not needs_lookup:
            return None
            
        if AdifProcessor._worker_lookup_instance is None:
            try:
                from callsign_lookup import CallsignLookup
                AdifProcessor._worker_lookup_instance = CallsignLookup()
                log.warning("Initialized shared lookup instance in adif processor")
            except ImportError:
                log.error("CallsignLookup not available in adif processor")
                return None
        
        return AdifProcessor._worker_lookup_instance
    
    # Global lookup instance for the worker process - initialized once and reused
    _worker_lookup_instance = None
    

    @staticmethod
    def _worker_process(task_queue, result_queue, progress_queue, stop_event):
        log.info("ADIF worker process started")
        
        try:
            while not stop_event.is_set():
                try:
                    task = task_queue.get(timeout=1)
                    if task is None:
                        break
                    
                    # log.info(f"Processing ADIF task: {task['id']}")
                    
                    lookup = AdifProcessor._get_or_create_lookup(task.get('needs_lookup', False))
                    
                    processing_time, parsed_data = AdifProcessor._parse_adif_multiprocess(
                        task['file_path'],
                        task['last_size'],
                        lookup=lookup,
                        max_lines=task['max_lines'],
                        progress_queue=progress_queue,
                        task_id=task['id'],
                        ignore_sat_entries=task.get('ignore_sat_entries', False)
                    )
                    
                    # Save cache after processing if lookup was used
                    if lookup:
                        try:
                            lookup.force_cache_save()
                        except Exception as e:
                            log.warning(f"Failed to save cache after ADIF processing: {e}")
                    
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
    def _parse_adif_multiprocess(
        file_path,
        last_size,
        lookup=None,
        max_lines=10,
        progress_queue=None,
        task_id=None,
        ignore_sat_entries=False
    ):
        start_time = time.time()
        
        parsed_wkb4_data = {}
        parsed_grid_data = {}
        parsed_entity_data = {} if lookup else None
        parsed_entity_qsl_data = {} if lookup else None

        if not os.path.exists(file_path):
            return time.time() - start_time, {
                'wkb4': parsed_wkb4_data,
                'entity': parsed_entity_data,
                'entity_qsl': parsed_entity_qsl_data,
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
                    'entity_qsl': parsed_entity_qsl_data,
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
            total_records = len([r for r in records if r.strip()])
            
            # Send initial progress - try multiple times to ensure it gets through
            if progress_queue and task_id:
                for attempt in range(3):
                    try:
                        progress_queue.put({
                            'task_id': task_id,
                            'processed': 0,
                            'total': total_records,
                            'file_path': file_path
                        }, timeout=0.1)
                        break 
                    except queue.Full:
                        if attempt == 2:  # Last attempt
                            pass  # Give up
                        else:
                            time.sleep(0.1)
            
            # Create progress callback for the shared function
            processed_count = 0
            def progress_callback(current_count, total_count):
                nonlocal processed_count
                processed_count = current_count
                # Send progress update every 25 records or at the end
                if progress_queue and task_id and (current_count % 25 == 0 or current_count == total_count):
                    try:
                        progress_queue.put({
                            'task_id': task_id,
                            'processed': current_count,
                            'total': total_count,
                            'file_path': file_path
                        }, timeout=0.01)
                    except queue.Full:
                        pass
            
            # Use shared record processing function
            process_adif_records(records, parsed_wkb4_data, parsed_grid_data, parsed_entity_data, lookup, progress_callback, parsed_entity_qsl_data=parsed_entity_qsl_data, ignore_sat_entries=ignore_sat_entries)

        processing_time = time.time() - start_time

        return processing_time, {
            'wkb4': parsed_wkb4_data,
            'entity': parsed_entity_data,
            'entity_qsl': parsed_entity_qsl_data,
            'grid': parsed_grid_data
        }