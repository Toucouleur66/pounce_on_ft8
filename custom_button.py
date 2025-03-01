from PyQt6 import QtWidgets

from constants import (
    CUSTOM_FONT,
)

class CustomButton(QtWidgets.QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.default_style = f"""
            QPushButton {{
                background-color: #E0E0E0;
                color: #000000;
                font: {CUSTOM_FONT.pointSize()}pt '{CUSTOM_FONT.family() }';
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                padding: 5px 10px;
            }}
            QPushButton:hover {{
                background-color: #FFD700;
                border: 2px solid #FFA500;
            }}
            QPushButton:pressed {{
                background-color: #FFFFFF;
                border: 2px solid #FFFFFF;
            }}
        """
        self.setStyleSheet(self.default_style)

        self.current_text     = text
        self.current_bg_color = "#E0E0E0;"
        self.current_fg_color = "#000000;"
    
    def resetStyle(self):
        self.setStyleSheet(self.default_style)
    
    def setVisibleState(self, visible):
        if visible:
            self.updateStyle(self.current_text, self.current_bg_color, self.current_fg_color) 
        else:
            self.setStyleSheet("""
                background-color: transparent;
                color: transparent;
            """)

    def updateStyle(self, text, bg_color, fg_color):
        self.setText(text)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color}; 
                color: {fg_color};
                border: 2px solid {bg_color};
                font: {CUSTOM_FONT.pointSize()}pt '{CUSTOM_FONT.family() }';
                border-radius: 8px;
                padding: 5px 10px;
            }}
        """)

        self.current_text     = text
        self.current_bg_color = bg_color
        self.current_fg_color = fg_color
