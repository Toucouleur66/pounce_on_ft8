from PyQt6 import QtWidgets

from constants import (
    CUSTOM_FONT_SMALL,
)

class CustomQLabel(QtWidgets.QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        
        self.setFont(CUSTOM_FONT_SMALL)
        self.setStyleSheet(f"font: {CUSTOM_FONT_SMALL.pointSize()}pt '{CUSTOM_FONT_SMALL.family()}';")