# country_files.py

import os
import requests
from datetime import datetime

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6 import QtWidgets

from utils import get_app_data_dir

from constants import CTY_WT_MOD_URL

class CountryFilesManager:
    def __init__(self, parent):
        self.parent = parent
        self.dat_file_path = os.path.join(get_app_data_dir(), "CTY_WT_MOD.DAT")
        self.url = CTY_WT_MOD_URL

    def load_country_file(self):
        """Download and process the CTY_WT_MOD.DAT file"""
        try:
            # Show progress dialog
            progress_dialog = QtWidgets.QProgressDialog("Downloading Country Files...", "Cancel", 0, 0, self.parent)
            progress_dialog.setWindowTitle("Downloading")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.show()
            
            # Download using requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Save the file
            with open(self.dat_file_path, 'wb') as f:
                f.write(response.content)
            
            progress_dialog.close()
            
            # Process the downloaded file
            self.process_country_file()
            
        except requests.RequestException as e:
            if 'progress_dialog' in locals():
                progress_dialog.close()
            QtWidgets.QMessageBox.critical(
                self.parent,
                "Download Failed",
                f"Failed to download Country Files: {str(e)}"
            )
        except Exception as e:
            if 'progress_dialog' in locals():
                progress_dialog.close()
            QtWidgets.QMessageBox.critical(
                self.parent,
                "Error",
                f"An error occurred: {str(e)}"
            )

    def process_country_file(self):
        """Process and analyze the downloaded CTY_WT_MOD.DAT file"""
        try:
            with open(self.dat_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse the file to extract statistics
            stats = self._parse_dat_file_stats(content)
            
            # Show completion dialog with statistics
            self._show_completion_dialog(stats)

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self.parent,
                "Error",
                f"An error occurred while processing the Country Files: {str(e)}"
            )

    def _parse_dat_file_stats(self, content):
        """Parse DAT file content and return statistics"""
        # Remove comments and empty lines
        cleaned_lines = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                cleaned_lines.append(line)
        
        # Join back and split by semicolons to get records
        cleaned_content = '\n'.join(cleaned_lines)
        records = cleaned_content.split(';')
        
        num_countries = 0
        num_prefixes = 0
        num_exact_calls = 0
        
        for record in records:
            record = record.strip()
            if not record:
                continue
            
            lines = [line.strip() for line in record.split('\n') if line.strip()]
            if not lines:
                continue
            
            # Find the main country line (contains colons)
            main_line = None
            prefix_lines = []
            
            for line in lines:
                if ':' in line and line.count(':') >= 7:
                    main_line = line
                    num_countries += 1
                else:
                    prefix_lines.append(line)
            
            # Count prefixes
            for line in prefix_lines:
                line = line.rstrip(',').strip()
                if line:
                    prefixes = [p.strip() for p in line.split(',') if p.strip()]
                    for prefix in prefixes:
                        if prefix.startswith('='):
                            num_exact_calls += 1
                        else:
                            num_prefixes += 1
        
        return {
            'countries': num_countries,
            'prefixes': num_prefixes,
            'exact_calls': num_exact_calls,
            'file_size': os.path.getsize(self.dat_file_path) if os.path.exists(self.dat_file_path) else 0,
            'last_modified': datetime.fromtimestamp(os.path.getmtime(self.dat_file_path)).strftime('%Y-%m-%d %H:%M:%S') if os.path.exists(self.dat_file_path) else 'Unknown'
        }

    def _show_completion_dialog(self, stats):
        """Show completion dialog with file statistics"""
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Country Files Updated")

        main_layout = QVBoxLayout(dialog)

        # Title section
        title_grid = QGridLayout()
        title_label = QLabel("<b>Country Files Data Updated</b>")
        title_font = QFont()
        title_font.setPointSize(14)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_grid.addWidget(title_label, 0, 0)
        main_layout.addLayout(title_grid)

        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # Statistics section
        details_grid = QGridLayout()
        labels = [
            ("Countries:", stats['countries']),
            ("Prefixes:", stats['prefixes']),
            ("Exact Calls:", stats['exact_calls']),
            ("File Size:", f"{stats['file_size']:,} bytes"),
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

        # Last modified section
        date_grid = QGridLayout()
        update_label = QLabel(f"File downloaded: {stats['last_modified']}")
        update_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        date_grid.addWidget(update_label, 0, 0)
        main_layout.addLayout(date_grid)

        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # OK button
        button = QPushButton("OK")
        button.clicked.connect(dialog.accept)
        button_layout = QVBoxLayout()
        button_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addLayout(button_layout)

        dialog.exec()