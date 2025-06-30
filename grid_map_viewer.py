import sys
import math
import os
import time
import pickle

from constants import (
    CUSTOM_FONT,
    GUI_LABEL_VERSION
)

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QFont, QPainter, QWheelEvent, QMouseEvent, QKeyEvent, QColor, QBrush, QPen, QPainterPath

from tiles_manager import TileCache, TileDownloader
from urllib.parse import urlparse
from logger import get_logger
from utils import darken_color, complementary_color

log     = get_logger(__name__)

class GridMapWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)

        self.zoom                       = 2
        self.center_lat                 = 0.0
        self.center_lon                 = 0.0
        self.tile_size                  = 256
        
        self.dragging                   = False
        self.last_pan_point             = QPoint()
        self.pan_velocity               = QPoint(0, 0)
        self.last_pan_time              = 0
        self.momentum_decay             = 0.92
        self.momentum_threshold         = 1.0
        
        self.center_pixel_offset_x      = 0.0
        self.center_pixel_offset_y      = 0.0
        
        self.show_grid                  = True
        self.show_ellipses              = True
        self.grid_color                 = Qt.GlobalColor.red
        self.grid_text_color            = Qt.GlobalColor.gray
        
        self.highlighted_squares        = []
        self.highlighted_grids          = []
        self.current_band               = None
        self.adif_data                  = {}

        # Buffer to store multiple ellipse groups
        self.ellipse_buffer             = []  
        self.max_ellipse_buffer_size    = 5
        
        self.blink_count                = 0
        self.blink_visible              = True
        self.blink_timer                = QTimer()
        self.blink_timer.timeout.connect(self.blink_update)

        self.memory_cache               = {}
        self.file_cache                  = TileCache()
        
        self.file_cache.clean_old_tiles(30)
        
        self.tile_downloader            = TileDownloader(self.file_cache, max_workers=8)
        self.tile_downloader.tile_downloaded.connect(self.on_tile_downloaded)
        
        self.setMouseTracking(True)
        
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        self.update_timer               = QTimer()
        self.update_timer.timeout.connect(self.update_animation)
        self.update_timer.start(16)
        
        self.settings_file               = os.path.join(os.path.dirname(__file__), "grid_map_settings.pickle")
        self.load_grid_map_settings()
    
    def save_grid_map_settings(self):
        settings = {
            'show_grid'     : self.show_grid,
            'show_ellipses' : self.show_ellipses
        }
        try:
            with open(self.settings_file, "wb") as f:
                pickle.dump(settings, f)
        except Exception as e:
            log.error(f"Failed to save grid map settings: {e}")
    
    def load_grid_map_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "rb") as f:
                    settings = pickle.load(f)
                    self.show_grid = settings.get('show_grid', True)
                    self.show_ellipses = settings.get('show_ellipses', True)
        except Exception as e:
            log.error(f"Failed to load grid map settings: {e}")
    
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
        
        return max(min_zoom_x, min_zoom_y, 2)
    
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
        
        half_height = self.height() / 2
        
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
        
        max_tile = 2 ** self.zoom
        
        for dy in range(-tiles_y//2, tiles_y//2 + 1):
            for dx in range(-tiles_x//2, tiles_x//2 + 1):
                tile_x = center_tile_x + dx
                tile_y = center_tile_y + dy
                
                if tile_y < 0 or tile_y >= max_tile:
                    continue
                
                wrapped_tile_x = tile_x % max_tile
                if wrapped_tile_x < 0:
                    wrapped_tile_x += max_tile
                
                screen_x = center_pixel_x + (dx * self.tile_size) - int(offset_x)
                screen_y = center_pixel_y + (dy * self.tile_size) - int(offset_y)
                
                key = self.get_tile_key(self.zoom, wrapped_tile_x, tile_y)
                pixmap = None
                
                if key in self.memory_cache:
                    pixmap = self.memory_cache[key]
                    painter.drawPixmap(screen_x, screen_y, pixmap)
                else:
                    cached_pixmap = self.file_cache.get_cached_tile(self.zoom, wrapped_tile_x, tile_y)
                    if cached_pixmap:
                        self.memory_cache[key] = cached_pixmap
                        painter.drawPixmap(
                            screen_x,
                            screen_y,
                            cached_pixmap
                        )
                    else:
                        self.tile_downloader.add_tile(self.zoom, wrapped_tile_x, tile_y)
                        painter.fillRect(
                            screen_x, 
                            screen_y,
                            self.tile_size,
                            self.tile_size,
                            Qt.GlobalColor.lightGray
                        )
        
        """
            Make sure to properly set the order of drawing elements.
        """
        if self.show_grid:
            self.draw_maidenhead_grid(painter)
            
        for square in self.highlighted_squares:
            self.fill_grid_square_with_color(painter, square, QColor(91, 105, 171, 128))
        
        self.set_ellipse_indicators(painter)
        
        if self.blink_visible and self.highlighted_grids:
            self.draw_highlighted_grids_block(painter)
    
    def wheelEvent(self, event: QWheelEvent):
        mouse_pos = event.position()
        mouse_x = mouse_pos.x()
        mouse_y = mouse_pos.y()
        
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
            
            world_size = self.get_world_bounds_at_zoom()
            center_pixel_x = center_tile_x * self.tile_size
            center_pixel_y = center_tile_y * self.tile_size
            
            half_height = self.height() / 2
            
            center_pixel_y = max(half_height, min(world_size - half_height, center_pixel_y))
            
            new_tile_x = center_pixel_x / self.tile_size
            new_tile_y = center_pixel_y / self.tile_size
            
            self.center_lat, self.center_lon = self.num2deg(new_tile_x, new_tile_y, self.zoom)
            self.pan_velocity = QPoint(0, 0)
            
            self.apply_pan_movement(0, 0)
            
            self.memory_cache.clear()
            
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
        
        offset_x        = screen_x - center_screen_x
        offset_y        = screen_y - center_screen_y
        
        world_size      = 2 ** self.zoom * self.tile_size
        center_world_x  = (self.center_lon + 180) / 360 * world_size
        center_world_y  = (1 - math.asinh(math.tan(math.radians(self.center_lat))) / math.pi) / 2 * world_size
        
        mouse_world_x   = center_world_x + offset_x
        mouse_world_y   = center_world_y + offset_y
        
        mouse_lon       = (mouse_world_x / world_size * 360) - 180
        lat_rad         = math.atan(math.sinh(math.pi * (1 - 2 * mouse_world_y / world_size)))
        mouse_lat       = math.degrees(lat_rad)
        
        return mouse_lat, mouse_lon

    def get_visible_grid_squares(self):
        top_left_lat, top_left_lon = self.screen_to_lat_lon_stable(0, 0)
        bottom_right_lat, bottom_right_lon = self.screen_to_lat_lon_stable(self.width(), self.height())
        
        north = max(top_left_lat, bottom_right_lat)
        south = min(top_left_lat, bottom_right_lat)
        east = max(top_left_lon, bottom_right_lon)
        west = min(top_left_lon, bottom_right_lon)
        
        lon_span = east - west
        if lon_span > 360:
            west = -180
            east = 180
        
        grid_squares = []

        def add_grid_type(unit_lat, unit_lon, grid_type, show_labels=True, color='red'):
            grid_base_lon = -180.0
            grid_base_lat = -90.0
            
            start_lon_idx = math.floor((west - grid_base_lon) / unit_lon)
            end_lon_idx   = math.ceil((east - grid_base_lon) / unit_lon) + 1
            start_lat_idx = math.floor((south - grid_base_lat) / unit_lat)
            end_lat_idx   = math.ceil((north - grid_base_lat) / unit_lat) + 1
            
            buffer = 1 if self.zoom <= 3 else 2
            
            extended_west = west - 360
            extended_east = east + 360
            
            for lon_idx in range(start_lon_idx - buffer, end_lon_idx + buffer):
                for lat_idx in range(start_lat_idx - buffer, end_lat_idx + buffer):
                    square_sw_lat = grid_base_lat + lat_idx * unit_lat
                    square_ne_lat = square_sw_lat + unit_lat
                    
                    if not (-90 <= square_sw_lat < 90 and square_ne_lat >= south and square_sw_lat <= north):
                        continue
                    
                    offsets = [0, 360, -360] if self.zoom >= 2 else [0]
                    
                    for offset in offsets:
                        square_sw_lon = grid_base_lon + lon_idx * unit_lon + offset
                        square_ne_lon = square_sw_lon + unit_lon
                        
                        if (square_ne_lon >= west and square_sw_lon <= east) or \
                           (square_ne_lon >= extended_west and square_sw_lon <= extended_east):
                            
                            grid_squares.append({
                                'sw_lat'        : square_sw_lat,
                                'sw_lon'        : square_sw_lon,
                                'ne_lat'        : square_ne_lat,
                                'ne_lon'        : square_ne_lon,
                                'type'          : grid_type,
                                'unit_lat'      : unit_lat,
                                'unit_lon'      : unit_lon,
                                'show_labels'   : show_labels,
                                'color'         : color
                            })

        # Only add the gray square grid if zoom level is 5 or higher
        if self.zoom >= 5:
            add_grid_type(1.0, 2.0, 'square', False, 'gray')
        
        if self.zoom >= 10:
            add_grid_type(1.0/24.0, 2.0/24.0, 'subsquare', True, 'red')
        elif self.zoom >= 6:
            add_grid_type(1.0, 2.0, 'square', True, 'red')
        elif self.zoom >= 5:
            add_grid_type(10.0, 20.0, 'field', True, 'red')
        else:
            # For zoom levels 3-4, only show field grid
            add_grid_type(10.0, 20.0, 'field', True, 'red')
            
        return grid_squares
    
    def draw_maidenhead_grid(self, painter):
        grid_squares = self.get_visible_grid_squares()
        
        font = QFont(CUSTOM_FONT)
        if self.zoom >= 12:
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4)
            font.setPointSize(22)     
        elif self.zoom >= 10:
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
            font.setPointSize(12)
        elif self.zoom >= 6:
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4)
            font.setPointSize(22)            
        else:
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 6)
            font.setPointSize(30)

        # print(self.zoom)
        painter.setPen(self.grid_color)
        painter.setFont(font)
        
        for grid in grid_squares:
            sw_lat      = grid['sw_lat']
            sw_lon      = grid['sw_lon']
            ne_lat      = grid['ne_lat']
            ne_lon      = grid['ne_lon']
            grid_type   = grid['type']
            show_labels = grid['show_labels']
            color       = grid['color']
            
            pen = painter.pen()
            if color == 'gray':
                pen.setColor(Qt.GlobalColor.gray)
                pen.setWidth(1)
            else:
                pen.setColor(self.grid_color)
                pen.setWidth(1)
            painter.setPen(pen)
            
            try:
                top_left_x, top_left_y          = self.lat_lon_to_screen_stable(ne_lat, sw_lon)
                top_right_x, top_right_y        = self.lat_lon_to_screen_stable(ne_lat, ne_lon)
                bottom_left_x, bottom_left_y    = self.lat_lon_to_screen_stable(sw_lat, sw_lon)
                bottom_right_x, bottom_right_y  = self.lat_lon_to_screen_stable(sw_lat, ne_lon)
                
                if (max(top_left_x, top_right_x, bottom_left_x, bottom_right_x) >= -50 and
                    min(top_left_x, top_right_x, bottom_left_x, bottom_right_x) <= self.width() + 50 and
                    max(top_left_y, top_right_y, bottom_left_y, bottom_right_y) >= -50 and
                    min(top_left_y, top_right_y, bottom_left_y, bottom_right_y) <= self.height() + 50):
                    
                    painter.drawLine(int(top_left_x), int(top_left_y), int(top_right_x), int(top_right_y))
                    painter.drawLine(int(top_right_x), int(top_right_y), int(bottom_right_x), int(bottom_right_y))
                    painter.drawLine(int(bottom_right_x), int(bottom_right_y), int(bottom_left_x), int(bottom_left_y))
                    painter.drawLine(int(bottom_left_x), int(bottom_left_y), int(top_left_x), int(top_left_y))
                    
                    if show_labels:
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
                            text_width   = font_metrics.horizontalAdvance(grid_label)
                            text_height  = font_metrics.height()
                            text_ascent  = font_metrics.ascent()
                            
                            text_x = int(screen_center_x - text_width / 2.0)
                            text_y = int(screen_center_y - text_height / 2.0 + text_ascent)
                               
                            painter.drawText(text_x, text_y, grid_label)                        
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
    
    def fill_grid_square_with_color(self, painter, grid_square, color):        
        if isinstance(color, str):
            fill_color = QColor(color)
            fill_color.setAlpha(255)
        else:
            fill_color = color
        
        grid_info = self.maidenhead_to_lat_lon(grid_square)
        if not grid_info:
            return
            
        min_lat = grid_info['min_lat']
        max_lat = grid_info['max_lat']
        min_lon = grid_info['min_lon']
        max_lon = grid_info['max_lon']
        
        offsets = [0, 360, -360] if self.zoom >= 2 else [0]
        
        for offset in offsets:
            offset_min_lon = min_lon + offset
            offset_max_lon = max_lon + offset
            
            try:
                top_left_x, top_left_y          = self.lat_lon_to_screen_stable(max_lat, offset_min_lon)
                top_right_x, top_right_y        = self.lat_lon_to_screen_stable(max_lat, offset_max_lon)
                bottom_left_x, bottom_left_y    = self.lat_lon_to_screen_stable(min_lat, offset_min_lon)
                bottom_right_x, bottom_right_y  = self.lat_lon_to_screen_stable(min_lat, offset_max_lon)
                
                if (max(top_left_x, top_right_x, bottom_left_x, bottom_right_x) >= -50 and
                    min(top_left_x, top_right_x, bottom_left_x, bottom_right_x) <= self.width() + 50 and
                    max(top_left_y, top_right_y, bottom_left_y, bottom_right_y) >= -50 and
                    min(top_left_y, top_right_y, bottom_left_y, bottom_right_y) <= self.height() + 50):
                    
                    brush = QBrush(fill_color)
                    
                    rect_x      = int(min(top_left_x, top_right_x, bottom_left_x, bottom_right_x))
                    rect_y      = int(min(top_left_y, top_right_y, bottom_left_y, bottom_right_y))
                    rect_width  = int(max(top_left_x, top_right_x, bottom_left_x, bottom_right_x) - rect_x) + 1
                    rect_height = int(max(top_left_y, top_right_y, bottom_left_y, bottom_right_y) - rect_y) + 1
                    
                    painter.fillRect(rect_x, rect_y, rect_width, rect_height, brush)
            except Exception:
                pass
    
    def draw_highlighted_grids_block(self, painter):
        for grid_color in self.highlighted_grids:
            grid_square = grid_color['grid']
            color_hex   = grid_color['color']
            
            color = QColor(color_hex)

            fill_color = complementary_color(color)
            fill_color.setAlpha(255) 
            
            border_color = color
            
            grid_info = self.maidenhead_to_lat_lon(grid_square)
            if not grid_info:
                continue
                
            min_lat = grid_info['min_lat']
            max_lat = grid_info['max_lat']
            min_lon = grid_info['min_lon']
            max_lon = grid_info['max_lon']
            
            offsets = [0, 360, -360] if self.zoom >= 2 else [0]
            
            for offset in offsets:
                offset_min_lon = min_lon + offset
                offset_max_lon = max_lon + offset
                
                try:
                    top_left_x, top_left_y          = self.lat_lon_to_screen_stable(max_lat, offset_min_lon)
                    top_right_x, top_right_y        = self.lat_lon_to_screen_stable(max_lat, offset_max_lon)
                    bottom_left_x, bottom_left_y    = self.lat_lon_to_screen_stable(min_lat, offset_min_lon)
                    bottom_right_x, bottom_right_y  = self.lat_lon_to_screen_stable(min_lat, offset_max_lon)
                    
                    if (max(top_left_x, top_right_x, bottom_left_x, bottom_right_x) >= -50 and
                        min(top_left_x, top_right_x, bottom_left_x, bottom_right_x) <= self.width() + 50 and
                        max(top_left_y, top_right_y, bottom_left_y, bottom_right_y) >= -50 and
                        min(top_left_y, top_right_y, bottom_left_y, bottom_right_y) <= self.height() + 50):
                        
                        rect_x      = int(min(top_left_x, top_right_x, bottom_left_x, bottom_right_x))
                        rect_y      = int(min(top_left_y, top_right_y, bottom_left_y, bottom_right_y))
                        rect_width  = int(max(top_left_x, top_right_x, bottom_left_x, bottom_right_x) - rect_x) + 1
                        rect_height = int(max(top_left_y, top_right_y, bottom_left_y, bottom_right_y) - rect_y) + 1
                        
                        brush = QBrush(fill_color)
                        painter.fillRect(rect_x, rect_y, rect_width, rect_height, brush)
                        
                        pen = QPen(border_color)
                        pen.setWidth(1)
                        painter.setPen(pen)
                        painter.drawRect(rect_x, rect_y, rect_width - 1, rect_height - 1)
                        
                except Exception:
                    pass
    
    def blink_update(self):
        self.blink_visible = not self.blink_visible
        self.blink_count += 1
        self.update()
        
        if self.blink_count >= 20:
            self.blink_timer.stop()
            self.blink_count = 0
            self.blink_visible = True
            self.update()
    
    def update_adif_data(self, adif_data):
        self.adif_data = adif_data
        self.update_grid_squares_for_band()
    
    def update_current_band(self, band):
        if self.current_band != band:
            self.current_band = band
            self.update_grid_squares_for_band()
    
    def update_grid_squares_for_band(self):
        if not self.current_band or not self.adif_data:
            self.set_highlighted_squares([])
            return

        """
            Update the highlighted squares based on the current band and ADIF data.
        """
        grid_squares = list(self.adif_data.get('grid', {}).get(self.current_band, {}).keys())

        self.set_highlighted_squares(grid_squares, center_on_last=False)
    
    def set_highlighted_squares(self, squares, center_on_last=True):
        self.highlighted_squares = squares
        
        if len(squares) > 0 and center_on_last:
            last_square = squares[-1]
            grid_info = self.maidenhead_to_lat_lon(last_square)
            if grid_info:
                self.center_lat = grid_info['center_lat']
                self.center_lon = grid_info['center_lon']
                self.center_pixel_offset_x = 0.0
                self.center_pixel_offset_y = 0.0
                self.apply_pan_movement(0, 0)
        
        self.update()
    
    def set_highlighted_grids(self, grids, center_on_last=False):
        self.highlighted_grids = []
        
        self.blink_timer.stop()
        self.blink_count = 0
        self.blink_visible = True
        
        self.highlighted_grids = grids
        
        if len(grids) > 0 and center_on_last:
            last_grid = grids[-1]['grid']
            grid_info = self.maidenhead_to_lat_lon(last_grid)
            if grid_info:
                self.center_lat = grid_info['center_lat']
                self.center_lon = grid_info['center_lon']
                self.center_pixel_offset_x = 0.0
                self.center_pixel_offset_y = 0.0
                self.apply_pan_movement(0, 0)
        
        if grids:
            self.blink_timer.start(300)  
        
        self.update()
    
    def clear_highlighted_grids(self):
        self.set_highlighted_grids([])
    
    def clear_ellipse_indicators(self):
        self.ellipse_buffer = []
        self.update()
    
    def add_ellipse_group_to_buffer(self, grids):
        if grids:
            # Remove duplicate grids within the group
            unique_grids = []
            seen_grids = set()
            for grid_data in grids:
                grid_key = grid_data['grid']
                if grid_key not in seen_grids:
                    seen_grids.add(grid_key)
                    unique_grids.append(grid_data)
            
            # Check if this exact ellipse group already exists
            new_grid_set = set(grid_data['grid'] for grid_data in unique_grids)
            for existing_group in self.ellipse_buffer:
                existing_grid_set = set(grid_data['grid'] for grid_data in existing_group)
                if new_grid_set == existing_grid_set:
                    return  # Don't add duplicate ellipse
            
            self.ellipse_buffer.append(unique_grids)
            
            if len(self.ellipse_buffer) > self.max_ellipse_buffer_size:
                self.ellipse_buffer.pop(0)  
            
            self.update()
    
    def set_ellipse_group_indicators(self, grids):
        self.add_ellipse_group_to_buffer(grids)
    
    def get_ellipse_buffer_info(self):
        return {
            'count'     : len(self.ellipse_buffer),
            'max_size'  : self.max_ellipse_buffer_size,
            'is_full'   : len(self.ellipse_buffer) >= self.max_ellipse_buffer_size
        }
    
    def set_ellipse_indicators(self, painter):
        if (
            not self.show_ellipses or 
            not hasattr(self, 'ellipse_buffer') or 
            not self.ellipse_buffer
        ):
            return
        
        """
            Draw all ellipse groups in the buffer (from oldest to newest)
        """
        for ellipse_group in self.ellipse_buffer:
            color_groups = {}
            for grid_data in ellipse_group:
                color = grid_data['color']
                if color not in color_groups:
                    color_groups[color] = []
                color_groups[color].append(grid_data['grid'])
            
            for color, grid_list in color_groups.items():
                if len(grid_list) >= 2:
                    self.set_ellipse_for_group(painter, grid_list, color)
    
    def set_ellipse_for_group(self, painter, grid_list, color):
        points = []
        for grid in grid_list:
            grid_info = self.maidenhead_to_lat_lon(grid)
            if grid_info:
                top_lat     = grid_info['max_lat']
                bottom_lat  = grid_info['min_lat']
                left_lon    = grid_info['min_lon']
                right_lon   = grid_info['max_lon']
                
                # Grid square corners
                corners = [
                    (top_lat, left_lon),      
                    (top_lat, right_lon),    
                    (bottom_lat, left_lon), 
                    (bottom_lat, right_lon) 
                ]
                
                offsets = [0, 360, -360] if self.zoom >= 2 else [0]
                for lat, lon in corners:
                    for offset in offsets:
                        try:
                            x, y = self.lat_lon_to_screen_stable(lat, lon + offset)
                            if (-50 <= x <= self.width() + 50 and -50 <= y <= self.height() + 50):
                                points.append((x, y))
                                break
                        except:
                            continue
        
        if len(points) < 1:
            return
            
        hull_points = self.convex_hull(points)
        
        if len(hull_points) < 1:
            return
            
        ellipse_path = self.create_ellipse_path(hull_points)
        
        # border_color = darken_color(QColor(color), 0.1)
        border_color = darken_color(QColor(color), 0.2)
        border_color.setAlpha(30)
        # fill_color = QColor(color)    
        fill_color = QColor(color)
        fill_color.setAlpha(40)
        
        pen = QPen(border_color)
        pen.setWidth(0)
        painter.setPen(pen)
        painter.fillPath(ellipse_path, QBrush(fill_color))
        painter.drawPath(ellipse_path)
    
    def convex_hull(self, points):
        def cross(o, a, b):
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
        
        points = sorted(set(points))
        if len(points) <= 1:
            return points
        
        lower = []
        for p in points:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)
        
        upper = []
        for p in reversed(points):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)
        
        return lower[:-1] + upper[:-1]
    
    def create_ellipse_path(self, hull_points):
        if len(hull_points) < 1:
            return QPainterPath()
        
        if len(hull_points) == 1:
            path = QPainterPath()
            x, y = hull_points[0]
            path.addEllipse(x - 10, y - 10, 20, 20)
            return path
        
        center_x = sum(p[0] for p in hull_points) / len(hull_points)
        center_y = sum(p[1] for p in hull_points) / len(hull_points)
        
        xx = sum((p[0] - center_x) ** 2 for p in hull_points) / len(hull_points)
        yy = sum((p[1] - center_y) ** 2 for p in hull_points) / len(hull_points)
        xy = sum((p[0] - center_x) * (p[1] - center_y) for p in hull_points) / len(hull_points)
        
        trace = xx + yy
        
        determinant = xx * yy - xy * xy
        
        lambda1 = (trace + math.sqrt(trace * trace - 4 * determinant)) / 2
        lambda2 = (trace - math.sqrt(trace * trace - 4 * determinant)) / 2
        
        if lambda1 < 0:
            lambda1 = 0
        if lambda2 < 0:
            lambda2 = 0
        
        if abs(xy) < 1e-10:
            angle = 0 if xx >= yy else math.pi / 2
        else:
            angle = math.atan2(lambda1 - xx, xy)
        
        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)
        
        max_major_positive = 0
        max_major_negative = 0
        max_minor_positive = 0
        max_minor_negative = 0
        
        for px, py in hull_points:
            dx = px - center_x
            dy = py - center_y
            
            proj_major = dx * cos_angle + dy * sin_angle
            proj_minor = -dx * sin_angle + dy * cos_angle
            
            if proj_major > 0:
                max_major_positive = max(max_major_positive, proj_major)
            else:
                max_major_negative = max(max_major_negative, abs(proj_major))
                
            if proj_minor > 0:
                max_minor_positive = max(max_minor_positive, proj_minor)
            else:
                max_minor_negative = max(max_minor_negative, abs(proj_minor))
        
        base_semi_major = max(max_major_positive, max_major_negative, 15)
        base_semi_minor = max(max_minor_positive, max_minor_negative, 15)
                
        padding_factor = 1  # Expands ellipse beyond the minimum encompassing size
        semi_major = base_semi_major * padding_factor
        semi_minor = base_semi_minor * padding_factor
        
        safety_padding = 1.15  # 15% extra padding to ensure coverage
        final_semi_major = semi_major * safety_padding
        final_semi_minor = semi_minor * safety_padding
        
        path = QPainterPath()
        
        num_points = 64
        for i in range(num_points + 1):
            t = 2 * math.pi * i / num_points
            
            cos_t = math.cos(t)
            sin_t = math.sin(t)
            
            x_local = final_semi_major * cos_t
            y_local = final_semi_minor * sin_t
            
            x_rotated = x_local * math.cos(angle) - y_local * math.sin(angle)
            y_rotated = x_local * math.sin(angle) + y_local * math.cos(angle)
            
            x = center_x + x_rotated
            y = center_y + y_rotated
            
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        
        path.closeSubpath()
        return path
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_G:
            self.show_grid = not self.show_grid
            self.update()
        elif event.key() == Qt.Key.Key_H:
            if len(self.highlighted_squares) > 0:
                self.set_highlighted_squares([])
            else:
                self.update_grid_squares_for_band()
        elif event.key() == Qt.Key.Key_C:
            self.set_highlighted_squares([])
        elif event.key() == Qt.Key.Key_E:
            self.show_ellipses = not self.show_ellipses
            self.update()
        else:
            super().keyPressEvent(event)
        
        self.save_grid_map_settings()
    
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
                self.apply_pan_movement(-delta.x(), -delta.y())
                
                if time_delta > 0:
                    velocity_x = -delta.x() / max(time_delta, 1) * 16
                    velocity_y = -delta.y() / max(time_delta, 1) * 16
                    
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
        self.blink_timer.stop()
        event.accept()

class GridMapWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(GUI_LABEL_VERSION + " - Grid Monitoring")
        self.setGeometry(100, 100, 1200, 800)
        
        self.map_widget = GridMapWidget()
        self.setCentralWidget(self.map_widget)
    
    def closeEvent(self, event):
        self.map_widget.closeEvent(event)
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    window = GridMapWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()