# clublog.py

import os
import xml.etree.ElementTree as ET
import gzip

from updater import DownloadDialog

from datetime import datetime

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6 import QtWidgets

from constants import (
    CURRENT_DIR,
    CTY_XML_URL
    )

class ClubLogManager:
    def __init__(self, parent):
        self.parent = parent
        self.xml_file_path = os.path.join(CURRENT_DIR, "cty.xml")
        self.url = CTY_XML_URL

    def load_clublog_info(self):
        dialog = DownloadDialog(self.url, self.xml_file_path, parent=self.parent)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.process_clublog_file()
        else:
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Download Cancelled",
                "The Club Log DXCC Info download was cancelled."
            )

    def process_clublog_file(self):
        try:
            with open(self.xml_file_path, 'rb') as f:
                magic = f.read(2)
            if magic == b'\x1f\x8b':  
                with gzip.open(self.xml_file_path, 'rb') as f_in:
                    decompressed_data = f_in.read()
                with open(self.xml_file_path, 'wb') as f_out:
                    f_out.write(decompressed_data)

            tree = ET.parse(self.xml_file_path)
            root = tree.getroot()
            last_update_date_raw = root.attrib.get('date', 'Unknown')
            last_update_date = datetime.strptime(last_update_date_raw, '%Y-%m-%dT%H:%M:%S%z').strftime('%Y-%m-%d %H:%M:%S')

            num_exceptions = len(root.find('exceptions').findall('exception'))
            num_invalid_operations = len(root.find('invalid_operations').findall('invalid'))
            num_zone_exceptions = len(root.find('zone_exceptions').findall('zone_exception'))
            num_prefixes = len(root.find('prefixes').findall('prefix'))
            num_entities = len(root.find('entities').findall('entity'))

            dialog = QDialog(self.parent)
            dialog.setWindowTitle("Club Log DXCC Info Updated")

            main_layout = QVBoxLayout(dialog)

            # Title section
            title_grid = QGridLayout()
            title_label = QLabel("<b>Club Log XML</b>")
            title_font = QFont()
            title_font.setPointSize(14)
            title_label.setFont(title_font)
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title_grid.addWidget(title_label, 0, 0)
            main_layout.addLayout(title_grid)

            main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

            details_grid = QGridLayout()
            labels = [
                ("Exceptions:", num_exceptions),
                ("Invalid Operations:", num_invalid_operations),
                ("Zone Exceptions:", num_zone_exceptions),
                ("Prefixes:", num_prefixes),
                ("Entities:", num_entities),
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
            update_label = QLabel(f"Last update from ClubLog: {last_update_date}")
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

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self.parent,
                "Error",
                f"An error occurred while processing the Club Log DXCC Info file: {str(e)}"
            )