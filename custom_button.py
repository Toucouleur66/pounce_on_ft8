from PyQt6 import QtWidgets

class CustomButton(QtWidgets.QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.default_style = """
            QPushButton {
                background-color: #E0E0E0;
                color: #000000;
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #FFD700;
                border: 2px solid #FFA500;
            }
            QPushButton:pressed {
                background-color: #FFFFFF;
                border: 2px solid #FFFFFF;
            }
        """
        self.setStyleSheet(self.default_style)
    
    def resetStyle(self):
        self.setStyleSheet(self.default_style)
    
    def setVisibleState(self, visible):
        if visible:
            self.resetStyle() 
            self.setEnabled(True)
        else:
            self.setStyleSheet("""
                background-color: transparent;
                color: transparent;
            """)
            self.setEnabled(False)
