from PyQt6 import QtWidgets

from constants import (
    CUSTOM_FONT,
)

class CustomQLabel(QtWidgets.QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        
        self.setFont(CUSTOM_FONT)
        self.setStyleSheet(f"font: {CUSTOM_FONT.pointSize()}pt '{CUSTOM_FONT.family()}';")