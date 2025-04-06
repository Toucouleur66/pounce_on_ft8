# tooltip.py
import platform

from PyQt6 import QtWidgets, QtCore, QtGui

from constants import (
    CUSTOM_FONT,
    TOOLTIP_QSS
)

class ToolTip(QtWidgets.QWidget):
    def __init__(self, widget, source_widget=None, default_text=''):
        super().__init__()
        self.widget = widget
        self.source_widget = source_widget if source_widget is not None else widget
        self.default_text = default_text
        self.tooltip_window = None
        self.widget.installEventFilter(self)

        QtWidgets.QToolTip.setFont(CUSTOM_FONT)
        QtWidgets.QApplication.instance().setStyleSheet(TOOLTIP_QSS)

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
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), tooltip_text, self.widget)

    def hide_tooltip(self):
        QtWidgets.QToolTip.hideText()