# adif_summary_dialog.py

import locale

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import (
    QDialog, QLabel, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QSpacerItem
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt

from custom_button import CustomButton
from custom_qlabel import CustomQLabel
from animated_toggle import AnimatedToggle

from utils import(
    AMATEUR_BANDS
)

from constants import (
    CUSTOM_FONT
)

from style import (
    get_main_table_qss,
    set_macos_window_appearance,
    EVEN_COLOR
)

from translatable_strings import AdifSummaryStrings, CommonStrings

class AdifSummaryDialog(QDialog):
    def __init__(self, processing_time, parsed_data, dark_mode=False, file_path=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(AdifSummaryStrings.WINDOW_TITLE())
        self.setModal(True)
        self.resize(900, 600)
        self.dark_mode = dark_mode
        self.parsed_data = parsed_data
        self.processing_time = processing_time
        self.file_path = file_path
        self.show_all_bands = False

        # Set locale for number formatting
        try:
            locale.setlocale(locale.LC_ALL, '')
        except locale.Error:
            locale.setlocale(locale.LC_ALL, 'C')

        # Apply macOS window appearance to match theme
        set_macos_window_appearance(self, dark_mode)

        # Layout principal
        main_layout = QVBoxLayout(self)

        title_label = QLabel(f"<b>{AdifSummaryStrings.TITLE_SUCCESS()}</b>")
        title_font = QFont()
        title_font.setPointSize(14)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # File path label
        if self.file_path:
            file_path_label = QLabel(AdifSummaryStrings.LABEL_FILE_PATH(self.file_path))
            file_path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.addWidget(file_path_label)

        processing_time_label = QLabel(AdifSummaryStrings.LABEL_PROCESSING_TIME(processing_time))
        processing_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(processing_time_label)

        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # Toggle and label layout
        toggle_layout = QHBoxLayout()

        processing_label = QLabel(AdifSummaryStrings.LABEL_UNIQUE_CALLSIGNS())
        processing_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        toggle_layout.addWidget(processing_label)

        toggle_layout.addStretch()

        self.show_all_bands_label = CustomQLabel(AdifSummaryStrings.TOGGLE_SHOW_ALL_BANDS())
        toggle_layout.addWidget(self.show_all_bands_label)

        self.show_all_bands_toggle = AnimatedToggle()
        self.show_all_bands_toggle.setChecked(False)
        self.show_all_bands_toggle.stateChanged.connect(self.toggle_show_all_bands)
        self.show_all_bands_toggle.setFixedSize(self.show_all_bands_toggle.sizeHint())
        toggle_layout.addWidget(self.show_all_bands_toggle)

        main_layout.addLayout(toggle_layout)

        main_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # Create container for tables
        self.table_container = QVBoxLayout()
        main_layout.addLayout(self.table_container)

        # Create container for totals row (separate table that stays at bottom)
        self.totals_container = QVBoxLayout()
        main_layout.addLayout(self.totals_container)

        # Build initial table
        self.build_table()

        main_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        button = CustomButton(CommonStrings.OK())
        button.setFixedWidth(80)
        button.clicked.connect(self.accept)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

    def toggle_show_all_bands(self, state):
        self.show_all_bands = state
        self.build_table()

    def format_number(self, number):
        return locale.format_string("%d", number, grouping=True)

    def build_table(self):
        while self.table_container.count():
            child = self.table_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        while self.totals_container.count():
            child = self.totals_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        years = sorted(self.parsed_data.keys())
        all_amateur_bands = list(AMATEUR_BANDS.keys())

        # Calculate band totals to determine which bands to show
        band_totals = {}
        for band in all_amateur_bands:
            band_total = sum(len(self.parsed_data[year].get(band, set())) for year in years)
            band_totals[band] = band_total

        # Filter bands based on toggle state
        if self.show_all_bands:
            amateur_bands = all_amateur_bands
        else:
            amateur_bands = [band for band in all_amateur_bands if band_totals[band] > 0]

        # Main data table (without totals row)
        table = QTableWidget()
        table.setColumnCount(len(amateur_bands) + 2)
        table.setRowCount(len(self.parsed_data))
        table.setHorizontalHeaderLabels([AdifSummaryStrings.HEADER_YEAR()] + amateur_bands + [AdifSummaryStrings.HEADER_TOTAL()])

        # Calculate column widths
        year_column_width = 80
        total_column_width = 100
        available_width = 850 - year_column_width - total_column_width - 20  # 20 for margins
        band_column_width = available_width // len(amateur_bands) if len(amateur_bands) > 0 else 80

        # Set all columns to Fixed mode with specific widths
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(0, year_column_width)
        for col in range(1, len(amateur_bands) + 1):
            table.setColumnWidth(col, band_column_width)
        table.setColumnWidth(len(amateur_bands) + 1, total_column_width)

        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        table.setFont(CUSTOM_FONT)
        table.setShowGrid(False)
        table.setStyleSheet(get_main_table_qss(self.dark_mode))

        # Fill the table
        for row, year in enumerate(years):
            year_item = QTableWidgetItem(str(year))
            year_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 0, year_item)

            year_total = 0
            for col, amateur_band in enumerate(amateur_bands, start=1):
                count = len(self.parsed_data[year].get(amateur_band, set()))
                count_item = QTableWidgetItem(self.format_number(count))
                count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, col, count_item)
                year_total += count

            total_item = QTableWidgetItem(self.format_number(year_total))
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            total_item.setBackground(QColor(EVEN_COLOR))
            total_item.setForeground(QColor("#555BC2"))
            table.setItem(row, len(amateur_bands) + 1, total_item)

        self.table_container.addWidget(table)

        # Totals table (separate, always visible at bottom)
        totals_table = QTableWidget()
        totals_table.setColumnCount(len(amateur_bands) + 2)
        totals_table.setRowCount(1)
        totals_table.horizontalHeader().setVisible(False)

        # Set all columns to Fixed mode with same widths as main table
        totals_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        totals_table.setColumnWidth(0, year_column_width)
        for col in range(1, len(amateur_bands) + 1):
            totals_table.setColumnWidth(col, band_column_width)
        totals_table.setColumnWidth(len(amateur_bands) + 1, total_column_width)

        totals_table.verticalHeader().setVisible(False)
        totals_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        totals_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        totals_table.setFont(CUSTOM_FONT)
        totals_table.setShowGrid(False)
        totals_table.setStyleSheet(get_main_table_qss(self.dark_mode))

        # Set fixed height for totals table (one row)
        totals_table.setFixedHeight(totals_table.verticalHeader().defaultSectionSize() + 2)

        # Add right margin to totals table to account for main table's scrollbar
        totals_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        totals_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Set right margin to match scrollbar width
        totals_table.setStyleSheet(get_main_table_qss(self.dark_mode) + "\nQTableWidget { margin-right: " + str(table.verticalScrollBar().sizeHint().width()) + "px; }")

        # "Total" label in first column
        total_label_item = QTableWidgetItem(AdifSummaryStrings.LABEL_TOTAL())
        total_label_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        total_label_item.setBackground(QColor(EVEN_COLOR))
        total_label_item.setForeground(QColor("#555BC2"))
        totals_table.setItem(0, 0, total_label_item)

        # Calculate and display total per band
        grand_total = 0
        for col, amateur_band in enumerate(amateur_bands, start=1):
            band_total = band_totals[amateur_band]
            band_total_item = QTableWidgetItem(self.format_number(band_total))
            band_total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            band_total_item.setBackground(QColor(EVEN_COLOR))
            band_total_item.setForeground(QColor("#555BC2"))
            totals_table.setItem(0, col, band_total_item)
            grand_total += band_total

        # Grand total in last column
        grand_total_item = QTableWidgetItem(self.format_number(grand_total))
        grand_total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        grand_total_item.setBackground(QColor(EVEN_COLOR))
        grand_total_item.setForeground(QColor("#555BC2"))
        totals_table.setItem(0, len(amateur_bands) + 1, grand_total_item)

        self.totals_container.addWidget(totals_table)
