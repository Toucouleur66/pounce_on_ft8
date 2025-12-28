# active_users_window.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QHBoxLayout, QLabel
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QPalette, QColor
from datetime import datetime
from custom_button import CustomButton
from time_ago_delegate import TimeAgoDelegate

from logger import get_logger
from utils import band_sort_key
from style import set_macos_window_appearance

from constants import GUI_LABEL_VERSION
from translatable_strings import ActiveUsersStrings, CommonStrings

log = get_logger(__name__)

class SortableTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        # Get UserRole data for sorting
        self_data = self.data(Qt.ItemDataRole.UserRole)
        other_data = other.data(Qt.ItemDataRole.UserRole)

        # If both have UserRole data, compare by that
        if self_data is not None and other_data is not None:
            # Handle dict with 'sort_key' (for Last Heartbeat column)
            if isinstance(self_data, dict) and 'sort_key' in self_data:
                self_value = self_data['sort_key']
            else:
                self_value = self_data

            if isinstance(other_data, dict) and 'sort_key' in other_data:
                other_value = other_data['sort_key']
            else:
                other_value = other_data

            return self_value < other_value

        # Otherwise, fall back to text comparison
        return super().__lt__(other)

class ActiveUsersWindow(QDialog):
    def __init__(self, telemetry_service, dark_mode=False, parent=None):
        super().__init__(parent)
        self.telemetry_service = telemetry_service
        self.dark_mode = dark_mode
        self.setWindowTitle(f"{ActiveUsersStrings.WINDOW_TITLE()} - {GUI_LABEL_VERSION}")
        self.setMinimumSize(650, 500)
        self.first_load = True

        self.setup_ui()
        self.apply_palette(dark_mode)
        self.setup_timer()

        # Fetch users immediately
        self.refresh_users()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Info label
        self.info_label = QLabel(ActiveUsersStrings.INFO_LOADING())
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            ActiveUsersStrings.HEADER_CALLSIGN(),
            ActiveUsersStrings.HEADER_LAST_HEARTBEAT(),
            ActiveUsersStrings.HEADER_GRID(),
            ActiveUsersStrings.HEADER_BAND(),
            ActiveUsersStrings.HEADER_VERSION(),
            ActiveUsersStrings.HEADER_OS()
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

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Callsign
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Last Heartbeat
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Grid
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Band
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Version
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # OS - stretches to fill window

        # Set TimeAgoDelegate for Last Heartbeat column
        self.table.setItemDelegateForColumn(1, TimeAgoDelegate())

        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()

        self.refresh_button = CustomButton(CommonStrings.REFRESH_NOW())
        self.refresh_button.clicked.connect(self.refresh_users)
        button_layout.addWidget(self.refresh_button)

        button_layout.addStretch()

        self.close_button = CustomButton(CommonStrings.CLOSE())
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def setup_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_users)
        self.refresh_timer.start(5000)  # 5 seconds

    def apply_palette(self, dark_mode):
        self.dark_mode = dark_mode

        # Force macOS title bar appearance to match theme
        set_macos_window_appearance(self, dark_mode)

        # Create palette for table
        table_palette = QPalette()

        if dark_mode:
            table_palette.setColor(QPalette.ColorRole.Base, QColor('#353535'))
            table_palette.setColor(QPalette.ColorRole.AlternateBase, QColor('#454545'))
            table_palette.setColor(QPalette.ColorRole.Text, QColor('#FFFFFF'))

            gridline_color = '#171717'
            background_color = '#353535'
        else:
            table_palette.setColor(QPalette.ColorRole.Base, QColor('#FFFFFF'))
            table_palette.setColor(QPalette.ColorRole.AlternateBase, QColor('#F4F5F5'))
            table_palette.setColor(QPalette.ColorRole.Text, QColor('#000000'))

            gridline_color = '#D3D3D3'
            background_color = '#FFFFFF'

        # Apply stylesheet with theme colors
        table_qss = f"""
            QTableWidget {{
                background-color: {background_color};
                gridline-color: {gridline_color};
                border: none;
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
            QHeaderView::section {{
                font-weight: normal;
                border: none;
                padding: 0 3px 0 3px;
            }}
            QTableCornerButton::section {{
                border: none;
            }}
            QHeaderView::section:horizontal:last {{
                border-right: none;
            }}
        """

        self.table.setStyleSheet(table_qss)
        self.table.setPalette(table_palette)
        self.table.setShowGrid(False)

    def refresh_users(self):
        try:
            # Ensure timer is running
            if not self.refresh_timer.isActive():
                log.warning("Timer was stopped, restarting...")
                self.refresh_timer.start(5000)

            result = self.telemetry_service.get_active_users()

            if result and result.get('success'):
                users = result.get('users', [])
                self.update_table(users)
                count = result.get('count', 0)
                self.info_label.setText(ActiveUsersStrings.INFO_ACTIVE_USERS(count))
            else:
                self.info_label.setText(ActiveUsersStrings.INFO_FAILED())
        except Exception as e:
            log.error(f"Error refreshing users: {e}")
            import traceback
            log.error(traceback.format_exc())
            self.info_label.setText(ActiveUsersStrings.INFO_ERROR(str(e)))

    def update_table(self, users):
        try:
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
                callsign_item.setFont(callsign_font)
                self.table.setItem(row, 0, callsign_item)

                # Last Heartbeat (use TimeAgoDelegate for display)
                last_seen = user.get('last_seen', '')
                heartbeat_item = SortableTableWidgetItem('')

                # Store datetime for TimeAgoDelegate and sorting
                try:
                    last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                    heartbeat_item.setData(Qt.ItemDataRole.UserRole, {
                        'row_datetime': last_seen_dt,
                        'sort_key': last_seen_dt.timestamp()
                    })
                except Exception:
                    heartbeat_item.setData(Qt.ItemDataRole.UserRole, {
                        'row_datetime': None,
                        'sort_key': 0
                    })

                self.table.setItem(row, 1, heartbeat_item)

                # Grid
                self.table.setItem(row, 2, QTableWidgetItem(user.get('grid', '')))

                # Band (with sort key for proper numeric ordering)
                band = user.get('band', '')
                band_item = SortableTableWidgetItem(band)
                band_item.setData(Qt.ItemDataRole.UserRole, band_sort_key(band))
                self.table.setItem(row, 3, band_item)

                # Version
                self.table.setItem(row, 4, QTableWidgetItem(user.get('version', '')))

                # OS
                self.table.setItem(row, 5, QTableWidgetItem(user.get('os', '')))

            # Re-enable sorting and restore previous sort order
            self.table.setSortingEnabled(True)
            self.table.sortItems(current_sort_column, current_sort_order)

        except Exception as e:
            log.error(f"Error in update_table: {e}")
            import traceback
            log.error(traceback.format_exc())
            # Re-enable sorting even on error
            self.table.setSortingEnabled(True)

    def closeEvent(self, event):
        self.refresh_timer.stop()
        event.accept()
