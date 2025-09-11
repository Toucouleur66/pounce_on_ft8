import sys
import math
import time
import platform
import os
import ctypes                

from datetime import datetime, timezone
from ctypes import wintypes
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSlider, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QWheelEvent, QMouseEvent, QKeyEvent, QColor, QBrush, QPen, QPainterPath, QPolygon, QCursor, QIcon

from custom_qlabel import CustomQLabel
from animated_toggle import AnimatedToggle
from animated_counter import AnimatedCounter
from tiles_manager import TileCache, TileDownloader
from theme_manager import ThemeManager
from tooltip import CustomToolTip
from custom_status_bar import CustomStatusBar
from context_menu_handler import ContextMenuHandler

from logger import get_logger

from utils import darken_color

from constants import (
    CURRENT_VERSION_NUMBER,
    CUSTOM_FONT,
    CUSTOM_FONT_SMALL,
    GUI_LABEL_VERSION,
    # Colors
    STATUS_MONITORING_COLOR,
    BG_COLOR_BLACK_ON_YELLOW,
    FG_COLOR_REGULAR_FOCUS,
    FG_COLOR_REGULAR_FOCUS,
    BG_COLOR_REGULAR_FOCUS,
    # Stylesheets
    QSLIDER_QSS,
    SLIDER_VALUE_LABEL_QSS,
    # Symbols
    LOTW_SYMBOL,
    QSL_RCVD_SYMBOL
)

log     = get_logger(__name__)

class GridMapWidget(QWidget):
    # Signal to emit message_uid when grid is clicked
    grid_clicked = pyqtSignal(str)  
    
    def __init__(self, main_gui=None):
        super().__init__()
        self.setMinimumSize(800, 600)
        self.setMouseTracking(True)  # Enable mouse tracking for tooltips
        
        # Context menu support
        self.main_gui = main_gui
        self.context_menu_handler = ContextMenuHandler(main_gui) if main_gui else None

        # Tooltip management
        self.tooltip_timer = QTimer()
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self.show_tooltip)
        self.current_tooltip_pos = None
        self.current_tooltip_grid = None
        self.custom_tooltip = None

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
        self.show_heatmap               = True
        self.show_worked                = True
        self.show_night                 = True
        self.grid_color                 = Qt.GlobalColor.red
        self.grid_text_color            = Qt.GlobalColor.gray
        
        # Test mode for night area
        self.test_time                  = None
        
        self.permanent_grids            = []
        self.worked_grids               = []
        self.confirmed_grids            = []
        self.new_grids                  = []
        self.operating_band             = None
        self.adif_data                  = {}

        # Buffer to store multiple heatmap groups
        self.heatmap_buffer             = []  
        self.max_heatmap_buffer_size    = 6
        
        # Heatmap caching for performance
        self.heatmap_cache              = {}
        self.heatmap_cache_key          = None

        self.max_possible_density       = 10.0
        self.influence_radius           = 250
        self.weight_scaling_factor      = 5.0

        self.new_grid_color_fill        = QColor(BG_COLOR_BLACK_ON_YELLOW)
        self.new_grid_border_color      = darken_color(self.new_grid_color_fill, 0.7)

        self.worked_grid_color_fill     = QColor(FG_COLOR_REGULAR_FOCUS)
        self.worked_grid_border_color   = darken_color(self.worked_grid_color_fill, 0.7)

        self.confirmed_color_fill       = QColor(91, 105, 171, 175)
        self.worked_color_fill          = QColor(255, 168, 180, 175)

        # First value is intensity
        # Viridis
        self.heatmap_gradient = {
            0.00: (64, 0, 128),
            0.20: (255, 0, 255),
            0.40: (0, 0, 255),  
            0.60: (0, 255, 0),  
            0.80: (255, 255, 0),
            1.00: (255, 0, 0)   
        }
    
        # Plasma
        self.heatmap_gradient = {
            0.00: (0, 0, 3),
            0.11: (23, 15, 60),
            0.22: (67, 15, 117),
            0.33: (113, 31, 129),
            0.44: (158, 46, 126),
            0.56: (203, 62, 113),
            0.67: (240, 96, 93),
            0.78: (252, 147, 102),
            0.89: (254, 201, 141),
            1.00: (251, 252, 191)
        }

        # Coolwarm
        self.heatmap_gradient = {
            0.00: (58, 76, 192),
            0.11: (92, 123, 229),
            0.22: (130, 165, 251),
            0.33: (170, 198, 253),
            0.44: (205, 217, 236),
            0.56: (233, 212, 201),
            0.67: (246, 183, 156),
            0.78: (241, 142, 112),
            0.89: (217, 88, 71),
            1.00: (179, 3, 38)
        }

        # Custom F5UKW v1 
        self.heatmap_gradient = {
            0.00: (58, 76, 192),
            0.11: (92, 123, 229),
            0.22: (130, 165, 251),
            0.33: (170, 198, 253),
            0.44: (205, 217, 236),
            0.56: (233, 212, 201),
            0.67: (246, 183, 156),
            0.78: (241, 142, 112),
            0.89: (217, 88, 71),
            1.00: (179, 3, 38)
        }

        # Custom F5UKW v2
        self.heatmap_gradient = {
            0.00: (153, 255, 255),  
            0.20: (0, 102, 255),    
            0.40: (204, 102, 153),  
            0.60: (153, 0, 255),    
            0.80: (102, 0, 153),    
            1.00: (0, 128, 0)       
        }
        
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
        self.setFocus()
        
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
            self.parent_app.save_unique_param('grid_map_show_heatmap', self.show_heatmap)
            self.parent_app.save_unique_param('grid_map_show_worked', self.show_worked)
            self.parent_app.save_unique_param('grid_map_show_night', self.show_night)

            self.parent_app.save_unique_param('grid_map_zoom', self.zoom)
            self.parent_app.save_unique_param('grid_map_center_lat', self.center_lat)
            self.parent_app.save_unique_param('grid_map_center_lon', self.center_lon)
    
    def load_grid_map_settings(self):
        self.show_grid      = True
        self.show_heatmap   = True
        self.show_worked    = True
        self.show_night     = True
        self.zoom           = 3
        self.center_lat     = 0.0
        self.center_lon     = 0.0
    
        if self.parent_app:
            params = self.parent_app.load_params()
            self.show_grid      = params.get('grid_map_show_grid', self.show_grid)
            self.show_heatmap   = params.get('grid_map_show_heatmap', self.show_heatmap)
            self.show_worked    = params.get('grid_map_show_worked', self.show_worked)
            self.show_night     = params.get('grid_map_show_night', self.show_night)

            self.zoom           = params.get('grid_map_zoom', self.zoom)
            self.center_lat     = max(-85, min(85, params.get('grid_map_center_lat', self.center_lat)))
            self.center_lon     = max(-180, min(180, params.get('grid_map_center_lon', self.center_lon)))
            
            self.center_pixel_offset_x = 0.0
            self.center_pixel_offset_y = 0.0
            
            self.validate_and_adjust_position()            
            self.apply_pan_movement(0, 0)
    
    def validate_and_adjust_position(self):
        center_tile_x, center_tile_y = self.deg2num(self.center_lat, self.center_lon, self.zoom)
        
        max_tile = 2 ** self.zoom
        
        visible_tiles_y = math.ceil(600 / self.tile_size) + 2  
        visible_tiles_x = math.ceil(800 / self.tile_size) + 2  
        
        min_safe_tile_y = visible_tiles_y // 2 + 1
        max_safe_tile_y = max_tile - (visible_tiles_y // 2) - 1
        
        if center_tile_y < min_safe_tile_y:
            safe_lat, _ = self.num2deg(center_tile_x, min_safe_tile_y, self.zoom)
            self.center_lat = safe_lat
        elif center_tile_y > max_safe_tile_y:
            safe_lat, _ = self.num2deg(center_tile_x, max_safe_tile_y, self.zoom)
            self.center_lat = safe_lat
    
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
        half_width = self.width() / 2
        
        # Constrain vertical movement
        center_pixel_y = max(half_height, min(world_size - half_height, center_pixel_y))
        
        # Constrain horizontal movement to prevent edge jumping
        # Allow seamless wrapping by using modulo for horizontal positioning
        center_pixel_x = center_pixel_x % world_size
        if center_pixel_x < 0:
            center_pixel_x += world_size
        
        new_tile_x = center_pixel_x / self.tile_size
        new_tile_y = center_pixel_y / self.tile_size
        
        self.center_pixel_offset_x = (new_tile_x - int(new_tile_x)) * self.tile_size
        self.center_pixel_offset_y = (new_tile_y - int(new_tile_y)) * self.tile_size
        
        new_lat, new_lon = self.num2deg(new_tile_x, new_tile_y, self.zoom)
        
        # Constrain coordinates to valid bounds to prevent showing grey areas
        self.center_lat = max(-85, min(85, new_lat))
        # Allow longitude wrapping for seamless horizontal panning
        while new_lon > 180:
            new_lon -= 360
        while new_lon < -180:
            new_lon += 360
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
            
        # Draw worked grids first (lower opacity)
        for grid in self.worked_grids:
            self.fill_grid_square_with_color(painter, grid, self.worked_color_fill)
            
        # Draw confirmed grids on top (higher opacity)
        for grid in self.confirmed_grids:
            self.fill_grid_square_with_color(painter, grid, self.confirmed_color_fill)
        
        self.set_heatmap_indicators(painter)
        
        if self.new_grids:
            self.draw_new_grids_block(painter)
        
        if self.clicked_grid and self.blink_visible:
            self.draw_clicked_grid(painter)

    def wheelEvent(self, event: QWheelEvent):
        min_zoom = self.get_min_zoom_for_size(self.width(), self.height())
        
        zoom_delta = 1 if event.angleDelta().y() > 0 else -1
        new_zoom = self.zoom + zoom_delta
        
        new_zoom = max(min_zoom, min(16, new_zoom))
        
        if new_zoom != self.zoom:
            # Store current center position to maintain it during zoom
            current_center_lat = self.center_lat
            current_center_lon = self.center_lon
            
            self.zoom = new_zoom
            
            # Keep the same center coordinates instead of recalculating based on mouse position
            self.center_lat = current_center_lat
            self.center_lon = current_center_lon
            
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
            
            QApplication.processEvents()
            
            self.repaint()
            
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
        if not grid or len(grid) < 4:
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
        
        north   = max(top_left_lat, bottom_right_lat)
        south   = min(top_left_lat, bottom_right_lat)
        east    = max(top_left_lon, bottom_right_lon)
        west    = min(top_left_lon, bottom_right_lon)
        
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
    
    def get_solar_position(self, utc_time=None):
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
        # Negative because sun moves westward
        solar_longitude = -(utc_hours - 12.0) * 15.0  
        
        while solar_longitude > 180:
            solar_longitude -= 360
        while solar_longitude < -180:
            solar_longitude += 360
        
            
        return solar_declination, solar_longitude
    
    def set_test_time(self, hour, minute=0, second=0):
        """
            Set a test time for debugging night area display
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
            
        solar_lat, solar_lon = self.get_solar_position()
        
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
        
        if len(terminator_points) > 0:
            self.fill_night_area(painter, terminator_points, night_color, solar_lat, solar_lon)
        
        self.draw_terminator_line(painter, solar_lat, solar_lon)
    
    def fill_night_area(
            self,
            painter,
            terminator_points,
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
    
    def draw_grid_square_diagonal(self, painter, grid_square, highlight_color, border_color):       
        grid_info = self.maidenhead_to_lat_lon(grid_square)
        if not grid_info:
            return
            
        min_lat = grid_info['min_lat']
        max_lat = grid_info['max_lat']
        min_lon = grid_info['min_lon']
        max_lon = grid_info['max_lon']
    
        top_left_x, top_left_y         = self.lat_lon_to_screen_stable(max_lat, min_lon)
        top_right_x, top_right_y       = self.lat_lon_to_screen_stable(max_lat, max_lon)
        bottom_left_x, bottom_left_y   = self.lat_lon_to_screen_stable(min_lat, min_lon)
        bottom_right_x, bottom_right_y = self.lat_lon_to_screen_stable(min_lat, max_lon)
        
        if (max(top_left_x, top_right_x, bottom_left_x, bottom_right_x) >= -50 and
            min(top_left_x, top_right_x, bottom_left_x, bottom_right_x) <= self.width() + 50 and
            max(top_left_y, top_right_y, bottom_left_y, bottom_right_y) >= -50 and
            min(top_left_y, top_right_y, bottom_left_y, bottom_right_y) <= self.height() + 50):
            
            rect_x = int(min(top_left_x, top_right_x, bottom_left_x, bottom_right_x))
            rect_y = int(min(top_left_y, top_right_y, bottom_left_y, bottom_right_y))
            rect_width = int(max(top_left_x, top_right_x, bottom_left_x, bottom_right_x) - rect_x) 
            rect_height = int(max(top_left_y, top_right_y, bottom_left_y, bottom_right_y) - rect_y)
            
            triangle_points = [
                QPoint(rect_x + rect_width, rect_y),               # top-right
                QPoint(rect_x, rect_y + rect_height),              # bottom-left
                QPoint(rect_x + rect_width, rect_y + rect_height)  # bottom-right
            ]
            
            triangle_polygon = QPolygon(triangle_points)
            
            highlight_brush = QBrush(highlight_color)
            pen = QPen(border_color)
            pen.setWidth(1)
            painter.setBrush(highlight_brush)
            painter.setPen(pen)
            painter.drawPolygon(triangle_polygon)                        
    
    def fill_grid_square_with_color(self, painter, grid, color):
        self.draw_grid_square(painter, grid, color)
        # self.draw_grid_square_diagonal(painter, grid, color, color)
    
    def draw_new_grids_block(self, painter):
        for grid in self.new_grids:
            grid_square = grid['grid']
            
            # Skip the clicked grid if it's currently blinking
            if self.clicked_grid and grid_square == self.clicked_grid:
                continue            
                        
            if self.show_worked and (
                grid_square in self.confirmed_grids
                or grid_square in self.worked_grids
            ):
                self.draw_grid_square(
                    painter,
                    grid_square,
                    self.worked_grid_color_fill,
                    self.worked_grid_border_color
                )
            else:
                # Draw regular rectangle for highlighted grid
                self.draw_grid_square(
                    painter,
                    grid_square,
                    self.new_grid_color_fill,
                    self.new_grid_border_color
                )
    
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
        self.update_grids_for_band()
        if hasattr(self.parent(), 'update_toggle_labels'):
            self.parent().update_toggle_labels()
    
    def update_operating_band(self, band):
        last_band = self.operating_band
        self.operating_band = band
        log.debug(f"GridMapWidget: Band changed from {last_band} to {band}")
        
        self.update_grids_for_band()            
        
        if last_band != band:
            log.debug(f"GridMapWidget: Clearing new grids for band change [ {last_band} ] to [ {band} ]")
            self.clear_new_grids()        
            self.clear_heatmap_indicators()

        if hasattr(self.parent(), 'update_toggle_labels'):
            self.parent().update_toggle_labels()
    
    def update_grids_for_band(self):
        if not self.operating_band or not self.adif_data:
            self.worked_grids    = []
            self.confirmed_grids = []
            return

        """
            Update the highlighted squares based on the current band and ADIF data.
        """
        band_data = self.adif_data.get('grid', {}).get(self.operating_band, {})
        
        confirmed_grids = []
        worked_grids = []
        
        # Process each grid's QSO data to separate confirmed/worked
        for grid_square, qso_list in band_data.items():
            if isinstance(qso_list, list):
                has_confirmed = any(qso.get('qsl_status', False) for qso in qso_list)
                
                # Priority: if ANY QSO is confirmed, the grid is confirmed, otherwise worked
                if has_confirmed:
                    confirmed_grids.append(grid_square)
                else:
                    worked_grids.append(grid_square)
        
        # Update the separate lists
        self.confirmed_grids = confirmed_grids
        self.worked_grids = worked_grids
        
        self.update()

        window = self.parent()
        while window and not isinstance(window, GridMapWindow):
            window = window.parent()
        if window and hasattr(window, 'check_grid_monitoring_status'):
            window.check_grid_monitoring_status()

        if hasattr(self.parent(), 'update_toggle_labels'):
            self.parent().update_toggle_labels()            
    
    def set_new_grids(self, grids, center_on_last=False):
        try:
            if self.blink_timer:
                self.blink_timer.stop()
            
            self.set_heatmap_group_indicators(grids)       

            self.new_grids = []
            self.blink_count = 0
            self.blink_visible = True
            
            unique_grids = []

            if grids:            
                seen_grids = set()
                for grid_data in grids:
                    # More robust grid key extraction
                    grid_key = grid_data.get('grid')
                    if grid_key and grid_key not in seen_grids:
                        seen_grids.add(grid_key)
                        unique_grids.append(grid_data)            

            self.new_grids = unique_grids
            
            # Handle centering operation separately to avoid blocking
            if len(unique_grids) > 0 and center_on_last:
                try:
                    last_grid = grids[-1].get('grid')
                    if last_grid:
                        grid_info = self.maidenhead_to_lat_lon(last_grid, adjust_for_view=False)
                        if grid_info:
                            self.center_lat = grid_info['center_lat']
                            self.center_lon = grid_info['center_lon']
                            self.center_pixel_offset_x = 0.0
                            self.center_pixel_offset_y = 0.0
                            self.apply_pan_movement(0, 0)
                except Exception as e:
                    log.error(f"Error centering on grid: {e}")
                        
            if grids and self.blink_timer:
                self.blink_timer.start(300)  
            
            self.update()            
        except Exception as e:
            log.error(f"Error to handle grids: {e}")
            self.update()
        finally:
            grid_count = len(grids) if grids else 0
            
            # Update status bar when grids change
            window = self.parent()
            while window and not isinstance(window, GridMapWindow):
                window = window.parent()
            if window and hasattr(window, 'check_grid_monitoring_status'):
                window.check_grid_monitoring_status()
    
    def clear_new_grids(self):
        self.set_new_grids([])
        
        if hasattr(self.parent(), 'update_toggle_labels'):
            self.parent().update_toggle_labels()
    
    def clear_heatmap_indicators(self):
        self.heatmap_buffer     = []
        self.heatmap_cache      = {}
        self.heatmap_cache_key  = None
        self.update()
    
    def set_heatmap_group_indicators(self, grids):
        grid_count = len(grids) if grids else 0       
        if grids:
            grids.sort(key=lambda grid: grid['priority'])            
            self.heatmap_buffer.append(grids)

            if len(self.heatmap_buffer) > self.max_heatmap_buffer_size:
                self.heatmap_buffer.pop(0)  

        self.update()
    
    def get_heatmap_buffer_info(self):
        return {
            'count'     : len(self.heatmap_buffer),
            'max_size'  : self.max_heatmap_buffer_size,
            'is_full'   : len(self.heatmap_buffer) >= self.max_heatmap_buffer_size
        }
    
    def set_heatmap_indicators(self, painter):
        if (
            not self.show_heatmap or 
            not hasattr(self, 'heatmap_buffer') or 
            not self.heatmap_buffer
        ):
            return
        
        """
            Generate and draw heatmap visualization from grid data
        """
        # Collect all grid data with their weights
        grid_density = {}
        
        for heatmap_group in self.heatmap_buffer:
            for grid_data in heatmap_group:
                grid_square = grid_data['grid']
                priority    = grid_data.get('priority', 1)
                
                # Use priority as weight for density calculation (minimum 1)
                weight = max(priority, 1)
                
                if grid_square in grid_density:
                    grid_density[grid_square]['weight'] += weight
                    grid_density[grid_square]['count'] += 1
                else:
                    grid_density[grid_square] = {
                        'weight': weight,
                        'count': 1
                    }
       
        if grid_density:
            try:
                self.draw_coordinate_based_heatmap(painter, grid_density)
            except Exception as e:
                log.error(f"Heatmap generation failed: {e}")
                
    def draw_coordinate_based_heatmap(self, painter, grid_density):
        """
            Draw density-based heatmap showing areas with high concentration of grids
        """
        
        # Convert all grid positions to screen coordinates
        grid_positions = []
        for grid_square, data in grid_density.items():
            grid_info = self.maidenhead_to_lat_lon(grid_square, adjust_for_view=True)

            if not grid_info:
                continue
            
            center_lat = grid_info['center_lat']
            center_lon = grid_info['center_lon']
            weight = data['weight']
            
            # Convert to screen coordinates
            screen_x, screen_y = self.lat_lon_to_screen_stable(center_lat, center_lon)
            
            # Only include if visible on screen
            if (
                -200 <= screen_x <= self.width() + 200 and
                -200 <= screen_y <= self.height() + 200
            ):
                grid_positions.append({
                    'x': screen_x,
                    'y': screen_y,
                    'weight': weight,
                    'grid': grid_square
                })
        
        if not grid_positions:
            return
        
        # log.info(f"Calculating density for {len(grid_positions)} grid positions")
        
        # Create heatmap effect by drawing overlapping circles at grid positions
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        # For each grid position, calculate its local density and draw accordingly
        for grid_pos in grid_positions:
            # Calculate density at this position based on nearby grids
            density = self.calculate_local_density(grid_pos, grid_positions)
            
            # Use the grid's own weight as a multiplier
            intensity = min(density * (grid_pos['weight'] / self.weight_scaling_factor), 1.0)

            
            # Draw the heatmap blob
            self.draw_heatmap_blob(painter, grid_pos['x'], grid_pos['y'], intensity)
        
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    
    def calculate_local_density(self, center_grid, all_grids):
        """
            Calculate density at a grid position based on proximity to other grids
        """
        density = 0.0
        # Pixels - grids within this distance influence density
        
        for other_grid in all_grids:
            # Calculate distance between grids
            dx = center_grid['x'] - other_grid['x']
            dy = center_grid['y'] - other_grid['y']
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance <= self.influence_radius:
                # Close grids contribute more to density
                if distance == 0:
                    # The grid itself
                    contribution = 1.0
                else:
                    # Inverse distance weighting with falloff
                    contribution = (self.influence_radius - distance) / self.influence_radius
                    contribution = contribution ** 2  # Square for steeper falloff
                
                # Weight the contribution by the other grid's importance
                weighted_contribution = contribution * (other_grid['weight'] / self.weight_scaling_factor)
                density += weighted_contribution
        
        # Normalize density to 0-1 range
        return min(density / self.max_possible_density, 1.0)
    
    def get_gradient_color(self, intensity):
        """
            Get color from configurable gradient based on intensity (0.0 to 1.0)
        """
        # Clamp intensity to valid range
        intensity = max(0.0, min(1.0, intensity))
        
        # Get sorted gradient keys
        thresholds = sorted(self.heatmap_gradient.keys())
        
        # Find the two colors to interpolate between
        lower_threshold = 0.0
        upper_threshold = 1.0
        lower_color = self.heatmap_gradient[0.0]
        upper_color = self.heatmap_gradient[1.0]
        
        for threshold in thresholds:
            if intensity <= threshold:
                upper_threshold = threshold
                upper_color = self.heatmap_gradient[threshold]
                break
            lower_threshold = threshold
            lower_color = self.heatmap_gradient[threshold]
        
        # If we're exactly at a threshold, return that color
        if intensity == lower_threshold:
            return QColor(*lower_color)
        if intensity == upper_threshold:
            return QColor(*upper_color)
            
        # Interpolate between the two colors
        if upper_threshold == lower_threshold:
            ratio = 0.0
        else:
            ratio = (intensity - lower_threshold) / (upper_threshold - lower_threshold)
        
        r = int(lower_color[0] + (upper_color[0] - lower_color[0]) * ratio)
        g = int(lower_color[1] + (upper_color[1] - lower_color[1]) * ratio)
        b = int(lower_color[2] + (upper_color[2] - lower_color[2]) * ratio)
        
        return QColor(r, g, b)
    
    def set_heatmap_gradient(self, gradient_dict):
        """
            Set a custom heatmap gradient
            gradient_dict format: {0.00: (255,0,255), 0.25: (0,0,255), ...}
        """
        self.heatmap_gradient = gradient_dict
        # Clear cache to force regeneration with new colors
        self.clear_heatmap_cache()
        self.update()
    
    def clear_heatmap_cache(self):
        self.heatmap_cache = {}
        self.heatmap_cache_key = None
    
    def draw_heatmap_blob(self, painter, center_x, center_y, intensity):
        """
            Draw a heatmap blob (gradient circle) at the specified screen position
        """
        # Get color from configurable gradient
        base_color = self.get_gradient_color(intensity)
        
        # Draw multiple overlapping circles for smooth gradient effect
        radii = [40, 25, 15, 8]  # Multiple sizes for gradient
        alphas = [20, 35, 55, 80]  # Increasing opacity toward center
        
        for radius, alpha in zip(radii, alphas):
            color = QColor(base_color)
            # Ensure minimum visibility - don't let alpha go below 25% of base alpha
            min_alpha = alpha * 0.25
            final_alpha = max(min_alpha, alpha * intensity)
            color.setAlpha(int(final_alpha))
            
            brush = QBrush(color)
            painter.setBrush(brush)
            painter.setPen(Qt.PenStyle.NoPen)
            
            # Draw circle centered at the grid position
            painter.drawEllipse(
                int(center_x - radius), 
                int(center_y - radius), 
                radius * 2, 
                radius * 2
            )
    
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
        elif event.key() == Qt.Key.Key_H:
            if hasattr(window, 'toggle_heatmap'):
                new_state = not self.show_heatmap
                window.toggle_heatmap(new_state)
                if hasattr(window, 'heatmap_toggle'):
                    window.heatmap_toggle.setChecked(new_state)
            else:
                self.show_heatmap = not self.show_heatmap
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
        """
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
        """

        self.save_grid_map_settings()
    
    def mousePressEvent(self, event: QMouseEvent):
        # Ensure we have focus when clicked
        self.setFocus()
        
        # Hide tooltip when clicking
        self.tooltip_timer.stop()
        self.hide_custom_tooltip()
        
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_pressed = True
            self.has_moved = False
            self.last_pan_point = event.pos()
            self.pan_velocity = QPoint(0, 0)
            self.last_pan_time = time.time() * 1000
        elif event.button() == Qt.MouseButton.RightButton:
            # Handle right-click for context menu
            self.handle_context_menu(event.pos())
    
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
        else:
            # Handle tooltip for permanent squares when not dragging
            self.handle_mouse_hover(event.pos())
    
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

        for grid_data in self.new_grids:
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
    
    def handle_context_menu(self, pos):
        """Handle right-click context menu for grids"""
        if not self.context_menu_handler:
            return
            
        # Find grid data at click position (same logic as handle_grid_click)
        lat, lon = self.screen_to_lat_lon(pos.x(), pos.y())

        for grid_data in self.new_grids:
            grid_square = grid_data['grid']
            grid_info = self.maidenhead_to_lat_lon(grid_square, adjust_for_view=True)

            if not grid_info:
                continue
            
            screen_coords = []
            for lat_coord in [grid_info['min_lat'], grid_info['max_lat']]:
                for lon_coord in [grid_info['min_lon'], grid_info['max_lon']]:
                    x, y = self.lat_lon_to_screen_stable(lat_coord, lon_coord)
                    screen_coords.append(f"({x:.0f},{y:.0f})")            
                
            min_screen_x = min(float(coord.split(',')[0][1:]) for coord in screen_coords)
            max_screen_x = max(float(coord.split(',')[0][1:]) for coord in screen_coords)
            min_screen_y = min(float(coord.split(',')[1][:-1]) for coord in screen_coords)
            max_screen_y = max(float(coord.split(',')[1][:-1]) for coord in screen_coords)
            
            click_x = pos.x()
            click_y = pos.y()
            
            if (min_screen_x <= click_x <= max_screen_x and
                min_screen_y <= click_y <= max_screen_y):
                # Found a grid at this position, show context menu
                self.context_menu_handler.show_context_menu(self, pos, grid_data, "grid")
                return
    
    def handle_mouse_hover(self, pos):
        """
            Handle mouse hover to show tooltips for permanent squares and highlighted grids
        """
        grid_square = self.find_permanent_square_at_position(pos)

        # If no permanent square found, check for highlighted grids
        if not grid_square:
            grid_square = self.find_new_grid_at_position(pos)
        
        if grid_square:
            # If hovering over the same grid, don't restart timer
            if grid_square == self.current_tooltip_grid:
                return
            
            # Stop current timer and start new one
            self.tooltip_timer.stop()
            self.current_tooltip_pos = pos
            self.current_tooltip_grid = grid_square
            self.tooltip_timer.start(0) 
        else:
            # Mouse moved away from permanent squares and highlighted grids
            self.tooltip_timer.stop()
            self.current_tooltip_grid = None
            self.hide_custom_tooltip()
    
    def show_tooltip(self):
        """
            Show tooltip after delay
        """
        if self.current_tooltip_grid and self.current_tooltip_pos:        
            qso_datas        = self.get_qso_datas_for_grid(self.current_tooltip_grid)
            highlighted_data = self.get_new_grid_data(self.current_tooltip_grid)

            tooltip_html = []

            if highlighted_data:
                tooltip_html.append(f"Decoded Grid: <b>{self.current_tooltip_grid}</b>")
                tooltip_html.append(f"""
                <table border="1" cellpadding="3" cellspacing="0" style="border-collapse: collapse; font-size: 12px;">
                    <tr>
                        <td>Callsign</td>                    
                        <td>Time</td>
                        <td>Report</td>
                        <td>DT</td>
                        <td>Freq</td>
                    </tr>
                    <tr style="color: {FG_COLOR_REGULAR_FOCUS}; background-color: {BG_COLOR_REGULAR_FOCUS};">
                        <td><b>{highlighted_data['callsign']}</b></td>                        
                        <td>{highlighted_data['decode_time'].strftime("%H:%M:%S")}</td>                        
                        <td>{highlighted_data['snr']:+3d} dB</td>
                        <td>{highlighted_data['delta_time']:+5.1f}s</td>
                        <td>{highlighted_data['delta_freq']:+6d}Hz</td>
                    </tr>
                </table>
                """)

            if qso_datas: 
                if highlighted_data:
                    tooltip_html.append("""<br style=\"font-size: 6px;">""")
                    style = ""
                else:
                    style = f"""
                            style="color: #ffffff; background-color: #000000;"
                        """

                tooltip_html.append(f"Worded Grid: <b>{self.current_tooltip_grid}</b>")           
                tooltip_html.append(f"""
                <table border="1" cellpadding="3" cellspacing="0" style="border-collapse: collapse; font-size: 12px;">
                    <tr{style}>
                        <td>Callsign</td>
                        <td>Date</td>
                        <td>Freq</td>
                        <td>Mode</td>
                        <td>Sent</td>
                        <td>Rcvd</td>
                        <td>QSL</td>
                    </tr>
                """)                

                for qso in qso_datas:                    
                    freq_mhz = ""
                    if qso['freq']:
                        try:
                            freq_val = float(qso['freq'])
                            freq_mhz = f"{freq_val:.4f}"
                        except (ValueError, TypeError):
                            freq_mhz = str(qso['freq'])
                    
                    if qso['qsl_status']:
                        background_color = self.confirmed_color_fill.name()
                        font_color = "#ffffff"
                        qsl_rcvd = QSL_RCVD_SYMBOL
                        if qso['qsl_status'] == 'V':
                            qsl_rcvd += LOTW_SYMBOL
                    else:
                        background_color = self.worked_color_fill.name()
                        font_color = "#000000"
                        qsl_rcvd     = ''

                    tooltip_html.append(f"""
                    <tr style="background-color: {background_color}; color: {font_color};">
                        <td><b>{qso['call']}</b></td>
                        <td>{qso['formatted_date']}</td>
                        <td style="vertical-align: middle;"><small>{freq_mhz}</small></td>
                        <td>{qso['mode']}</td>
                        <td>{qso['rst_sent']}</td>
                        <td>{qso['rst_rcvd']}</td>
                        <td>{qsl_rcvd}</td>
                    </tr>
                    """)

                tooltip_html.append("</table>")

            tooltip_html = "\n".join(tooltip_html)

            if highlighted_data:
                self.custom_tooltip = CustomToolTip(
                    tooltip_html, 
                    "default",
                    bg_color = self.new_grid_color_fill.name() if not qso_datas else self.worked_grid_color_fill.name(),
                    fg_color = self.new_grid_border_color.name() if not qso_datas else self.worked_grid_border_color.name()
                )
            elif qso_datas:
                self.custom_tooltip = CustomToolTip(
                    tooltip_html,
                    "default"
                )
            if self.custom_tooltip:
                global_pos = self.mapToGlobal(self.current_tooltip_pos)
                self.custom_tooltip.showToolTip(global_pos)

    def hide_custom_tooltip(self):
        """
            Hide the custom tooltip
        """
        if self.custom_tooltip:
            self.custom_tooltip.hideToolTip()
            self.custom_tooltip = None
    
    def find_permanent_square_at_position(self, pos):
        """
            Find which permanent square is under the given position
        """
        # Check confirmed grids first
        for grid_square in self.confirmed_grids:
            if self.is_position_in_grid_square(pos, grid_square):
                return grid_square
        
        # Then check worked grids
        for grid_square in self.worked_grids:
            if self.is_position_in_grid_square(pos, grid_square):
                return grid_square
                
        # Finally check permanent grids for backward compatibility
        for grid_square in self.permanent_grids:
            if self.is_position_in_grid_square(pos, grid_square):
                return grid_square
        return None
    
    def find_new_grid_at_position(self, pos):
        """
            Find which highlighted grid is under the given position
        """
        for grid_data in self.new_grids:
            grid_square = grid_data['grid']
            if self.is_position_in_grid_square(pos, grid_square):
                return grid_square
        return None
    
    def get_new_grid_data(self, grid_square):
        """
            Get the data for a highlighted grid
        """
        for grid_data in self.new_grids:
            if grid_data['grid'] == grid_square:
                return grid_data
        return None
    
    def is_position_in_grid_square(self, pos, grid_square):
        """
            Check if a screen position is within the given grid square
        """
        grid_info = self.maidenhead_to_lat_lon(grid_square, adjust_for_view=True)
        if not grid_info:
            return False
        
        # Get screen coordinates for all corners of the grid square
        corners = [
            (grid_info['min_lat'], grid_info['min_lon']),
            (grid_info['min_lat'], grid_info['max_lon']),
            (grid_info['max_lat'], grid_info['min_lon']),
            (grid_info['max_lat'], grid_info['max_lon'])
        ]
        
        screen_coords = []
        for lat, lon in corners:
            x, y = self.lat_lon_to_screen_stable(lat, lon)
            screen_coords.append((x, y))
        
        min_x = min(coord[0] for coord in screen_coords)
        max_x = max(coord[0] for coord in screen_coords)
        min_y = min(coord[1] for coord in screen_coords)
        max_y = max(coord[1] for coord in screen_coords)
        
        return min_x <= pos.x() <= max_x and min_y <= pos.y() <= max_y
    
    def get_callsigns_for_grid(self, grid_square):
        """
            Get callsigns that have been worked in the given grid square
        """
        if not self.adif_data or not self.operating_band:
            return []
        
        callsigns = set()        
        grid_data = self.adif_data.get('grid', {}).get(self.operating_band, {})
        
        # Get QSO data for this grid
        if grid_square in grid_data and isinstance(grid_data[grid_square], list):
            for qso in grid_data[grid_square]:
                if qso.get('call'):
                    callsigns.add(qso['call'])

        return sorted(list(callsigns))[:10]  # Limit to 10 callsigns for tooltip
    
    def get_separated_callsigns_for_grid(self, grid_square):
        """
            Get confirmed and worked callsigns separately for the given grid square
            Priority: if a callsign has ANY confirmed QSO, it appears only in confirmed list
        """
        if not self.adif_data or not self.operating_band:
            return [], []
        
        all_calls = {}  # callsign -> has_confirmed_qso
        grid_data = self.adif_data.get('grid', {}).get(self.operating_band, {})
        
        # Get QSO data for this grid and track confirmed status per callsign
        if grid_square in grid_data and isinstance(grid_data[grid_square], list):
            for qso in grid_data[grid_square]:
                call = qso.get('call')
                if call:
                    if call not in all_calls:
                        all_calls[call] = False
                    if qso.get('qsl_status', False):
                        all_calls[call] = True
        
        # Separate based on priority: confirmed takes precedence
        confirmed_calls = [call for call, is_confirmed in all_calls.items() if is_confirmed]
        worked_calls = [call for call, is_confirmed in all_calls.items() if not is_confirmed]

        return sorted(confirmed_calls)[:10], sorted(worked_calls)[:10]
    
    def get_qso_datas_for_grid(self, grid_square):
        """
            Get detailed QSO information for the given grid square, sorted by date (newest first)
        """
        if not self.adif_data or not self.operating_band:
            return []
        
        grid_data = self.adif_data.get('grid', {}).get(self.operating_band, {})
        
        if grid_square in grid_data and isinstance(grid_data[grid_square], list):
            qso_map = {}  
            
            for qso in grid_data[grid_square]:
                qso_date = qso.get('qso_date', '')
                formatted_date = ''
                if qso_date and len(qso_date) >= 8:
                    try:
                        formatted_date = f"{qso_date[0:4]}-{qso_date[4:6]}-{qso_date[6:8]}"
                    except:
                        formatted_date = qso_date
                
                call = qso.get('call', '')
                dedup_key = f"{call}_{qso_date}"
                
                qso_detail = {
                    'call': call,
                    'qso_date': qso_date, 
                    'formatted_date': formatted_date, 
                    'freq': qso.get('freq', ''),
                    'mode': qso.get('mode', ''),
                    'rst_sent': qso.get('rst_sent', ''),
                    'rst_rcvd': qso.get('rst_rcvd', ''),
                    'qsl_status':  qso.get('qsl_status'),
                    'is_confirmed': bool(qso.get('qsl_status'))
                }
                
                if dedup_key in qso_map:
                    existing = qso_map[dedup_key]
                    if qso_detail['is_confirmed'] and not existing['is_confirmed']:
                        qso_map[dedup_key] = qso_detail
                else:
                    qso_map[dedup_key] = qso_detail
            
            qsos = list(qso_map.values())
            qsos.sort(key=lambda x: x['qso_date'] or '00000000', reverse=True)
            return qsos
        
        return []
    
    def leaveEvent(self, event):
        """
            Hide tooltip when mouse leaves the widget
        """
        self.tooltip_timer.stop()
        self.current_tooltip_grid = None
        self.hide_custom_tooltip()
        super().leaveEvent(event)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        min_zoom = self.get_min_zoom_for_size(self.width(), self.height())
        
        if self.zoom < min_zoom - 1:
            self.zoom = min_zoom
            self.memory_cache.clear()
            self.update()
    
    def closeEvent(self, event):
        self.tile_downloader.stop()
        self.blink_timer.stop()
        event.accept()

class GridMapWindow(QMainWindow):
    def __init__(self, main_gui=None):
        super().__init__()
        self.setWindowTitle(GUI_LABEL_VERSION + " - Grid Monitoring")
        self.setGeometry(100, 100, 1200, 800)
        self.main_gui = main_gui
        
        # Set window icon for Windows taskbar
        if platform.system() == 'Windows':
            if getattr(sys, 'frozen', False): 
                icon_path = os.path.join(sys._MEIPASS, "pounce.ico")
            else:
                icon_path = "pounce.ico"
            self.setWindowIcon(QIcon(icon_path))
            
            # Ensure proper taskbar grouping with main application
            try:
                # Define the necessary Windows structures and functions
                user32 = ctypes.windll.user32
                shell32 = ctypes.windll.shell32
                
                # This will be called after the window is shown to set proper taskbar properties
                def set_taskbar_properties():
                    try:
                        hwnd = int(self.winId())
                        if hwnd:
                            # Set window properties for proper taskbar handling
                            myappid = f"f5ukw.waitandpounce.{CURRENT_VERSION_NUMBER}"
                            # Use SHGetPropertyStoreForWindow to set AppUserModelID
                            pass  # The process-level AppUserModelID should be sufficient
                    except:
                        pass
                
                self._set_taskbar_properties = set_taskbar_properties
            except (ImportError, AttributeError):
                self._set_taskbar_properties = lambda: None
              
        self.map_widget = GridMapWidget(self.main_gui)
        
        self.status_bar = CustomStatusBar()
        self.status_bar_label_updated_grids         = CustomQLabel()
        self.status_bar_label_processing            = CustomQLabel()
        self.status_bar_label_last_decoded          = CustomQLabel()
        self.status_bar_label_band                  = CustomQLabel()
        self.status_bar_label_total_worked_grids    = CustomQLabel()
        self.status_bar_label_total_confirmed_grids = CustomQLabel()
        
        self.last_decode_time = None
        
        # Initialize animated counters for grid counts
        self.worked_counter = AnimatedCounter(duration_ms=3_000, parent=self)
        self.confirmed_counter = AnimatedCounter(duration_ms=3_000, parent=self)
        self.worked_counter.valueChanged.connect(self.update_grid_counts_from_animation)
        self.confirmed_counter.valueChanged.connect(self.update_grid_counts_from_animation)
        
        self.setup_main_layout()
        self.init_status_bar()
        
        # Timer to update status bar periodically
        self.status_bar_timer = QTimer(self)
        self.status_bar_timer.timeout.connect(self.check_grid_monitoring_status)
        self.status_bar_timer.start(5_000)  
        
        self.theme_manager = ThemeManager()
        self.theme_manager.theme_changed.connect(self.apply_theme_to_all)

        self.theme_timer = QTimer(self)
        self.theme_timer.timeout.connect(self.theme_manager.check_theme_change)
        self.theme_timer.start(1_000) 

        self.apply_theme_to_all(self.theme_manager.dark_mode)
        
        self.map_widget.setFocus()
        
    def setup_main_layout(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        main_layout.addWidget(self.map_widget)
        
        self.controls_widget = QWidget()
        self.controls_widget.setObjectName("controls_widget")        
        
        self.grid_toggle = AnimatedToggle(
            checked_color=STATUS_MONITORING_COLOR,
            pulse_checked_color=f"{STATUS_MONITORING_COLOR}FF"
        )
        self.grid_toggle.setFixedSize(self.grid_toggle.sizeHint())
        self.grid_toggle.setChecked(self.map_widget.show_grid)
        self.grid_toggle.stateChanged.connect(self.toggle_grid)
        
        self.worked_toggle = AnimatedToggle(
            checked_color=STATUS_MONITORING_COLOR,
            pulse_checked_color=f"{STATUS_MONITORING_COLOR}FF"
        )
        self.worked_toggle.setFixedSize(self.worked_toggle.sizeHint())
        self.worked_toggle.setChecked(self.map_widget.show_worked)
        self.worked_toggle.stateChanged.connect(self.toggle_worked)
        
        self.night_toggle = AnimatedToggle(
            checked_color=STATUS_MONITORING_COLOR,
            pulse_checked_color=f"{STATUS_MONITORING_COLOR}FF"
        )
        self.night_toggle.setFixedSize(self.night_toggle.sizeHint())
        self.night_toggle.setChecked(self.map_widget.show_night)
        self.night_toggle.stateChanged.connect(self.toggle_night)        
        
        self.heatmap_controls_widget = QWidget()
        self.heatmap_controls_widget.setFixedHeight(40)
        self.heatmap_controls_widget.setObjectName("HeatMapControlsWidget")
        
        self.heatmap_toggle = AnimatedToggle(
            checked_color=STATUS_MONITORING_COLOR,
            pulse_checked_color=f"{STATUS_MONITORING_COLOR}FF"
        )
        self.heatmap_toggle.setFixedSize(self.heatmap_toggle.sizeHint())
        self.heatmap_toggle.setChecked(self.map_widget.show_heatmap)
        self.heatmap_toggle.stateChanged.connect(self.toggle_heatmap)        
        
        self.density_slider = QSlider(Qt.Orientation.Horizontal)
        self.density_slider.setRange(10, 200) 
        self.density_slider.setValue(int(self.map_widget.max_possible_density * 10))
        self.density_slider.setFixedWidth(100)
        self.density_slider.setStyleSheet(QSLIDER_QSS)
        self.density_slider.valueChanged.connect(self.update_density)
        
        self.density_label = CustomQLabel(f"{self.map_widget.max_possible_density:.1f}")
        self.density_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.density_label.setStyleSheet(SLIDER_VALUE_LABEL_QSS)
        self.density_label.setFixedWidth(40)
        self.density_label.setFixedHeight(25)
        
        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(50, 1000)  
        self.radius_slider.setValue(self.map_widget.influence_radius)
        self.radius_slider.setFixedWidth(80)
        self.radius_slider.setStyleSheet(QSLIDER_QSS)
        self.radius_slider.valueChanged.connect(self.update_radius)        
        
        self.radius_label = CustomQLabel(f"{self.map_widget.influence_radius}")
        self.radius_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.radius_label.setStyleSheet(SLIDER_VALUE_LABEL_QSS)
        self.radius_label.setFixedHeight(25)
        self.radius_label.setFixedWidth(40)

        self.weight_slider = QSlider(Qt.Orientation.Horizontal)
        self.weight_slider.setRange(10, 100)  # 1.0 to 10.0 in 0.1 steps
        self.weight_slider.setValue(int(self.map_widget.weight_scaling_factor * 10))
        self.weight_slider.setFixedWidth(80)
        self.weight_slider.setStyleSheet(QSLIDER_QSS)
        self.weight_slider.valueChanged.connect(self.update_weight)

        self.weight_label = CustomQLabel(f"{self.map_widget.weight_scaling_factor:.1f}")
        self.weight_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.weight_label.setStyleSheet(SLIDER_VALUE_LABEL_QSS)
        self.weight_label.setFixedWidth(40)
        self.weight_label.setFixedHeight(25)
        
        heatmap_layout = QHBoxLayout(self.heatmap_controls_widget)
        heatmap_layout.setContentsMargins(0, 0, 0, 0)
        heatmap_layout.setSpacing(0)
        
        heatmap_layout.addStretch()
        heatmap_layout.addWidget(CustomQLabel("Density"))
        heatmap_layout.addSpacing(10)
        heatmap_layout.addWidget(self.density_slider)
        heatmap_layout.addSpacing(10)
        heatmap_layout.addWidget(self.density_label)
        heatmap_layout.addSpacing(15)
        heatmap_layout.addWidget(CustomQLabel("Radius"))
        heatmap_layout.addSpacing(10)
        heatmap_layout.addWidget(self.radius_slider)
        heatmap_layout.addSpacing(10)
        heatmap_layout.addWidget(self.radius_label)
        heatmap_layout.addSpacing(15)
        heatmap_layout.addWidget(CustomQLabel("Weight"))
        heatmap_layout.addSpacing(10)
        heatmap_layout.addWidget(self.weight_slider)
        heatmap_layout.addSpacing(10)
        heatmap_layout.addWidget(self.weight_label)

        # Set fixed height for controls widget
        self.controls_widget.setFixedHeight(50)
        
        # Main horizontal layout
        horizontal_layout = QHBoxLayout(self.controls_widget)
        horizontal_layout.setContentsMargins(10, 5, 10, 5)
        horizontal_layout.setSpacing(0) 

        # Left side: basic toggles
        horizontal_layout.addWidget(CustomQLabel("Grid square"))        
        horizontal_layout.addWidget(self.grid_toggle)        
        horizontal_layout.addSpacing(20)                
        horizontal_layout.addWidget(CustomQLabel("Grids"))
        horizontal_layout.addWidget(self.worked_toggle)
        horizontal_layout.addSpacing(20)        
        horizontal_layout.addWidget(CustomQLabel("Greyline"))                
        horizontal_layout.addWidget(self.night_toggle)
        horizontal_layout.addSpacing(20)
        horizontal_layout.addWidget(CustomQLabel("Heatmap"))
        horizontal_layout.addWidget(self.heatmap_toggle)
        horizontal_layout.addSpacing(20)
        
        # Add stretch to push heatmap controls to the right
        horizontal_layout.addStretch()
        
        # Right side: heatmap controls widget
        # horizontal_layout.addWidget(self.heatmap_controls_widget)
        
        self.update_heatmap_controls_opacity()
        
        main_layout.addWidget(self.controls_widget)
    
    def init_status_bar(self):
        self.setStatusBar(self.status_bar)

        for label in (
            self.status_bar_label_updated_grids,
            self.status_bar_label_processing,
            self.status_bar_label_last_decoded,
            self.status_bar_label_band,
            self.status_bar_label_total_worked_grids,
            self.status_bar_label_total_confirmed_grids
        ):
            label.setMouseTracking(True)
            label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            label.setStyleSheet(f"""
                QLabel {{
                    font-family: {CUSTOM_FONT_SMALL.family()};
                    font-size: {CUSTOM_FONT_SMALL.pointSize()}pt;            
                    padding-left: 5px;
                    padding-right: 5px;      
                    border: none;
                }}
            """)
        
        self.status_bar.addWidget(self.status_bar_label_updated_grids)       
        self.status_bar_label_updated_grids.setFixedWidth(90)
        self.status_bar.addWidget(self.status_bar_label_processing, 1)   
        self.status_bar.addWidget(self.status_bar_label_last_decoded, 2)                 
        self.status_bar.addWidget(self.status_bar_label_band)
        self.status_bar_label_band.setFixedWidth(80)
        self.status_bar.addWidget(self.status_bar_label_total_worked_grids)
        self.status_bar_label_total_worked_grids.setFixedWidth(100)
        self.status_bar.addWidget(self.status_bar_label_total_confirmed_grids)
        self.status_bar_label_total_confirmed_grids.setFixedWidth(100)     

        self.status_bar.setContentsMargins(10, 3, 10, 3)

    def update_status_bar_color(self, style):
        if hasattr(self, 'status_bar'):
            self.status_bar.setStyleSheet(style)
    
    def check_grid_monitoring_status(self):
        self.status_bar_label_updated_grids.setText(f"Buffered: {sum(len(group) for group in self.map_widget.heatmap_buffer)}")        

        if self.map_widget.operating_band:
            target_total_worked = len(self.map_widget.worked_grids) + len(self.map_widget.confirmed_grids) 
            target_confirmed    = len(self.map_widget.confirmed_grids)
            
            current_worked      = self.worked_counter.get_current_value()
            current_confirmed   = self.confirmed_counter.get_current_value()

            worked_changed      = abs(target_total_worked - current_worked) > 0
            confirmed_changed   = abs(target_confirmed - current_confirmed) > 0
            
            if worked_changed or confirmed_changed:
                if worked_changed:
                    self.worked_counter.animate_to(target_total_worked, current_worked)
                if confirmed_changed:
                    self.confirmed_counter.animate_to(target_confirmed, current_confirmed)
            else:
                self.update_grid_count_display(target_total_worked, target_confirmed)
    
    def update_grid_counts_from_animation(self):
        self.update_grid_count_display(
            self.worked_counter.get_current_value(),
            self.confirmed_counter.get_current_value()
        )
    
    def update_grid_count_display(self, worked_count, confirmed_count=None):
        if self.map_widget.operating_band:
            self.status_bar_label_band.setText(f"Band: <u>{self.map_widget.operating_band}</u>")
            self.status_bar_label_total_worked_grids.setText(f"Worked: {worked_count}")            
            if confirmed_count is not None:
                self.status_bar_label_total_confirmed_grids.setText(f"Confirmed: {confirmed_count}")            
    
    def update_toggle_labels(self):
        if hasattr(self, 'grid_toggle'):
            self.grid_toggle.setChecked(self.map_widget.show_grid)
        if hasattr(self, 'heatmap_toggle'):
            self.heatmap_toggle.setChecked(self.map_widget.show_heatmap)
        if hasattr(self, 'worked_toggle'):
            self.worked_toggle.setChecked(self.map_widget.show_worked)
        if hasattr(self, 'night_toggle'):
            self.night_toggle.setChecked(self.map_widget.show_night)
        
        # Update status bar labels
        self.check_grid_monitoring_status()
    
    def toggle_grid(self, checked):
        self.map_widget.show_grid = checked
        self.map_widget.update()
        self.map_widget.save_grid_map_settings()
    
    def toggle_heatmap(self, checked):
        self.map_widget.show_heatmap = checked
        self.map_widget.update()
        self.map_widget.save_grid_map_settings()
        self.update_heatmap_controls_opacity()
    
    def toggle_worked(self, checked):
        self.map_widget.show_worked = checked
        if checked:
            self.map_widget.update_grids_for_band()
        else:
            self.map_widget.worked_grids    = []
            self.map_widget.confirmed_grids = []
        
        # Redraw highlighted grids to apply/remove diagonal drawing
        self.map_widget.update()
    
    def toggle_night(self, checked):
        self.map_widget.show_night = checked
        self.map_widget.update()
        self.map_widget.save_grid_map_settings()
    
    def update_density(self, value):
        self.map_widget.max_possible_density = value / 10.0
        self.density_label.setText(f"{self.map_widget.max_possible_density:.1f}")
        self.map_widget.clear_heatmap_cache()
        self.map_widget.update()
    
    def update_radius(self, value):
        self.map_widget.influence_radius = value
        self.radius_label.setText(f"{self.map_widget.influence_radius}")
        self.map_widget.clear_heatmap_cache()
        self.map_widget.update()
    
    def update_weight(self, value):
        self.map_widget.weight_scaling_factor = value / 10.0
        self.weight_label.setText(f"{self.map_widget.weight_scaling_factor:.1f}")
        self.map_widget.clear_heatmap_cache()
        self.map_widget.update()
    
    def update_heatmap_controls_opacity(self):
        if hasattr(self, 'heatmap_controls_widget'):
            if self.map_widget.show_heatmap:
                self.heatmap_controls_widget.setEnabled(True)
                                
                self.heatmap_controls_widget.setGraphicsEffect(None)
                for child in self.heatmap_controls_widget.findChildren(QSlider):
                    child.setGraphicsEffect(None)
                for child in self.heatmap_controls_widget.findChildren(CustomQLabel):
                    child.setGraphicsEffect(None)
                    
            else:                
                self.heatmap_controls_widget.setEnabled(False)
                
                container_effect = QGraphicsOpacityEffect()
                container_effect.setOpacity(0.5)
                self.heatmap_controls_widget.setGraphicsEffect(container_effect)
                                
                for child in self.heatmap_controls_widget.findChildren(QSlider):
                    effect = QGraphicsOpacityEffect()
                    effect.setOpacity(0.5)
                    child.setGraphicsEffect(effect)
                    
                for child in self.heatmap_controls_widget.findChildren(CustomQLabel):
                    effect = QGraphicsOpacityEffect()
                    effect.setOpacity(0.5)
                    child.setGraphicsEffect(effect)
    
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

        self.heatmap_controls_widget.setStyleSheet(f"""
            QWidget#HeatMapControlsWidget {{                
                border-radius: 8px;
            }}
        """)
    
    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, '_set_taskbar_properties'):
            self._set_taskbar_properties()
    
    def activateEvent(self, event):
        super().activateEvent(event)
    
    def closeEvent(self, event):
        log.warning("Closing GridMapWindow")        
        if hasattr(self, 'status_bar_timer'):
            self.status_bar_timer.stop()
        if (
            hasattr(self.map_widget, 'parent_app') and 
            self.map_widget.parent_app and 
            not getattr(self.map_widget.parent_app, 'app_shutting_down', False)
        ):            
            self.map_widget.parent_app.update_grid_monitor_preference(False)
        self.map_widget.closeEvent(event)
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    window = GridMapWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()