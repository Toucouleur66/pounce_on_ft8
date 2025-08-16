# bulk_downloader.py

import os
import requests
import gzip
import csv
import xml.etree.ElementTree as ET
from datetime import datetime

from PyQt6.QtWidgets import QProgressDialog, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6 import QtWidgets

from utils import get_app_data_dir
from constants import CTY_XML_URL, CTY_WT_MOD_URL

class BulkDownloader:
    def __init__(self, parent):
        self.parent = parent
        self.files_to_download = [
            {
                'name': 'ClubLog DXCC Info',
                'url': CTY_XML_URL,
                'path': os.path.join(get_app_data_dir(), "cty.xml"),
                'processor': self._process_clublog_file
            },
            {
                'name': 'Country Files',
                'url': CTY_WT_MOD_URL,
                'path': os.path.join(get_app_data_dir(), "CTY_WT_MOD.DAT"),
                'processor': self._process_country_file
            },
            {
                'name': 'LoTW Activity',
                'url': "https://lotw.arrl.org/lotw-user-activity.csv",
                'path': os.path.join(get_app_data_dir(), "lotw-user-activity.csv"),
                'processor': self._process_lotw_file
            }
        ]
    
    def download_all_files_silent(self):
        results = []
        
        for file_info in self.files_to_download:
            try:
                success = self._download_file_silent(file_info)
                results.append({
                    'name': file_info['name'],
                    'success': success,
                    'path': file_info['path']
                })
            except Exception as e:
                results.append({
                    'name': file_info['name'],
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def download_all_files_with_progress(self):
        progress_dialog = QProgressDialog("Downloading reference files...", "Cancel", 0, len(self.files_to_download), self.parent)
        progress_dialog.setWindowTitle("Bulk Download")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.show()
        
        results = []
        
        for i, file_info in enumerate(self.files_to_download):
            if progress_dialog.wasCanceled():
                break
                
            progress_dialog.setLabelText(f"Downloading {file_info['name']}...")
            progress_dialog.setValue(i)
            
            # Process events to update UI
            QtWidgets.QApplication.processEvents()
            
            try:
                success = self._download_file_silent(file_info)
                results.append({
                    'name': file_info['name'],
                    'success': success,
                    'path': file_info['path']
                })
            except Exception as e:
                results.append({
                    'name': file_info['name'],
                    'success': False,
                    'error': str(e)
                })
        
        progress_dialog.setValue(len(self.files_to_download))
        progress_dialog.close()
        
        # Show summary
        self._show_download_summary(results)
        
        return results
    
    def _download_file_silent(self, file_info):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(file_info['url'], headers=headers, timeout=30)
        response.raise_for_status()
        
        # Save the file
        with open(file_info['path'], 'wb') as f:
            f.write(response.content)
        
        # Process the file if processor is available
        if file_info.get('processor'):
            file_info['processor'](file_info['path'])
        
        return True
    
    def _process_clublog_file(self, file_path):
        try:
            # Check if file is gzipped
            with open(file_path, 'rb') as f:
                magic = f.read(2)
            
            if magic == b'\x1f\x8b':  # gzip magic number
                with gzip.open(file_path, 'rb') as f_in:
                    decompressed_data = f_in.read()
                with open(file_path, 'wb') as f_out:
                    f_out.write(decompressed_data)
        except Exception:
            pass  # If processing fails, file is still downloaded
    
    def _process_country_file(self, file_path):
        pass
    
    def _process_lotw_file(self, file_path):
        pass
    
    def _show_download_summary(self, results):
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        if not failed:
            # All successful
            file_list = '\n'.join([f"• {r['name']}" for r in successful])
            QMessageBox.information(
                self.parent,
                "Download Complete",
                f"Successfully downloaded {len(successful)} files:\n\n{file_list}"
            )
        elif not successful:
            # All failed
            error_list = '\n'.join([f"• {r['name']}: {r.get('error', 'Unknown error')}" for r in failed])
            QMessageBox.critical(
                self.parent,
                "Download Failed",
                f"Failed to download all files:\n\n{error_list}"
            )
        else:
            # Mixed results
            success_list = '\n'.join([f"• {r['name']}" for r in successful])
            error_list = '\n'.join([f"• {r['name']}: {r.get('error', 'Unknown error')}" for r in failed])
            QMessageBox.warning(
                self.parent,
                "Download Partially Complete",
                f"Successfully downloaded {len(successful)} files:\n{success_list}\n\n"
                f"Failed to download {len(failed)} files:\n{error_list}"
            )
    
    def get_file_info(self):
        info = []
        for file_info in self.files_to_download:
            file_exists = os.path.exists(file_info['path'])
            file_size = os.path.getsize(file_info['path']) if file_exists else 0
            last_modified = datetime.fromtimestamp(os.path.getmtime(file_info['path'])).strftime('%Y-%m-%d %H:%M:%S') if file_exists else 'Never'
            
            info.append({
                'name': file_info['name'],
                'url': file_info['url'],
                'path': file_info['path'],
                'exists': file_exists,
                'size': file_size,
                'last_modified': last_modified
            })
        
        return info