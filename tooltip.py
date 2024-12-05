# tooltip.py
import platform

from PyQt6 import QtWidgets, QtCore, QtGui

from constants import (
    CUSTOM_FONT_MONO,
    NOTICE_QSS
)

class ToolTip(QtWidgets.QWidget):
    def __init__(self, widget, text=''):
        super().__init__()
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.installEventFilter(self)

        QtWidgets.QToolTip.setFont(CUSTOM_FONT_MONO)
        QtWidgets.QApplication.instance().setStyleSheet(NOTICE_QSS)

    def eventFilter(self, obj, event):
        if obj == self.widget:
            if event.type() == QtCore.QEvent.Type.Enter:
                self.show_tooltip()
            elif event.type() == QtCore.QEvent.Type.Leave:
                self.hide_tooltip()
        return super().eventFilter(obj, event)

    def show_tooltip(self):
        self.text = self.widget.text().replace(",", "<br/>")
        if not self.text:
            return
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), self.text, self.widget)

    def hide_tooltip(self):
        QtWidgets.QToolTip.hideText()