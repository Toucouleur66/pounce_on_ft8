# exclusion_dialog.py

from PyQt6 import QtWidgets, QtCore
from custom_button import CustomButton

from constants import (
    CUSTOM_FONT_SMALL
)

from style import (
    get_setting_qss,
    EVEN_COLOR,
    STATUS_TRX_COLOR
)

class ExclusionDialog(QtWidgets.QDialog):
    def __init__(self, callsign, parent=None):
        super().__init__(parent)

        self.callsign = callsign
        self.selected_minutes = 10  
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle(f"Exclude {self.callsign}")
        self.setMinimumWidth(450)

        layout = QtWidgets.QVBoxLayout(self)
        
        # Notice text similar to setting_dialog.py
        notice_text = f"<p>Please select time so callsign <b>{self.callsign}</b> will be excluded for a limited time.</p><p>Once this time over, <b>{self.callsign}</b> will automatically be removed from your Excluded Callsigns.</p>"

        notice_label = QtWidgets.QLabel(notice_text)
        notice_label.setWordWrap(True)
        notice_label.setFont(CUSTOM_FONT_SMALL)
        notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        notice_label.setAutoFillBackground(True)

        layout.addWidget(notice_label)
        
        # Time selector using CustomButton row
        time_label = QtWidgets.QLabel(f"Exclusion time for <b>{self.callsign}</b>")
        time_label.setFont(CUSTOM_FONT_SMALL)
        layout.addWidget(time_label)
        
        button_layout = QtWidgets.QHBoxLayout()
        
        time_options = [
            ("2 min", 2),
            ("10 min", 10), 
            ("1 hour", 60),
            ("1 day", 1440),
            ("1 week", 10080),
            ("1 month", 43200)
        ]
        
        self.time_buttons = []
        
        for display_text, minutes in time_options:
            button = CustomButton(display_text)
            button.setCheckable(True)
            button.minutes = minutes
            
            if minutes == 10:
                button.setChecked(True)
                # Apply the selected style to the default button
                self.on_time_button_toggled(button, display_text, True)
            
            def make_button_handler(btn, mins, display_text):
                def handler(checked):
                    if checked:  # Only act when button is being checked, not unchecked
                        # Uncheck all other buttons
                        for b in self.time_buttons:
                            if b != btn:
                                b.setChecked(False)
                        # Update selected minutes
                        self.selected_minutes = mins
                    # Update button style
                    self.on_time_button_toggled(btn, display_text, checked)
                return handler
            
            button.toggled.connect(make_button_handler(button, minutes, display_text))
            self.time_buttons.append(button)
            button_layout.addWidget(button)
        
        layout.addLayout(button_layout)
        
        first_separator = QtWidgets.QFrame()
        first_separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        first_separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        layout.addWidget(first_separator)

        button_layout = QtWidgets.QHBoxLayout()
        cancel_button = CustomButton("Cancel")
        ok_button = CustomButton("OK")
        
        cancel_button.clicked.connect(self.reject)
        ok_button.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)
    
    def on_time_button_toggled(self, button, time_text, checked):
        if checked:
            button.updateStyle(time_text, STATUS_TRX_COLOR, "#FFFFFF")
        else:
            button.resetStyle()
    
    def get_selected_minutes(self):
        return self.selected_minutes