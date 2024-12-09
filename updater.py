# updater.py

from PyQt6 import QtCore, QtWidgets, QtNetwork

import sys
import os
import platform
import requests
import subprocess

from packaging import version
from datetime import datetime
from logger import get_logger

log     = get_logger(__name__)

from constants import (
    EXPIRATION_DATE,
    CURRENT_VERSION_NUMBER,
    UPDATE_JSON_INFO_URL,
    GUI_LABEL_VERSION,
    CUSTOM_FONT,
)

class Updater:
    def __init__(self, parent=None):
        self.parent = parent

    def check_expiration(self):
        current_date = datetime.now()
        if current_date > EXPIRATION_DATE:      
            expiration_date_str = EXPIRATION_DATE.strftime('%B %d, %Y')

            dialog = QtWidgets.QDialog()
            dialog.setWindowTitle("Program Expired")
            dialog.setFixedSize(300, 200)

            layout = QtWidgets.QVBoxLayout(dialog)

            label = QtWidgets.QLabel(f"The application expired on <u>{expiration_date_str}</u>.<br /><br />Please contact the author.")
            label.setFont(CUSTOM_FONT)
            label.setTextFormat(QtCore.Qt.TextFormat.RichText)
            label.setWordWrap(True)
            layout.addWidget(label)

            ok_button = QtWidgets.QPushButton("Ok")
            ok_button.setFixedWidth(80) 
            ok_button.clicked.connect(dialog.accept)

            button_layout = QtWidgets.QHBoxLayout()
            button_layout.addStretch()  
            button_layout.addWidget(ok_button)
            button_layout.addStretch()  
            layout.addLayout(button_layout)

            dialog.exec()
            sys.exit()

    def check_for_expiration_or_update(self):
        try:
            response = requests.get(UPDATE_JSON_INFO_URL, timeout=5)
            if response.status_code == 200:
                update_info = response.json()[platform.system().lower()]
                latest_version = update_info.get('version')
                log.warning(f"Last known version available: {latest_version}")
                if version.parse(latest_version) > version.parse(CURRENT_VERSION_NUMBER):
                    if self.prompt_user_for_update(update_info):
                        download_url = update_info['download_url']
                        self.download_and_install_update(download_url)
        except requests.RequestException:
            pass
    
        self.check_expiration()
        return None

    def prompt_user_for_update(self, update_info):
        latest_version  = update_info['version']
        release_date    = update_info['release_date']
        changelog       = update_info.get('changelog', 'No changelog available.')

        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle(f"Update Available: {GUI_LABEL_VERSION}")
        dialog.setModal(True)
        
        layout = QtWidgets.QVBoxLayout(dialog)

        label = QtWidgets.QLabel(
            f"New <u>{latest_version}</u> version is available.<br>"
            f"Released on: {release_date}<br><br>"
            f"<u>Changelog:</u><br>{changelog.replace('\n', '<br>')}<br><br>"
            "Do you want to download and install this update?"
        )
        label.setWordWrap(True)
        label.setFont(CUSTOM_FONT)
        layout.addWidget(label)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Yes | QtWidgets.QDialogButtonBox.StandardButton.No
        )
        layout.addWidget(button_box)

        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        result = dialog.exec()
        return result == QtWidgets.QDialog.DialogCode.Accepted

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

    def install_update(self, save_path):
        if platform.system() == 'Windows':
            os.startfile(save_path)
            sys.exit()
        elif platform.system() == 'Darwin':
            subprocess.Popen(['open', save_path])
            QtWidgets.QMessageBox.information(
                None, 'Manual Installation Required',
                'The update has been downloaded. Please follow the instructions to install it manually.'
            )
            sys.exit()
        else:
            QtWidgets.QMessageBox.information(
                None, 'Update Downloaded',
                f'The update has been downloaded to {save_path}. Please install it manually.'
            )
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
