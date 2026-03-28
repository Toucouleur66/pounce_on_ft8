# lotw_incoming_dialog.py

import re

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QHBoxLayout, QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor

from custom_button import CustomButton
from logger import get_logger
from style import set_macos_window_appearance
from constants import GUI_LABEL_VERSION, ADIF_WORKED_CALLSIGNS_FILE

log = get_logger(__name__)


class LoTWIncomingDialog(QDialog):
    def __init__(self, adif_data, since_date='', dark_mode=False, parent=None):
        super().__init__(parent)
        self.dark_mode   = dark_mode
        self._since_date = since_date
        self.setWindowTitle(f"LoTW Incoming - {GUI_LABEL_VERSION}")
        self.setMinimumSize(550, 450)

        self._records = self._parse_adif(adif_data)
        self._stats   = self._compute_stats(self._records)

        self._setup_ui()
        self._populate_table()
        self._apply_palette(dark_mode)

    def _parse_adif(self, adif_data):
        records = []
        for block in re.split(r'<eor>', adif_data, flags=re.IGNORECASE):
            block = block.strip()
            if not block:
                continue

            def field(tag):
                m = re.search(rf'<{tag}:\d+>([^\s<]+)', block, re.IGNORECASE)
                return m.group(1) if m else ''

            qso_date = field('qso_date')
            time_on  = field('time_on')
            callsign = field('call')
            band     = field('band')
            mode     = field('mode')

            # Format date DD/MM/YYYY and time HHMM
            if len(qso_date) == 8:
                date_str = f"{qso_date[6:8]}/{qso_date[4:6]}/{qso_date[:4]}"
            else:
                date_str = qso_date

            time_str = time_on[:4] if len(time_on) >= 4 else time_on

            if callsign:
                records.append({
                    'date':     date_str,
                    'time':     time_str,
                    'callsign': callsign.upper(),
                    'band':     band,
                    'mode':     mode.upper(),
                    'raw_date': qso_date,
                })

        return records

    def _compute_stats(self, records):
        qsl_rcvd = len(records)

        # Count how many are NOT in our local ADIF
        not_in_log = 0
        try:
            import os
            if os.path.exists(ADIF_WORKED_CALLSIGNS_FILE):
                with open(ADIF_WORKED_CALLSIGNS_FILE, 'r', encoding='utf-8') as f:
                    local = f.read()

                for r in records:
                    call_pat = re.search(
                        rf'<call:\d+>{re.escape(r["callsign"])}',
                        local, re.IGNORECASE
                    )
                    if not call_pat:
                        not_in_log += 1
        except Exception as e:
            log.error(f"Error computing LoTW stats: {e}")

        return {'qsl_rcvd': qsl_rcvd, 'not_in_log': not_in_log}

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['Date', 'Time', 'Callsign', 'Band', 'Mode'])

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.verticalHeader().setDefaultSectionSize(24)

        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Date
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Time
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)             # Callsign — wider
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Band
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)             # Mode — compact
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(4, 70)

        layout.addWidget(self.table)

        # Stats label (two lines: counts + fetch date)
        self.stats_label = QLabel()
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stats_label)

        self.since_label = QLabel()
        self.since_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.since_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = CustomButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _populate_table(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self._records))

        for row, r in enumerate(self._records):
            self.table.setItem(row, 0, QTableWidgetItem(r['date']))
            self.table.setItem(row, 1, QTableWidgetItem(r['time']))
            self.table.setItem(row, 2, QTableWidgetItem(r['callsign']))
            self.table.setItem(row, 3, QTableWidgetItem(r['band']))
            self.table.setItem(row, 4, QTableWidgetItem(r['mode']))

        self.table.setSortingEnabled(True)

        self.stats_label.setText(
            f"{self._stats['qsl_rcvd']} QSL(s) rcvd, "
            f"{self._stats['not_in_log']} QSO(s) not in log"
        )
        since_text = f"Fetched from LoTW since: {self._since_date}" if self._since_date else ""
        self.since_label.setText(since_text)

    def _apply_palette(self, dark_mode):
        set_macos_window_appearance(self, dark_mode)

        palette = QPalette()
        if dark_mode:
            palette.setColor(QPalette.ColorRole.Base, QColor('#353535'))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor('#454545'))
            palette.setColor(QPalette.ColorRole.Text, QColor('#FFFFFF'))
            bg = '#353535'
            grid = '#171717'
        else:
            palette.setColor(QPalette.ColorRole.Base, QColor('#FFFFFF'))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor('#F4F5F5'))
            palette.setColor(QPalette.ColorRole.Text, QColor('#000000'))
            bg = '#FFFFFF'
            grid = '#D3D3D3'

        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {bg};
                gridline-color: {grid};
                border: none;
            }}
            QTableWidget::item {{ padding: 5px; }}
            QHeaderView::section {{
                font-weight: normal;
                border: none;
                padding: 0 3px 0 3px;
            }}
            QTableCornerButton::section {{ border: none; }}
        """)
        self.table.setPalette(palette)
        self.table.setShowGrid(False)
