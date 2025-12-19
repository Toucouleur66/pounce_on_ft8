# active_users_window.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QHBoxLayout, QLabel
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
from datetime import datetime
from custom_button import CustomButton
from logger import get_logger
from constants import TABLE_SETTING_QSS, GUI_LABEL_VERSION
from utils import AMATEUR_BANDS

log = get_logger(__name__)


def get_band_sort_key(band):
    """
    Get numeric sort key for band.
    Converts bands to meters for proper numeric sorting.
    Examples: 160m -> 160, 10m -> 10, 70cm -> 0.7
    """
    if not band:
        return 9999

    if band.endswith('m'):
        # Convert to float (e.g., "160m" -> 160.0)
        try:
            return float(band[:-1])
        except ValueError:
            return 9999
    elif band.endswith('cm'):
        # Convert centimeters to meters (e.g., "70cm" -> 0.7)
        try:
            return float(band[:-2]) / 100
        except ValueError:
            return 9999

    return 9999


class SortableTableWidgetItem(QTableWidgetItem):
    """Custom QTableWidgetItem that sorts by UserRole data if available."""

    def __lt__(self, other):
        # Get UserRole data for sorting
        self_data = self.data(Qt.ItemDataRole.UserRole)
        other_data = other.data(Qt.ItemDataRole.UserRole)

        # If both have UserRole data, compare by that
        if self_data is not None and other_data is not None:
            return self_data < other_data

        # Otherwise, fall back to text comparison
        return super().__lt__(other)


class ActiveUsersWindow(QDialog):
    def __init__(self, telemetry_service, parent=None):
        super().__init__(parent)
        self.telemetry_service = telemetry_service
        self.setWindowTitle(f"Active Users - {GUI_LABEL_VERSION}")
        self.setMinimumSize(600, 500)
        self.first_load = True

        self.setup_ui()
        self.setup_timer()

        # Fetch users immediately
        self.refresh_users()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Info label
        self.info_label = QLabel("Loading active users...")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Callsign",
            "Last Heartbeat",
            "Grid",
            "Band",
            "Version",
            "OS"
        ])

        # Configure table
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)  # Remove grid lines
        self.table.setSortingEnabled(True)  # Enable sorting on column headers

        # Center-align row numbers
        self.table.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        # Apply stylesheet - remove all separators
        self.table.setStyleSheet(TABLE_SETTING_QSS + """
            QHeaderView::section {
                border: 0px;
            }
            QHeaderView {
                border: none;
            }
            QTableView {
                border: none;
            }
            QTableCornerButton::section {
                border: none;
                background-color: transparent;
            }
        """)

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Callsign
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Last Heartbeat
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Grid
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Band
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Version
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # OS - stretches to fill window

        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()

        self.refresh_button = CustomButton("Refresh Now")
        self.refresh_button.clicked.connect(self.refresh_users)
        button_layout.addWidget(self.refresh_button)

        button_layout.addStretch()

        self.close_button = CustomButton("Close")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def setup_timer(self):
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_users)
        self.refresh_timer.start(5000)  # 5 seconds

    def refresh_users(self):
        try:
            result = self.telemetry_service.get_active_users()

            if result and result.get('success'):
                users = result.get('users', [])
                self.update_table(users)
                count = result.get('count', 0)
                self.info_label.setText(f"Active users: {count} (refreshing every 5 seconds)")
            else:
                self.info_label.setText("Failed to fetch active users. Retrying...")
                log.warning("Failed to fetch active users from API")
        except Exception as e:
            log.error(f"Error refreshing users: {e}")
            self.info_label.setText(f"Error: {str(e)}")

    def update_table(self, users):
        if not self.first_load:
            current_sort_column = self.table.horizontalHeader().sortIndicatorSection()
            current_sort_order = self.table.horizontalHeader().sortIndicatorOrder()
        else:
            current_sort_column = 1  # Last Heartbeat
            current_sort_order = Qt.SortOrder.DescendingOrder
            self.first_load = False

        # Disable sorting while updating to avoid issues
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(users))

        for row, user in enumerate(users):
            # Callsign
            callsign_item = QTableWidgetItem(user.get('callsign', ''))
            callsign_font = QFont()
            callsign_font.setBold(True)
            callsign_item.setFont(callsign_font)
            self.table.setItem(row, 0, callsign_item)

            # Last Heartbeat (format as relative time and store actual timestamp for sorting)
            last_seen = user.get('last_seen', '')
            last_seen_formatted = self.format_last_seen(last_seen)
            heartbeat_item = SortableTableWidgetItem(last_seen_formatted)

            # Store actual timestamp for proper sorting
            try:
                last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                heartbeat_item.setData(Qt.ItemDataRole.UserRole, last_seen_dt.timestamp())
            except Exception:
                heartbeat_item.setData(Qt.ItemDataRole.UserRole, 0)

            self.table.setItem(row, 1, heartbeat_item)

            # Grid
            self.table.setItem(row, 2, QTableWidgetItem(user.get('grid', '')))

            # Band (with sort key for proper numeric ordering)
            band = user.get('band', '')
            band_item = SortableTableWidgetItem(band)
            # Store numeric band value for proper sorting (70cm=0.7, 2m=2, 10m=10, 160m=160)
            band_sort_key = get_band_sort_key(band)
            band_item.setData(Qt.ItemDataRole.UserRole, band_sort_key)
            self.table.setItem(row, 3, band_item)

            # Version
            self.table.setItem(row, 4, QTableWidgetItem(user.get('version', '')))

            # OS
            self.table.setItem(row, 5, QTableWidgetItem(user.get('os', '')))

        # Re-enable sorting and restore previous sort order
        self.table.setSortingEnabled(True)
        self.table.sortItems(current_sort_column, current_sort_order)

    def format_last_seen(self, last_seen_str):
        if not last_seen_str:
            return "Unknown"

        try:
            last_seen = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00'))
            now = datetime.now(last_seen.tzinfo)
            delta = now - last_seen

            seconds = int(delta.total_seconds())

            if seconds < 60:
                return f"{seconds}s ago"
            elif seconds < 3600:
                minutes = seconds // 60
                return f"{minutes}m ago"
            elif seconds < 86400:
                hours = seconds // 3600
                return f"{hours}h ago"
            else:
                days = seconds // 86400
                return f"{days}d ago"
        except Exception as e:
            log.error(f"Error formatting last_seen: {e}")
            return last_seen_str

    def closeEvent(self, event):
        self.refresh_timer.stop()
        event.accept()
