# tiles_manager.py

import requests
import os
import time
import threading

from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import pyqtSignal, QThreadPool, QRunnable, QObject

class TileCache:
    def __init__(self, cache_dir="map_cache"):
        self.cache_dir = cache_dir
        self.ensure_cache_dir()
    
    def ensure_cache_dir(self):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def get_cache_path(self, zoom, x, y):
        zoom_dir = os.path.join(self.cache_dir, str(zoom))
        if not os.path.exists(zoom_dir):
            os.makedirs(zoom_dir)
        return os.path.join(zoom_dir, f"{x}_{y}.png")
    
    def is_cached(self, zoom, x, y):
        cache_path = self.get_cache_path(zoom, x, y)
        return os.path.exists(cache_path)
    
    def get_cached_tile(self, zoom, x, y):
        cache_path = self.get_cache_path(zoom, x, y)
        if os.path.exists(cache_path):
            pixmap = QPixmap(cache_path)
            if not pixmap.isNull():
                return pixmap
        return None
    
    def save_tile(self, zoom, x, y, data):
        cache_path = self.get_cache_path(zoom, x, y)
        try:
            with open(cache_path, 'wb') as f:
                f.write(data)
        except Exception as e:
            print(f"Error saving tile to cache: {e}")
    
    def clean_old_tiles(self, max_age_days=30):
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60
        
        for root, dirs, files in os.walk(self.cache_dir):
            for file in files:
                if file.endswith('.png'):
                    file_path = os.path.join(root, file)
                    try:
                        file_age = current_time - os.path.getmtime(file_path)
                        if file_age > max_age_seconds:
                            os.remove(file_path)
                    except Exception as e:
                        print(f"Error cleaning cache file {file_path}: {e}")

class TileDownloadWorker(QRunnable):
    def __init__(self, zoom, x, y, tile_cache, signal_emitter):
        super().__init__()
        self.zoom = zoom
        self.x = x
        self.y = y
        self.tile_cache = tile_cache
        self.signal_emitter = signal_emitter
        
    def run(self):
        try:
            url = f"https://tile.openstreetmap.org/{self.zoom}/{self.x}/{self.y}.png"
            headers = {'User-Agent': 'PyQt6 Map Viewer'}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                self.tile_cache.save_tile(self.zoom, self.x, self.y, response.content)
                
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                if not pixmap.isNull():
                    self.signal_emitter.tile_downloaded.emit(self.zoom, self.x, self.y, pixmap)
        except Exception as e:
            print(f"Error downloading tile {self.zoom}/{self.x}/{self.y}: {e}")

class TileDownloadSignals(QObject):
    tile_downloaded = pyqtSignal(int, int, int, QPixmap)

class TileDownloader(QObject):
    def __init__(self, tile_cache, max_workers=6):
        super().__init__()
        self.tile_cache = tile_cache
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(max_workers)
        self.signals = TileDownloadSignals()
        self.downloading_tiles = set()
        self.mutex = threading.Lock()
        
        self.signals.tile_downloaded.connect(self._on_tile_completed)
        
    @property
    def tile_downloaded(self):
        return self.signals.tile_downloaded
        
    def add_tile(self, zoom, x, y):
        tile_key = (zoom, x, y)
        with self.mutex:
            if tile_key not in self.downloading_tiles:
                self.downloading_tiles.add(tile_key)
                worker = TileDownloadWorker(zoom, x, y, self.tile_cache, self.signals)
                self.thread_pool.start(worker)
    
    def _on_tile_completed(self, zoom, x, y, pixmap):
        with self.mutex:
            tile_key = (zoom, x, y)
            if tile_key in self.downloading_tiles:
                self.downloading_tiles.remove(tile_key)
    
    def stop(self):
        self.thread_pool.waitForDone(5000)
