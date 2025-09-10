# tooltip.py
import platform

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtGui import QTextDocument
from datetime import datetime

from constants import (
    CUSTOM_FONT,
    BG_COLOR_BLACK_ON_YELLOW,
    FG_COLOR_BLACK_ON_YELLOW,
    BG_COLOR_BLACK_ON_PURPLE,
    FG_COLOR_BLACK_ON_PURPLE,
    BG_COLOR_BLACK_ON_SAUMON,
    BG_COLOR_BLACK_ON_CYAN,
    FG_COLOR_BLACK_ON_CYAN,
    BG_COLOR_REGULAR_FOCUS,
    FG_COLOR_REGULAR_FOCUS
)

class TooltipManager:
    _instance = None
    _current_tooltip = None
    _focus_timer = None
    _main_window = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._setup_focus_monitoring()
        return cls._instance
    
    @classmethod
    def _setup_focus_monitoring(cls):
        if not cls._focus_timer:
            cls._focus_timer = QtCore.QTimer()
            cls._focus_timer.timeout.connect(cls._check_focus)
            cls._focus_timer.start(100) 
    
    @classmethod
    def _check_focus(cls):
        if cls._current_tooltip and not cls._is_app_really_active():
            cls.hide_current_tooltip()
    
    @classmethod
    def _is_app_really_active(cls):
        app = QtWidgets.QApplication.instance()
        if not app:
            return False
        
        focused_widget = app.focusWidget()
        if focused_widget:
            return True
        
        active_window = app.activeWindow()
        if active_window and active_window.isActiveWindow():
            return True
        
        for widget in app.allWidgets():
            if widget.isWindow() and widget.isActiveWindow():
                return True
        
        return False
    
    @classmethod
    def hide_current_tooltip(cls):
        if cls._current_tooltip:
            cls._current_tooltip.hideToolTip()
            cls._current_tooltip = None
    
    @classmethod
    def set_current_tooltip(cls, tooltip):
        cls.hide_current_tooltip()
        cls._current_tooltip = tooltip
    
    @classmethod
    def is_app_active(cls):
        return cls._is_app_really_active()

class CustomToolTip(QtWidgets.QWidget):
    def __init__(self, text, tooltip_type="default", bg_color=None, fg_color=None, parent=None):
        window_flags = QtCore.Qt.WindowType.ToolTip | QtCore.Qt.WindowType.FramelessWindowHint
        if platform.system() == 'Windows':
            window_flags |= QtCore.Qt.WindowType.WindowStaysOnTopHint
        elif platform.system() == 'Darwin':
            # On macOS, add flags to minimize border appearance
            window_flags |= QtCore.Qt.WindowType.WindowStaysOnTopHint | QtCore.Qt.WindowType.NoDropShadowWindowHint
        
        super().__init__(parent, window_flags)
        self.text = text
        self.tooltip_type = tooltip_type
        self.custom_bg_color = bg_color
        self.custom_fg_color = fg_color
        self.padding = 8
        # Reduce border radius on macOS for cleaner appearance
        self.radius = 1 if platform.system() == 'Darwin' else 3
        
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        
        # Additional attributes for macOS to minimize border
        if platform.system() == 'Darwin':
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow, False)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.setFont(CUSTOM_FONT)
        
        self.color_map = {
            "wanted_callsigns": (
                BG_COLOR_BLACK_ON_YELLOW,
                FG_COLOR_BLACK_ON_YELLOW
            ),
            "monitored_callsigns": (
                BG_COLOR_BLACK_ON_PURPLE,
                FG_COLOR_BLACK_ON_PURPLE
            ),
            "wanted_cq_zones": (
                BG_COLOR_BLACK_ON_SAUMON,
                FG_COLOR_BLACK_ON_YELLOW
            ),
            "monitored_cq_zones": (
                BG_COLOR_BLACK_ON_CYAN,
                FG_COLOR_BLACK_ON_CYAN
            ),
            "default": (
                BG_COLOR_REGULAR_FOCUS,
                FG_COLOR_REGULAR_FOCUS                
            )
        }
        
        self.adjustSize()

    def sizeHint(self):
        # Use QTextDocument to calculate proper size for HTML content
        doc = QTextDocument()
        doc.setDefaultFont(self.font())
        
        # Convert <br/> to <br> for proper HTML parsing
        html_text = self.text.replace("<br/>", "<br>")
        doc.setHtml(html_text)
        
        # Get the document size
        doc_size = doc.size()
        
        # Add padding
        width = int(doc_size.width()) + 2 * self.padding + 8
        height = int(doc_size.height()) + 2 * self.padding + 4
        
        return QtCore.QSize(width, height)
    
    def showToolTip(self, pos=None):
        if not TooltipManager.is_app_active():
            return
            
        TooltipManager.set_current_tooltip(self)
        
        self.adjustSize()
        if pos is None:
            pos = QtGui.QCursor.pos()
        
        # Find the screen that contains the tooltip position
        screen = QtWidgets.QApplication.screenAt(pos)
        if screen is None:
            screen = QtWidgets.QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        
        offset_x = 15
        offset_y = 20
        
        tooltip_rect = self.geometry()
        tooltip_rect.moveTopLeft(pos + QtCore.QPoint(offset_x, offset_y))
        
        if tooltip_rect.right() > screen_rect.right():
            tooltip_rect.moveTopLeft(pos + QtCore.QPoint(-tooltip_rect.width() - offset_x, offset_y))
        
        if tooltip_rect.bottom() > screen_rect.bottom():
            tooltip_rect.moveTopLeft(pos + QtCore.QPoint(offset_x, -tooltip_rect.height() - offset_y))
        
        if tooltip_rect.right() > screen_rect.right():
            tooltip_rect.moveRight(screen_rect.right() - 10)
        if tooltip_rect.bottom() > screen_rect.bottom():
            tooltip_rect.moveBottom(screen_rect.bottom() - 10)
        if tooltip_rect.left() < screen_rect.left():
            tooltip_rect.moveLeft(screen_rect.left() + 10)
        if tooltip_rect.top() < screen_rect.top():
            tooltip_rect.moveTop(screen_rect.top() + 10)
        
        self.move(tooltip_rect.topLeft())
        self.show()
    
    def hideToolTip(self):
        self.hide()
        if TooltipManager._current_tooltip == self:
            TooltipManager._current_tooltip = None
    
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(rect), self.radius, self.radius)
        
        self.setMask(QtGui.QRegion(path.toFillPolygon().toPolygon()))
        
        if self.custom_bg_color and self.custom_fg_color:
            bg_color, fg_color = self.custom_bg_color, self.custom_fg_color
        else:
            bg_color, fg_color = self.color_map.get(self.tooltip_type, self.color_map["default"])
        
        background_color = QtGui.QColor(bg_color)
        painter.fillPath(path, background_color)
        
        # Use QTextDocument for HTML rendering
        doc = QTextDocument()
        doc.setDefaultFont(self.font())
        
        # Convert <br/> to <br> for proper HTML parsing
        html_text = self.text.replace("<br/>", "<br>")
        
        # Set HTML content with custom styling
        html_content = f'<div style="color: {fg_color};">{html_text}</div>'
        doc.setHtml(html_content)
        
        # Set the document size to fit our text area
        text_rect = rect.adjusted(self.padding, self.padding, -self.padding, -self.padding)
        doc.setTextWidth(text_rect.width())
        
        # Translate painter to text position and draw
        painter.translate(text_rect.x(), text_rect.y())
        doc.drawContents(painter)

class ToolTip(QtWidgets.QWidget):
    def __init__(self, widget, source_widget=None, default_text='', tooltip_type="default", bg_color=None, fg_color=None):
        super().__init__()
        self.widget = widget
        self.source_widget = source_widget if source_widget is not None else widget
        self.default_text = default_text
        self.tooltip_type = tooltip_type
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.tooltip_window = None
        self.event_filter_installed = False
        
        self.show_timer = QtCore.QTimer()
        self.show_timer.setSingleShot(True)
        self.show_timer.timeout.connect(self._show_tooltip_delayed)
        self.show_delay = 0  
        
        self.mouse_over = False
        
        # Delay event filter installation to ensure widget is ready
        QtCore.QTimer.singleShot(100, self._install_event_filter)
    
    def _install_event_filter(self):
        if not self.event_filter_installed and self.widget:
            self.widget.installEventFilter(self)
            self.event_filter_installed = True

    def eventFilter(self, obj, event):
        if obj == self.widget:
            if event.type() == QtCore.QEvent.Type.Enter:
                self.mouse_over = True
                self.show_tooltip()
            elif event.type() == QtCore.QEvent.Type.Leave:
                self.mouse_over = False
                self.hide_tooltip()
        return super().eventFilter(obj, event)

    def show_tooltip(self):
        if not self.mouse_over:
            return
        
        TooltipManager.hide_current_tooltip()
        
        self.show_timer.stop()    
        self.show_timer.start(self.show_delay)
    
    def _show_tooltip_delayed(self):
        if not self.mouse_over or not TooltipManager.is_app_active():
            return
            
        if hasattr(self.source_widget, 'text'):
            raw_text = self.source_widget.text()
        else:
            raw_text = self.default_text
        
        if not raw_text:
            return

        text_parts = [part.strip() for part in raw_text.split(",") if part.strip()]
        tooltip_text = "<br/>".join(sorted(text_parts))
            
        if self.mouse_over:
            if self.tooltip_window:
                self.tooltip_window.hideToolTip()
            
            self.tooltip_window = CustomToolTip(tooltip_text, self.tooltip_type, self.bg_color, self.fg_color)
    
            cursor_pos = QtGui.QCursor.pos()
            self.tooltip_window.showToolTip(cursor_pos)

    def hide_tooltip(self):
        self.show_timer.stop()
        
        if self.tooltip_window:
            self.tooltip_window.hideToolTip()
            self.tooltip_window = None
        
        TooltipManager.hide_current_tooltip()

class ExcludedCallsignsToolTip(ToolTip):
    def __init__(
            self,
            widget,
            source_widget = None,
            default_text  = '',
            main_window   = None,
            band          = None,
            bg_color      = None,
            fg_color      = None
        ):
        super().__init__(widget, source_widget, default_text, "excluded_callsigns", bg_color, fg_color)
        self.main_window = main_window
        self.band = band
    
    def get_time_remaining_for_callsign(self, callsign):
        if not self.main_window or not self.band:
            return None
            
        temp_excluded = getattr(self.main_window, 'temp_excluded_callsigns', {})
        
        if self.band not in temp_excluded:
            return None
        
        callsign_upper = callsign.upper()
        if callsign_upper not in temp_excluded[self.band]:
            return None
            
        expiration_time = temp_excluded[self.band][callsign_upper]
        current_time = datetime.now()
        
        if current_time >= expiration_time:
            return None  # Already expired
            
        time_remaining = expiration_time - current_time
        
        # Convert to appropriate units
        total_minutes = int(time_remaining.total_seconds() // 60)
        
        if total_minutes < 60:
            return f"{total_minutes} min"
        elif total_minutes < 1440:  # Less than 24 hours
            hours = total_minutes // 60
            return f"{hours}h"
        elif total_minutes < 10080:  # Less than 7 days
            days = total_minutes // 1440
            return f"{days}d"
        else:  # 7 days or more
            weeks = total_minutes // 10080
            return f"{weeks}w"
    
    def _show_tooltip_delayed(self):
        if not self.mouse_over or not TooltipManager.is_app_active():
            return
            
        if hasattr(self.source_widget, 'text'):
            raw_text = self.source_widget.text()
        else:
            raw_text = self.default_text
        
        if not raw_text:
            return

        text_parts = [part.strip() for part in raw_text.split(",") if part.strip()]
        
        # Add time remaining for temporarily excluded callsigns
        enhanced_parts = []
        for callsign in text_parts:
            time_remaining = self.get_time_remaining_for_callsign(callsign)
            if time_remaining:
                enhanced_parts.append(f"{callsign} ({time_remaining} left)")
            else:
                enhanced_parts.append(callsign)
        
        tooltip_text = "<br/>".join(sorted(enhanced_parts))
            
        if self.mouse_over:
            if self.tooltip_window:
                self.tooltip_window.hideToolTip()
            
            self.tooltip_window = CustomToolTip(tooltip_text, self.tooltip_type, self.bg_color, self.fg_color)
            TooltipManager.set_current_tooltip(self.tooltip_window)
            self.tooltip_window.showToolTip()