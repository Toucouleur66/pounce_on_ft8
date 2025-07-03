import sys
import math
import time
from datetime import datetime, timezone

from constants import (
    CUSTOM_FONT,
    GUI_LABEL_VERSION,
    STATUS_MONITORING_COLOR,
    FG_COLOR_REGULAR_FOCUS,
    BG_COLOR_REGULAR_FOCUS
)

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QWheelEvent, QMouseEvent, QKeyEvent, QColor, QBrush, QPen, QPainterPath

from custom_qlabel import CustomQLabel
from animated_toggle import AnimatedToggle
from tiles_manager import TileCache, TileDownloader
from theme_manager import ThemeManager

from logger import get_logger

from utils import darken_color, complementary_color

log     = get_logger(__name__)

class GridMapWidget(QWidget):
    # Signal to emit message_uid when grid is clicked
    grid_clicked = pyqtSignal(str)  
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)

        self.zoom                       = 2
        self.center_lat                 = 0.0
        self.center_lon                 = 0.0
        self.tile_size                  = 256
        
        self.dragging                   = False
        self.mouse_pressed              = False
        self.has_moved                  = False
        self.last_pan_point             = QPoint()
        self.pan_velocity               = QPoint(0, 0)
        self.last_pan_time              = 0
        self.momentum_decay             = 0.92
        self.momentum_threshold         = 1.0
        
        self.center_pixel_offset_x      = 0.0
        self.center_pixel_offset_y      = 0.0
        
        self.show_grid                  = True
        self.show_ellipses              = True
        self.show_worked                = True
        self.show_night                 = True
        self.grid_color                 = Qt.GlobalColor.red
        self.grid_text_color            = Qt.GlobalColor.gray
        
        # Test mode for night area - set to None for normal operation
        self.test_time                  = None
        
        self.permanent_squares        = []
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
        self.clicked_grid               = None

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

        self.parent_app = None  
        self.load_grid_map_settings()
    
    def set_parent_app(self, parent_app):
        self.parent_app = parent_app
        self.load_grid_map_settings()
        
        # Update UI toggles to reflect loaded settings
        window = self.parent()
        while window and not isinstance(window, GridMapWindow):
            window = window.parent()
        if window and hasattr(window, 'update_toggle_labels'):
            window.update_toggle_labels()
    
    def save_grid_map_settings(self):
        if self.parent_app:
            self.parent_app.save_unique_param('grid_map_show_grid', self.show_grid)
            self.parent_app.save_unique_param('grid_map_show_ellipses', self.show_ellipses)
            self.parent_app.save_unique_param('grid_map_show_worked', self.show_worked)
            self.parent_app.save_unique_param('grid_map_show_night', self.show_night)

            self.parent_app.save_unique_param('grid_map_zoom', self.zoom)
            self.parent_app.save_unique_param('grid_map_center_lat', self.center_lat)
            self.parent_app.save_unique_param('grid_map_center_lon', self.center_lon)
    
    def load_grid_map_settings(self):
        self.show_grid      = True
        self.show_ellipses  = True
        self.show_worked    = True
        self.show_night     = True
        self.zoom           = 3
        self.center_lat     = 0.0
        self.center_lon     = 0.0
    
        if self.parent_app:
            params = self.parent_app.load_params()
            self.show_grid      = params.get('grid_map_show_grid', self.show_grid)
            self.show_ellipses  = params.get('grid_map_show_ellipses', self.show_ellipses)
            self.show_worked    = params.get('grid_map_show_worked', self.show_worked)
            self.show_night     = params.get('grid_map_show_night', self.show_night)

            self.zoom           = params.get('grid_map_zoom', self.zoom)
            self.center_lat     = params.get('grid_map_center_lat', self.center_lat)
            self.center_lon     = params.get('grid_map_center_lon', self.center_lon)
    
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
            Make sure to properly set the order of drawing elements (like Z-index).
        """
        self.draw_daylight_overlay(painter)
        
        if self.show_grid:
            self.draw_maidenhead_grid(painter)
            
        for square in self.permanent_squares:
            self.fill_grid_square_with_color(painter, square, QColor(91, 105, 171, 128))
        
        self.set_ellipse_indicators(painter)
        
        # Draw highlighted grids (always visible)
        if self.highlighted_grids:
            self.draw_highlighted_grids_block(painter)
        
        # Draw clicked grid with blinking effect (only the clicked one blinks)
        if self.clicked_grid and self.blink_visible:
            self.draw_clicked_grid(painter)

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
            
            # Save settings when zoom changes
            self.save_grid_map_settings()
    
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
    
    def maidenhead_to_lat_lon(self, grid, adjust_for_view=True):
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
            
            min_lon = subsquare_base_lon
            max_lon = subsquare_base_lon + (2.0/24.0)
            center_lon = subsquare_base_lon + (1.0/24.0)
            
            min_lat = subsquare_base_lat
            max_lat = subsquare_base_lat + (1.0/24.0)
            center_lat = subsquare_base_lat + (1.0/48.0)
        else:
            min_lon = square_base_lon
            max_lon = square_base_lon + 2.0
            center_lon = square_base_lon + 1.0
            
            min_lat = square_base_lat
            max_lat = square_base_lat + 1.0
            center_lat = square_base_lat + 0.5
        
        if adjust_for_view:
            _, view_center_lon = self.screen_to_lat_lon_stable(self.width()//2, self.height()//2)
            
            longitude_diff = view_center_lon - center_lon
            best_offset = round(longitude_diff / 360.0) * 360.0
            min_lon += best_offset
            max_lon += best_offset
            center_lon += best_offset
        
        return {
            'min_lat': min_lat,
            'max_lat': max_lat,
            'min_lon': min_lon,
            'max_lon': max_lon,
            'center_lat': center_lat,
            'center_lon': center_lon
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
            
            for lon_idx in range(start_lon_idx - buffer, end_lon_idx + buffer):
                for lat_idx in range(start_lat_idx - buffer, end_lat_idx + buffer):
                    square_sw_lat = grid_base_lat + lat_idx * unit_lat
                    square_ne_lat = square_sw_lat + unit_lat
                    
                    if not (-90 <= square_sw_lat < 90 and square_ne_lat >= south and square_sw_lat <= north):
                        continue
                    
                    square_sw_lon = grid_base_lon + lon_idx * unit_lon
                    square_ne_lon = square_sw_lon + unit_lon
                    
                    # Check if this grid square is visible in current view
                    is_visible = False
                    
                    if west <= east:
                        if square_ne_lon >= west and square_sw_lon <= east:
                            is_visible = True
                    else:
                        if square_ne_lon >= west or square_sw_lon <= east:
                            is_visible = True
                    
                    if not is_visible:
                        for offset in [360, -360]:
                            offset_sw = square_sw_lon + offset
                            offset_ne = square_ne_lon + offset
                            
                            if west <= east:
                                if offset_ne >= west and offset_sw <= east:
                                    square_sw_lon = offset_sw
                                    square_ne_lon = offset_ne
                                    is_visible = True
                                    break
                            else:
                                if (offset_ne >= west or offset_sw <= east):
                                    square_sw_lon = offset_sw
                                    square_ne_lon = offset_ne
                                    is_visible = True
                                    break
                    
                    if is_visible:
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
        
        # Track drawn labels to prevent duplicates
        drawn_labels = set()
        
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
                    
                    # Create a unique key for this label position to prevent duplicates
                    label_key = f"{grid_label}_{grid_type}"
                    
                    if (grid_label and label_key not in drawn_labels and
                        10 <= screen_center_x <= self.width() - 10 and 
                        10 <= screen_center_y <= self.height() - 10):
                        
                        drawn_labels.add(label_key)
                        
                        painter.setPen(self.grid_text_color)
                        
                        font_metrics = painter.fontMetrics()
                        text_width   = font_metrics.horizontalAdvance(grid_label)
                        text_height  = font_metrics.height()
                        text_ascent  = font_metrics.ascent()
                        
                        text_x = int(screen_center_x - text_width / 2.0)
                        text_y = int(screen_center_y - text_height / 2.0 + text_ascent)
                            
                        painter.drawText(text_x, text_y, grid_label)                        
    
    def get_grid_label(self, lat, lon, grid_type):
        normalized_lon = self.normalize_longitude(lon)
        full_grid = self.lat_lon_to_maidenhead(lat, normalized_lon)
        
        if grid_type == 'field':
            return full_grid[:2]
        elif grid_type == 'square':
            return full_grid[:4]
        elif grid_type == 'subsquare':
            return full_grid[:6]
        
        return full_grid
    
    def calculate_solar_position(self, utc_time=None):
        """
            Calculate the subsolar point (where the sun is directly overhead)
        """
        if utc_time is None:
            # Use test time if set, otherwise use current time
            if self.test_time is not None:
                utc_time = self.test_time
            else:
                utc_time = datetime.now(timezone.utc)
        
        j2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        delta = utc_time - j2000
        days_since_j2000 = delta.total_seconds() / 86400.0
        
        solar_declination = 23.45 * math.sin(math.radians((360/365.25) * (days_since_j2000 - 81)))
        
        utc_hours = utc_time.hour + utc_time.minute / 60.0 + utc_time.second / 3600.0
        solar_longitude = -(utc_hours - 12.0) * 15.0  # Negative because sun moves westward
        
        while solar_longitude > 180:
            solar_longitude -= 360
        while solar_longitude < -180:
            solar_longitude += 360
        
            
        return solar_declination, solar_longitude
    
    def set_test_time(self, hour, minute=0, second=0):
        """
            Set a test time for debugging night area display
            Args:
                hour: UTC hour (0-23)
                minute: UTC minute (0-59) 
                second: UTC second (0-59)
        """
        today = datetime.now(timezone.utc).date()
        self.test_time = datetime.combine(today, datetime.min.time().replace(
            hour=hour, minute=minute, second=second
        )).replace(tzinfo=timezone.utc)
        
        log.info(f"Test time UTC: {self.test_time.isoformat()}")
        
        self.update()
    
    def draw_daylight_overlay(self, painter):
        """
            Draw day/night overlay showing current daylight conditions
        """
        if not self.show_night:
            return
            
        solar_lat, solar_lon = self.calculate_solar_position()
        
        night_color = QColor(0, 0, 0, 50)
        
        self.draw_smooth_night_overlay(painter, solar_lat, solar_lon, night_color)
    
    def draw_smooth_night_overlay(self, painter, solar_lat, solar_lon, night_color):
        """
            Draw smooth night overlay using terminator curve calculation
        """        
        terminator_points = []
        
        _, left_lon = self.screen_to_lat_lon_stable(0, 0)
        _, right_lon = self.screen_to_lat_lon_stable(self.width(), self.height())
            
        if right_lon > left_lon:
            lon_range = (left_lon - 10, right_lon + 10)  
        else:
            lon_range = (left_lon - 10, right_lon + 370)  
        
        lon_step = 0.5  
        current_lon = lon_range[0]
        
        while current_lon <= lon_range[1]:        
            norm_lon = self.normalize_longitude(current_lon)
            
            terminator_lat = self.calculate_terminator_latitude(norm_lon, solar_lat, solar_lon)
            
            screen_x, screen_y = self.lat_lon_to_screen_stable(terminator_lat, current_lon)
            
            if -100 <= screen_x <= self.width() + 100:
                terminator_points.append((screen_x, screen_y, current_lon, terminator_lat))
            
            current_lon += lon_step
        
        if len(terminator_points) < 3:
            return
        
        terminator_path = QPainterPath()
        terminator_path.moveTo(terminator_points[0][0], terminator_points[0][1])
        
        for x, y, _, _ in terminator_points[1:]:
            terminator_path.lineTo(x, y)
        
        """
            Determine which side of terminator is night using solar position
            The night side is always away from the sun (opposite the solar longitude)
            If solar longitude is positive, night extends toward negative longitudes
            This is independent of current map view
        """
        solar_norm_lon = self.normalize_longitude(solar_lon)
        
        """
            Night area extends in the direction opposite to the sun
            If sun is in eastern hemisphere (lon >= 0), night extends westward (left)
            If sun is in western hemisphere (lon < 0), night extends eastward (right)
        """
        night_extends_left = solar_norm_lon < 0
        
        
        if len(terminator_points) > 0:
            self.fill_night_area(painter, terminator_path, terminator_points, night_extends_left, night_color, solar_lat, solar_lon)
        
        self.draw_terminator_line(painter, solar_lat, solar_lon)
    
    def fill_night_area(
            self,
            painter,
            terminator_path,
            terminator_points,
            night_extends_left,
            night_color,
            solar_lat,
            solar_lon
        ):
        screen_w, screen_h = self.width(), self.height()
        margin = 200

        full_rect = QPainterPath()
        full_rect.addRect(-margin, -margin, screen_w + 2*margin, screen_h + 2*margin)

        extended_points = []
        
        # Extend terminator line to left and right edges of screen
        # longitude of first point
        first_lon = terminator_points[0][2]  
        # longitude of last point
        last_lon = terminator_points[-1][2]  
        
        # Add points extending to the left edge
        extend_left_lon = first_lon - 10
        extend_left_lat = self.calculate_terminator_latitude(extend_left_lon, solar_lat, solar_lon)
        extend_left_x = -margin
        extend_left_y, _ = self.lat_lon_to_screen_stable(extend_left_lat, extend_left_lon)
        extended_points.append((extend_left_x, extend_left_y))
        
        # Add all terminator points
        extended_points.extend([(x, y) for x, y, _, _ in terminator_points])
        
        # Add points extending to the right edge  
        extend_right_lon = last_lon + 10
        extend_right_lat = self.calculate_terminator_latitude(extend_right_lon, solar_lat, solar_lon)
        extend_right_x = screen_w + margin
        extend_right_y, _ = self.lat_lon_to_screen_stable(extend_right_lat, extend_right_lon)
        extended_points.append((extend_right_x, extend_right_y))
        
        # Create the extended terminator path
        extended_terminator = QPainterPath()
        extended_terminator.moveTo(extended_points[0][0], extended_points[0][1])
        for x, y in extended_points[1:]:
            extended_terminator.lineTo(x, y)
        
        # Create day area by connecting terminator to appropriate screen edge
        day_path = QPainterPath(extended_terminator)
        
        # Determine which side of terminator is day based on terminator slope
        first_y = extended_points[0][1]
        last_y = extended_points[-1][1]
        terminator_slopes_down = last_y > first_y
        
        if terminator_slopes_down:
            # Terminator slopes down, day is above it
            day_path.lineTo(screen_w + margin, -margin)
            day_path.lineTo(-margin, -margin)
        else:
            # Terminator slopes up, day is below it  
            day_path.lineTo(screen_w + margin, screen_h + margin)
            day_path.lineTo(-margin, screen_h + margin)
        
        day_path.closeSubpath()

        night_path = full_rect.subtracted(day_path)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillPath(night_path, QBrush(night_color))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

    def get_visible_longitude_range(self, left_lon, right_lon):
        """
            Calculate the visible longitude range, handling 180°/-180° wrapping
        """
        if right_lon > left_lon:
            # Normal case: doesn't cross the date line
            return {'min': left_lon, 'max': right_lon, 'wraps': False}
        else:
            # Crosses the date line: left_lon > right_lon
            return {'min': left_lon, 'max': right_lon + 360, 'wraps': True}
    
    def generate_longitude_sequence(self, min_lon, max_lon, step):
        """
            Generate longitude sequence that handles wrapping
        """
        longitudes = []
        current = min_lon
        
        while current <= max_lon:
            longitudes.append(current)
            current += step
        
        return longitudes
    
    def normalize_longitude(self, lon):
        while lon > 180:
            lon -= 360
        while lon < -180:
            lon += 360
        return lon
    
    def draw_terminator_line(self, painter, solar_lat, solar_lon):
        painter.setPen(QPen(QColor(255, 255, 0, 0), 0))  
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        
        _, left_lon = self.screen_to_lat_lon_stable(0, 0)
        _, right_lon = self.screen_to_lat_lon_stable(self.width(), self.height())
        
        # Handle longitude wrapping
        lon_range = self.get_visible_longitude_range(left_lon, right_lon)
        
        terminator_points = []
        # Every 2 degrees for line drawing
        lon_step = 2.0  
        
        for lon in self.generate_longitude_sequence(lon_range['min'], lon_range['max'], lon_step):
            normalized_lon = self.normalize_longitude(lon)
            terminator_lat = self.calculate_terminator_latitude(normalized_lon, solar_lat, solar_lon)
            
            # Convert to screen coordinates
            screen_x, screen_y = self.lat_lon_to_screen_stable(terminator_lat, lon)
            
            # Check if point is visible on screen
            if -50 <= screen_x <= self.width() + 50 and -50 <= screen_y <= self.height() + 50:
                terminator_points.append((screen_x, screen_y))
        
        # Draw connected line segments
        if len(terminator_points) >= 2:
            terminator_path = QPainterPath()
            terminator_path.moveTo(terminator_points[0][0], terminator_points[0][1])
            
            for screen_x, screen_y in terminator_points[1:]:
                terminator_path.lineTo(screen_x, screen_y)
            
            painter.drawPath(terminator_path)
    
    def calculate_terminator_latitude(self, longitude, solar_lat, solar_lon):
        """
            Calculate the latitude of the solar terminator at a given longitude
        """
        hour_angle = math.radians(longitude - solar_lon)
        solar_lat_rad = math.radians(solar_lat)
        
        if abs(hour_angle) < 1e-10: # At subsolar longitude
            return solar_lat
        if abs(abs(hour_angle) - math.pi/2) < 1e-10:  # 90 degrees from subsolar
            return 0.0
        if abs(abs(hour_angle) - math.pi) < 1e-10:  # Opposite side of earth
            return -solar_lat
        
        try:
            if abs(solar_lat) < 1e-10:  # Solar declination near zero (equinox)
                return 0.0
                
            tan_lat = -(math.cos(solar_lat_rad) * math.cos(hour_angle)) / math.sin(solar_lat_rad)
            
            # Handle extreme values near poles
            if abs(tan_lat) > math.tan(math.radians(89.9)):
                # Near polar regions - return extreme latitude
                return 89.9 if tan_lat > 0 else -89.9
                
            terminator_lat = math.degrees(math.atan(tan_lat))
            
            # Clamp to reasonable bounds but allow closer to poles
            return max(-89.9, min(89.9, terminator_lat))
            
        except (ZeroDivisionError, ValueError):
            return 0.0
    
    def draw_grid_square(self, painter, grid_square, fill_color, border_color=None):
        if isinstance(fill_color, str):
            fill_color = QColor(fill_color)
            fill_color.setAlpha(255)
        
        grid_info = self.maidenhead_to_lat_lon(grid_square)
        if not grid_info:
            return
            
        min_lat = grid_info['min_lat']
        max_lat = grid_info['max_lat']
        min_lon = grid_info['min_lon']
        max_lon = grid_info['max_lon']
    
        top_left_x, top_left_y          = self.lat_lon_to_screen_stable(max_lat, min_lon)
        top_right_x, top_right_y        = self.lat_lon_to_screen_stable(max_lat, max_lon)
        bottom_left_x, bottom_left_y    = self.lat_lon_to_screen_stable(min_lat, min_lon)
        bottom_right_x, bottom_right_y  = self.lat_lon_to_screen_stable(min_lat, max_lon)
        
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
            
            if border_color:
                pen = QPen(border_color)
                pen.setWidth(1)
                painter.setPen(pen)
                painter.drawRect(rect_x, rect_y, rect_width - 1, rect_height - 1)
    
    def fill_grid_square_with_color(self, painter, grid_square, color):
        self.draw_grid_square(painter, grid_square, color)
    
    def draw_highlighted_grids_block(self, painter):
        for grid_color in self.highlighted_grids:
            grid_square     = grid_color['grid']
            
            # Skip the clicked grid if it's currently blinking
            if self.clicked_grid and grid_square == self.clicked_grid:
                continue
                
            color_hex       = grid_color['color']
            
            color           = QColor(color_hex)
            border_color    = darken_color(color, 0.5)
            fill_color       = complementary_color(color)
            fill_color.setAlpha(255) 
            
            self.draw_grid_square(painter, grid_square, fill_color, border_color)
    
    def draw_clicked_grid(self, painter):
        if not self.clicked_grid:
            return
            
        fill_color    = QColor(FG_COLOR_REGULAR_FOCUS) 
        border_color = QColor(BG_COLOR_REGULAR_FOCUS)  
        
        self.draw_grid_square(painter, self.clicked_grid, fill_color, border_color)
    
    def trigger_grid_blink(self, message_uid):
        if not message_uid:
            return
            
        if self.parent_app:
            row = self.parent_app.output_model.findRowByUid(message_uid)
            if row != -1:
                source_index = self.parent_app.output_model.index(row, 0)
                if source_index.isValid():
                    message_data = self.parent_app.output_model.data(source_index, Qt.ItemDataRole.UserRole)
                    if message_data and message_data.get('grid'):
                        self.clicked_grid = message_data.get('grid')
                        self.blink_count = 0
                        self.blink_visible = True
                        self.blink_timer.start(300)
    
    def update_status_menu_for_grid(self, message):
        # Get the parent window to access the main app
        window = self.parent()
        while window and not hasattr(window, 'map_widget'):
            window = window.parent()
        
        if window and hasattr(window, 'map_widget'):
            main_app = getattr(window.map_widget, 'parent_app', None)
            if main_app and hasattr(main_app, 'set_message_to_focus_value_label'):                
                main_app.set_message_to_focus_value_label(message)
    
    def blink_update(self):
        self.blink_visible = not self.blink_visible
        self.blink_count += 1
        self.update()
        
        if self.blink_count >= 20:
            self.blink_timer.stop()
            self.blink_count = 0
            self.blink_visible = True
            self.clicked_grid = None
            self.update()
    
    def update_adif_data(self, adif_data):
        self.adif_data = adif_data
        self.update_grid_squares_for_band()
        if hasattr(self.parent(), 'update_toggle_labels'):
            self.parent().update_toggle_labels()
    
    def update_current_band(self, band):
        if self.current_band != band:
            self.current_band = band
            self.update_grid_squares_for_band()
            if hasattr(self.parent(), 'update_toggle_labels'):
                self.parent().update_toggle_labels()
    
    def update_grid_squares_for_band(self):
        if not self.current_band or not self.adif_data:
            self.set_permanent_squares([])
            return

        """
            Update the highlighted squares based on the current band and ADIF data.
        """
        grid_squares = list(self.adif_data.get('grid', {}).get(self.current_band, {}).keys())

        self.set_permanent_squares(grid_squares, center_on_last=False)
    
    def set_permanent_squares(self, squares, center_on_last=True):
        self.permanent_squares = squares
        
        if len(squares) > 0 and center_on_last:
            last_square = squares[-1]
            grid_info = self.maidenhead_to_lat_lon(last_square, adjust_for_view=False)
            if grid_info:
                self.center_lat = grid_info['center_lat']
                self.center_lon = grid_info['center_lon']
                self.center_pixel_offset_x = 0.0
                self.center_pixel_offset_y = 0.0
                self.apply_pan_movement(0, 0)
        
        self.update()

        if hasattr(self.parent(), 'update_toggle_labels'):
            self.parent().update_toggle_labels()
    
    def set_highlighted_grids(self, grids, center_on_last=False):
        self.highlighted_grids = []
        
        self.blink_timer.stop()
        self.blink_count = 0
        self.blink_visible = True
        
        self.highlighted_grids = grids
        
        if len(grids) > 0 and center_on_last:
            last_grid = grids[-1]['grid']
            grid_info = self.maidenhead_to_lat_lon(last_grid, adjust_for_view=False)
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
        # Update status bar if parent has one
        if hasattr(self.parent(), 'update_toggle_labels'):
            self.parent().update_toggle_labels()
    
    def clear_ellipse_indicators(self):
        self.ellipse_buffer = []
        self.update()
    
    def add_ellipse_group_to_buffer(self, grids):
        if grids:
            unique_grids = []
            seen_grids = set()
            for grid_data in grids:
                grid_key = grid_data['grid']
                if grid_key not in seen_grids:
                    seen_grids.add(grid_key)
                    unique_grids.append(grid_data)
            
            self.ellipse_buffer.append(unique_grids)
            
            if len(self.ellipse_buffer) > self.max_ellipse_buffer_size:
                self.ellipse_buffer.pop(0)  
            
            self.update()
    
    def set_ellipse_group_indicators(self, grids):
         # Sort grids by priority (highest first) for proper z-index drawing
        grids.sort(key=lambda grid: grid['priority'])
        
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
                    color_groups[color] = {'grids': [], 'priority': grid_data.get('priority', 1)}
                color_groups[color]['grids'].append(grid_data['grid'])
            
            for color, group_info in color_groups.items():
                grid_list = group_info['grids']
                priority = group_info['priority']
                if len(grid_list) >= 2:
                    self.set_ellipse_for_group(painter, grid_list, color, priority)
    
    def set_ellipse_for_group(self, painter, grid_list, color, priority=1):
        points = []
        for grid in grid_list:
            grid_info = self.maidenhead_to_lat_lon(grid, adjust_for_view=True)
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
                        x, y = self.lat_lon_to_screen_stable(lat, lon + offset)
                        if (-50 <= x <= self.width() + 50 and -50 <= y <= self.height() + 50):
                            points.append((x, y))
                            break
        
        if len(points) < 1:
            return
            
        hull_points = self.convex_hull(points)
        
        if len(hull_points) < 1:
            return
            
        ellipse_path = self.create_ellipse_path(hull_points)
        
        if priority > 1:
            # Priority ellipses: Draw with overlay effect for better visibility
            # Step 1: Draw base ellipse with normal transparency
            base_border = darken_color(QColor(color), 0.2)
            base_border.setAlpha(30)
            base_fill = QColor(color)
            base_fill.setAlpha(40)
            
            pen = QPen(base_border)
            pen.setWidth(0)
            painter.setPen(pen)
            painter.fillPath(ellipse_path, QBrush(base_fill))
            painter.drawPath(ellipse_path)
            
            # Step 2: Add overlay effect - brighter center with gradient fade
            overlay_fill = QColor(color)
            overlay_fill.setAlpha(25)  # Lighter overlay
            
            # Create a slightly smaller ellipse for the overlay effect
            smaller_path = self.create_ellipse_path(hull_points, scale_factor=0.8)
            pen = QPen(Qt.PenStyle.NoPen)
            painter.setPen(pen)
            painter.fillPath(smaller_path, QBrush(overlay_fill))            
        else:
            # Priority 1: Draw normally with standard transparency
            border_color = darken_color(QColor(color), 0.2)
            border_color.setAlpha(30)
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
    
    def create_ellipse_path(self, hull_points, scale_factor=1.0):
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
                
        # Expands ellipse beyond the minimum encompassing size
        padding_factor = 1 
        semi_major = base_semi_major * padding_factor
        semi_minor = base_semi_minor * padding_factor
        
        # 15% extra padding to ensure coverage
        safety_padding = 1.15  
        final_semi_major = semi_major * safety_padding * scale_factor
        final_semi_minor = semi_minor * safety_padding * scale_factor
        
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
        window = self.window()  
        if event.key() == Qt.Key.Key_G:    
            if hasattr(window, 'toggle_grid'):
                new_state = not self.show_grid
                window.toggle_grid(new_state)
                if hasattr(window, 'grid_toggle'):
                    window.grid_toggle.setChecked(new_state)
            else:
                self.show_grid = not self.show_grid
                self.update()                
        elif event.key() == Qt.Key.Key_W:
            if hasattr(window, 'toggle_worked'):
                new_state = not self.show_worked
                window.toggle_worked(new_state)
                if hasattr(window, 'worked_toggle'):
                    window.worked_toggle.setChecked(new_state)
            else:
                self.show_worked = not self.show_worked
                self.update()            
        elif event.key() == Qt.Key.Key_N:
            if hasattr(window, 'toggle_ellipses'):
                new_state = not self.show_ellipses
                window.toggle_ellipses(new_state)
                if hasattr(window, 'ellipse_toggle'):
                    window.ellipse_toggle.setChecked(new_state)
            else:
                self.show_ellipses = not self.show_ellipses
                self.update()
        elif event.key() == Qt.Key.Key_L:
            if hasattr(window, 'toggle_night'):
                new_state = not self.show_night
                window.toggle_night(new_state)
                if hasattr(window, 'night_toggle'):
                    window.night_toggle.setChecked(new_state)
            else:
                self.show_night = not self.show_night
                self.update()
        elif sys.platform == 'darwin':
            if event.key() == Qt.Key.Key_1:
                self.set_test_time(6)  
            elif event.key() == Qt.Key.Key_2:
                self.set_test_time(12) 
            elif event.key() == Qt.Key.Key_3:
                self.set_test_time(13) 
            elif event.key() == Qt.Key.Key_4:
                self.set_test_time(0)  
            elif event.key() == Qt.Key.Key_0:
                self.test_time = None
                self.update()
        else:
            super().keyPressEvent(event)

        self.save_grid_map_settings()
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_pressed = True
            self.has_moved = False
            self.last_pan_point = event.pos()
            self.pan_velocity = QPoint(0, 0)
            self.last_pan_time = time.time() * 1000
    
    def mouseMoveEvent(self, event: QMouseEvent):
        if self.mouse_pressed:
            if not self.dragging:
                # Start dragging if mouse moved enough
                delta = event.pos() - self.last_pan_point
                if abs(delta.x()) > 3 or abs(delta.y()) > 3:
                    self.dragging = True
                    self.has_moved = True
            
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
                self.last_pan_time  = current_time
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            was_dragging        = self.dragging
            self.mouse_pressed  = False
            self.dragging       = False
            
            if not was_dragging and not self.has_moved:
                self.handle_grid_click(event.pos())
            elif was_dragging:
                # Save settings when panning ends
                self.save_grid_map_settings()
    
    def handle_grid_click(self, pos):
        lat, lon = self.screen_to_lat_lon(pos.x(), pos.y())

        for grid_data in self.highlighted_grids:
            grid_square = grid_data['grid']
            grid_info = self.maidenhead_to_lat_lon(grid_square, adjust_for_view=True)
            if not grid_info:
                continue
            
            screen_coords = []
            for lat in [grid_info['min_lat'], grid_info['max_lat']]:
                for lon in [grid_info['min_lon'], grid_info['max_lon']]:
                    x, y = self.lat_lon_to_screen_stable(lat, lon)
                    screen_coords.append(f"({x:.0f},{y:.0f})")            
                
            min_screen_x = min(float(coord.split(',')[0][1:]) for coord in screen_coords)
            max_screen_x = max(float(coord.split(',')[0][1:]) for coord in screen_coords)
            min_screen_y = min(float(coord.split(',')[1][:-1]) for coord in screen_coords)
            max_screen_y = max(float(coord.split(',')[1][:-1]) for coord in screen_coords)
            
            click_x = pos.x()
            click_y = pos.y()
            
            if (min_screen_x <= click_x <= max_screen_x and
                min_screen_y <= click_y <= max_screen_y):
                message_uid = grid_data.get('message_uid')
                if message_uid:
                    # Store clicked grid for blinking
                    self.clicked_grid = grid_square
                    self.blink_count = 0
                    self.blink_visible = True
                    self.blink_timer.start(300)
                    
                    # Emit grid click with message UID
                    self.grid_clicked.emit(message_uid)
                    
                    # Update status menu with this grid's information
                    self.update_status_menu_for_grid(grid_data)
                break
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        # Only adjust zoom if it's really too low for the window size
        # Allow some flexibility to preserve user's preferred zoom level
        min_zoom = self.get_min_zoom_for_size(self.width(), self.height())
        # Only force zoom adjustment if current zoom is significantly below minimum
        if self.zoom < min_zoom - 1:
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
        
        self.theme_manager = ThemeManager()
        self.theme_manager.theme_changed.connect(self.apply_theme_to_all)

        self.theme_timer = QTimer(self)
        self.theme_timer.timeout.connect(self.theme_manager.check_theme_change)
        self.theme_timer.start(1_000) 

        self.apply_theme_to_all(self.theme_manager.dark_mode)
        
        self.map_widget = GridMapWidget()
        
        self.setup_main_layout()
    
    def setup_main_layout(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        main_layout.addWidget(self.map_widget)
        
        self.controls_widget = QWidget()
        self.controls_widget.setObjectName("controls_widget")
        self.controls_widget.setFixedHeight(50)
        
        horizontal_layout = QHBoxLayout(self.controls_widget)
        horizontal_layout.setContentsMargins(10, 5, 10, 5)
        horizontal_layout.setSpacing(0) 
        horizontal_layout.addWidget(CustomQLabel("Grid maps"))
        
        self.grid_toggle = AnimatedToggle(
            checked_color=STATUS_MONITORING_COLOR,
            pulse_checked_color=f"{STATUS_MONITORING_COLOR}FF"
        )
        self.grid_toggle.setFixedSize(self.grid_toggle.sizeHint())
        self.grid_toggle.setChecked(self.map_widget.show_grid)
        self.grid_toggle.stateChanged.connect(self.toggle_grid)
        
        horizontal_layout.addWidget(self.grid_toggle)        
        horizontal_layout.addSpacing(20)        
        horizontal_layout.addWidget(CustomQLabel("Nowcast"))
        
        self.ellipse_toggle = AnimatedToggle(
            checked_color=STATUS_MONITORING_COLOR,
            pulse_checked_color=f"{STATUS_MONITORING_COLOR}FF"
        )
        self.ellipse_toggle.setFixedSize(self.ellipse_toggle.sizeHint())
        self.ellipse_toggle.setChecked(self.map_widget.show_ellipses)
        self.ellipse_toggle.stateChanged.connect(self.toggle_ellipses)
        
        horizontal_layout.addWidget(self.ellipse_toggle)
        horizontal_layout.addSpacing(20)        
        horizontal_layout.addWidget(CustomQLabel("Worked Grids"))
        
        self.worked_toggle = AnimatedToggle(
            checked_color=STATUS_MONITORING_COLOR,
            pulse_checked_color=f"{STATUS_MONITORING_COLOR}FF"
        )
        self.worked_toggle.setFixedSize(self.worked_toggle.sizeHint())
        self.worked_toggle.setChecked(self.map_widget.show_worked)
        self.worked_toggle.stateChanged.connect(self.toggle_worked)
        
        horizontal_layout.addWidget(self.worked_toggle)
        horizontal_layout.addSpacing(20)        
        horizontal_layout.addWidget(CustomQLabel("Greyline"))
        
        self.night_toggle = AnimatedToggle(
            checked_color=STATUS_MONITORING_COLOR,
            pulse_checked_color=f"{STATUS_MONITORING_COLOR}FF"
        )
        self.night_toggle.setFixedSize(self.night_toggle.sizeHint())
        self.night_toggle.setChecked(self.map_widget.show_night)
        self.night_toggle.stateChanged.connect(self.toggle_night)
        
        horizontal_layout.addWidget(self.night_toggle)
        horizontal_layout.addStretch() 
        
        main_layout.addWidget(self.controls_widget)
    
    def update_toggle_labels(self):
        if hasattr(self, 'grid_toggle'):
            self.grid_toggle.setChecked(self.map_widget.show_grid)
        if hasattr(self, 'ellipse_toggle'):
            self.ellipse_toggle.setChecked(self.map_widget.show_ellipses)
        if hasattr(self, 'worked_toggle'):
            self.worked_toggle.setChecked(self.map_widget.show_worked)
        if hasattr(self, 'night_toggle'):
            self.night_toggle.setChecked(self.map_widget.show_night)
    
    def toggle_grid(self, checked):
        self.map_widget.show_grid = checked
        self.map_widget.update()
        self.map_widget.save_grid_map_settings()
    
    def toggle_ellipses(self, checked):
        self.map_widget.show_ellipses = checked
        self.map_widget.update()
        self.map_widget.save_grid_map_settings()
    
    def toggle_worked(self, checked):
        self.map_widget.show_worked = checked
        if checked:
            self.map_widget.update_grid_squares_for_band()
        else:
            self.map_widget.set_permanent_squares([])
    
    def toggle_night(self, checked):
        self.map_widget.show_night = checked
        self.map_widget.update()
        self.map_widget.save_grid_map_settings()
    
    def check_theme_change(self):
        current_dark_mode = self.theme_manager.is_dark_apperance()
        if current_dark_mode != self.dark_mode:
            self.dark_mode = current_dark_mode
            self.apply_palette(self.dark_mode)

    def apply_theme_to_all(self, dark_mode):
        self.apply_palette(dark_mode)            
    
    def apply_palette(self, dark_mode):
        self.dark_mode = dark_mode
        
        if dark_mode:
            qt_bg_color = "#353535"
        else:
            qt_bg_color = "#E0E0E0"
        
        # Apply theme to main window
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {qt_bg_color};
            }}
        """)
    
    def closeEvent(self, event):
        # Trigger main app to save window positions (including this grid map window)
        if hasattr(self.map_widget, 'parent_app') and self.map_widget.parent_app:
            self.map_widget.parent_app.save_window_position()
        self.map_widget.closeEvent(event)
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    window = GridMapWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()