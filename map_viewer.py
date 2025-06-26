#!/usr/bin/env python3

import sys
import math
import requests
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt6.QtCore import Qt, QPoint, QRect, QTimer, QThread, pyqtSignal, QMutex, QThreadPool, QRunnable, QObject
from PyQt6.QtGui import QPainter, QPixmap, QWheelEvent, QMouseEvent, QKeyEvent
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from io import BytesIO
import os
from urllib.parse import urlparse
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
import threading


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


class MapWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)
        
        self.zoom = 2
        self.center_lat = 0.0
        self.center_lon = 0.0
        self.tile_size = 256
        
        self.dragging = False
        self.last_pan_point = QPoint()
        self.pan_velocity = QPoint(0, 0)
        self.last_pan_time = 0
        self.momentum_decay = 0.92
        self.momentum_threshold = 1.0
        
        self.center_pixel_offset_x = 0.0
        self.center_pixel_offset_y = 0.0
        
        self.show_grid = True
        self.grid_color = Qt.GlobalColor.red
        self.grid_text_color = Qt.GlobalColor.darkRed
        
        self.memory_cache = {}
        self.file_cache = TileCache()
        
        self.file_cache.clean_old_tiles(30)
        
        self.tile_downloader = TileDownloader(self.file_cache, max_workers=8)
        self.tile_downloader.tile_downloaded.connect(self.on_tile_downloaded)
        
        self.setMouseTracking(True)
        
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_animation)
        self.update_timer.start(16)
    
    def deg2num(self, lat_deg, lon_deg, zoom):
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        x = int((lon_deg + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return (x, y)
    
    def num2deg(self, x, y, zoom):
        n = 2.0 ** zoom
        lon_deg = x / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat_deg = math.degrees(lat_rad)
        return (lat_deg, lon_deg)
    
    def get_min_zoom_for_size(self, width, height):
        min_tiles_x = math.ceil(width / self.tile_size)
        min_tiles_y = math.ceil(height / self.tile_size)
        
        min_zoom_x = math.ceil(math.log2(max(1, min_tiles_x)))
        min_zoom_y = math.ceil(math.log2(max(1, min_tiles_y)))
        
        return max(min_zoom_x, min_zoom_y, 1)
    
    def get_tile_key(self, zoom, x, y):
        return f"{zoom}/{x}/{y}"
    
    def on_tile_downloaded(self, zoom, x, y, pixmap):
        key = self.get_tile_key(zoom, x, y)
        self.memory_cache[key] = pixmap
        self.update()
    
    def update_animation(self):
        needs_update = False
        
        if not self.dragging and (abs(self.pan_velocity.x()) > self.momentum_threshold or 
                                  abs(self.pan_velocity.y()) > self.momentum_threshold):
            
            old_lat, old_lon = self.center_lat, self.center_lon
            old_offset_x, old_offset_y = self.center_pixel_offset_x, self.center_pixel_offset_y
            
            self.apply_pan_movement(self.pan_velocity.x(), self.pan_velocity.y())
            
            if (abs(self.center_lat - old_lat) < 0.0001 and 
                abs(self.center_lon - old_lon) < 0.0001 and
                abs(self.center_pixel_offset_x - old_offset_x) < 1 and
                abs(self.center_pixel_offset_y - old_offset_y) < 1):
                self.pan_velocity = QPoint(0, 0)
            else:
                self.pan_velocity = QPoint(
                    int(self.pan_velocity.x() * self.momentum_decay),
                    int(self.pan_velocity.y() * self.momentum_decay)
                )
            needs_update = True
        elif not self.dragging:
            self.pan_velocity = QPoint(0, 0)
        
        if needs_update:
            self.update()
    
    def get_world_bounds_at_zoom(self):
        world_size = 2 ** self.zoom * self.tile_size
        return world_size
    
    def apply_pan_movement(self, delta_x, delta_y):
        self.center_pixel_offset_x += delta_x
        self.center_pixel_offset_y += delta_y
        
        center_tile_x, center_tile_y = self.deg2num(self.center_lat, self.center_lon, self.zoom)
        
        world_size = self.get_world_bounds_at_zoom()
        center_pixel_x = center_tile_x * self.tile_size + self.center_pixel_offset_x
        center_pixel_y = center_tile_y * self.tile_size + self.center_pixel_offset_y
        
        half_width = self.width() / 2
        half_height = self.height() / 2
        
        center_pixel_x = max(half_width, min(world_size - half_width, center_pixel_x))
        center_pixel_y = max(half_height, min(world_size - half_height, center_pixel_y))
        
        new_tile_x = center_pixel_x / self.tile_size
        new_tile_y = center_pixel_y / self.tile_size
        
        self.center_pixel_offset_x = (new_tile_x - int(new_tile_x)) * self.tile_size
        self.center_pixel_offset_y = (new_tile_y - int(new_tile_y)) * self.tile_size
        
        new_lat, new_lon = self.num2deg(new_tile_x, new_tile_y, self.zoom)
        
        self.center_lat = new_lat
        self.center_lon = new_lon
    
    def paintEvent(self, event):
        painter = QPainter(self)
        
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        painter.fillRect(self.rect(), Qt.GlobalColor.lightGray)
        
        widget_width = self.width()
        widget_height = self.height()
        
        exact_x, exact_y = self.deg2num(self.center_lat, self.center_lon, self.zoom)
        center_tile_x = int(exact_x)
        center_tile_y = int(exact_y)
        
        offset_x = (exact_x - center_tile_x) * self.tile_size + self.center_pixel_offset_x
        offset_y = (exact_y - center_tile_y) * self.tile_size + self.center_pixel_offset_y
        
        tiles_x = math.ceil(widget_width / self.tile_size) + 2
        tiles_y = math.ceil(widget_height / self.tile_size) + 2
        
        center_pixel_x = widget_width // 2
        center_pixel_y = widget_height // 2
        
        for dy in range(-tiles_y//2, tiles_y//2 + 1):
            for dx in range(-tiles_x//2, tiles_x//2 + 1):
                tile_x = center_tile_x + dx
                tile_y = center_tile_y + dy
                
                max_tile = 2 ** self.zoom
                if tile_x < 0 or tile_x >= max_tile or tile_y < 0 or tile_y >= max_tile:
                    continue
                
                screen_x = center_pixel_x + (dx * self.tile_size) - int(offset_x)
                screen_y = center_pixel_y + (dy * self.tile_size) - int(offset_y)
                
                key = self.get_tile_key(self.zoom, tile_x, tile_y)
                pixmap = None
                
                if key in self.memory_cache:
                    pixmap = self.memory_cache[key]
                    painter.drawPixmap(screen_x, screen_y, pixmap)
                else:
                    cached_pixmap = self.file_cache.get_cached_tile(self.zoom, tile_x, tile_y)
                    if cached_pixmap:
                        self.memory_cache[key] = cached_pixmap
                        painter.drawPixmap(screen_x, screen_y, cached_pixmap)
                    else:
                        self.tile_downloader.add_tile(self.zoom, tile_x, tile_y)
                        painter.fillRect(screen_x, screen_y, self.tile_size, self.tile_size, 
                                       Qt.GlobalColor.lightGray)
        
        if self.show_grid:
            self.draw_maidenhead_grid(painter)
    
    def wheelEvent(self, event: QWheelEvent):
        mouse_pos = event.position()
        mouse_x = mouse_pos.x()
        mouse_y = mouse_pos.y()
        
        old_zoom = self.zoom
        
        min_zoom = self.get_min_zoom_for_size(self.width(), self.height())
        
        zoom_delta = 1 if event.angleDelta().y() > 0 else -1
        new_zoom = self.zoom + zoom_delta
        
        new_zoom = max(min_zoom, min(16, new_zoom))
        
        if new_zoom != self.zoom:
            mouse_lat, mouse_lon = self.screen_to_lat_lon(mouse_x, mouse_y)
            
            self.zoom = new_zoom
            
            self.center_lat, self.center_lon = self.calculate_center_for_cursor_point(
                mouse_x, mouse_y, mouse_lat, mouse_lon)
            
            self.center_pixel_offset_x = 0.0
            self.center_pixel_offset_y = 0.0
            
            center_tile_x, center_tile_y = self.deg2num(self.center_lat, self.center_lon, self.zoom)
            self.center_lat, self.center_lon = self.num2deg(center_tile_x, center_tile_y, self.zoom)
            self.pan_velocity = QPoint(0, 0)
            
            self.memory_cache.clear()
            
            self.update()
            
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            
            self.repaint()
    
    def screen_to_lat_lon(self, screen_x, screen_y):
        center_screen_x = self.width() / 2
        center_screen_y = self.height() / 2
        
        offset_x = screen_x - center_screen_x
        offset_y = screen_y - center_screen_y
        
        total_offset_x = offset_x + self.center_pixel_offset_x
        total_offset_y = offset_y + self.center_pixel_offset_y
        
        world_size = 2 ** self.zoom * self.tile_size
        center_world_x = (self.center_lon + 180) / 360 * world_size
        center_world_y = (1 - math.asinh(math.tan(math.radians(self.center_lat))) / math.pi) / 2 * world_size
        
        mouse_world_x = center_world_x + total_offset_x
        mouse_world_y = center_world_y + total_offset_y
        
        mouse_lon = (mouse_world_x / world_size * 360) - 180
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * mouse_world_y / world_size)))
        mouse_lat = math.degrees(lat_rad)
        
        return mouse_lat, mouse_lon
    
    def lat_lon_to_screen(self, lat: float, lon: float):
        n = 2 ** self.zoom
        xtile = (lon + 180.0) / 360.0 * n
        ytile = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n

        cx_tile = (self.center_lon + 180.0) / 360.0 * n
        cy_tile = (1.0 - math.asinh(math.tan(math.radians(self.center_lat))) / math.pi) / 2.0 * n

        dx_px = (xtile - cx_tile) * self.tile_size - self.center_pixel_offset_x
        dy_px = (ytile - cy_tile) * self.tile_size - self.center_pixel_offset_y

        screen_x = self.width()  / 2 + dx_px
        screen_y = self.height() / 2 + dy_px
        return screen_x, screen_y
    
    def lat_lon_to_screen_stable(self, lat: float, lon: float):
        n = 2 ** self.zoom
        xtile = (lon + 180.0) / 360.0 * n
        ytile = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n

        cx_tile = (self.center_lon + 180.0) / 360.0 * n
        cy_tile = (1.0 - math.asinh(math.tan(math.radians(self.center_lat))) / math.pi) / 2.0 * n

        dx_px = (xtile - cx_tile) * self.tile_size
        dy_px = (ytile - cy_tile) * self.tile_size

        screen_x = self.width() / 2 + dx_px
        screen_y = self.height() / 2 + dy_px
        return screen_x, screen_y

    
    def calculate_center_for_cursor_point(self, cursor_x, cursor_y, target_lat, target_lon):
        center_screen_x = self.width() / 2
        center_screen_y = self.height() / 2
        
        offset_x = cursor_x - center_screen_x
        offset_y = cursor_y - center_screen_y
        
        world_size = 2 ** self.zoom * self.tile_size
        target_world_x = (target_lon + 180) / 360 * world_size
        target_world_y = (1 - math.asinh(math.tan(math.radians(target_lat))) / math.pi) / 2 * world_size
        
        center_world_x = target_world_x - offset_x
        center_world_y = target_world_y - offset_y
        
        center_lon = (center_world_x / world_size * 360) - 180
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * center_world_y / world_size)))
        center_lat = math.degrees(lat_rad)
        
        center_lat = max(-85, min(85, center_lat))
        center_lon = max(-180, min(180, center_lon))
        
        return center_lat, center_lon
    
    def lat_lon_to_maidenhead(self, lat, lon):
        norm_lon = lon + 180.0
        norm_lat = lat + 90.0
        
        field_lon_idx = int(norm_lon / 20.0)
        field_lat_idx = int(norm_lat / 10.0)
        
        field_lon_idx = min(max(field_lon_idx, 0), 17)
        field_lat_idx = min(max(field_lat_idx, 0), 17)
        
        field = chr(ord('A') + field_lon_idx) + chr(ord('A') + field_lat_idx)
        
        field_base_lon = field_lon_idx * 20.0
        field_base_lat = field_lat_idx * 10.0
        
        square_lon_idx = int((norm_lon - field_base_lon) / 2.0)
        square_lat_idx = int((norm_lat - field_base_lat) / 1.0)
        
        square_lon_idx = min(max(square_lon_idx, 0), 9)
        square_lat_idx = min(max(square_lat_idx, 0), 9)
        
        square = str(square_lon_idx) + str(square_lat_idx)
        
        square_base_lon = field_base_lon + square_lon_idx * 2.0
        square_base_lat = field_base_lat + square_lat_idx * 1.0
        
        subsquare_lon_idx = int((norm_lon - square_base_lon) / (2.0/24.0))
        subsquare_lat_idx = int((norm_lat - square_base_lat) / (1.0/24.0))
        
        subsquare_lon_idx = min(max(subsquare_lon_idx, 0), 23)
        subsquare_lat_idx = min(max(subsquare_lat_idx, 0), 23)
        
        subsquare = chr(ord('a') + subsquare_lon_idx) + chr(ord('a') + subsquare_lat_idx)
        
        return field + square + subsquare
    
    def maidenhead_to_lat_lon(self, grid):
        if len(grid) < 4:
            return None
            
        field_lon_idx = ord(grid[0].upper()) - ord('A')
        field_lat_idx = ord(grid[1].upper()) - ord('A')
        
        square_lon_idx = int(grid[2])
        square_lat_idx = int(grid[3])
        
        field_base_lon = field_lon_idx * 20.0 - 180.0
        field_base_lat = field_lat_idx * 10.0 - 90.0
        
        square_base_lon = field_base_lon + square_lon_idx * 2.0
        square_base_lat = field_base_lat + square_lat_idx * 1.0
        
        if len(grid) >= 6:
            subsquare_lon_idx = ord(grid[4].lower()) - ord('a')
            subsquare_lat_idx = ord(grid[5].lower()) - ord('a')
            
            subsquare_base_lon = square_base_lon + subsquare_lon_idx * (2.0/24.0)
            subsquare_base_lat = square_base_lat + subsquare_lat_idx * (1.0/24.0)
            
            return {
                'min_lat': subsquare_base_lat,
                'max_lat': subsquare_base_lat + (1.0/24.0),
                'min_lon': subsquare_base_lon,
                'max_lon': subsquare_base_lon + (2.0/24.0),
                'center_lat': subsquare_base_lat + (1.0/48.0),
                'center_lon': subsquare_base_lon + (1.0/24.0)
            }
        else:
            return {
                'min_lat': square_base_lat,
                'max_lat': square_base_lat + 1.0,
                'min_lon': square_base_lon,
                'max_lon': square_base_lon + 2.0,
                'center_lat': square_base_lat + 0.5,
                'center_lon': square_base_lon + 1.0
            }
    
    def screen_to_lat_lon_stable(self, screen_x, screen_y):
        center_screen_x = self.width() / 2
        center_screen_y = self.height() / 2
        
        offset_x = screen_x - center_screen_x
        offset_y = screen_y - center_screen_y
        
        world_size = 2 ** self.zoom * self.tile_size
        center_world_x = (self.center_lon + 180) / 360 * world_size
        center_world_y = (1 - math.asinh(math.tan(math.radians(self.center_lat))) / math.pi) / 2 * world_size
        
        mouse_world_x = center_world_x + offset_x
        mouse_world_y = center_world_y + offset_y
        
        mouse_lon = (mouse_world_x / world_size * 360) - 180
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * mouse_world_y / world_size)))
        mouse_lat = math.degrees(lat_rad)
        
        return mouse_lat, mouse_lon

    def get_visible_grid_squares(self):
        top_left_lat, top_left_lon = self.screen_to_lat_lon_stable(0, 0)
        bottom_right_lat, bottom_right_lon = self.screen_to_lat_lon_stable(self.width(), self.height())
        
        north = max(top_left_lat, bottom_right_lat)
        south = min(top_left_lat, bottom_right_lat)
        east = max(top_left_lon, bottom_right_lon)
        west = min(top_left_lon, bottom_right_lon)
        
        grid_squares = []

        if self.zoom >= 10:
            unit_lat = 1.0/24.0
            unit_lon = 2.0/24.0
            grid_type = 'subsquare'
        elif self.zoom >= 5:
            unit_lat = 1.0
            unit_lon = 2.0
            grid_type = 'square'
        else:
            unit_lat = 10.0
            unit_lon = 20.0
            grid_type = 'field'
        
        grid_base_lon = -180.0
        grid_base_lat = -90.0
        
        start_lon_idx = math.floor((west - grid_base_lon) / unit_lon)
        end_lon_idx = math.ceil((east - grid_base_lon) / unit_lon) + 1
        start_lat_idx = math.floor((south - grid_base_lat) / unit_lat)
        end_lat_idx = math.ceil((north - grid_base_lat) / unit_lat) + 1
        
        buffer = 2
        for lon_idx in range(start_lon_idx - buffer, end_lon_idx + buffer):
            for lat_idx in range(start_lat_idx - buffer, end_lat_idx + buffer):
                square_sw_lon = grid_base_lon + lon_idx * unit_lon
                square_sw_lat = grid_base_lat + lat_idx * unit_lat
                square_ne_lon = square_sw_lon + unit_lon
                square_ne_lat = square_sw_lat + unit_lat
                
                if (-90 <= square_sw_lat < 90 and -180 <= square_sw_lon < 180 and
                    square_ne_lon >= west and square_sw_lon <= east and
                    square_ne_lat >= south and square_sw_lat <= north):
                    
                    grid_squares.append({
                        'sw_lat': square_sw_lat,
                        'sw_lon': square_sw_lon,
                        'ne_lat': square_ne_lat,
                        'ne_lon': square_ne_lon,
                        'type': grid_type,
                        'unit_lat': unit_lat,
                        'unit_lon': unit_lon
                    })
            
        return grid_squares
    
    def draw_maidenhead_grid(self, painter):
        grid_squares = self.get_visible_grid_squares()
        
        pen = painter.pen()
        pen.setColor(self.grid_color)
        pen.setWidth(1)
        painter.setPen(pen)
        
        font = painter.font()
        if self.zoom >= 16:
            font.setPointSize(8)
        elif self.zoom >= 5:
            font.setPointSize(10)
        else:
            font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        
        for grid in grid_squares:
            sw_lat = grid['sw_lat']
            sw_lon = grid['sw_lon']
            ne_lat = grid['ne_lat']
            ne_lon = grid['ne_lon']
            grid_type = grid['type']
            
            try:
                top_left_x, top_left_y = self.lat_lon_to_screen_stable(ne_lat, sw_lon)
                top_right_x, top_right_y = self.lat_lon_to_screen_stable(ne_lat, ne_lon)
                bottom_left_x, bottom_left_y = self.lat_lon_to_screen_stable(sw_lat, sw_lon)
                bottom_right_x, bottom_right_y = self.lat_lon_to_screen_stable(sw_lat, ne_lon)
                
                if (max(top_left_x, top_right_x, bottom_left_x, bottom_right_x) >= -50 and
                    min(top_left_x, top_right_x, bottom_left_x, bottom_right_x) <= self.width() + 50 and
                    max(top_left_y, top_right_y, bottom_left_y, bottom_right_y) >= -50 and
                    min(top_left_y, top_right_y, bottom_left_y, bottom_right_y) <= self.height() + 50):
                    
                    painter.drawLine(int(top_left_x), int(top_left_y), int(top_right_x), int(top_right_y))
                    painter.drawLine(int(top_right_x), int(top_right_y), int(bottom_right_x), int(bottom_right_y))
                    painter.drawLine(int(bottom_right_x), int(bottom_right_y), int(bottom_left_x), int(bottom_left_y))
                    painter.drawLine(int(bottom_left_x), int(bottom_left_y), int(top_left_x), int(top_left_y))
                    
                    screen_center_x = (top_left_x + bottom_right_x) / 2.0
                    screen_center_y = (top_left_y + bottom_right_y) / 2.0
                    
                    center_lat = (sw_lat + ne_lat) / 2.0
                    center_lon = (sw_lon + ne_lon) / 2.0
                    
                    grid_label = self.get_grid_label(center_lat, center_lon, grid_type)
                    
                    if (grid_label and 
                        10 <= screen_center_x <= self.width() - 10 and 
                        10 <= screen_center_y <= self.height() - 10):
                        
                        painter.setPen(self.grid_text_color)
                        
                        font_metrics = painter.fontMetrics()
                        text_width = font_metrics.horizontalAdvance(grid_label)
                        text_height = font_metrics.height()
                        text_ascent = font_metrics.ascent()
                        
                        text_x = int(screen_center_x - text_width / 2.0)
                        text_y = int(screen_center_y - text_height / 2.0 + text_ascent)
                        
                        bg_margin = 2
                        bg_x = int(screen_center_x - text_width / 2.0 - bg_margin)
                        bg_y = int(screen_center_y - text_height / 2.0 - bg_margin)
                        bg_width = text_width + 2 * bg_margin
                        bg_height = text_height + 2 * bg_margin
                        
                        painter.fillRect(bg_x, bg_y, bg_width, bg_height, Qt.GlobalColor.white)
                        
                        painter.drawText(text_x, text_y, grid_label)
                        painter.setPen(pen)
                        
            except Exception:
                continue
    
    def get_grid_label(self, lat, lon, grid_type):
        full_grid = self.lat_lon_to_maidenhead(lat, lon)
        
        if grid_type == 'field':
            return full_grid[:2]
        elif grid_type == 'square':
            return full_grid[:4]
        elif grid_type == 'subsquare':
            return full_grid[:6]
        
        return full_grid
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_G:
            self.show_grid = not self.show_grid
            self.update()
        else:
            super().keyPressEvent(event)
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.last_pan_point = event.pos()
            self.pan_velocity = QPoint(0, 0)
            self.last_pan_time = time.time() * 1000
    
    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            current_time = time.time() * 1000
            delta = event.pos() - self.last_pan_point
            time_delta = current_time - self.last_pan_time
            
            if delta.x() != 0 or delta.y() != 0:
                self.apply_pan_movement(delta.x(), delta.y())
                
                if time_delta > 0:
                    velocity_x = delta.x() / max(time_delta, 1) * 16
                    velocity_y = delta.y() / max(time_delta, 1) * 16
                    
                    self.pan_velocity = QPoint(
                        int(self.pan_velocity.x() * 0.8 + velocity_x * 0.2),
                        int(self.pan_velocity.y() * 0.8 + velocity_y * 0.2)
                    )
                
                self.update()
            
            self.last_pan_point = event.pos()
            self.last_pan_time = current_time
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        min_zoom = self.get_min_zoom_for_size(self.width(), self.height())
        if self.zoom < min_zoom:
            self.zoom = min_zoom
            self.memory_cache.clear()
            self.update()
    
    def closeEvent(self, event):
        self.tile_downloader.stop()
        event.accept()


class MapWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("World Map Viewer")
        self.setGeometry(100, 100, 1200, 800)
        
        self.map_widget = MapWidget()
        self.setCentralWidget(self.map_widget)
    
    def closeEvent(self, event):
        self.map_widget.closeEvent(event)
        event.accept()


def main():
    app = QApplication(sys.argv)
    
    window = MapWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()