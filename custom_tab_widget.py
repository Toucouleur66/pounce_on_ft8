from PyQt6 import QtWidgets, QtCore, QtGui

from constants import (    
    STATUS_TRX_COLOR,
    STATUS_MONITORING_COLOR,
    STATUS_DECODING_COLOR,
    STATUS_LABEL_DISABLED_COLOR
)

class CustomTabWidget(QtWidgets.QWidget):
    tabClicked = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tab_bar              = QtWidgets.QToolBar()
        self.custom_font          = QtGui.QFont(".AppleSystemUIFont", 13) 
        self.stacked_widget       = QtWidgets.QStackedWidget()
        layout                    = QtWidgets.QVBoxLayout()

        self.tab_buttons          = []
        self.tab_contents         = []
        self.current_index        = 0
        self.operating_band_index = None
        
        self.tab_bar.setMovable(False)
        self.tab_bar.setStyleSheet("background: transparent; border: none;")

        layout.addWidget(self.tab_bar)
        layout.addWidget(self.stacked_widget)
        
        self.setLayout(layout)

    def addTab(self, content_widget, label):
        index = len(self.tab_buttons)
    
        button = QtWidgets.QToolButton()
        button.setText(label)
        button.setCheckable(True)
        button.setFont(self.custom_font)
        button.setStyleSheet(self.get_default_button_style())
        button.clicked.connect(lambda checked, idx=index: self.on_tab_clicked(idx))
    
        self.tab_bar.addWidget(button)
    
        self.tab_buttons.append(button)
    
        self.stacked_widget.addWidget(content_widget)
    
        self.tab_contents.append(content_widget)

    def get_content_widget(self, index):
        return self.stacked_widget.widget(index)

    def on_tab_clicked(self, index):
        self.set_selected_tab(index)
        self.tabClicked.emit(index)

    def get_default_button_style(self):
        return f"""
            QToolButton {{
                background-color: #e5e5e5;
                color: black;
                border-radius: 8px;
                border: 1px solid transparent;
                padding: 4px;
            }}
            QToolButton:hover {{
                background-color: transparent;
                border: 1px solid #ccc;
                padding: 4px;
            }}
        """

    def update_styles(self):
        for i, button in enumerate(self.tab_buttons):
            if i == self.current_index and i != self.operating_band_index:
                button.setStyleSheet(f"""
                    QToolButton {{
                        background-color: {STATUS_LABEL_DISABLED_COLOR};
                        color: white;
                        border-radius: 8px;
                        border: 1px solid {STATUS_LABEL_DISABLED_COLOR};
                        padding: 4px;                        
                    }}
                    QToolButton:hover {{
                        background-color: {STATUS_MONITORING_COLOR};
                        color: white;
                    }}
                """)
            elif i == self.operating_band_index:
                button.setStyleSheet(f"""
                    QToolButton {{
                        background-color: {STATUS_TRX_COLOR};
                        color: white;
                        border-radius: 8px;
                        border: 1px solid transparent;
                        padding: 4px;
                    }}
                    QToolButton:hover {{
                        background-color: {STATUS_DECODING_COLOR};
                    }}
                """)
            else:
                button.setStyleSheet(self.get_default_button_style())

    def set_selected_tab(self, index):
        if 0 <= self.current_index < len(self.tab_buttons):
            self.tab_buttons[self.current_index].setChecked(False)
        self.current_index = index
        if 0 <= self.current_index < len(self.tab_buttons):
            self.tab_buttons[self.current_index].setChecked(True)
        self.update_styles()
        self.stacked_widget.setCurrentIndex(self.current_index)

    def set_operating_tab(self, band_name):
        if band_name is None:
            self.operating_band_index = None
        else:
            try:
                index = [button.text() for button in self.tab_buttons].index(band_name)
                self.operating_band_index = index
            except ValueError:
                self.operating_band_index = None
        self.update_styles()
