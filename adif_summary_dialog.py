# adif_summary_dialog.py

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QSpacerItem
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from custom_button import CustomButton

from utils import(
    AMATEUR_BANDS
)

from constants import (
    # Fonts
    CUSTOM_FONT
)

class AdifSummaryDialog(QDialog):
    def __init__(self, processing_time, parsed_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ADIF File Analyzer")
        self.setModal(True)
        self.resize(800, 600)  

        # Layout principal
        main_layout = QVBoxLayout(self)

        # Section Titre
        title_label = QLabel("<b>ADIF File Parsed Successfully</b>")
        title_font = QFont()
        title_font.setPointSize(14)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        processing_time_label = QLabel(f"Total processing time: {processing_time:.4f}s")
        processing_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(processing_time_label)

        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        processing_label = QLabel(f"Unique callsigns per Year and per Band:")
        processing_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(processing_label)

        main_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        table = QTableWidget()
        table.setColumnCount(len(list(AMATEUR_BANDS.keys())))  
        table.setRowCount(len(parsed_data))
        table.setHorizontalHeaderLabels(['Year'] + list(AMATEUR_BANDS.keys()))
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        table.setFont(CUSTOM_FONT)

        # Remplir le tableau
        years = sorted(parsed_data.keys())
        amateur_bands = list(AMATEUR_BANDS.keys())

        for row, year in enumerate(years):
            year_item = QTableWidgetItem(str(year))
            year_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 0, year_item)

            for col, amateur_band in enumerate(amateur_bands, start=1):
                count = len(parsed_data[year].get(amateur_band, set()))
                count_item = QTableWidgetItem(str(count))
                count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, col, count_item)

        main_layout.addWidget(table)

        main_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        button = CustomButton("Ok")
        button.setFixedWidth(80)
        button.clicked.connect(self.accept)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
