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

class CustomToolTip(QtWidgets.QWidget):
    def __init__(self, text, tooltip_type="default", bg_color=None, fg_color=None, parent=None):
        super().__init__(parent, QtCore.Qt.WindowType.ToolTip | QtCore.Qt.WindowType.FramelessWindowHint)
        self.text = text
        self.tooltip_type = tooltip_type
        self.custom_bg_color = bg_color
        self.custom_fg_color = fg_color
        self.padding = 14
        self.radius = 3
        
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
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
        
        width = max_width + 2 * self.padding + 8
        
        line_height = fm.height()
        total_height = len(text_lines) * line_height + (len(text_lines) - 1) * 4
        height = total_height + 2 * self.padding
        
        return QtCore.QSize(width, height)
    
    def showToolTip(self, pos=None):
        self.adjustSize()
        if pos is None:
            pos = QtGui.QCursor.pos()
        
        screen = QtWidgets.QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        
        tooltip_rect = self.geometry()
        tooltip_rect.moveTopLeft(pos)
        
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
        y_offset = 0
        
        for i, line in enumerate(text_lines):
            line_y = text_rect.y() + y_offset
            line_rect = QtCore.QRect(text_rect.x(), line_y, text_rect.width(), line_height)
            painter.drawText(line_rect, QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop, line)
            y_offset += line_height + 4

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

    def eventFilter(self, obj, event):
        if obj == self.widget:
            if event.type() == QtCore.QEvent.Type.Enter:
                self.show_tooltip()
            elif event.type() == QtCore.QEvent.Type.Leave:
                self.hide_tooltip()
        return super().eventFilter(obj, event)

    def show_tooltip(self):
        if hasattr(self.source_widget, 'text'):
            raw_text = self.source_widget.text()
        else:
            raw_text = self.default_text
        
        if not raw_text:
            return

        text_parts = [part.strip() for part in raw_text.split(",") if part.strip()]
        tooltip_text = "<br/>".join(sorted(text_parts))
        
        if self.tooltip_window:
            self.tooltip_window.hideToolTip()
        
        self.tooltip_window = CustomToolTip(tooltip_text, self.tooltip_type, self.bg_color, self.fg_color)
        self.tooltip_window.showToolTip(QtGui.QCursor.pos())

    def hide_tooltip(self):
        if self.tooltip_window:
            self.tooltip_window.hideToolTip()
            self.tooltip_window = None