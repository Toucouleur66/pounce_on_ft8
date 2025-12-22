# clublog.py

import os
import xml.etree.ElementTree as ET
import gzip
import json
import requests
from urllib.parse import urlencode

from updater import DownloadDialog

from datetime import datetime

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6 import QtWidgets

from logger import get_logger

from utils import get_app_data_dir

from constants import (
    CTY_XML_URL,
    CLUB_LOG_CACHE_FILE
    )

log = get_logger(__name__)

class ClubLogManager:
    def __init__(self, parent):
        self.parent = parent
        self.xml_file_path = os.path.join(get_app_data_dir(), "cty.xml")
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
            dialog.setWindowTitle("Club Log's DXCC Info Updated")

            main_layout = QVBoxLayout(dialog)

            # Title section
            title_grid = QGridLayout()
            title_label = QLabel("<b>Club Log's Data parsed</b>")
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


class ClubLogUploader:
    REALTIME_API_URL = "https://clublog.org/realtime.php"

    def __init__(self, email, password, api_key, callsign):
        self.email = email
        self.password = password
        self.api_key = api_key
        self.callsign = callsign
        self.cache_file = CLUB_LOG_CACHE_FILE

    @staticmethod
    def get_cache_info():
        try:
            if os.path.exists(CLUB_LOG_CACHE_FILE):
                with open(CLUB_LOG_CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    return (
                        data.get('last_sync_time'),
                        data.get('total_qsos', 0),
                        data.get('last_callsign', ''),
                        data.get('last_band', '')
                    )
        except Exception as e:
            log.error(f"Error reading Club Log cache: {e}")
        return None, 0, '', ''

    def update_cache(self, callsign, band):
        try:
            data = {
                'last_sync_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_qsos': self.get_cache_info()[1] + 1,
                'last_callsign': callsign,
                'last_band': band
            }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Error updating Club Log cache: {e}")

    def upload_qso(self, adif_record):
        try:
            data = {
                'email': self.email,
                'password': self.password,
                'callsign': self.callsign,
                'adif': adif_record,
                'api': self.api_key
            }

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            log.debug(f"Uploading to Club Log: {self.REALTIME_API_URL}")
            log.debug(f"Request data: email={self.email}, callsign={self.callsign}, api={self.api_key}")
            log.debug(f"ADIF record: {adif_record}")

            response = requests.post(
                self.REALTIME_API_URL,
                data=urlencode(data),
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                return True, response.text
            else:
                log.warning(f"Response status code: {response.status_code}")
                log.warning(f"Response headers: {dict(response.headers)}")
                log.warning(f"Response text: {response.text}")

                if response.status_code == 403:
                    log.error(f"Club Log authentication failed - stopping uploads")
                    return False, "Authentication failed"
                elif response.status_code == 500:
                    log.error(f"Club Log server error - will retry later")
                    return False, "Server error"
                elif response.status_code == 400:
                    log.error(f"Club Log invalid QSO data: {response.text}")
                    return False, "Invalid QSO data"
                else:
                    log.error(f"Club Log unexpected response: {response.status_code} - {response.text}")
                    return False, f"Unexpected response: {response.status_code}"

        except requests.exceptions.Timeout:
            log.error("Club Log upload timeout")
            return False, "Timeout"
        except Exception as e:
            log.error(f"Club Log upload error: {e}")
            return False, str(e)