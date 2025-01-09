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

        self.adif_file_path = adif_file_path
        self.adif_worked_callsigns_file = adif_worked_callsigns_file

        self.adif_last_mtime = {adif_file_path: None, adif_worked_callsigns_file: None}
        self.adif_data = defaultdict(lambda: defaultdict(set))

        self._running = False

        self.callbacks = []
        self.stop_event = Event()

        self.monitoring_thread = threading.Thread(target=self.monitor_adif_files, daemon=True)

    def start(self):
        self._running = True
        self.monitoring_thread.start()

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
                            new_data, processing_time = parse_adif(file_path)

                            self.merge_adif_data(new_data)
                            
                            log.info(f"Processed ({processing_time:.4f}s): {file_path}")
                    except Exception as e:
                        log.error(f"Error processing {file_path}: {e}")

            self.stop_event.wait(7.5)

    def merge_adif_data(self, new_data):
        for year, bands in new_data.items():
            for band, calls in bands.items():
                self.adif_data[year][band].update(calls)

        self.notify_callbacks()                

    def get_adif_data(self):
        return self.adif_data                
