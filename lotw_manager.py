# lotw_manager.py

import os
import csv
from datetime import datetime

from updater import DownloadDialog

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6 import QtWidgets

from constants import CURRENT_DIR

class LoTWManager:
    def __init__(self, parent):
        self.parent = parent
        self.csv_file_path = os.path.join(CURRENT_DIR, "lotw-user-activity.csv")
        self.url = "https://lotw.arrl.org/lotw-user-activity.csv"

    def load_lotw_info(self):
        dialog = DownloadDialog(self.url, self.csv_file_path, parent=self.parent)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.process_lotw_file()
        else:
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Download Cancelled",
                "The LoTW User Activity download was cancelled."
            )

    def process_lotw_file(self):
        try:
            # Parse CSV file and count entries
            lotw_data = {}
            total_entries = 0
            latest_date = None
            earliest_date = None
            
            with open(self.csv_file_path, 'r', encoding='utf-8') as f:
                # Skip header if present
                csv_reader = csv.reader(f)
                header = next(csv_reader, None)
                
                for row in csv_reader:
                    if len(row) >= 2:
                        callsign = row[0].strip().upper()
                        date_str = row[1].strip()
                        
                        try:
                            # Parse date (format: YYYY-MM-DD)
                            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                            lotw_data[callsign] = date_str
                            total_entries += 1
                            
                            # Track date range
                            if latest_date is None or date_obj > latest_date:
                                latest_date = date_obj
                            if earliest_date is None or date_obj < earliest_date:
                                earliest_date = date_obj
                                
                        except ValueError:
                            continue  # Skip invalid date entries
            
            # Save processed data for callsign lookup
            self.save_lotw_cache(lotw_data)
            
            # Show summary dialog
            self.show_summary_dialog(total_entries, earliest_date, latest_date)
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self.parent,
                "Error",
                f"An error occurred while processing the LoTW User Activity file: {str(e)}"
            )

    def save_lotw_cache(self, lotw_data):
        cache_file = os.path.join(CURRENT_DIR, "lotw_cache.json")
        try:
            import json
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(lotw_data, f, indent=2)
        except Exception as e:
            print(f"Failed to save LoTW cache: {e}")

    def show_summary_dialog(self, total_entries, earliest_date, latest_date):
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("LoTW User Activity Updated")

        main_layout = QVBoxLayout(dialog)

        # Title section
        title_grid = QGridLayout()
        title_label = QLabel("<b>LoTW User Activity Data Processed</b>")
        title_font = QFont()
        title_font.setPointSize(14)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_grid.addWidget(title_label, 0, 0)
        main_layout.addLayout(title_grid)

        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        details_grid = QGridLayout()
        
        # Format date range
        date_range = "Unknown"
        if earliest_date and latest_date:
            date_range = f"{earliest_date.strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')}"
        
        labels = [
            ("Total Callsigns:", total_entries),
            ("Date Range:", date_range),
        ]
        
        for row, (label_text, value) in enumerate(labels):
            label = QLabel(label_text)
            label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            value_label = QLabel(str(value))
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            details_grid.addWidget(label, row, 0)
            details_grid.addWidget(value_label, row, 1)

        main_layout.addLayout(details_grid)

        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        date_grid = QGridLayout()
        update_label = QLabel(f"LoTW data downloaded: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        update_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        date_grid.addWidget(update_label, 0, 0)
        main_layout.addLayout(date_grid)

        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        button = QPushButton("OK")
        button.clicked.connect(dialog.accept)
        button_layout = QVBoxLayout()
        button_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addLayout(button_layout)

        dialog.exec()