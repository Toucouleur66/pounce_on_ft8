# lotw_sync_worker.py

import os
import re

from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal

from logger import get_logger
from constants import ADIF_WORKED_CALLSIGNS_FILE

log = get_logger(__name__)


class LoTWDownloadWorker(QObject):
    """
    Lightweight worker: download only, no ADIF update.
    Used by the settings dialog test button.
    """
    finished = pyqtSignal(bool, str)   # success, adif_data_or_error

    def __init__(self, username, password, since):
        super().__init__()
        self._username = username
        self._password = password
        self._since    = since

    def run(self):
        try:
            from lotw_uploader import LoTWClient
            client = LoTWClient(self._username, self._password)
            success, result = client.download_qsos(qsl_since=self._since)
            log.info(f"LoTW test download done: success={success}, size={len(result) if success else 0} bytes")
            self.finished.emit(success, result)
        except Exception as e:
            log.error(f"LoTW test download exception: {e}")
            self.finished.emit(False, str(e))


class LoTWSyncWorker(QObject):
    finished = pyqtSignal(bool, str, int)   # success, new_since_date, updated_count

    def __init__(self, username, password, qso_since_str):
        super().__init__()
        self._username      = username
        self._password      = password
        self._qso_since_str = qso_since_str

    def run(self):
        log.info(f"LoTW SyncWorker started (since: {self._qso_since_str})")

        try:
            from lotw_uploader import LoTWClient
            client = LoTWClient(self._username, self._password)
            success, result = client.download_qsos(qsl_since=self._qso_since_str or None)
        except Exception as e:
            log.error(f"LoTW SyncWorker download exception: {e}")
            self.finished.emit(False, self._qso_since_str, 0)
            return

        if not success:
            log.error(f"LoTW SyncWorker download failed: {result}")
            self.finished.emit(False, self._qso_since_str, 0)
            return

        # Parse confirmed QSOs from LoTW response
        # Key: (callsign_upper, qso_date_YYYYMMDD, band_lower)
        confirmed = {}
        for block in re.split(r'<eor>', result, flags=re.IGNORECASE):
            call_m = re.search(r'<call:\d+>([^\s<]+)',      block, re.IGNORECASE)
            date_m = re.search(r'<qso_date:\d+>(\d{8})',   block, re.IGNORECASE)
            band_m = re.search(r'<band:\d+>([^\s<]+)',      block, re.IGNORECASE)
            if call_m and date_m and band_m:
                key = (call_m.group(1).upper(), date_m.group(1), band_m.group(1).lower())
                confirmed[key] = True

        if not confirmed:
            log.info("LoTW SyncWorker: no new QSLs")
            # Still update since_date so we don't re-download the same empty window
            new_since = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.finished.emit(True, new_since, 0)
            return

        log.info(f"LoTW SyncWorker: {len(confirmed)} confirmed QSO(s) from LoTW")

        # Update local ADIF file
        updated_count = self._update_adif(confirmed)

        new_since = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.finished.emit(True, new_since, updated_count)

    def _update_adif(self, confirmed):
        if not os.path.exists(ADIF_WORKED_CALLSIGNS_FILE):
            log.warning("LoTW SyncWorker: local ADIF file not found, skipping update")
            return 0

        try:
            with open(ADIF_WORKED_CALLSIGNS_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            log.error(f"LoTW SyncWorker: failed to read ADIF file: {e}")
            return 0

        # Split preserving the <eor> tag via a capturing group
        parts      = re.split(r'(<eor>\n?)', content, flags=re.IGNORECASE)
        output     = []
        updated    = 0
        i          = 0

        while i < len(parts):
            chunk = parts[i]

            # Is the next part an <eor> tag? → this chunk is a QSO body
            if i + 1 < len(parts) and re.match(r'<eor>', parts[i + 1], re.IGNORECASE):
                eor_tag = parts[i + 1]
                i += 2

                call_m = re.search(r'<call:\d+>([^\s<]+)',    chunk, re.IGNORECASE)
                date_m = re.search(r'<qso_date:\d+>(\d{8})', chunk, re.IGNORECASE)
                band_m = re.search(r'<band:\d+>([^\s<]+)',    chunk, re.IGNORECASE)

                if call_m and date_m and band_m:
                    key = (call_m.group(1).upper(), date_m.group(1), band_m.group(1).lower())

                    if key in confirmed:
                        added = []
                        if '<lotw_qsl_rcvd' not in chunk.lower():
                            chunk += ' <lotw_qsl_rcvd:1>V'
                            added.append('lotw_qsl_rcvd:1>V')
                        if '<lotw_qsl_sent' not in chunk.lower():
                            chunk += ' <lotw_qsl_sent:1>Y'
                            added.append('lotw_qsl_sent:1>Y')
                        if added:
                            chunk += ' ' 
                            updated += 1
                            log.info(
                                f"LoTW Sync: QSL received for {call_m.group(1).upper()} "
                                f"on {date_m.group(1)} [ {band_m.group(1)} ]"
                            )

                output.append(chunk + eor_tag)
            else:
                output.append(chunk)
                i += 1

        if updated:
            try:
                new_content = ''.join(output)
                with open(ADIF_WORKED_CALLSIGNS_FILE, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                log.info(f"LoTW SyncWorker: ADIF file updated — {updated} record(s) modified")
            except Exception as e:
                log.error(f"LoTW SyncWorker: failed to write ADIF file: {e}")
                return 0
        else:
            log.info("LoTW SyncWorker: no local records matched — ADIF file unchanged")

        return updated
