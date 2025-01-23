# updater.py

from PyQt6 import QtCore, QtWidgets, QtNetwork

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
    CUSTOM_FONT,
    CUSTOM_FONT_README
)

class Updater:
    def __init__(self, parent=None):
        self.parent         = parent
        self.latest_version = None

    def check_expiration_or_update(self, force_show_dialog=False):
        try:
            response = requests.get(UPDATE_JSON_INFO_URL, timeout=5)
            if response.status_code == 200:
                update_info = response.json().get(platform.system().lower(), {})
                self.latest_version = update_info.get('version')
                if version.parse(self.latest_version) > version.parse(CURRENT_VERSION_NUMBER) or force_show_dialog:
                    log.warning(f"Last known version available: {self.latest_version}")                    
                    self.show_update_dialog(update_info)
        except requests.RequestException as e:
            log.error(f"Can't fetch data to get update: {e}")
            update_info = {}

        self.check_expiration()

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
        dialog.setWindowTitle(f"Latest known version: {self.latest_version}")

        dialog.setModal(True)
        dialog.resize(750, 400)

        layout = QtWidgets.QVBoxLayout(dialog)

        # Zone défilante pour le README
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

        if self.latest_version and version.parse(self.latest_version) > version.parse(CURRENT_VERSION_NUMBER):
            download_button = CustomButton("Start download")
            download_button.clicked.connect(lambda: self.handle_download(update_info))
            button_layout.addWidget(download_button)

        quit_button = CustomButton("Quit")
        quit_button.setFixedWidth(80)
        quit_button.clicked.connect(dialog.accept)
        button_layout.addWidget(quit_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        dialog.exec()

    def handle_download(self, update_info):
        download_url = update_info.get('download_url')
        if download_url:
            save_filename = os.path.basename(download_url)
            save_path = os.path.join(os.path.expanduser("~"), "Downloads", save_filename)

            dialog = DownloadDialog(download_url, save_path)
            if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                self.install_update(save_path)
            else:
                QtWidgets.QMessageBox.warning(
                    None,
                    "Download cancelled",
                    "The update download has been cancelled."
                )
        else:
            QtWidgets.QMessageBox.critical(
                None,
                "error",
                "Download URL not available"
            )

    def install_update(self, save_path):
        try:
            if platform.system().lower() == "windows":
                os.startfile(save_path)
            elif platform.system().lower() == "darwin":
                subprocess.call(["open", save_path])
            else:
                subprocess.call(["xdg-open", save_path])
            sys.exit()
        except Exception as e:
            log.error(f"Can't update program: {e}")
            QtWidgets.QMessageBox.critical(
                None,
                "Error",
                "Try to manually update the program"
            )

    def check_expiration(self):
        current_date = datetime.now()
        if current_date > EXPIRATION_DATE:
            expiration_date_str = EXPIRATION_DATE.strftime('%B %d, %Y')

            dialog = QtWidgets.QDialog()
            dialog.setWindowTitle("Program Expired")
            dialog.setFixedSize(300, 200)

            layout = QtWidgets.QVBoxLayout(dialog)
            label = QtWidgets.QLabel(f"{GUI_LABEL_VERSION} expired on <u>{expiration_date_str}</u>.<br /><br />Please contact the author.")

            label.setFont(CUSTOM_FONT)
            label.setTextFormat(QtCore.Qt.TextFormat.RichText)
            label.setWordWrap(True)
            layout.addWidget(label)

            ok_button = CustomButton("OK")
            ok_button.setFixedWidth(80)
            ok_button.clicked.connect(dialog.accept)

            button_layout = QtWidgets.QHBoxLayout()
            button_layout.addStretch()
            button_layout.addWidget(ok_button)
            button_layout.addStretch()
            layout.addLayout(button_layout)

            dialog.exec()
            sys.exit()

    def download_and_install_update(self, download_url):
        save_filename = os.path.basename(download_url)
        save_path = os.path.join(os.path.expanduser("~"), "Downloads", save_filename)

        dialog = DownloadDialog(download_url, save_path)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.install_update(save_path)
        else:
            QtWidgets.QMessageBox.warning(
                None,
                "Download Cancelled",
                "The update download was cancelled."
            )

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
