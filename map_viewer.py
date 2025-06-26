#!/usr/bin/env python3

import sys
import math
import requests
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt6.QtCore import Qt, QPoint, QRect, QTimer, QThread, pyqtSignal, QMutex, QThreadPool, QRunnable, QObject
from PyQt6.QtGui import QPainter, QPixmap, QWheelEvent, QMouseEvent
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
        """Remove tiles older than max_age_days"""
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
                # Save to cache first
                self.tile_cache.save_tile(self.zoom, self.x, self.y, response.content)
                
                # Create pixmap and emit signal
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
        
        # Connect the completion signal once
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
        self.thread_pool.waitForDone(5000)  # Wait up to 5 seconds for completion


class MapWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)
        
        # Map parameters
        self.zoom = 2
        self.center_lat = 0.0
        self.center_lon = 0.0
        self.tile_size = 256
        
        # Interaction state
        self.dragging = False
        self.last_pan_point = QPoint()
        self.pan_velocity = QPoint(0, 0)
        self.last_pan_time = 0
        self.momentum_decay = 0.92
        self.momentum_threshold = 1.0
        
        # Smooth panning with pixel-level precision
        self.center_pixel_offset_x = 0.0
        self.center_pixel_offset_y = 0.0
        
        # Cache systems
        self.memory_cache = {}  # In-memory pixmap cache
        self.file_cache = TileCache()  # Persistent file cache
        
        # Clean old cache files on startup (optional)
        self.file_cache.clean_old_tiles(30)
        
        # Tile downloader with parallel processing
        self.tile_downloader = TileDownloader(self.file_cache, max_workers=8)
        self.tile_downloader.tile_downloaded.connect(self.on_tile_downloaded)
        
        # Enable mouse tracking for pan
        self.setMouseTracking(True)
        
        # Update timer for smooth animations
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_animation)
        self.update_timer.start(16)  # ~60 FPS
    
    def deg2num(self, lat_deg, lon_deg, zoom):
        """Convert lat/lon to tile numbers"""
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        x = int((lon_deg + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return (x, y)
    
    def num2deg(self, x, y, zoom):
        """Convert tile numbers to lat/lon"""
        n = 2.0 ** zoom
        lon_deg = x / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat_deg = math.degrees(lat_rad)
        return (lat_deg, lon_deg)
    
    def get_min_zoom_for_size(self, width, height):
        """Calculate minimum zoom level to fill the window"""
        # World is 2^zoom tiles wide and high
        # Each tile is 256x256 pixels
        # We want at least enough tiles to fill the screen
        min_tiles_x = math.ceil(width / self.tile_size)
        min_tiles_y = math.ceil(height / self.tile_size)
        
        # World has 2^zoom tiles in each direction
        # So we need 2^zoom >= max(min_tiles_x, min_tiles_y)
        min_zoom_x = math.ceil(math.log2(max(1, min_tiles_x)))
        min_zoom_y = math.ceil(math.log2(max(1, min_tiles_y)))
        
        return max(min_zoom_x, min_zoom_y, 1)  # At least zoom level 1
    
    def get_tile_key(self, zoom, x, y):
        return f"{zoom}/{x}/{y}"
    
    def on_tile_downloaded(self, zoom, x, y, pixmap):
        """Handle downloaded tile"""
        key = self.get_tile_key(zoom, x, y)
        self.memory_cache[key] = pixmap
        self.update()
    
    def update_animation(self):
        """Handle smooth animations and momentum"""
        needs_update = False
        
        # Handle momentum when not dragging
        if not self.dragging and (abs(self.pan_velocity.x()) > self.momentum_threshold or 
                                  abs(self.pan_velocity.y()) > self.momentum_threshold):
            
            # Store old position to check if movement was blocked
            old_lat, old_lon = self.center_lat, self.center_lon
            old_offset_x, old_offset_y = self.center_pixel_offset_x, self.center_pixel_offset_y
            
            # Apply momentum movement
            self.apply_pan_movement(self.pan_velocity.x(), self.pan_velocity.y())
            
            # Check if movement was blocked by boundaries
            if (abs(self.center_lat - old_lat) < 0.0001 and 
                abs(self.center_lon - old_lon) < 0.0001 and
                abs(self.center_pixel_offset_x - old_offset_x) < 1 and
                abs(self.center_pixel_offset_y - old_offset_y) < 1):
                # Hit boundary, stop momentum
                self.pan_velocity = QPoint(0, 0)
            else:
                # Decay velocity
                self.pan_velocity = QPoint(
                    int(self.pan_velocity.x() * self.momentum_decay),
                    int(self.pan_velocity.y() * self.momentum_decay)
                )
            needs_update = True
        elif not self.dragging:
            # Stop momentum if below threshold
            self.pan_velocity = QPoint(0, 0)
        
        if needs_update:
            self.update()
    
    def get_world_bounds_at_zoom(self):
        """Get world bounds in pixels at current zoom level"""
        world_size = 2 ** self.zoom * self.tile_size
        return world_size
    
    def apply_pan_movement(self, delta_x, delta_y):
        """Apply pan movement with boundary checking"""
        # Add to pixel offset for smooth sub-pixel movement
        self.center_pixel_offset_x += delta_x
        self.center_pixel_offset_y += delta_y
        
        # Get current center in tile coordinates
        center_tile_x, center_tile_y = self.deg2num(self.center_lat, self.center_lon, self.zoom)
        
        # Calculate new position in pixels
        world_size = self.get_world_bounds_at_zoom()
        center_pixel_x = center_tile_x * self.tile_size + self.center_pixel_offset_x
        center_pixel_y = center_tile_y * self.tile_size + self.center_pixel_offset_y
        
        # Apply boundary limits
        half_width = self.width() / 2
        half_height = self.height() / 2
        
        # Clamp to world bounds
        center_pixel_x = max(half_width, min(world_size - half_width, center_pixel_x))
        center_pixel_y = max(half_height, min(world_size - half_height, center_pixel_y))
        
        # Convert back to tile coordinates
        new_tile_x = center_pixel_x / self.tile_size
        new_tile_y = center_pixel_y / self.tile_size
        
        # Update pixel offset
        self.center_pixel_offset_x = (new_tile_x - int(new_tile_x)) * self.tile_size
        self.center_pixel_offset_y = (new_tile_y - int(new_tile_y)) * self.tile_size
        
        # Convert back to lat/lon
        new_lat, new_lon = self.num2deg(new_tile_x, new_tile_y, self.zoom)
        
        # Update center coordinates
        self.center_lat = new_lat
        self.center_lon = new_lon
    
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Enable smooth rendering
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)  # Don't antialias tiles
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        painter.fillRect(self.rect(), Qt.GlobalColor.lightGray)
        
        # Calculate visible tiles
        widget_width = self.width()
        widget_height = self.height()
        
        # Get exact tile coordinates for center point
        exact_x, exact_y = self.deg2num(self.center_lat, self.center_lon, self.zoom)
        center_tile_x = int(exact_x)
        center_tile_y = int(exact_y)
        
        # Calculate pixel offset within the center tile (including smooth offset)
        offset_x = (exact_x - center_tile_x) * self.tile_size + self.center_pixel_offset_x
        offset_y = (exact_y - center_tile_y) * self.tile_size + self.center_pixel_offset_y
        
        # Calculate how many tiles we need to cover the widget
        tiles_x = math.ceil(widget_width / self.tile_size) + 2
        tiles_y = math.ceil(widget_height / self.tile_size) + 2
        
        # Center point on screen
        center_pixel_x = widget_width // 2
        center_pixel_y = widget_height // 2
        
        # Draw tiles
        for dy in range(-tiles_y//2, tiles_y//2 + 1):
            for dx in range(-tiles_x//2, tiles_x//2 + 1):
                tile_x = center_tile_x + dx
                tile_y = center_tile_y + dy
                
                # Check tile bounds
                max_tile = 2 ** self.zoom
                if tile_x < 0 or tile_x >= max_tile or tile_y < 0 or tile_y >= max_tile:
                    continue
                
                # Calculate tile position on screen
                screen_x = center_pixel_x + (dx * self.tile_size) - int(offset_x)
                screen_y = center_pixel_y + (dy * self.tile_size) - int(offset_y)
                
                # Get tile from cache or request download
                key = self.get_tile_key(self.zoom, tile_x, tile_y)
                pixmap = None
                
                # Try memory cache first
                if key in self.memory_cache:
                    pixmap = self.memory_cache[key]
                    painter.drawPixmap(screen_x, screen_y, pixmap)
                else:
                    # Try file cache
                    cached_pixmap = self.file_cache.get_cached_tile(self.zoom, tile_x, tile_y)
                    if cached_pixmap:
                        # Load from file cache into memory cache
                        self.memory_cache[key] = cached_pixmap
                        painter.drawPixmap(screen_x, screen_y, cached_pixmap)
                    else:
                        # Request tile download if not cached anywhere
                        self.tile_downloader.add_tile(self.zoom, tile_x, tile_y)
                        # Draw placeholder
                        painter.fillRect(screen_x, screen_y, self.tile_size, self.tile_size, 
                                       Qt.GlobalColor.lightGray)
                        # Optional: draw tile coordinates for debugging
                        # painter.drawText(screen_x + 10, screen_y + 20, f"{tile_x},{tile_y}")
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle zoom with mouse wheel centered on cursor"""
        # Get mouse position
        mouse_pos = event.position()
        mouse_x = mouse_pos.x()
        mouse_y = mouse_pos.y()
        
        # Store old zoom for comparison
        old_zoom = self.zoom
        
        # Calculate minimum zoom level for current window size
        min_zoom = self.get_min_zoom_for_size(self.width(), self.height())
        
        # Determine new zoom level
        zoom_delta = 1 if event.angleDelta().y() > 0 else -1
        new_zoom = self.zoom + zoom_delta
        
        # Apply zoom limits
        new_zoom = max(min_zoom, min(18, new_zoom))
        
        # Only proceed if zoom actually changed
        if new_zoom != self.zoom:
            # Get the lat/lon under the mouse cursor BEFORE zoom change
            mouse_lat, mouse_lon = self.screen_to_lat_lon(mouse_x, mouse_y)
            
            # Update zoom level
            self.zoom = new_zoom
            
            # Calculate where the mouse point should be after zoom
            new_mouse_x, new_mouse_y = self.lat_lon_to_screen(mouse_lat, mouse_lon)
            
            # Calculate how much to adjust the center
            offset_x = new_mouse_x - mouse_x
            offset_y = new_mouse_y - mouse_y
            
            # Adjust center by converting offset to lat/lon movement
            if offset_x != 0 or offset_y != 0:
                self.apply_pan_movement(-offset_x, -offset_y)
            
            # Reset pixel offsets and momentum
            self.center_pixel_offset_x = 0.0
            self.center_pixel_offset_y = 0.0
            self.pan_velocity = QPoint(0, 0)
            
            # Clear memory cache
            self.memory_cache.clear()
            self.update()
    
    def screen_to_lat_lon(self, screen_x, screen_y):
        """Convert screen coordinates to lat/lon"""
        # Get center position
        center_screen_x = self.width() / 2
        center_screen_y = self.height() / 2
        
        # Calculate offset in pixels
        offset_x = screen_x - center_screen_x + self.center_pixel_offset_x
        offset_y = screen_y - center_screen_y + self.center_pixel_offset_y
        
        # Convert to tile coordinates
        center_tile_x, center_tile_y = self.deg2num(self.center_lat, self.center_lon, self.zoom)
        
        # Add pixel offset as tile fraction
        mouse_tile_x = center_tile_x + (offset_x / self.tile_size)
        mouse_tile_y = center_tile_y + (offset_y / self.tile_size)
        
        # Convert to lat/lon
        mouse_lat, mouse_lon = self.num2deg(mouse_tile_x, mouse_tile_y, self.zoom)
        
        return mouse_lat, mouse_lon
    
    def lat_lon_to_screen(self, lat, lon):
        """Convert lat/lon to screen coordinates"""
        # Convert to tile coordinates
        tile_x, tile_y = self.deg2num(lat, lon, self.zoom)
        
        # Get center tile coordinates
        center_tile_x, center_tile_y = self.deg2num(self.center_lat, self.center_lon, self.zoom)
        
        # Calculate offset in tiles
        offset_tile_x = tile_x - center_tile_x
        offset_tile_y = tile_y - center_tile_y
        
        # Convert to pixels
        offset_x = offset_tile_x * self.tile_size - self.center_pixel_offset_x
        offset_y = offset_tile_y * self.tile_size - self.center_pixel_offset_y
        
        # Convert to screen coordinates
        center_screen_x = self.width() / 2
        center_screen_y = self.height() / 2
        
        screen_x = center_screen_x + offset_x
        screen_y = center_screen_y + offset_y
        
        return screen_x, screen_y
    
    def mousePressEvent(self, event: QMouseEvent):
        """Start panning"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.last_pan_point = event.pos()
            self.pan_velocity = QPoint(0, 0)  # Stop momentum
            self.last_pan_time = time.time() * 1000  # Current time in ms
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle panning with immediate response"""
        if self.dragging:
            current_time = time.time() * 1000
            delta = event.pos() - self.last_pan_point
            time_delta = current_time - self.last_pan_time
            
            # Apply pan movement immediately for responsiveness
            if delta.x() != 0 or delta.y() != 0:
                self.apply_pan_movement(delta.x(), delta.y())
                
                # Calculate velocity for momentum
                if time_delta > 0:
                    velocity_x = delta.x() / max(time_delta, 1) * 16
                    velocity_y = delta.y() / max(time_delta, 1) * 16
                    
                    # Smooth velocity for natural momentum
                    self.pan_velocity = QPoint(
                        int(self.pan_velocity.x() * 0.8 + velocity_x * 0.2),
                        int(self.pan_velocity.y() * 0.8 + velocity_y * 0.2)
                    )
                
                self.update()
            
            self.last_pan_point = event.pos()
            self.last_pan_time = current_time
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Stop panning and start momentum"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            # Momentum will continue based on current pan_velocity
    
    def resizeEvent(self, event):
        """Handle window resize to update minimum zoom"""
        super().resizeEvent(event)
        
        # Check if current zoom is too low for new window size
        min_zoom = self.get_min_zoom_for_size(self.width(), self.height())
        if self.zoom < min_zoom:
            self.zoom = min_zoom
            self.memory_cache.clear()
            self.update()
    
    def closeEvent(self, event):
        """Clean up when closing"""
        self.tile_downloader.stop()
        event.accept()


class MapWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("World Map Viewer")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create map widget
        self.map_widget = MapWidget()
        self.setCentralWidget(self.map_widget)
    
    def closeEvent(self, event):
        """Clean up when closing"""
        self.map_widget.closeEvent(event)
        event.accept()


def main():
    app = QApplication(sys.argv)
    
    window = MapWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()