# updater.py

from PyQt6 import QtCore, QtWidgets, QtNetwork
from PyQt6.QtCore import QThread, pyqtSignal

import sys
import os
import platform
import requests
import subprocess
import shutil
import tempfile

from pathlib import Path
from packaging import version
from datetime import datetime

from custom_button import CustomButton

from logger import get_logger

log     = get_logger(__name__)

from constants import (
    EXPIRATION_DATE,
    CURRENT_VERSION_NUMBER,
    UPDATE_JSON_INFO_URL,
    GUI_LABEL_VERSION,
    README_URL,
    CUSTOM_FONT_README
)

class Updater(QThread):
    update_info_fetched = pyqtSignal(dict)
    update_check_failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.latest_version = None

    def run(self):
        try:
            response = requests.get(UPDATE_JSON_INFO_URL, timeout=5)
            if response.status_code == 200:
                update_info = response.json().get(platform.system().lower(), {})
                self.latest_version = update_info.get('version')

                log.warning(f"Last known version available: {self.latest_version}")
                self.update_info_fetched.emit(update_info)
        except requests.RequestException as e:
            log.error(f"Can't fetch data to get update: {e}")
            self.update_check_failed.emit(f"Error checking updates: {e}")

class UpdateManager:
    def __init__(self, parent=None):
        self.parent = parent
        self.latest_version = None
        self.updater_thread = Updater()

        self.updater_thread.update_info_fetched.connect(self.handle_update_info)
        self.updater_thread.update_check_failed.connect(self.handle_update_error)

    def handle_update_info(self, update_info):
        remote_version_str = update_info.get('version')
        
        if not remote_version_str:
            if self.force_show_dialog:
                self.show_update_dialog(update_info)
            return

        if version.parse(remote_version_str) > version.parse(CURRENT_VERSION_NUMBER):
            self.show_update_dialog(update_info)
        else:
            if self.force_show_dialog:
                self.show_update_dialog(update_info)

    def check_expiration_or_update(self, force_show_dialog=False):
        self.check_expiration()
        self.force_show_dialog = force_show_dialog
        self.updater_thread.start()

    def handle_update_error(self, error_message):
        log.error(error_message)
    
    def fetch_readme(self):
        try:
            response = requests.get(README_URL, timeout=5)
            if response.status_code == 200:
                return response.text
        except requests.RequestException as e:
            log.error(f"Can't fetch README.txt: {e}")
            return "Can't fetch README.txt"

    def show_update_dialog(self, update_info):
        readme_content = self.fetch_readme()

        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle(f"Latest known version: {update_info.get('version')}")

        dialog.setModal(True)
        dialog.resize(750, 400)

        layout = QtWidgets.QVBoxLayout(dialog)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        readme_widget = QtWidgets.QWidget()
        readme_layout = QtWidgets.QVBoxLayout(readme_widget)

        readme_label = QtWidgets.QLabel(readme_content)
        readme_label.setFont(CUSTOM_FONT_README)
        readme_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        readme_label.setWordWrap(True)

        readme_layout.addWidget(readme_label)
        scroll_area.setWidget(readme_widget)
        layout.addWidget(scroll_area)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        if update_info.get('version') and version.parse(update_info.get('version')) > version.parse(CURRENT_VERSION_NUMBER):
            sourceforge_button = CustomButton("Download from SourceForge")
            sourceforge_button.clicked.connect(self.open_sourceforge_link)
            button_layout.addWidget(sourceforge_button)

        quit_button = CustomButton("Quit")
        quit_button.setFixedWidth(80)
        quit_button.clicked.connect(dialog.accept)
        button_layout.addWidget(quit_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        dialog.exec()

    def open_sourceforge_link(self):
        import webbrowser
        webbrowser.open("https://sourceforge.net/projects/wait-and-pounce-ft8/")        

    def check_expiration(self):
        current_date = datetime.now()
        if current_date > EXPIRATION_DATE:
            expiration_date_str = EXPIRATION_DATE.strftime('%B %d, %Y')

            QtWidgets.QMessageBox.critical(None, "Program Expired",
                                           f"{GUI_LABEL_VERSION} expired on {expiration_date_str}.\n\nPlease contact the author.")
            sys.exit()

class DownloadDialog(QtWidgets.QDialog):
    def __init__(self, url, save_path, parent=None, title=None):
        super().__init__(parent)
        self.setWindowTitle("Downloading Update")
        self.setFixedSize(400, 80)
        self.url = QtCore.QUrl(url)
        self.save_path = save_path

        self.network_manager = QtNetwork.QNetworkAccessManager(self)
        self.reply = None

        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setRange(0, 100)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(f"Download in progress"))
        layout.addWidget(self.progress_bar)

        self.start_download()

    def start_download(self):
        request = QtNetwork.QNetworkRequest(self.url)
        self.reply = self.network_manager.get(request)
        self.reply.downloadProgress.connect(self.on_download_progress)
        self.reply.finished.connect(self.on_download_finished)
        self.reply.readyRead.connect(self.on_ready_read)

        self.file = open(self.save_path, 'wb')

    def on_download_progress(self, bytes_received, bytes_total):
        if bytes_total > 0:
            progress = int(bytes_received * 100 / bytes_total)
            self.progress_bar.setValue(progress)
            self.setWindowTitle(f"Downloading Update ({progress}%)")

    def on_ready_read(self):
        self.file.write(self.reply.readAll().data())

    def on_download_finished(self):
        self.file.close()
        if self.reply.error() == QtNetwork.QNetworkReply.NetworkError.NoError:
            self.accept()
        else:
            QtWidgets.QMessageBox.critical(
                self, "Download Failed",
                f"Failed to download the update: {self.reply.errorString()}"
            )
            self.reject()
