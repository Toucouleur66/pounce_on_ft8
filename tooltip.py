# tooltip.py
import platform

from PyQt6 import QtWidgets, QtCore, QtGui

from constants import (
    CUSTOM_FONT,
    BG_COLOR_BLACK_ON_YELLOW,
    FG_COLOR_BLACK_ON_YELLOW,
    BG_COLOR_BLACK_ON_PURPLE,
    FG_COLOR_BLACK_ON_PURPLE,
    BG_COLOR_BLACK_ON_SAUMON,
    BG_COLOR_BLACK_ON_CYAN,
    FG_COLOR_BLACK_ON_CYAN
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
            "default": ("#3498db", "#FFFFFF")
        }
        
        self.adjustSize()

    def sizeHint(self):
        fm = QtGui.QFontMetrics(self.font())
        text_lines = self.text.split("<br/>")
        max_width = 0
        
        for line in text_lines:
            line_width = fm.horizontalAdvance(line)
            max_width = max(max_width, line_width)
        
        # Add extra margin for text rendering
        width = max_width + 2 * self.padding + 8
        
        # Calculate height more accurately
        line_height = fm.height()
        line_spacing = 4
        
        # Total height: all lines + spacing between lines + padding + extra margin
        total_height = len(text_lines) * line_height + (len(text_lines) - 1) * line_spacing
        height = total_height + 2 * self.padding + 4  # Extra 4px to prevent cutting
        
        return QtCore.QSize(width, height)
    
    def showToolTip(self, pos=None):
        if not TooltipManager.is_app_active():
            return
            
        TooltipManager.set_current_tooltip(self)
        
        self.adjustSize()
        if pos is None:
            pos = QtGui.QCursor.pos()
        
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
        
        painter.setPen(QtGui.QColor(fg_color))
        painter.setFont(self.font())
        
        text_rect = rect.adjusted(self.padding, self.padding, -self.padding, -self.padding)
        text_lines = self.text.split("<br/>")
        
        fm = QtGui.QFontMetrics(self.font())
        line_height = fm.height()
        line_spacing = 4
        y_offset = 0
        
        for line in text_lines:
            line_y = text_rect.y() + y_offset
            line_rect = QtCore.QRect(text_rect.x(), line_y, text_rect.width(), line_height)
            painter.drawText(line_rect, QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop, line)
            y_offset += line_height + line_spacing

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
        self.widget.installEventFilter(self)
        
        self.show_timer = QtCore.QTimer()
        self.show_timer.setSingleShot(True)
        self.show_timer.timeout.connect(self._show_tooltip_delayed)
        self.show_delay = 300  
        
        self.mouse_over = False

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