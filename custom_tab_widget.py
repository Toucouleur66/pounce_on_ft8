from PyQt6 import QtWidgets, QtCore

from constants import (    
    STATUS_TRX_COLOR,
    STATUS_DECODING_COLOR,
    STATUS_COLOR_LABEL_OFF,
    STATUS_COLOR_LABEL_SELECTED,
    CUSTOM_FONT
)

class CustomTabWidget(QtWidgets.QWidget):
    tabClicked = QtCore.pyqtSignal(str) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tab_bar = QtWidgets.QToolBar()
        self.stacked_widget = QtWidgets.QStackedWidget()
        tab_bar_layout = QtWidgets.QHBoxLayout()

        self.tab_buttons = {}
        self.tab_contents = {}
        self.band_name_to_index = {}
        self.index_to_band_name = {}
        self.current_band_name = None
        self.operating_band_name = None

        self.tab_bar.setMovable(False)
        self.tab_bar.setStyleSheet("background: transparent; border: none;")

        tab_bar_layout.addWidget(self.tab_bar)
        tab_bar_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        tab_bar_layout.setContentsMargins(0, 0, 0, 0)
        tab_bar_container = QtWidgets.QWidget()
        tab_bar_container.setLayout(tab_bar_layout)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(tab_bar_container)
        main_layout.addWidget(self.stacked_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

    def addTab(self, content_widget, band_name):
        index = self.stacked_widget.count()
        self.band_name_to_index[band_name] = index
        self.index_to_band_name[index] = band_name

        button = QtWidgets.QToolButton()
        button.setText(band_name)
        button.setCheckable(True)
        button.setFont(CUSTOM_FONT)
        button.setStyleSheet(self.get_default_button_style())
        button.clicked.connect(lambda checked, bname=band_name: self.on_tab_clicked(bname))

        self.tab_bar.addWidget(button)
        self.tab_buttons[band_name] = button
        self.stacked_widget.addWidget(content_widget)
        self.tab_contents[band_name] = content_widget

    def get_content_widget(self, band_name):
        index = self.band_name_to_index.get(band_name)
        if index is not None:
            return self.stacked_widget.widget(index)
        else:
            return None

    def on_tab_clicked(self, band_name):
        self.set_selected_tab(band_name)
        self.tabClicked.emit(band_name)

    def get_default_button_style(self):
        return f"""
            QToolButton {{
                background-color: {STATUS_COLOR_LABEL_OFF};
                color: black;
                border-radius: 8px;
                font-size: 12px;
                border: 1px solid transparent;
                padding: 10px;
                margin-right: 1px;
            }}
            QToolButton:hover {{
                background-color: #ECECEC;
                border: 1px solid #ccc;
                padding: 4px;
            }}
        """

    def update_styles(self):
        for band_name, button in self.tab_buttons.items():
            if band_name == self.current_band_name and band_name != self.operating_band_name:
                button.setStyleSheet(f"""
                    QToolButton {{
                        background-color: {STATUS_COLOR_LABEL_SELECTED};
                        color: white;
                        border-radius: 8px;
                        font-size: 12px;
                        border: 1px solid {STATUS_COLOR_LABEL_SELECTED};
                        padding: 10px;
                        margin-right: 1px;                    
                    }}                    
                """)
            elif band_name == self.operating_band_name:
                button.setStyleSheet(f"""
                    QToolButton {{
                        background-color: {STATUS_TRX_COLOR};
                        color: white;
                        border-radius: 8px;
                        font-size: 12px;
                        border: 1px solid transparent;
                        padding: 10px;
                        margin-right: 1px;
                    }}
                    QToolButton:hover {{
                        background-color: {STATUS_DECODING_COLOR};
                    }}
                """)
            else:
                button.setStyleSheet(self.get_default_button_style())

    def set_selected_tab(self, band_name):
        if self.current_band_name is not None and self.current_band_name in self.tab_buttons:
            self.tab_buttons[self.current_band_name].setChecked(False)
        self.current_band_name = band_name
        if self.current_band_name in self.tab_buttons:
            self.tab_buttons[self.current_band_name].setChecked(True)
        self.update_styles()
        index = self.band_name_to_index.get(self.current_band_name)
        if index is not None:
            self.stacked_widget.setCurrentIndex(index)

    def set_operating_tab(self, band_name):
        if band_name is None:
            self.operating_band_name = None
        elif band_name in self.tab_buttons:
            self.operating_band_name = band_name
        else:
            self.operating_band_name = None
        self.update_styles()
