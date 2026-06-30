# setting_dialog

import platform
import subprocess
import os
import sys
import re

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QFileDialog, QTableWidgetItem
from PyQt6.QtCore import Qt

from custom_button import CustomButton
from priority_table import PriorityTableWidget
from adif_summary_dialog import AdifSummaryDialog
from lotw_manager import LoTWManager
from lotw_uploader import LoTWClient
from lotw_incoming_dialog import LoTWIncomingDialog
from lotw_sync_worker import LoTWDownloadWorker
from clublog import ClubLogUploader
from window_monitoring_dialog import WindowMonitoringDialog
from window_controller import WindowController

from datetime import datetime

from translatable_strings import SettingsStrings, CommonStrings

from utils import get_local_ip_address, get_log_filename
from utils import parse_adif
from utils import AMATEUR_BANDS, ADIF_FIELD_RE

from style import get_setting_qss, get_table_setting_qss, get_odd_color, get_groupbox_qss, set_macos_window_appearance

from style import (
    # Colors
    STATUS_TRX_COLOR,
    EVEN_COLOR,
    ODD_COLOR
)

from constants import (
    # Labels
    GUI_LABEL_NAME,
    # Modes
    MODE_NORMAL,
    MODE_FOX_HOUND,
    MODE_SUPER_FOX,
    MODE_CUSTOM,
    WKB4_REPLY_MODE_ALWAYS,
    WKB4_REPLY_MODE_CURRENT_YEAR,
    WKB4_REPLY_MODE_NEVER,
    FREQ_MINIMUM,
    FREQ_MAXIMUM,
    FREQ_MINIMUM_FOX_HOUND,
    FREQ_MAXIMUM_SUPER_FOX,
    # Marathon
    MARATHON_UNLIMITED,
    # Priority
    PRIORITY_LIST,
    # UDP related
    DEFAULT_UDP_PORT,
    DEFAULT_AUTO_START_MONITORING,
    DEFAULT_SECONDARY_UDP_SERVER,
    DEFAULT_SENDING_REPLY,
    DEFAULT_POLITE_REPLY,
    DEFAULT_GAP_FINDER,
    DEFAULT_WATCHDOG,
    DEFAULT_WATCHDOG_NUMBER_OF_ATTEMPTS,
    DEFAULT_WATCHDOG_RETRY_TIME,
    DEFAULT_DEBUG_OUTPUT,
    DEFAULT_POUNCE_LOG,
    DEFAULT_LOG_PACKET_DATA,
    DEFAULT_REPLY_ATTEMPTS,
    DEFAULT_DELAY_BETWEEN_SOUND,
    DEFAULT_MAX_WAITING_DELAY,
    DEFAULT_MINIMUM_REPORT,
    DEFAULT_JTDX_CLICK_PROMPT_LOG_QSO,
    DEFAULT_JTDX_CLICK_DELAY,
    # PstRotator
    DEFAULT_PSTROTATOR_HOST,
    DEFAULT_PSTROTATOR_PORT,
    DEFAULT_ENABLE_PSTROTATOR_WANTED,
    DEFAULT_ENABLE_PSTROTATOR_SCHEDULE,
    DEFAULT_PSTROTATOR_THRESHOLD,
    DEFAULT_ENABLE_PSTROTATOR_PARK,
    DEFAULT_PSTROTATOR_PARK_DELAY,
    # Fonts
    CUSTOM_FONT,
    CUSTOM_FONT_SMALL,
    # ADIF
    ADIF_WORKED_CALLSIGNS_FILE
)

from logger import get_logger

log = get_logger(__name__)


class TimeHHMMDelegate(QtWidgets.QStyledItemDelegate):
    """Cell editor restricted to a valid HH:mm time (00:00 - 23:59)."""

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QTimeEdit(parent)
        editor.setDisplayFormat("HH:mm")
        editor.setFrame(False)
        return editor

    def setEditorData(self, editor, index):
        text = index.data(QtCore.Qt.ItemDataRole.EditRole) or "00:00"
        time = QtCore.QTime.fromString(str(text), "HH:mm")
        if not time.isValid():
            time = QtCore.QTime(0, 0)
        editor.setTime(time)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.time().toString("HH:mm"), QtCore.Qt.ItemDataRole.EditRole)


class AzimuthDelegate(QtWidgets.QStyledItemDelegate):
    """Cell editor restricted to an integer azimuth (0 - 359)."""

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QSpinBox(parent)
        editor.setRange(0, 359)
        editor.setFrame(False)
        return editor

    def setEditorData(self, editor, index):
        try:
            value = int(str(index.data(QtCore.Qt.ItemDataRole.EditRole)).strip())
        except (TypeError, ValueError):
            value = 0
        editor.setValue(max(0, min(359, value)))

    def setModelData(self, editor, model, index):
        editor.interpretText()
        model.setData(index, str(editor.value()), QtCore.Qt.ItemDataRole.EditRole)

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, params=None, dark_mode=False):
        super().__init__(parent)
        self.setWindowTitle(SettingsStrings.WINDOW_TITLE())

        self.params = params or {}
        self.dark_mode = dark_mode

        # Collections for widgets that need theme updates
        self.notice_labels = []
        self.group_boxes = []
        self.table_widgets = []

        self.marathon_preference     = self.params.get('marathon_preference', {})
        self.dxcc_preference         = self.params.get('dxcc_preference', {})
        self.grid_tracker_preference = self.params.get('grid_tracker_preference', {})

        layout = QtWidgets.QVBoxLayout(self)

        main_horizontal_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(main_horizontal_layout)

        self.menu_list = QtWidgets.QListWidget()
        self.menu_list.setFont(CUSTOM_FONT)
        self.menu_list.setFixedWidth(180)
        self.menu_list.setAlternatingRowColors(True)
        self.menu_list.setUniformItemSizes(True)

        menu_items = [
            SettingsStrings.MENU_SERVER(),
            SettingsStrings.MENU_GENERAL_SETTINGS(),
            SettingsStrings.MENU_WATCHDOG_RETRY(),
            SettingsStrings.MENU_OFFSET_UPDATER(),
            SettingsStrings.MENU_SOUND_ALERTS(),
            SettingsStrings.MENU_LOTW(),
            SettingsStrings.MENU_DX_MARATHON(),
            SettingsStrings.MENU_DXCC_PROGRAM(),
            SettingsStrings.MENU_GRID_TRACKER(),
            SettingsStrings.MENU_PRIORITY_MANAGER(),
            SettingsStrings.MENU_LOGBOOK_ANALYSIS(),
            SettingsStrings.MENU_WORKED_BEFORE(),
            SettingsStrings.MENU_CLUB_LOG(),
            SettingsStrings.MENU_LOGBOOK_BACKUP(),
            SettingsStrings.MENU_AUTOMATE_TASKS(),
            SettingsStrings.MENU_PSTROTATOR(),
            SettingsStrings.MENU_DEBUGGING()
        ]

        for i, item in enumerate(menu_items, 1):
            #self.menu_list.addItem(f"{i}. {item}")
            self.menu_list.addItem(f" {item}")  # Add spaces for Windows 11 spacing

        # Set higher height for all items
        for i in range(self.menu_list.count()):
            item = self.menu_list.item(i)
            item.setSizeHint(QtCore.QSize(170, 32))

        self.stacked_widget = QtWidgets.QStackedWidget()

        main_horizontal_layout.addWidget(self.menu_list)
        main_horizontal_layout.addWidget(self.stacked_widget)

        server_page       = QtWidgets.QWidget()
        general_page      = QtWidgets.QWidget()
        watchdog_page     = QtWidgets.QWidget()
        offset_page       = QtWidgets.QWidget()
        sound_page        = QtWidgets.QWidget()
        lotw_page         = QtWidgets.QWidget()
        marathon_page     = QtWidgets.QWidget()
        dxcc_page         = QtWidgets.QWidget()
        grid_tracker_page = QtWidgets.QWidget()
        priority_page     = QtWidgets.QWidget()
        log_analysis_page = QtWidgets.QWidget()
        worked_b4_page    = QtWidgets.QWidget()
        club_log_page     = QtWidgets.QWidget()
        backup_page       = QtWidgets.QWidget()
        automate_tasks_page = QtWidgets.QWidget()
        automate_tasks_page.setMinimumHeight(250)
        pstrotator_page   = QtWidgets.QWidget()
        pstrotator_page.setMinimumHeight(250)
        debugging_page    = QtWidgets.QWidget()
        debugging_page.setMinimumHeight(250)

        self.stacked_widget.addWidget(server_page)
        self.stacked_widget.addWidget(general_page)
        self.stacked_widget.addWidget(watchdog_page)
        self.stacked_widget.addWidget(offset_page)
        self.stacked_widget.addWidget(sound_page)
        self.stacked_widget.addWidget(lotw_page)
        self.stacked_widget.addWidget(marathon_page)
        self.stacked_widget.addWidget(dxcc_page)
        self.stacked_widget.addWidget(grid_tracker_page)
        self.stacked_widget.addWidget(priority_page)
        self.stacked_widget.addWidget(log_analysis_page)
        self.stacked_widget.addWidget(worked_b4_page)
        self.stacked_widget.addWidget(club_log_page)
        self.stacked_widget.addWidget(backup_page)
        self.stacked_widget.addWidget(automate_tasks_page)
        self.stacked_widget.addWidget(pstrotator_page)
        self.stacked_widget.addWidget(debugging_page)

        server_layout         = QtWidgets.QVBoxLayout(server_page)
        general_layout        = QtWidgets.QVBoxLayout(general_page)
        watchdog_layout       = QtWidgets.QVBoxLayout(watchdog_page)
        offset_layout         = QtWidgets.QVBoxLayout(offset_page)
        sound_layout          = QtWidgets.QVBoxLayout(sound_page)
        priority_layout       = QtWidgets.QVBoxLayout(priority_page)
        lotw_layout           = QtWidgets.QVBoxLayout(lotw_page)
        marathon_layout       = QtWidgets.QVBoxLayout(marathon_page)
        dxcc_layout           = QtWidgets.QVBoxLayout(dxcc_page)
        grid_tracker_layout   = QtWidgets.QVBoxLayout(grid_tracker_page)
        log_analysis_layout   = QtWidgets.QVBoxLayout(log_analysis_page)
        worked_b4_layout      = QtWidgets.QVBoxLayout(worked_b4_page)
        club_log_layout       = QtWidgets.QVBoxLayout(club_log_page)
        backup_layout         = QtWidgets.QVBoxLayout(backup_page)
        automate_tasks_layout = QtWidgets.QVBoxLayout(automate_tasks_page)
        pstrotator_layout     = QtWidgets.QVBoxLayout(pstrotator_page)
        debugging_layout      = QtWidgets.QVBoxLayout(debugging_page)

        self.menu_list.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)
        self.menu_list.setCurrentRow(0)  # Select first item by default

        self.setMinimumWidth(700)
        self.setMinimumHeight(700)
        self.resize(700, 700)

        """
            Server Settings
        """
        jtdx_notice_text = SettingsStrings.SERVER_NOTICE_JTDX()
        jtdx_notice_label = QtWidgets.QLabel(jtdx_notice_text)
        jtdx_notice_label.setWordWrap(True)
        jtdx_notice_label.setFont(CUSTOM_FONT_SMALL)
        jtdx_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        jtdx_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))

        self.notice_labels.append(jtdx_notice_label)
        jtdx_notice_label.setAutoFillBackground(True)

        primary_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_PRIMARY_UDP())
        self.group_boxes.append(primary_group)
        primary_group.setFont(CUSTOM_FONT_SMALL)
        primary_layout = QtWidgets.QGridLayout()

        self.primary_udp_server_address = QtWidgets.QLineEdit()
        self.primary_udp_server_address.setFont(CUSTOM_FONT)
        self.primary_udp_server_port = QtWidgets.QLineEdit()
        self.primary_udp_server_port.setFont(CUSTOM_FONT)

        self.enable_auto_start_monitoring = QtWidgets.QCheckBox(SettingsStrings.CHECK_AUTO_START())
        self.enable_auto_start_monitoring.setFont(CUSTOM_FONT)
        self.enable_auto_start_monitoring.setChecked(DEFAULT_AUTO_START_MONITORING)

        udp_server_label = QtWidgets.QLabel(SettingsStrings.LABEL_UDP_SERVER())
        udp_server_label.setFont(CUSTOM_FONT)
        primary_layout.addWidget(udp_server_label, 0, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        primary_layout.addWidget(self.primary_udp_server_address, 0, 1)
        udp_server_port_label = QtWidgets.QLabel(SettingsStrings.LABEL_UDP_PORT())
        udp_server_port_label.setFont(CUSTOM_FONT)
        primary_layout.addWidget(udp_server_port_label, 1, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        primary_layout.addWidget(self.primary_udp_server_port, 1, 1)
        primary_layout.addWidget(self.enable_auto_start_monitoring, 2, 0, 1, 2)
        primary_layout.setColumnMinimumWidth(0, 200)
        primary_layout.setColumnStretch(0, 0)

        primary_group.setLayout(primary_layout)

        secondary_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_SECONDARY_UDP())
        self.group_boxes.append(secondary_group)
        secondary_group.setFont(CUSTOM_FONT_SMALL)
        secondary_layout = QtWidgets.QGridLayout()

        self.secondary_udp_server_address = QtWidgets.QLineEdit()
        self.secondary_udp_server_address.setFont(CUSTOM_FONT)
        self.secondary_udp_server_port = QtWidgets.QLineEdit()
        self.secondary_udp_server_port.setFont(CUSTOM_FONT)

        self.enable_secondary_udp_server = QtWidgets.QCheckBox(SettingsStrings.CHECK_ENABLE_SECONDARY())
        self.enable_secondary_udp_server.setFont(CUSTOM_FONT)
        self.enable_secondary_udp_server.setChecked(DEFAULT_SECONDARY_UDP_SERVER)

        secondary_udp_server_label = QtWidgets.QLabel(SettingsStrings.LABEL_UDP_SERVER())
        secondary_udp_server_label.setFont(CUSTOM_FONT)
        secondary_layout.addWidget(secondary_udp_server_label, 0, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        secondary_layout.addWidget(self.secondary_udp_server_address, 0, 1)
        secondary_udp_server_port_label = QtWidgets.QLabel(SettingsStrings.LABEL_UDP_PORT())
        secondary_udp_server_port_label.setFont(CUSTOM_FONT)
        secondary_layout.addWidget(secondary_udp_server_port_label, 1, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        secondary_layout.addWidget(self.secondary_udp_server_port, 1, 1)
        secondary_layout.addWidget(self.enable_secondary_udp_server, 2, 0, 1, 2)
        secondary_layout.setColumnMinimumWidth(0, 200)
        secondary_layout.setColumnStretch(0, 0)

        secondary_group.setLayout(secondary_layout)

        logging_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_LOGGING_UDP())
        self.group_boxes.append(logging_group)
        logging_group.setFont(CUSTOM_FONT_SMALL)
        logging_layout = QtWidgets.QGridLayout()

        self.logging_udp_server_address = QtWidgets.QLineEdit()
        self.logging_udp_server_address.setFont(CUSTOM_FONT)
        self.logging_udp_server_port = QtWidgets.QLineEdit()
        self.logging_udp_server_port.setFont(CUSTOM_FONT)

        self.enable_logging_udp_server = QtWidgets.QCheckBox(SettingsStrings.CHECK_ENABLE_LOGGING())
        self.enable_logging_udp_server.setFont(CUSTOM_FONT)
        self.enable_logging_udp_server.setChecked(DEFAULT_SECONDARY_UDP_SERVER)

        logging_udp_server_label = QtWidgets.QLabel(SettingsStrings.LABEL_UDP_SERVER())
        logging_udp_server_label.setFont(CUSTOM_FONT)
        logging_layout.addWidget(logging_udp_server_label, 0, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        logging_layout.addWidget(self.logging_udp_server_address, 0, 1)
        logging_udp_server_port_label = QtWidgets.QLabel(SettingsStrings.LABEL_UDP_PORT())
        logging_udp_server_port_label.setFont(CUSTOM_FONT)
        logging_layout.addWidget(logging_udp_server_port_label, 1, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        logging_layout.addWidget(self.logging_udp_server_port, 1, 1)
        logging_layout.addWidget(self.enable_logging_udp_server, 2, 0, 1, 2)
        logging_layout.setColumnMinimumWidth(0, 200)
        logging_layout.setColumnStretch(0, 0)

        logging_group.setLayout(logging_layout)

        server_layout.addWidget(jtdx_notice_label)
        server_layout.addWidget(primary_group)
        server_layout.addWidget(secondary_group)
        server_layout.addWidget(logging_group)
        server_layout.addStretch()

        """
            Main Settings
        """
        general_notice_text = SettingsStrings.GENERAL_NOTICE()
        general_notice_label = QtWidgets.QLabel(general_notice_text)
        general_notice_label.setWordWrap(True)
        general_notice_label.setFont(CUSTOM_FONT_SMALL)
        general_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        general_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(general_notice_label)
        general_notice_label.setAutoFillBackground(True)

        """
            Offset Settings
        """
        offset_notice_text = SettingsStrings.OFFSET_NOTICE()
        offset_notice_label = QtWidgets.QLabel(offset_notice_text)
        offset_notice_label.setWordWrap(True)
        offset_notice_label.setFont(CUSTOM_FONT_SMALL)
        offset_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        offset_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(offset_notice_label)
        offset_notice_label.setAutoFillBackground(True)

        offset_settings_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_OFFSET_SETTINGS())
        self.group_boxes.append(offset_settings_group)
        offset_settings_group.setFont(CUSTOM_FONT_SMALL)

        offset_settings_widget = QtWidgets.QWidget()
        offset_settings_layout = QtWidgets.QGridLayout(offset_settings_widget)
        offset_settings_layout.setVerticalSpacing(15)

        self.enable_gap_finder = QtWidgets.QCheckBox(SettingsStrings.CHECK_ENABLE_GAP_FINDER())
        self.enable_gap_finder.setFont(CUSTOM_FONT)
        self.enable_gap_finder.setChecked(DEFAULT_GAP_FINDER)

        offset_settings_layout.addWidget(self.enable_gap_finder, 0, 0, 1, 2)

        offset_settings_group.setLayout(QtWidgets.QVBoxLayout())
        offset_settings_group.layout().setContentsMargins(0, 0, 0, 0)
        offset_settings_group.layout().addWidget(offset_settings_widget)

        general_settings_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_GENERAL_SETTINGS())
        self.group_boxes.append(general_settings_group)
        general_settings_group.setFont(CUSTOM_FONT_SMALL)

        general_settings_widget = QtWidgets.QWidget()
        general_settings_layout = QtWidgets.QGridLayout(general_settings_widget)
        general_settings_layout.setVerticalSpacing(15)

        self.enable_sending_reply = QtWidgets.QCheckBox(SettingsStrings.CHECK_ENABLE_REPLY())
        self.enable_sending_reply.setFont(CUSTOM_FONT)
        self.enable_sending_reply.setChecked(DEFAULT_SENDING_REPLY)

        self.enable_polite_reply = QtWidgets.QCheckBox(SettingsStrings.CHECK_ENABLE_POLITE_REPLY())
        self.enable_polite_reply.setFont(CUSTOM_FONT)
        self.enable_polite_reply.setChecked(DEFAULT_POLITE_REPLY)
        self.enable_polite_reply.toggled.connect(self.populate_priority_list)

        self.enable_log_all_valid_contact = QtWidgets.QCheckBox(SettingsStrings.CHECK_LOG_ALL_VALID())
        self.enable_log_all_valid_contact.setFont(CUSTOM_FONT)
        self.enable_log_all_valid_contact.setChecked(True)

        self.enable_reply_to_valid_callsign = QtWidgets.QCheckBox(SettingsStrings.CHECK_IGNORE_INVALID_CALLSIGN())
        self.enable_reply_to_valid_callsign.setFont(CUSTOM_FONT)
        self.enable_reply_to_valid_callsign.setChecked(True)

        self.enable_reply_to_valid_direction = QtWidgets.QCheckBox(SettingsStrings.CHECK_IGNORE_WRONG_CONTINENT())
        self.enable_reply_to_valid_direction.setFont(CUSTOM_FONT)
        self.enable_reply_to_valid_direction.setChecked(True)

        general_settings_layout.addWidget(self.enable_sending_reply, 0, 0, 1, 2)
        general_settings_layout.addWidget(self.enable_polite_reply, 1, 0, 1, 2)
        general_settings_layout.addWidget(self.enable_log_all_valid_contact, 2, 0, 1, 2)
        general_settings_layout.addWidget(self.enable_reply_to_valid_callsign, 3, 0, 1, 2)
        general_settings_layout.addWidget(self.enable_reply_to_valid_direction, 4, 0, 1, 2)

        general_settings_group.setLayout(QtWidgets.QVBoxLayout())
        general_settings_group.layout().setContentsMargins(0, 0, 0, 0)
        general_settings_group.layout().addWidget(general_settings_widget)


        self.freq_range_type_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_FREQ_RANGE())
        self.group_boxes.append(self.freq_range_type_group)
        self.freq_range_type_group.setFont(CUSTOM_FONT_SMALL)

        udp_freq_range_type_widget = QtWidgets.QWidget()
        udp_freq_range_type_layout = QtWidgets.QVBoxLayout(udp_freq_range_type_widget)

        self.radio_normal   = QtWidgets.QRadioButton()
        self.radio_foxhound = QtWidgets.QRadioButton()
        self.radio_superfox = QtWidgets.QRadioButton()
        self.radio_custom   = QtWidgets.QRadioButton()

        self.freq_range_mode_var = QtWidgets.QButtonGroup()
        self.freq_range_mode_var.addButton(self.radio_normal)
        self.freq_range_mode_var.addButton(self.radio_foxhound)
        self.freq_range_mode_var.addButton(self.radio_superfox)
        self.freq_range_mode_var.addButton(self.radio_custom)

        # Define frequency ranges for each preset
        self.freq_range = {
            self.radio_normal:   (FREQ_MINIMUM, FREQ_MAXIMUM),
            self.radio_foxhound: (FREQ_MINIMUM_FOX_HOUND, FREQ_MAXIMUM),
            self.radio_superfox: (FREQ_MINIMUM, FREQ_MAXIMUM_SUPER_FOX),
        }

        modes = [
            (
                self.radio_normal,
                MODE_NORMAL,
                FREQ_MINIMUM,
                FREQ_MAXIMUM
            ),
            (
                self.radio_foxhound,
                MODE_FOX_HOUND,
                FREQ_MINIMUM_FOX_HOUND,
                FREQ_MAXIMUM
            ),
            (
                self.radio_superfox,
                MODE_SUPER_FOX,
                FREQ_MINIMUM,
                FREQ_MAXIMUM_SUPER_FOX
            ),
            (
                self.radio_custom,
                MODE_CUSTOM,
                FREQ_MINIMUM,
                FREQ_MAXIMUM
            ),
        ]

        self.mode_table_widget = QtWidgets.QTableWidget()
        self.mode_table_widget.setRowCount(len(modes))
        self.mode_table_widget.setColumnCount(3)  # Removed radio button column

        self.mode_table_widget.setColumnWidth(0, 120)  # Min Frequency
        self.mode_table_widget.setColumnWidth(1, 120)  # Max Frequency

        self.mode_table_widget.horizontalHeader().setStretchLastSection(True)
        self.mode_table_widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)

        self.mode_table_widget.setShowGrid(False)
        self.mode_table_widget.horizontalHeader().setVisible(False)
        self.mode_table_widget.verticalHeader().setVisible(False)
        self.mode_table_widget.setAlternatingRowColors(True)
        self.mode_table_widget.setFont(CUSTOM_FONT_SMALL)

        self.mode_table_widget.horizontalHeader().setHighlightSections(False)
        self.mode_table_widget.verticalHeader().setHighlightSections(False)
        self.mode_table_widget.setFrameStyle(QtWidgets.QFrame.Shape.NoFrame)

        headers = [
            SettingsStrings.LABEL_MIN_FREQUENCY(),
            SettingsStrings.LABEL_MAX_FREQUENCY(),
            SettingsStrings.LABEL_MODE()
        ]
        self.mode_table_widget.setHorizontalHeaderLabels(headers)
        self.mode_table_widget.horizontalHeader().setFont(CUSTOM_FONT_SMALL)
        self.mode_table_widget.horizontalHeader().setVisible(True)
        self.mode_table_widget.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

        self.mode_table_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed
        )

        self.mode_table_widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.mode_table_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        row_height = 30
        self.row_to_radio = {}

        for row, (button, label, freq_min, freq_max) in enumerate(modes):
            self.mode_table_widget.setRowHeight(row, row_height)

            # Store the mapping between row and radio button
            self.row_to_radio[row] = button

            freq_min_item = QTableWidgetItem(f"{freq_min}Hz")
            freq_min_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            freq_min_item.setFont(CUSTOM_FONT_SMALL)
            freq_min_item.setFlags(freq_min_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.mode_table_widget.setItem(row, 0, freq_min_item)

            freq_max_item = QTableWidgetItem(f"{freq_max}Hz")
            freq_max_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            freq_max_item.setFont(CUSTOM_FONT_SMALL)
            freq_max_item.setFlags(freq_max_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.mode_table_widget.setItem(row, 1, freq_max_item)

            label_item = QTableWidgetItem(f"{label}")
            label_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            label_item.setFont(CUSTOM_FONT_SMALL)
            self.mode_table_widget.setItem(row, 2, label_item)

        # Auto-size table to fit all rows without scrolling
        # self.mode_table_widget.resizeRowsToContents()
        header_height = self.mode_table_widget.horizontalHeader().sizeHint().height()
        total_height = header_height + (row_height * len(modes)) + 15
        self.mode_table_widget.setFixedHeight(total_height)

        self.mode_table_widget.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                font-weight: normal;
                border: none;
                padding: 10 4px 4px 4px;
            }
        """)

        self.mode_table_widget.setStyleSheet(get_table_setting_qss())
        self.table_widgets.append(self.mode_table_widget)
        self.mode_table_widget.verticalHeader().setVisible(False)
        self.mode_table_widget.cellClicked.connect(self.on_table_row_selected)

        udp_freq_range_type_layout.addWidget(self.mode_table_widget)

        self.freq_range_type_group.setLayout(QtWidgets.QVBoxLayout())
        self.freq_range_type_group.layout().setContentsMargins(0, 0, 0, 0)
        self.freq_range_type_group.layout().addWidget(udp_freq_range_type_widget)

        # Custom range group
        self.custom_range_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_CUSTOM_RANGE())
        self.group_boxes.append(self.custom_range_group)
        self.custom_range_group.setFont(CUSTOM_FONT_SMALL)

        custom_range_widget = QtWidgets.QWidget()
        custom_range_layout = QtWidgets.QHBoxLayout(custom_range_widget)
        custom_range_layout.setContentsMargins(0, 5, 0, 0)

        # Labels and input fields for frequency range
        min_label = QtWidgets.QLabel(SettingsStrings.LABEL_MIN_FREQ())
        min_label.setFont(CUSTOM_FONT_SMALL)
        self.min_freq = QtWidgets.QSpinBox()
        self.min_freq.setRange(0, 10000)
        self.min_freq.setValue(FREQ_MINIMUM)
        self.min_freq.setSuffix("Hz")
        self.min_freq.setFont(CUSTOM_FONT_SMALL)

        max_label = QtWidgets.QLabel(SettingsStrings.LABEL_MAX_FREQ())
        max_label.setFont(CUSTOM_FONT_SMALL)
        self.max_freq = QtWidgets.QSpinBox()
        self.max_freq.setRange(0, 10000)
        self.max_freq.setValue(FREQ_MAXIMUM)
        self.max_freq.setSuffix("Hz")
        self.max_freq.setFont(CUSTOM_FONT_SMALL)

        custom_range_layout.addWidget(min_label)
        custom_range_layout.addWidget(self.min_freq)
        custom_range_layout.addStretch()  # This pushes max fields to the right
        custom_range_layout.addWidget(max_label)
        custom_range_layout.addWidget(self.max_freq)

        # Store custom frequency values
        self.custom_min_freq_value = FREQ_MINIMUM
        self.custom_max_freq_value = FREQ_MAXIMUM

        # Connect frequency input changes to auto-select custom and update table
        self.min_freq.valueChanged.connect(self.on_frequency_changed)
        self.max_freq.valueChanged.connect(self.on_frequency_changed)

        self.custom_range_group.setLayout(QtWidgets.QVBoxLayout())
        self.custom_range_group.layout().setContentsMargins(10, 10, 10, 10)
        self.custom_range_group.layout().addWidget(custom_range_widget)

        offset_layout.addWidget(offset_notice_label)
        offset_layout.addWidget(offset_settings_group)
        offset_layout.addWidget(self.freq_range_type_group)
        offset_layout.addWidget(self.custom_range_group)
        offset_layout.addStretch()

        minimum_report_text = SettingsStrings.MINIMUM_REPORT_NOTICE()
        minimum_report_notice = QtWidgets.QLabel(minimum_report_text)
        minimum_report_notice.setWordWrap(True)
        minimum_report_notice.setFont(CUSTOM_FONT_SMALL)
        minimum_report_notice.setTextFormat(QtCore.Qt.TextFormat.RichText)
        minimum_report_notice.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(minimum_report_notice)
        minimum_report_notice.setAutoFillBackground(True)

        minimum_report_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_MINIMUM_REPORT())
        self.group_boxes.append(minimum_report_group)
        minimum_report_group.setFont(CUSTOM_FONT_SMALL)
        minimum_report_layout = QtWidgets.QHBoxLayout()

        minimum_report_label = QtWidgets.QLabel(SettingsStrings.LABEL_MINIMUM_REPORT())
        minimum_report_label.setFont(CUSTOM_FONT)
        minimum_report_label.setFixedWidth(400)

        self.minimum_report_combo = QtWidgets.QComboBox()
        self.minimum_report_combo.setEditable(False)
        self.minimum_report_combo.setMinimumWidth(100)

        report_values = [f"{i:+d}dB" for i in range(10, -27, -1)]
        self.minimum_report_combo.addItems(report_values)

        default_index = 10 - DEFAULT_MINIMUM_REPORT
        self.minimum_report_combo.setCurrentIndex(default_index)

        minimum_report_layout.addWidget(minimum_report_label)
        minimum_report_layout.addWidget(self.minimum_report_combo)
        minimum_report_layout.addStretch()

        minimum_report_group.setLayout(minimum_report_layout)

        general_layout.addWidget(general_notice_label)
        general_layout.addWidget(general_settings_group)
        general_layout.addWidget(minimum_report_notice)
        general_layout.addWidget(minimum_report_group)

        general_layout.addStretch()

        """
            Watchdog and Retry page
        """
        watchdog_notice_text = SettingsStrings.WATCHDOG_NOTICE()
        watchdog_notice_label = QtWidgets.QLabel(watchdog_notice_text)
        watchdog_notice_label.setWordWrap(True)
        watchdog_notice_label.setFont(CUSTOM_FONT_SMALL)
        watchdog_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        watchdog_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(watchdog_notice_label)
        watchdog_notice_label.setAutoFillBackground(True)

        watchdog_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_WATCHDOG_RETRY())
        self.group_boxes.append(watchdog_group)
        watchdog_group.setFont(CUSTOM_FONT_SMALL)

        watchdog_widget = QtWidgets.QWidget()
        watchdog_grid_layout = QtWidgets.QGridLayout(watchdog_widget)
        watchdog_grid_layout.setVerticalSpacing(15)

        self.enable_watchdog = QtWidgets.QCheckBox(SettingsStrings.CHECK_ENABLE_WATCHDOG())
        self.enable_watchdog.setFont(CUSTOM_FONT)
        self.enable_watchdog.setChecked(DEFAULT_WATCHDOG)

        watchdog_number_of_attempts_label = QtWidgets.QLabel(SettingsStrings.LABEL_WATCHDOG_NUMBER_OF_ATTEMPTS())
        watchdog_number_of_attempts_label.setFont(CUSTOM_FONT)
        watchdog_number_of_attempts_label.setFixedWidth(200)

        self.watchdog_number_of_attempts = QtWidgets.QLineEdit()
        self.watchdog_number_of_attempts.setFont(CUSTOM_FONT)
        self.watchdog_number_of_attempts.setMinimumWidth(100)
        self.watchdog_number_of_attempts.setText(str(DEFAULT_WATCHDOG_NUMBER_OF_ATTEMPTS))
        self.watchdog_number_of_attempts.setValidator(QtGui.QIntValidator(1, 9999, self))

        watchdog_retry_time_label = QtWidgets.QLabel(SettingsStrings.LABEL_WATCHDOG_RETRY_TIME())
        watchdog_retry_time_label.setFont(CUSTOM_FONT)
        watchdog_retry_time_label.setFixedWidth(200)

        self.watchdog_retry_time = QtWidgets.QLineEdit()
        self.watchdog_retry_time.setFont(CUSTOM_FONT)
        self.watchdog_retry_time.setMinimumWidth(100)
        self.watchdog_retry_time.setText(str(DEFAULT_WATCHDOG_RETRY_TIME))
        self.watchdog_retry_time.setValidator(QtGui.QIntValidator(1, 9999, self))

        watchdog_retry_minutes_label = QtWidgets.QLabel(SettingsStrings.LABEL_MINUTES())
        watchdog_retry_minutes_label.setFont(CUSTOM_FONT)

        watchdog_grid_layout.addWidget(self.enable_watchdog, 0, 0, 1, 3)
        watchdog_grid_layout.addWidget(watchdog_number_of_attempts_label, 1, 0)
        watchdog_grid_layout.addWidget(self.watchdog_number_of_attempts, 1, 1)
        watchdog_grid_layout.addWidget(watchdog_retry_time_label, 2, 0)
        watchdog_grid_layout.addWidget(self.watchdog_retry_time, 2, 1)
        watchdog_grid_layout.addWidget(watchdog_retry_minutes_label, 2, 2)
        watchdog_grid_layout.setColumnStretch(2, 1)

        watchdog_group.setLayout(QtWidgets.QVBoxLayout())
        watchdog_group.layout().setContentsMargins(0, 0, 0, 0)
        watchdog_group.layout().addWidget(watchdog_widget)

        watchdog_layout.addWidget(watchdog_notice_label)
        watchdog_layout.addWidget(watchdog_group)
        watchdog_layout.addStretch()

        """
            Priority Manager Group
        """
        self.priority_manager_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_PRIORITY_MANAGER())
        self.group_boxes.append(self.priority_manager_group)
        self.priority_manager_group.setFont(CUSTOM_FONT_SMALL)
        priority_group_layout = QtWidgets.QVBoxLayout()

        priority_notice_text = SettingsStrings.PRIORITY_NOTICE()
        priority_notice_label = QtWidgets.QLabel(priority_notice_text)
        priority_notice_label.setWordWrap(True)
        priority_notice_label.setFont(CUSTOM_FONT_SMALL)
        priority_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        priority_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(priority_notice_label)

        max_reply_text = SettingsStrings.SEQUENCING_NOTICE()
        max_reply_notice_label = QtWidgets.QLabel(max_reply_text)
        max_reply_notice_label.setWordWrap(True)
        max_reply_notice_label.setFont(CUSTOM_FONT_SMALL)
        max_reply_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        max_reply_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(max_reply_notice_label)
        max_reply_notice_label.setAutoFillBackground(True)

        self.max_reply_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_SEQUENCING())
        self.group_boxes.append(self.max_reply_group)
        self.max_reply_group.setFont(CUSTOM_FONT_SMALL)

        max_reply_layout = QtWidgets.QVBoxLayout()

        max_reply_label = QtWidgets.QLabel(SettingsStrings.LABEL_MAX_ATTEMPTS())
        max_reply_label.setFont(CUSTOM_FONT)
        max_reply_label.setFixedWidth(200)

        self.max_reply_attempts_combo = QtWidgets.QComboBox()
        self.max_reply_attempts_combo.setEditable(False)
        self.max_reply_attempts_combo.setMinimumWidth(100)

        self.max_reply_attempts_combo.addItems([str(i) for i in range(4, 31)])
        self.max_reply_attempts_combo.setCurrentIndex(DEFAULT_REPLY_ATTEMPTS)

        reply_attempts_layout = QtWidgets.QHBoxLayout()
        reply_attempts_layout.addWidget(max_reply_label)
        reply_attempts_layout.addWidget(self.max_reply_attempts_combo)
        times_label = QtWidgets.QLabel(SettingsStrings.LABEL_TIMES())
        times_label.setFont(CUSTOM_FONT)
        reply_attempts_layout.addWidget(times_label)

        max_reply_layout.addLayout(reply_attempts_layout)

        max_waiting_delay_label = QtWidgets.QLabel(SettingsStrings.LABEL_MAX_WAITING_DELAY())
        max_waiting_delay_label.setFont(CUSTOM_FONT)
        max_waiting_delay_label.setFixedWidth(200)

        self.max_waiting_delay_combo = QtWidgets.QComboBox()
        self.max_waiting_delay_combo.setEditable(False)
        self.max_waiting_delay_combo.setMinimumWidth(100)

        waiting_delay_values = list(range(1, 11, 1))
        self.max_waiting_delay_combo.addItems([str(value) for value in waiting_delay_values])

        default_waiting_delay = str(DEFAULT_MAX_WAITING_DELAY)
        if default_waiting_delay in [str(v) for v in waiting_delay_values]:
            self.max_waiting_delay_combo.setCurrentText(default_waiting_delay)
        else:
            self.max_waiting_delay_combo.setCurrentText(str(waiting_delay_values[0]))

        waiting_delay_layout = QtWidgets.QHBoxLayout()
        waiting_delay_layout.addWidget(max_waiting_delay_label)
        waiting_delay_layout.addWidget(self.max_waiting_delay_combo)
        minutes_label = QtWidgets.QLabel(SettingsStrings.LABEL_MINUTES())
        minutes_label.setFont(CUSTOM_FONT)
        waiting_delay_layout.addWidget(minutes_label)

        max_reply_layout.addLayout(waiting_delay_layout)

        max_reply_layout.addStretch()

        self.max_reply_group.setLayout(max_reply_layout)
        self.max_reply_group.layout().setSpacing(5)

        self.priority_table = PriorityTableWidget()
        self.priority_table.setColumnCount(2)
        self.priority_table.setShowGrid(False)
        self.priority_table.setHorizontalHeaderLabels([
            SettingsStrings.HEADER_PRIORITY(),
            SettingsStrings.HEADER_REPLY_TO()
        ])
        self.priority_table.setMaximumHeight(190)
        self.priority_table.setAlternatingRowColors(True)
        self.priority_table.verticalHeader().setVisible(False)
        self.priority_table.horizontalHeader().setStretchLastSection(True)
        self.priority_table.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.priority_table.setColumnWidth(0, 80)
        self.priority_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                font-weight: normal;
                border: none;
                padding: 10 4px 4px 10px;
            }
        """)

        self.priority_table.horizontalHeader().setFont(CUSTOM_FONT_SMALL)
        self.priority_table.setStyleSheet(get_table_setting_qss())
        self.table_widgets.append(self.priority_table)

        self.priority_table.rowsMoved.connect(self.update_priority_labels)

        priority_group_layout.addWidget(priority_notice_label)
        priority_group_layout.addWidget(self.priority_table)
        self.priority_manager_group.setLayout(priority_group_layout)

        # Move priority-related widgets to Priority page
        priority_layout.addWidget(max_reply_notice_label)
        priority_layout.addWidget(self.max_reply_group)
        priority_layout.addWidget(self.priority_manager_group)
        priority_layout.addStretch()

        """
            LoTW Settings
        """
        last_update, entry_count = LoTWManager.get_cache_info()
        if last_update:
            lotw_cache_text = SettingsStrings.LOTW_CACHE_STATUS(entry_count, last_update)
        else:
            lotw_cache_text = SettingsStrings.LOTW_NO_DATA()

        lotw_notice_text = SettingsStrings.LOTW_NOTICE()
        lotw_notice_label = QtWidgets.QLabel(lotw_notice_text)
        lotw_notice_label.setWordWrap(True)
        lotw_notice_label.setFont(CUSTOM_FONT_SMALL)
        lotw_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        lotw_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(lotw_notice_label)
        lotw_notice_label.setAutoFillBackground(True)

        lotw_cache_info = QtWidgets.QLabel(lotw_cache_text)
        lotw_cache_info.setWordWrap(True)
        lotw_cache_info.setFont(CUSTOM_FONT_SMALL)
        lotw_cache_info.setTextFormat(QtCore.Qt.TextFormat.RichText)
        lotw_cache_info.setStyleSheet(get_setting_qss(ODD_COLOR))
        self.notice_labels.append(lotw_cache_info)
        lotw_cache_info.setAutoFillBackground(True)

        lotw_settings_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_LOTW_SETTINGS())
        self.group_boxes.append(lotw_settings_group)
        lotw_settings_group.setFont(CUSTOM_FONT_SMALL)

        lotw_settings_widget = QtWidgets.QWidget()
        lotw_settings_layout = QtWidgets.QGridLayout(lotw_settings_widget)

        self.enable_reply_to_lotw_only = QtWidgets.QCheckBox(SettingsStrings.CHECK_LOTW_ONLY())
        self.enable_reply_to_lotw_only.setFont(CUSTOM_FONT)
        self.enable_reply_to_lotw_only.setChecked(False)

        lotw_settings_layout.addWidget(self.enable_reply_to_lotw_only, 0, 0, 1, 2)

        lotw_settings_group.setLayout(QtWidgets.QVBoxLayout())
        lotw_settings_group.layout().setContentsMargins(0, 0, 0, 0)
        lotw_settings_group.layout().addWidget(lotw_settings_widget)

        # LoTW Upload/Download Settings
        last_upload, total_uploaded, last_callsign_uploaded, last_band_uploaded = LoTWClient.get_cache_info()
        if last_upload:
            lotw_upload_cache_text = SettingsStrings.LOTW_UPLOAD_STATUS(total_uploaded, last_upload, last_callsign_uploaded, last_band_uploaded)
        else:
            lotw_upload_cache_text = SettingsStrings.LOTW_NO_UPLOADS()

        self.lotw_upload_cache_info = QtWidgets.QLabel(lotw_upload_cache_text)
        self.lotw_upload_cache_info.setWordWrap(True)
        self.lotw_upload_cache_info.setFont(CUSTOM_FONT_SMALL)
        self.lotw_upload_cache_info.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.lotw_upload_cache_info.setStyleSheet(get_setting_qss(ODD_COLOR))
        self.notice_labels.append(self.lotw_upload_cache_info)
        self.lotw_upload_cache_info.setAutoFillBackground(True)

        lotw_upload_settings_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_LOTW_UPLOAD_SETTINGS())
        self.group_boxes.append(lotw_upload_settings_group)
        lotw_upload_settings_group.setFont(CUSTOM_FONT_SMALL)

        lotw_upload_settings_widget = QtWidgets.QWidget()
        lotw_upload_settings_layout = QtWidgets.QGridLayout(lotw_upload_settings_widget)

        self.enable_lotw_upload = QtWidgets.QCheckBox(SettingsStrings.CHECK_ENABLE_LOTW_SYNCH())
        self.enable_lotw_upload.setFont(CUSTOM_FONT)
        self.enable_lotw_upload.setChecked(False)

        lotw_username_label = QtWidgets.QLabel(SettingsStrings.LABEL_LOTW_USERNAME())
        lotw_username_label.setFont(CUSTOM_FONT)
        self.lotw_username = QtWidgets.QLineEdit()
        self.lotw_username.setFont(CUSTOM_FONT)
        self.lotw_username.setPlaceholderText(SettingsStrings.PLACEHOLDER_LOTW_USERNAME())

        lotw_password_label = QtWidgets.QLabel(SettingsStrings.LABEL_LOTW_PASSWORD())
        lotw_password_label.setFont(CUSTOM_FONT)
        self.lotw_password = QtWidgets.QLineEdit()
        self.lotw_password.setFont(CUSTOM_FONT)
        self.lotw_password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.lotw_password.setPlaceholderText(SettingsStrings.PLACEHOLDER_LOTW_PASSWORD())

        lotw_location_label = QtWidgets.QLabel(SettingsStrings.LABEL_LOTW_LOCATION())
        lotw_location_label.setFont(CUSTOM_FONT)
        self.lotw_location = QtWidgets.QLineEdit()
        self.lotw_location.setFont(CUSTOM_FONT)
        self.lotw_location.setPlaceholderText(SettingsStrings.PLACEHOLDER_LOTW_LOCATION())

        lotw_signing_password_label = QtWidgets.QLabel(SettingsStrings.LABEL_LOTW_SIGNING_PASSWORD())
        lotw_signing_password_label.setFont(CUSTOM_FONT)
        self.lotw_signing_password = QtWidgets.QLineEdit()
        self.lotw_signing_password.setFont(CUSTOM_FONT)
        self.lotw_signing_password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.lotw_signing_password.setPlaceholderText(SettingsStrings.PLACEHOLDER_LOTW_SIGNING_PASSWORD())

        lotw_qso_since_date_label = QtWidgets.QLabel(SettingsStrings.LABEL_LOTW_QSO_SINCE_DATE())
        lotw_qso_since_date_label.setFont(CUSTOM_FONT)
        self.lotw_qso_since_date = QtWidgets.QDateTimeEdit()
        self.lotw_qso_since_date.setFont(CUSTOM_FONT)
        self.lotw_qso_since_date.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.lotw_qso_since_date.setCalendarPopup(False)  # No calendar popup
        # Set default to 1 year ago
        from datetime import datetime, timedelta
        default_date = datetime.now() - timedelta(days=365)
        self.lotw_qso_since_date.setDateTime(default_date)

        lotw_download_interval_label = QtWidgets.QLabel(SettingsStrings.LABEL_LOTW_DOWNLOAD_INTERVAL())
        lotw_download_interval_label.setFont(CUSTOM_FONT)
        self.lotw_download_interval = QtWidgets.QSpinBox()
        self.lotw_download_interval.setFont(CUSTOM_FONT)
        self.lotw_download_interval.setMinimum(5)
        self.lotw_download_interval.setMaximum(1440)
        self.lotw_download_interval.setValue(10)

        tqsl_path_label = QtWidgets.QLabel(SettingsStrings.LABEL_TQSL_PATH())
        tqsl_path_label.setFont(CUSTOM_FONT)
        self.tqsl_path = QtWidgets.QLineEdit()
        self.tqsl_path.setFont(CUSTOM_FONT)

        self.browse_tqsl_button = QtWidgets.QPushButton(SettingsStrings.BUTTON_BROWSE_TQSL())
        self.browse_tqsl_button.setFont(CUSTOM_FONT)
        self.browse_tqsl_button.clicked.connect(self.browse_tqsl_path)

        tqsl_path_layout = QtWidgets.QHBoxLayout()
        tqsl_path_layout.addWidget(self.tqsl_path)
        tqsl_path_layout.addWidget(self.browse_tqsl_button)

        tqsl_dir_label = QtWidgets.QLabel(SettingsStrings.LABEL_TQSL_DIR())
        tqsl_dir_label.setFont(CUSTOM_FONT)
        self.tqsl_dir = QtWidgets.QLineEdit()
        self.tqsl_dir.setFont(CUSTOM_FONT)

        self.browse_tqsl_dir_button = QtWidgets.QPushButton(SettingsStrings.BUTTON_BROWSE_TQSL_DIR())
        self.browse_tqsl_dir_button.setFont(CUSTOM_FONT)
        self.browse_tqsl_dir_button.clicked.connect(self.browse_tqsl_dir)

        tqsl_dir_layout = QtWidgets.QHBoxLayout()
        tqsl_dir_layout.addWidget(self.tqsl_dir)
        tqsl_dir_layout.addWidget(self.browse_tqsl_dir_button)

        self.test_lotw_upload_button = QtWidgets.QPushButton(SettingsStrings.BUTTON_TEST_LOTW_UPLOAD())
        self.test_lotw_upload_button.setFont(CUSTOM_FONT)
        self.test_lotw_upload_button.clicked.connect(self.test_lotw_upload_last_qso)

        self.test_lotw_download_button = QtWidgets.QPushButton(SettingsStrings.BUTTON_TEST_LOTW_DOWNLOAD())
        self.test_lotw_download_button.setFont(CUSTOM_FONT)
        self.test_lotw_download_button.clicked.connect(self.test_lotw_download_qsls)

        test_buttons_layout = QtWidgets.QHBoxLayout()
        test_buttons_layout.addWidget(self.test_lotw_upload_button)
        test_buttons_layout.addWidget(self.test_lotw_download_button)

        lotw_upload_settings_layout.addWidget(self.enable_lotw_upload, 0, 0, 1, 2)
        lotw_upload_settings_layout.addWidget(lotw_username_label, 1, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        lotw_upload_settings_layout.addWidget(self.lotw_username, 1, 1)
        lotw_upload_settings_layout.addWidget(lotw_password_label, 2, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        lotw_upload_settings_layout.addWidget(self.lotw_password, 2, 1)
        lotw_upload_settings_layout.addWidget(lotw_location_label, 3, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        lotw_upload_settings_layout.addWidget(self.lotw_location, 3, 1)
        lotw_upload_settings_layout.addWidget(lotw_signing_password_label, 4, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        lotw_upload_settings_layout.addWidget(self.lotw_signing_password, 4, 1)
        lotw_upload_settings_layout.addWidget(lotw_qso_since_date_label, 5, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        lotw_upload_settings_layout.addWidget(self.lotw_qso_since_date, 5, 1)
        lotw_upload_settings_layout.addWidget(lotw_download_interval_label, 6, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        lotw_upload_settings_layout.addWidget(self.lotw_download_interval, 6, 1)
        lotw_upload_settings_layout.addWidget(tqsl_path_label, 7, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        lotw_upload_settings_layout.addLayout(tqsl_path_layout, 7, 1)
        lotw_upload_settings_layout.addWidget(tqsl_dir_label, 8, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        lotw_upload_settings_layout.addLayout(tqsl_dir_layout, 8, 1)
        lotw_upload_settings_layout.addLayout(test_buttons_layout, 9, 0, 1, 2)

        # Reduce vertical spacing between rows
        lotw_upload_settings_layout.setVerticalSpacing(10)

        lotw_upload_settings_group.setLayout(QtWidgets.QVBoxLayout())
        lotw_upload_settings_group.layout().setContentsMargins(0, 0, 0, 0)
        lotw_upload_settings_group.layout().addWidget(lotw_upload_settings_widget)

        lotw_layout.addWidget(lotw_notice_label)
        lotw_layout.addWidget(lotw_cache_info)
        lotw_layout.addWidget(lotw_settings_group)
        lotw_layout.addWidget(self.lotw_upload_cache_info)
        lotw_layout.addWidget(lotw_upload_settings_group)
        lotw_layout.addStretch()

        """
            Sound Settings
        """
        sound_notice_text = SettingsStrings.SOUND_NOTICE()

        sound_notice_label = QtWidgets.QLabel(sound_notice_text)
        sound_notice_label.setWordWrap(True)
        sound_notice_label.setFont(CUSTOM_FONT_SMALL)
        sound_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        sound_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(sound_notice_label)
        sound_notice_label.setAutoFillBackground(True)

        sound_settings_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_SOUND_SETTINGS())
        self.group_boxes.append(sound_settings_group)
        sound_settings_group.setFont(CUSTOM_FONT_SMALL)
        sound_settings_layout = QtWidgets.QGridLayout()

        play_sound_notice_label = QtWidgets.QLabel(SettingsStrings.LABEL_PLAY_SOUND_WHEN())
        play_sound_notice_label.setFont(CUSTOM_FONT)
        play_sound_notice_label.setFont(CUSTOM_FONT_SMALL)

        self.enable_sound_wanted_callsigns = QtWidgets.QCheckBox(SettingsStrings.CHECK_SOUND_WANTED())
        self.enable_sound_wanted_callsigns.setFont(CUSTOM_FONT)
        self.enable_sound_wanted_callsigns.setChecked(True)

        self.enable_sound_directed_my_callsign = QtWidgets.QCheckBox(SettingsStrings.CHECK_SOUND_DIRECTED())
        self.enable_sound_directed_my_callsign.setFont(CUSTOM_FONT)
        self.enable_sound_directed_my_callsign.setChecked(True)

        self.enable_sound_monitored_callsigns = QtWidgets.QCheckBox(SettingsStrings.CHECK_SOUND_MONITORED())
        self.enable_sound_monitored_callsigns.setFont(CUSTOM_FONT)
        self.enable_sound_monitored_callsigns.setChecked(True)

        self.delay_between_sound_for_monitored = QtWidgets.QLineEdit()
        self.delay_between_sound_for_monitored.setFixedWidth(50)
        self.delay_between_sound_for_monitored.setFont(CUSTOM_FONT)

        delay_layout = QtWidgets.QHBoxLayout()
        delay_layout.addWidget(self.delay_between_sound_for_monitored)
        seconds_label = QtWidgets.QLabel(SettingsStrings.LABEL_SECONDS())
        seconds_label.setFont(CUSTOM_FONT)
        delay_layout.addWidget(seconds_label)
        delay_layout.addStretch()

        sound_settings_layout.addWidget(play_sound_notice_label, 0, 0, 1, 2)
        sound_settings_layout.addWidget(self.enable_sound_wanted_callsigns, 1, 0, 1, 2)
        sound_settings_layout.addWidget(self.enable_sound_directed_my_callsign, 2, 0, 1, 2)
        sound_settings_layout.addWidget(self.enable_sound_monitored_callsigns, 3, 0, 1, 2)
        delay_between_label = QtWidgets.QLabel(SettingsStrings.LABEL_DELAY_BETWEEN())
        delay_between_label.setFont(CUSTOM_FONT)
        sound_settings_layout.addWidget(delay_between_label, 4, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        sound_settings_layout.addLayout(delay_layout, 4, 1, 1, 2)
        sound_settings_layout.setVerticalSpacing(15)
        sound_settings_layout.setRowMinimumHeight(4, 30)  # Ensure minimum height for the delay row

        sound_settings_group.setLayout(sound_settings_layout)
        sound_settings_group.setMinimumHeight(180)  # Set minimum height for the group box

        sound_layout.addWidget(sound_notice_label)
        sound_layout.addWidget(sound_settings_group)
        sound_layout.addStretch()

        """
            Log Analysis Settings
        """
        log_analysis_notice_text = SettingsStrings.LOG_ANALYSIS_NOTICE()

        log_analysis_notice_label = QtWidgets.QLabel(log_analysis_notice_text)
        log_analysis_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(log_analysis_notice_label)
        log_analysis_notice_label.setWordWrap(True)
        log_analysis_notice_label.setFont(CUSTOM_FONT_SMALL)
        log_analysis_notice_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        file_selection_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_FILE_SELECTION())
        self.group_boxes.append(file_selection_group)
        file_selection_group.setFont(CUSTOM_FONT_SMALL)
        file_selection_group.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        file_selection_widget = QtWidgets.QWidget()
        file_selection_layout = QtWidgets.QVBoxLayout(file_selection_widget)

        # Buttons layout
        buttons_widget = QtWidgets.QWidget()
        buttons_layout = QtWidgets.QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)

        # Add ADIF File button
        self.add_file_button = QtWidgets.QPushButton(SettingsStrings.BUTTON_SELECT_ADIF())
        self.add_file_button.setFont(CUSTOM_FONT)
        self.add_file_button.clicked.connect(self.add_adif_file)

        buttons_layout.addWidget(self.add_file_button)
        buttons_layout.addStretch()

        # Table for file list
        self.adif_files_table = QtWidgets.QTableWidget()
        self.adif_files_table.setColumnCount(2)

        # Set column widths - narrow first column for counter, stretch second for file paths
        self.adif_files_table.setColumnWidth(0, 40)  # Fixed width for counter column
        self.adif_files_table.horizontalHeader().setStretchLastSection(True)  # Stretch second column
        self.adif_files_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)

        self.adif_files_table.setShowGrid(False)
        self.adif_files_table.horizontalHeader().setVisible(False)
        self.adif_files_table.verticalHeader().setVisible(False)
        self.adif_files_table.setAlternatingRowColors(True)
        self.adif_files_table.setFont(CUSTOM_FONT_SMALL)

        self.adif_files_table.horizontalHeader().setHighlightSections(False)
        self.adif_files_table.verticalHeader().setHighlightSections(False)
        self.adif_files_table.setFrameStyle(QtWidgets.QFrame.Shape.NoFrame)

        self.adif_files_table.setHorizontalHeaderLabels(["", SettingsStrings.HEADER_ADIF_FILES()])
        self.adif_files_table.horizontalHeader().setFont(CUSTOM_FONT_SMALL)
        self.adif_files_table.horizontalHeader().setVisible(True)
        self.adif_files_table.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

        self.adif_files_table.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed
        )

        self.adif_files_table.selectionModel().selectionChanged.connect(self.on_table_selection_changed)

        self.adif_files_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                font-weight: normal;
                border: none;
                padding: 10 4px 4px 4px;
            }
        """)

        self.adif_files_table.setStyleSheet(get_table_setting_qss())
        self.table_widgets.append(self.adif_files_table)

        # List to keep track of selected files
        self.selected_adif_files = []

        file_selection_layout.addWidget(buttons_widget)
        file_selection_layout.addWidget(self.adif_files_table)

        # Clear button layout (right-aligned, after table)
        clear_button_widget = QtWidgets.QWidget()
        clear_button_layout = QtWidgets.QHBoxLayout(clear_button_widget)
        clear_button_layout.setContentsMargins(0, 0, 0, 0)

        # Summary button
        self.summary_file_button = QtWidgets.QPushButton(CommonStrings.SUMMARY())
        self.summary_file_button.setFont(CUSTOM_FONT)
        self.summary_file_button.setFixedWidth(80)
        self.summary_file_button.clicked.connect(self.show_selected_file_summary)
        self.summary_file_button.setEnabled(False)  # Initially disabled

        # Clear button
        self.clear_file_button = QtWidgets.QPushButton(CommonStrings.CLEAR())
        self.clear_file_button.setFont(CUSTOM_FONT)
        self.clear_file_button.setFixedWidth(60)
        self.clear_file_button.clicked.connect(self.clear_selected_file)
        self.clear_file_button.setEnabled(False)  # Initially disabled

        clear_button_layout.addStretch()
        clear_button_layout.addWidget(self.summary_file_button)
        clear_button_layout.addWidget(self.clear_file_button)

        file_selection_layout.addWidget(clear_button_widget)

        file_selection_group.setLayout(QtWidgets.QVBoxLayout())
        file_selection_group.layout().setContentsMargins(0, 0, 0, 0)
        file_selection_group.layout().addWidget(file_selection_widget)

        """
            Worked Before Settings
        """
        worked_b4_notice_text = SettingsStrings.WORKED_B4_NOTICE()

        worked_b4_notice_label = QtWidgets.QLabel(worked_b4_notice_text)
        worked_b4_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(worked_b4_notice_label)
        worked_b4_notice_label.setWordWrap(True)
        worked_b4_notice_label.setFont(CUSTOM_FONT_SMALL)
        worked_b4_notice_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        self.adif_wkb4_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_WKB4_SETTINGS())
        self.group_boxes.append(self.adif_wkb4_group)
        self.adif_wkb4_group.setFont(CUSTOM_FONT_SMALL)
        adif_wkb4_layout = QtWidgets.QVBoxLayout()
        adif_wkb4_layout.setSpacing(10)

        self.radio_reply_always = QtWidgets.QRadioButton(SettingsStrings.RADIO_REPLY_ALWAYS())
        self.radio_reply_current_year = QtWidgets.QRadioButton(SettingsStrings.RADIO_REPLY_CURRENT_YEAR(datetime.now().year))
        self.radio_reply_never = QtWidgets.QRadioButton(SettingsStrings.RADIO_REPLY_NEVER())
        self.radio_reply_never.setChecked(True)

        self.radio_reply_always.setFont(CUSTOM_FONT)
        self.radio_reply_current_year.setFont(CUSTOM_FONT)
        self.radio_reply_never.setFont(CUSTOM_FONT)

        adif_wkb4_layout.addWidget(self.radio_reply_always)
        adif_wkb4_layout.addWidget(self.radio_reply_current_year)
        adif_wkb4_layout.addWidget(self.radio_reply_never)
        adif_wkb4_layout.setSpacing(15)

        self.adif_wkb4_group.setLayout(adif_wkb4_layout)
        self.adif_wkb4_group.setVisible(False)

        """
            Marathon Settings
        """
        marathon_notice_text = SettingsStrings.MARATHON_NOTICE()
        marathon_notice_label = QtWidgets.QLabel(marathon_notice_text)
        marathon_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(marathon_notice_label)
        marathon_notice_label.setWordWrap(True)
        marathon_notice_label.setFont(CUSTOM_FONT_SMALL)
        marathon_notice_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        self.marathon_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_MARATHON_SETTINGS())
        self.group_boxes.append(self.marathon_group)
        self.marathon_group.setFont(CUSTOM_FONT_SMALL)
        marathon_select_layout = QtWidgets.QGridLayout()

        self.band_buttons = {}
        max_cols = 3
        row = 0
        col = 0

        for amateur_band in list(AMATEUR_BANDS.keys()):
            btn = CustomButton(amateur_band)
            btn.setCheckable(True)
            btn.toggled.connect(lambda checked, btn=btn, name=amateur_band: self.on_band_toggled(btn, name, checked))
            self.band_buttons[amateur_band] = btn
            marathon_select_layout.addWidget(btn, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        btn = CustomButton(MARATHON_UNLIMITED)
        btn.setCheckable(True)
        btn.toggled.connect(lambda checked, btn=btn, name=MARATHON_UNLIMITED: self.on_band_toggled(btn, MARATHON_UNLIMITED, checked))
        self.band_buttons[MARATHON_UNLIMITED] = btn
        marathon_select_layout.addWidget(btn, row, col)

        self.marathon_group.setLayout(marathon_select_layout)

        """
            Marathon Settings
        """
        marathon_layout.addWidget(marathon_notice_label)
        marathon_layout.addWidget(self.marathon_group)
        marathon_layout.addStretch()

        """
            DXCC Program Settings
        """
        dxcc_notice_text = SettingsStrings.DXCC_NOTICE()
        dxcc_notice_label = QtWidgets.QLabel(dxcc_notice_text)
        dxcc_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(dxcc_notice_label)
        dxcc_notice_label.setWordWrap(True)
        dxcc_notice_label.setFont(CUSTOM_FONT_SMALL)
        dxcc_notice_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        self.dxcc_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_DXCC_SETTINGS())
        self.group_boxes.append(self.dxcc_group)
        self.dxcc_group.setFont(CUSTOM_FONT_SMALL)
        dxcc_select_layout = QtWidgets.QGridLayout()

        self.dxcc_band_buttons = {}
        max_cols = 3
        row = 0
        col = 0

        for amateur_band in list(AMATEUR_BANDS.keys()):
            btn = CustomButton(amateur_band)
            btn.setCheckable(True)
            btn.toggled.connect(lambda checked, btn=btn, name=amateur_band: self.on_dxcc_band_toggled(btn, name, checked))
            self.dxcc_band_buttons[amateur_band] = btn
            dxcc_select_layout.addWidget(btn, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        btn = CustomButton(MARATHON_UNLIMITED)
        btn.setCheckable(True)
        btn.toggled.connect(lambda checked, btn=btn, name=MARATHON_UNLIMITED: self.on_dxcc_band_toggled(btn, MARATHON_UNLIMITED, checked))
        self.dxcc_band_buttons[MARATHON_UNLIMITED] = btn
        dxcc_select_layout.addWidget(btn, row, col)

        self.dxcc_group.setLayout(dxcc_select_layout)

        # Keep replying to an entity until it is confirmed (QSL) checkbox
        self.enable_dxcc_reply_unconfirmed = QtWidgets.QCheckBox(SettingsStrings.CHECK_ENABLE_DXCC_UNCONFIRMED())
        self.enable_dxcc_reply_unconfirmed.setFont(CUSTOM_FONT_SMALL)
        self.enable_dxcc_reply_unconfirmed.setChecked(False)

        dxcc_layout.addWidget(dxcc_notice_label)
        dxcc_layout.addWidget(self.dxcc_group)
        dxcc_layout.addWidget(self.enable_dxcc_reply_unconfirmed)
        dxcc_layout.addStretch()

        """
            Log Analysis Settings
        """
        log_analysis_layout.addWidget(log_analysis_notice_label)
        log_analysis_layout.addWidget(file_selection_group)
        log_analysis_layout.addStretch()

        """
            Worked Before Settings
        """
        worked_b4_layout.addWidget(worked_b4_notice_label)
        worked_b4_layout.addWidget(self.adif_wkb4_group)
        worked_b4_layout.addStretch()

        """
            Club Log Settings
        """
        club_log_notice_text = SettingsStrings.CLUB_LOG_NOTICE()

        club_log_notice_label = QtWidgets.QLabel(club_log_notice_text)
        club_log_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(club_log_notice_label)
        club_log_notice_label.setWordWrap(True)
        club_log_notice_label.setFont(CUSTOM_FONT_SMALL)
        club_log_notice_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        last_sync, total_qsos, last_callsign, last_band = ClubLogUploader.get_cache_info()
        if last_sync:
            club_log_cache_text = SettingsStrings.CLUB_LOG_STATUS(total_qsos, last_sync, last_callsign, last_band)
        else:
            club_log_cache_text = SettingsStrings.CLUB_LOG_NO_UPLOADS()

        self.club_log_cache_info = QtWidgets.QLabel(club_log_cache_text)
        self.club_log_cache_info.setWordWrap(True)
        self.club_log_cache_info.setFont(CUSTOM_FONT_SMALL)
        self.club_log_cache_info.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.club_log_cache_info.setStyleSheet(get_setting_qss(ODD_COLOR))
        self.notice_labels.append(self.club_log_cache_info)
        self.club_log_cache_info.setAutoFillBackground(True)

        club_log_settings_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_CLUB_LOG_SETTINGS())
        self.group_boxes.append(club_log_settings_group)
        club_log_settings_group.setFont(CUSTOM_FONT_SMALL)

        club_log_settings_widget = QtWidgets.QWidget()
        club_log_settings_layout = QtWidgets.QGridLayout(club_log_settings_widget)

        self.enable_club_log_synch = QtWidgets.QCheckBox(SettingsStrings.CHECK_ENABLE_CLUB_LOG())
        self.enable_club_log_synch.setFont(CUSTOM_FONT)
        self.enable_club_log_synch.setChecked(False)

        club_log_email_label = QtWidgets.QLabel(SettingsStrings.LABEL_EMAIL())
        club_log_email_label.setFont(CUSTOM_FONT)
        self.club_log_email = QtWidgets.QLineEdit()
        self.club_log_email.setFont(CUSTOM_FONT)
        self.club_log_email.setPlaceholderText(SettingsStrings.PLACEHOLDER_EMAIL())

        club_log_password_label = QtWidgets.QLabel(SettingsStrings.LABEL_PASSWORD())
        club_log_password_label.setFont(CUSTOM_FONT)
        self.club_log_password = QtWidgets.QLineEdit()
        self.club_log_password.setFont(CUSTOM_FONT)
        self.club_log_password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.club_log_password.setPlaceholderText(SettingsStrings.PLACEHOLDER_PASSWORD())

        club_log_callsign_label = QtWidgets.QLabel(SettingsStrings.LABEL_CALLSIGN())
        club_log_callsign_label.setFont(CUSTOM_FONT)
        self.club_log_callsign = QtWidgets.QLineEdit()
        self.club_log_callsign.setFont(CUSTOM_FONT)
        self.club_log_callsign.setPlaceholderText(SettingsStrings.PLACEHOLDER_CALLSIGN())

        club_log_api_key_label = QtWidgets.QLabel(SettingsStrings.LABEL_API_KEY())
        club_log_api_key_label.setFont(CUSTOM_FONT)
        self.club_log_api_key = QtWidgets.QLineEdit()
        self.club_log_api_key.setFont(CUSTOM_FONT)
        self.club_log_api_key.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.club_log_api_key.setPlaceholderText(SettingsStrings.PLACEHOLDER_CLUB_LOG_API_KEY())

        self.test_club_log_upload_button = QtWidgets.QPushButton(SettingsStrings.BUTTON_TEST_CLUB_LOG_UPLOAD())
        self.test_club_log_upload_button.setFont(CUSTOM_FONT)
        self.test_club_log_upload_button.clicked.connect(self.test_club_log_upload_last_qso)

        club_log_test_buttons_layout = QtWidgets.QHBoxLayout()
        club_log_test_buttons_layout.addWidget(self.test_club_log_upload_button)

        club_log_settings_layout.addWidget(self.enable_club_log_synch, 0, 0, 1, 2)
        club_log_settings_layout.addWidget(club_log_email_label, 1, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        club_log_settings_layout.addWidget(self.club_log_email, 1, 1)
        club_log_settings_layout.addWidget(club_log_password_label, 2, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        club_log_settings_layout.addWidget(self.club_log_password, 2, 1)
        club_log_settings_layout.addWidget(club_log_callsign_label, 3, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        club_log_settings_layout.addWidget(self.club_log_callsign, 3, 1)
        club_log_settings_layout.addWidget(club_log_api_key_label, 4, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        club_log_settings_layout.addWidget(self.club_log_api_key, 4, 1)
        club_log_settings_layout.addLayout(club_log_test_buttons_layout, 5, 0, 1, 2)

        club_log_settings_group.setLayout(QtWidgets.QVBoxLayout())
        club_log_settings_group.layout().setContentsMargins(0, 0, 0, 0)
        club_log_settings_group.layout().addWidget(club_log_settings_widget)

        club_log_layout.addWidget(club_log_notice_label)
        club_log_layout.addWidget(self.club_log_cache_info)
        club_log_layout.addWidget(club_log_settings_group)
        club_log_layout.addStretch()

        """
            Select bands for Grid Tracker
        """
        grid_tracker_notice_text = SettingsStrings.GRID_TRACKER_NOTICE()
        grid_tracker_notice_label = QtWidgets.QLabel(grid_tracker_notice_text)
        grid_tracker_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(grid_tracker_notice_label)
        grid_tracker_notice_label.setWordWrap(True)
        grid_tracker_notice_label.setFont(CUSTOM_FONT_SMALL)
        grid_tracker_notice_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        # Separator line
        grid_tracker_separator = QtWidgets.QFrame()
        grid_tracker_separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        grid_tracker_separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)

        # Grid reply new grid on any band checkbox
        self.enable_grid_reply_new_grid = QtWidgets.QCheckBox(SettingsStrings.CHECK_ENABLE_GRID_TRACKER_NEW_GRID())
        self.enable_grid_reply_new_grid.setFont(CUSTOM_FONT_SMALL)
        self.enable_grid_reply_new_grid.setChecked(False)

        grid_tracker_per_band_notice_text = SettingsStrings.GRID_TRACKER_PER_BAND_NOTICE()

        grid_tracker_per_band_notice_label = QtWidgets.QLabel(grid_tracker_per_band_notice_text)
        grid_tracker_per_band_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(grid_tracker_per_band_notice_label)
        grid_tracker_per_band_notice_label.setWordWrap(True)
        grid_tracker_per_band_notice_label.setFont(CUSTOM_FONT_SMALL)
        grid_tracker_per_band_notice_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        self.grid_tracker_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_GRID_TRACKER_SETTINGS())
        self.group_boxes.append(self.grid_tracker_group)
        self.grid_tracker_group.setFont(CUSTOM_FONT_SMALL)
        grid_tracker_select_layout = QtWidgets.QGridLayout()

        self.grid_tracker_band_buttons = {}
        max_cols = 3
        row = 0
        col = 0

        for amateur_band in list(AMATEUR_BANDS.keys()):
            btn = CustomButton(amateur_band)
            btn.setCheckable(True)
            btn.toggled.connect(lambda checked, btn=btn, name=amateur_band: self.on_grid_tracker_band_toggled(btn, name, checked))
            self.grid_tracker_band_buttons[amateur_band] = btn
            grid_tracker_select_layout.addWidget(btn, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        self.grid_tracker_group.setLayout(grid_tracker_select_layout)

        # Grid reply unconfirmed checkbox
        self.enable_grid_reply_unconfirmed = QtWidgets.QCheckBox(SettingsStrings.CHECK_ENABLE_GRID_TRACKER())
        self.enable_grid_reply_unconfirmed.setFont(CUSTOM_FONT_SMALL)
        self.enable_grid_reply_unconfirmed.setChecked(False)

        grid_tracker_layout.addWidget(grid_tracker_notice_label)
        grid_tracker_layout.addWidget(self.enable_grid_reply_new_grid)
        grid_tracker_layout.addWidget(grid_tracker_separator)
        grid_tracker_layout.addWidget(grid_tracker_per_band_notice_label)
        grid_tracker_layout.addWidget(self.grid_tracker_group)
        grid_tracker_layout.addWidget(self.enable_grid_reply_unconfirmed)
        grid_tracker_layout.addStretch()

        """
            Backup Settings
        """
        adif_backup_selection_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_BACKUP_FILE())
        self.group_boxes.append(adif_backup_selection_group)
        adif_backup_selection_group.setFont(CUSTOM_FONT_SMALL)
        adif_backup_selection_group.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        working_log_notice_text = SettingsStrings.BACKUP_NOTICE()

        working_log_notice_label = QtWidgets.QLabel(working_log_notice_text)
        working_log_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(working_log_notice_label)
        working_log_notice_label.setWordWrap(True)
        working_log_notice_label.setFont(CUSTOM_FONT_SMALL)
        working_log_notice_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        adif_backup_widget = QtWidgets.QWidget()
        adif_backup_layout = QtWidgets.QVBoxLayout(adif_backup_widget)

        # Button (above path field, left-aligned)
        self.select_backup_file_button = QtWidgets.QPushButton("Select File")
        self.select_backup_file_button.setFont(CUSTOM_FONT)
        self.select_backup_file_button.setFixedWidth(120)
        self.select_backup_file_button.clicked.connect(self.open_backup_file_dialog)

        # Path field
        self.show_backup_file_path = QtWidgets.QLineEdit()
        self.show_backup_file_path.setText(ADIF_WORKED_CALLSIGNS_FILE)
        self.show_backup_file_path.setReadOnly(False)
        self.show_backup_file_path.textChanged.connect(self.update_backup_file_status)

        # Status info widget
        self.backup_file_status_info = QtWidgets.QLabel()
        self.backup_file_status_info.setWordWrap(True)
        self.backup_file_status_info.setFont(CUSTOM_FONT_SMALL)
        self.backup_file_status_info.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.backup_file_status_info.setStyleSheet(get_setting_qss(ODD_COLOR))
        self.notice_labels.append(self.backup_file_status_info)
        self.backup_file_status_info.setAutoFillBackground(True)

        adif_backup_layout.addWidget(self.select_backup_file_button)
        adif_backup_layout.addWidget(self.show_backup_file_path)
        adif_backup_layout.addWidget(self.backup_file_status_info)

        """
        adif_backup_layout.addWidget(self.open_backup_file_button, 0, 2)
        """
        adif_backup_selection_group.setLayout(QtWidgets.QVBoxLayout())
        adif_backup_selection_group.layout().setContentsMargins(0, 0, 0, 0)
        adif_backup_selection_group.layout().addWidget(adif_backup_widget)

        # Initialize backup file status display
        self.update_backup_file_status()

        backup_layout.addWidget(working_log_notice_label)
        backup_layout.addWidget(self.backup_file_status_info)
        backup_layout.addWidget(adif_backup_selection_group)
        backup_layout.addStretch()

        """
            Automate Tasks Settings
        """
        automate_tasks_notice_text = SettingsStrings.AUTOMATE_TASKS_NOTICE()
        automate_tasks_notice_label = QtWidgets.QLabel(automate_tasks_notice_text)
        automate_tasks_notice_label.setWordWrap(True)
        automate_tasks_notice_label.setFont(CUSTOM_FONT_SMALL)
        automate_tasks_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        automate_tasks_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(automate_tasks_notice_label)
        automate_tasks_notice_label.setAutoFillBackground(True)

        automate_tasks_settings_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_AUTOMATE_TASKS_SETTINGS())
        self.group_boxes.append(automate_tasks_settings_group)
        automate_tasks_settings_group.setFont(CUSTOM_FONT_SMALL)
        automate_tasks_settings_layout = QtWidgets.QVBoxLayout()
        automate_tasks_settings_layout.setSpacing(15)

        self.enable_jtdx_click_log_qso = QtWidgets.QCheckBox(SettingsStrings.CLOSE_JTDX_LOG_QSO_PROMPT())
        self.enable_jtdx_click_log_qso.setFont(CUSTOM_FONT)
        self.enable_jtdx_click_log_qso.setChecked(DEFAULT_JTDX_CLICK_PROMPT_LOG_QSO)

        # Create horizontal layout for checkbox and test button
        jtdx_log_qso_layout = QtWidgets.QHBoxLayout()
        jtdx_log_qso_layout.addWidget(self.enable_jtdx_click_log_qso)
        jtdx_log_qso_layout.addStretch()

        # Add Test button aligned to the right
        self.test_jtdx_log_qso_button = CustomButton(SettingsStrings.BUTTON_AUTOMATE_TASKS_TEST())
        self.test_jtdx_log_qso_button.setMaximumWidth(100)
        self.test_jtdx_log_qso_button.clicked.connect(self.test_jtdx_log_qso_window)
        jtdx_log_qso_layout.addWidget(self.test_jtdx_log_qso_button)

        automate_tasks_settings_layout.addLayout(jtdx_log_qso_layout)

        # Add delay slider for JTDX click delay
        jtdx_delay_layout = QtWidgets.QHBoxLayout()
        jtdx_delay_label = QtWidgets.QLabel(SettingsStrings.JTDX_CLICK_DELAY_LABEL())
        jtdx_delay_label.setFont(CUSTOM_FONT)
        self.jtdx_click_delay_slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.jtdx_click_delay_slider.setMinimum(0)
        self.jtdx_click_delay_slider.setMaximum(30)
        self.jtdx_click_delay_slider.setValue(DEFAULT_JTDX_CLICK_DELAY)
        self.jtdx_click_delay_value_label = QtWidgets.QLabel(f"{DEFAULT_JTDX_CLICK_DELAY} s")
        self.jtdx_click_delay_value_label.setFont(CUSTOM_FONT)
        self.jtdx_click_delay_value_label.setMinimumWidth(40)
        self.jtdx_click_delay_slider.valueChanged.connect(
            lambda v: self.jtdx_click_delay_value_label.setText(f"{v} s")
        )
        jtdx_delay_layout.addWidget(jtdx_delay_label)
        jtdx_delay_layout.addWidget(self.jtdx_click_delay_slider)
        jtdx_delay_layout.addWidget(self.jtdx_click_delay_value_label)
        jtdx_delay_layout.addStretch()

        automate_tasks_settings_layout.addLayout(jtdx_delay_layout)

        automate_tasks_settings_group.setLayout(automate_tasks_settings_layout)

        # Test button outside the group
        self.test_windows_monitoring_button = CustomButton(SettingsStrings.BUTTON_TEST_WINDOWS_MONITORING())
        self.test_windows_monitoring_button.clicked.connect(self.open_windows_monitoring_test)

        # Add automate tasks settings to automate tasks page
        automate_tasks_layout.addWidget(automate_tasks_notice_label)
        automate_tasks_layout.addWidget(automate_tasks_settings_group)
        automate_tasks_layout.addWidget(self.test_windows_monitoring_button)
        automate_tasks_layout.addStretch()

        """
            Antenna Rotator (PstRotatorAz) Settings
        """
        pstrotator_notice_label = QtWidgets.QLabel(SettingsStrings.PSTROTATOR_NOTICE())
        pstrotator_notice_label.setWordWrap(True)
        pstrotator_notice_label.setFont(CUSTOM_FONT_SMALL)
        pstrotator_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        pstrotator_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(pstrotator_notice_label)
        pstrotator_notice_label.setAutoFillBackground(True)

        # Connection group
        pstrotator_connection_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_PSTROTATOR_CONNECTION())
        self.group_boxes.append(pstrotator_connection_group)
        pstrotator_connection_group.setFont(CUSTOM_FONT_SMALL)
        pstrotator_connection_layout = QtWidgets.QGridLayout()

        pstrotator_host_label = QtWidgets.QLabel(SettingsStrings.LABEL_UDP_SERVER())
        pstrotator_host_label.setFont(CUSTOM_FONT)
        self.pstrotator_host = QtWidgets.QLineEdit()
        self.pstrotator_host.setFont(CUSTOM_FONT)

        pstrotator_port_label = QtWidgets.QLabel(SettingsStrings.LABEL_UDP_PORT())
        pstrotator_port_label.setFont(CUSTOM_FONT)
        self.pstrotator_port = QtWidgets.QLineEdit()
        self.pstrotator_port.setFont(CUSTOM_FONT)
        self.pstrotator_port.setValidator(QtGui.QIntValidator(1, 65535, self))

        pstrotator_current_azimuth_label = QtWidgets.QLabel(SettingsStrings.LABEL_PSTROTATOR_CURRENT_AZIMUTH())
        pstrotator_current_azimuth_label.setFont(CUSTOM_FONT)
        self.pstrotator_current_azimuth_value = QtWidgets.QLabel(SettingsStrings.PSTROTATOR_AZIMUTH_UNKNOWN())
        self.pstrotator_current_azimuth_value.setFont(CUSTOM_FONT)

        pstrotator_connection_layout.addWidget(pstrotator_host_label, 0, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        pstrotator_connection_layout.addWidget(self.pstrotator_host, 0, 1)
        pstrotator_connection_layout.addWidget(pstrotator_port_label, 1, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        pstrotator_connection_layout.addWidget(self.pstrotator_port, 1, 1)
        pstrotator_connection_layout.addWidget(pstrotator_current_azimuth_label, 2, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        pstrotator_connection_layout.addWidget(self.pstrotator_current_azimuth_value, 2, 1)
        pstrotator_connection_layout.setColumnMinimumWidth(0, 200)
        pstrotator_connection_layout.setColumnStretch(0, 0)

        pstrotator_connection_group.setLayout(pstrotator_connection_layout)

        # Wanted tracking group
        pstrotator_wanted_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_PSTROTATOR_WANTED())
        self.group_boxes.append(pstrotator_wanted_group)
        pstrotator_wanted_group.setFont(CUSTOM_FONT_SMALL)
        pstrotator_wanted_layout = QtWidgets.QVBoxLayout()

        self.enable_pstrotator_wanted = QtWidgets.QCheckBox(SettingsStrings.CHECK_PSTROTATOR_WANTED())
        self.enable_pstrotator_wanted.setFont(CUSTOM_FONT)
        self.enable_pstrotator_wanted.setChecked(DEFAULT_ENABLE_PSTROTATOR_WANTED)
        pstrotator_wanted_layout.addWidget(self.enable_pstrotator_wanted)

        # Movement threshold (applies to all automatic moves).
        pstrotator_threshold_layout = QtWidgets.QHBoxLayout()
        pstrotator_threshold_label = QtWidgets.QLabel(SettingsStrings.LABEL_PSTROTATOR_THRESHOLD())
        pstrotator_threshold_label.setFont(CUSTOM_FONT)
        self.pstrotator_threshold = QtWidgets.QSpinBox()
        self.pstrotator_threshold.setFont(CUSTOM_FONT)
        self.pstrotator_threshold.setRange(0, 180)
        self.pstrotator_threshold.setSuffix(SettingsStrings.SUFFIX_PSTROTATOR_DEGREES())
        self.pstrotator_threshold.setValue(DEFAULT_PSTROTATOR_THRESHOLD)
        pstrotator_threshold_layout.addWidget(pstrotator_threshold_label)
        pstrotator_threshold_layout.addWidget(self.pstrotator_threshold)
        pstrotator_threshold_layout.addStretch()
        pstrotator_wanted_layout.addLayout(pstrotator_threshold_layout)

        pstrotator_wanted_group.setLayout(pstrotator_wanted_layout)

        # Return-to-previous-position group (depends on Wanted Tracking).
        pstrotator_park_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_PSTROTATOR_PARK())
        self.group_boxes.append(pstrotator_park_group)
        pstrotator_park_group.setFont(CUSTOM_FONT_SMALL)
        self.pstrotator_park_group = pstrotator_park_group
        pstrotator_park_layout = QtWidgets.QVBoxLayout()

        self.enable_pstrotator_park = QtWidgets.QCheckBox(SettingsStrings.CHECK_PSTROTATOR_PARK())
        self.enable_pstrotator_park.setFont(CUSTOM_FONT)
        self.enable_pstrotator_park.setChecked(DEFAULT_ENABLE_PSTROTATOR_PARK)
        self.enable_pstrotator_park.toggled.connect(self.update_pstrotator_park_enabled)
        pstrotator_park_layout.addWidget(self.enable_pstrotator_park)

        # Container dimmed when parking is disabled (values kept).
        self.pstrotator_park_body = QtWidgets.QWidget()
        pstrotator_park_body_layout = QtWidgets.QGridLayout(self.pstrotator_park_body)
        pstrotator_park_body_layout.setContentsMargins(0, 0, 0, 0)

        pstrotator_park_delay_label = QtWidgets.QLabel(SettingsStrings.LABEL_PSTROTATOR_PARK_DELAY())
        pstrotator_park_delay_label.setFont(CUSTOM_FONT)
        self.pstrotator_park_delay = QtWidgets.QSpinBox()
        self.pstrotator_park_delay.setFont(CUSTOM_FONT)
        self.pstrotator_park_delay.setRange(1, 1440)
        self.pstrotator_park_delay.setSuffix(SettingsStrings.SUFFIX_PSTROTATOR_MINUTES())
        self.pstrotator_park_delay.setValue(DEFAULT_PSTROTATOR_PARK_DELAY)

        pstrotator_park_body_layout.addWidget(pstrotator_park_delay_label, 0, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        pstrotator_park_body_layout.addWidget(self.pstrotator_park_delay, 0, 1, QtCore.Qt.AlignmentFlag.AlignLeft)
        pstrotator_park_body_layout.setColumnMinimumWidth(0, 200)
        pstrotator_park_body_layout.setColumnStretch(2, 1)

        pstrotator_park_layout.addWidget(self.pstrotator_park_body)
        pstrotator_park_group.setLayout(pstrotator_park_layout)

        # The whole park group only makes sense when Wanted Tracking is on.
        self.enable_pstrotator_wanted.toggled.connect(self.update_pstrotator_park_enabled)

        # Hourly schedule group
        pstrotator_schedule_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_PSTROTATOR_SCHEDULE())
        self.group_boxes.append(pstrotator_schedule_group)
        pstrotator_schedule_group.setFont(CUSTOM_FONT_SMALL)
        pstrotator_schedule_layout = QtWidgets.QVBoxLayout()

        self.enable_pstrotator_schedule = QtWidgets.QCheckBox(SettingsStrings.CHECK_PSTROTATOR_SCHEDULE())
        self.enable_pstrotator_schedule.setFont(CUSTOM_FONT)
        self.enable_pstrotator_schedule.setChecked(DEFAULT_ENABLE_PSTROTATOR_SCHEDULE)
        self.enable_pstrotator_schedule.toggled.connect(self.update_pstrotator_schedule_enabled)
        pstrotator_schedule_layout.addWidget(self.enable_pstrotator_schedule)

        # Container that gets dimmed when the schedule is disabled (values kept).
        self.pstrotator_schedule_body = QtWidgets.QWidget()
        pstrotator_schedule_body_layout = QtWidgets.QVBoxLayout(self.pstrotator_schedule_body)
        pstrotator_schedule_body_layout.setContentsMargins(0, 0, 0, 0)

        self.pstrotator_schedule_table = QtWidgets.QTableWidget()
        self.pstrotator_schedule_table.setColumnCount(2)
        self.pstrotator_schedule_table.setHorizontalHeaderLabels([
            SettingsStrings.HEADER_PSTROTATOR_TIME(),
            SettingsStrings.HEADER_PSTROTATOR_AZIMUTH()
        ])
        # Validated cell editors: HH:mm time and 0-359 azimuth only.
        self.pstrotator_schedule_table.setItemDelegateForColumn(0, TimeHHMMDelegate(self.pstrotator_schedule_table))
        self.pstrotator_schedule_table.setItemDelegateForColumn(1, AzimuthDelegate(self.pstrotator_schedule_table))
        self.pstrotator_schedule_table.setShowGrid(False)
        self.pstrotator_schedule_table.setAlternatingRowColors(True)
        self.pstrotator_schedule_table.verticalHeader().setVisible(False)
        self.pstrotator_schedule_table.setFrameStyle(QtWidgets.QFrame.Shape.NoFrame)
        self.pstrotator_schedule_table.horizontalHeader().setStretchLastSection(True)
        self.pstrotator_schedule_table.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.pstrotator_schedule_table.horizontalHeader().setFont(CUSTOM_FONT_SMALL)
        self.pstrotator_schedule_table.horizontalHeader().setHighlightSections(False)
        self.pstrotator_schedule_table.verticalHeader().setHighlightSections(False)
        self.pstrotator_schedule_table.setColumnWidth(0, 200)
        self.pstrotator_schedule_table.setMaximumHeight(190)
        self.pstrotator_schedule_table.setFont(CUSTOM_FONT_SMALL)
        self.pstrotator_schedule_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.pstrotator_schedule_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                font-weight: normal;
                border: none;
                padding: 10 4px 4px 4px;
            }
        """)
        self.pstrotator_schedule_table.setStyleSheet(get_table_setting_qss())
        self.table_widgets.append(self.pstrotator_schedule_table)
        # Re-sort by time whenever a cell is edited (guarded against recursion).
        self._pstrotator_sorting = False
        self.pstrotator_schedule_table.itemChanged.connect(self.on_pstrotator_schedule_item_changed)
        pstrotator_schedule_body_layout.addWidget(self.pstrotator_schedule_table)

        pstrotator_schedule_buttons_layout = QtWidgets.QHBoxLayout()
        self.pstrotator_add_button = CustomButton(SettingsStrings.BUTTON_PSTROTATOR_ADD())
        self.pstrotator_add_button.setMaximumWidth(120)
        self.pstrotator_add_button.clicked.connect(self.add_pstrotator_schedule_row)
        self.pstrotator_remove_button = CustomButton(SettingsStrings.BUTTON_PSTROTATOR_REMOVE())
        self.pstrotator_remove_button.setMaximumWidth(120)
        self.pstrotator_remove_button.clicked.connect(self.remove_pstrotator_schedule_row)
        pstrotator_schedule_buttons_layout.addWidget(self.pstrotator_add_button)
        pstrotator_schedule_buttons_layout.addWidget(self.pstrotator_remove_button)
        pstrotator_schedule_buttons_layout.addStretch()
        pstrotator_schedule_body_layout.addLayout(pstrotator_schedule_buttons_layout)

        pstrotator_schedule_layout.addWidget(self.pstrotator_schedule_body)
        pstrotator_schedule_group.setLayout(pstrotator_schedule_layout)

        pstrotator_layout.addWidget(pstrotator_notice_label)
        pstrotator_layout.addWidget(pstrotator_connection_group)
        pstrotator_layout.addWidget(pstrotator_wanted_group)
        pstrotator_layout.addWidget(pstrotator_park_group)
        pstrotator_layout.addWidget(pstrotator_schedule_group)
        pstrotator_layout.addStretch()

        """
            Debug Settings
        """
        debug_notice_text = SettingsStrings.DEBUG_NOTICE()
        debug_notice_label = QtWidgets.QLabel(debug_notice_text)
        debug_notice_label.setWordWrap(True)
        debug_notice_label.setFont(CUSTOM_FONT_SMALL)
        debug_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        debug_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(debug_notice_label)
        debug_notice_label.setAutoFillBackground(True)

        log_settings_group = QtWidgets.QGroupBox(SettingsStrings.GROUP_DEBUG_SETTINGS())
        self.group_boxes.append(log_settings_group)
        log_settings_group.setFont(CUSTOM_FONT_SMALL)
        log_settings_layout = QtWidgets.QVBoxLayout()
        log_settings_layout.setSpacing(15)

        self.enable_debug_output = QtWidgets.QCheckBox(SettingsStrings.CHECK_ENABLE_POUNCE_LOG())
        self.enable_debug_output.setFont(CUSTOM_FONT)
        self.enable_debug_output.setChecked(DEFAULT_DEBUG_OUTPUT)

        self.enable_extra_gui_debug_output = QtWidgets.QCheckBox(SettingsStrings.CHECK_ENABLE_GUI_DEBUG())
        self.enable_extra_gui_debug_output.setFont(CUSTOM_FONT)
        self.enable_extra_gui_debug_output.setChecked(False)

        self.enable_pounce_log = QtWidgets.QCheckBox(SettingsStrings.CHECK_SAVE_LOG())
        self.enable_pounce_log.setFont(CUSTOM_FONT)
        self.enable_pounce_log.setChecked(DEFAULT_POUNCE_LOG)

        self.enable_log_packet_data = QtWidgets.QCheckBox(SettingsStrings.CHECK_LOG_PACKET_DATA())
        self.enable_log_packet_data.setFont(CUSTOM_FONT)
        self.enable_log_packet_data.setChecked(DEFAULT_LOG_PACKET_DATA)

        log_settings_layout.addWidget(self.enable_pounce_log)
        log_settings_layout.addWidget(self.enable_log_packet_data)
        log_settings_layout.addWidget(self.enable_extra_gui_debug_output)
        log_settings_layout.addWidget(self.enable_debug_output)

        log_settings_group.setLayout(log_settings_layout)

        # Add button to open log folder
        self.open_log_folder_button = CustomButton(SettingsStrings.BUTTON_OPEN_LOG_FOLDER())
        self.open_log_folder_button.clicked.connect(self.open_log_folder_clicked)

        # Add debug settings to debugging page
        debugging_layout.addWidget(debug_notice_label)
        debugging_layout.addWidget(log_settings_group)
        debugging_layout.addWidget(self.open_log_folder_button)
        debugging_layout.addStretch()

        self.load_params()

        # Live-update the "Current azimuth" label from the rotator poller.
        self.pst_rotator = getattr(parent, 'pst_rotator', None)
        if self.pst_rotator is not None:
            self.pst_rotator.azimuth_read.connect(self.update_pstrotator_current_azimuth)

        self.button_box = QtWidgets.QDialogButtonBox()
        self.ok_button = CustomButton(CommonStrings.OK())
        self.cancel_button = CustomButton(CommonStrings.CANCEL())

        self.button_box.addButton(self.ok_button, QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        self.button_box.addButton(self.cancel_button, QtWidgets.QDialogButtonBox.ButtonRole.RejectRole)

        layout.addWidget(self.button_box)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self.on_page_changed(0)
        self.menu_list.currentRowChanged.connect(self.on_page_changed)

    def get_ordinal(self, number):
        if number == 0:
            return "1st"
        elif number == 1:
            return "2nd"
        elif number == 2:
            return "3rd"
        else:
            return f"{number+1}th"

    def update_priority_labels(self):
        row_height = 30
        for i in range(self.priority_table.rowCount()):
            self.priority_table.setRowHeight(i, row_height)

            priority_item = QTableWidgetItem(self.get_ordinal(i))
            priority_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            priority_item.setFlags(priority_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            priority_item.setFont(CUSTOM_FONT_SMALL)
            self.priority_table.setItem(i, 0, priority_item)

    def populate_priority_list(self):
        if not hasattr(self, 'priority_table'):
            return

        # Get current order from table
        current_order = []
        for i in range(self.priority_table.rowCount()):
            feature_item = self.priority_table.item(i, 1)
            if feature_item:
                current_order.append(feature_item.text())

        # Load from saved settings
        if not current_order:
            saved_order = self.params.get('priority_order', list(PRIORITY_LIST.values()))
            reverse_mapping = {v: k for k, v in PRIORITY_LIST.items()}
            for item in saved_order:
                try:
                    if item in reverse_mapping:
                        current_order.append(reverse_mapping[item])
                    elif item in PRIORITY_LIST:
                        current_order.append(item)
                except KeyError:
                    pass

        available_items = []
        if self.enable_sending_reply.isChecked():
            for display_name, key in PRIORITY_LIST.items():
                if key == "marathon":
                    if not self.marathon_preference or not any(self.marathon_preference.values()):
                        continue
                elif key == "dxcc_entity":
                    if not self.dxcc_preference or not any(self.dxcc_preference.values()):
                        continue
                elif key == "wanted_grid":
                    if not self.grid_tracker_preference or not any(self.grid_tracker_preference.values()):
                        continue
                available_items.append(display_name)
            if not self.enable_polite_reply.isChecked():
                 if available_items:
                    available_items.pop()

        final_order = []
        for item in current_order:
            if item in available_items:
                final_order.append(item)
                available_items.remove(item)
        final_order.extend(available_items)

        self.priority_table.setRowCount(len(final_order))

        row_height = 30
        for i, item_name in enumerate(final_order):
            self.priority_table.setRowHeight(i, row_height)

            priority_item = QTableWidgetItem(self.get_ordinal(i))
            priority_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            priority_item.setFlags(priority_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            priority_item.setFont(CUSTOM_FONT_SMALL)
            self.priority_table.setItem(i, 0, priority_item)

            # Feature column
            feature_item = QTableWidgetItem(item_name)
            feature_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            feature_item.setFlags(feature_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            feature_item.setFont(CUSTOM_FONT_SMALL)
            self.priority_table.setItem(i, 1, feature_item)

    def update_priority_manager_visibility(self):
        if self.enable_sending_reply.isChecked():
            self.priority_manager_group.setVisible(True)
            self.populate_priority_list()
        else:
            self.priority_manager_group.setVisible(False)

    def on_band_toggled(self, button, band_name, checked):
        if not hasattr(self, "_previous_band_states"):
            self._previous_band_states = {}

        if band_name == MARATHON_UNLIMITED:
            if checked:
                self._previous_band_states = {
                    name: btn.isChecked() for name, btn in self.band_buttons.items() if name != MARATHON_UNLIMITED
                }
                for name, btn in self.band_buttons.items():
                    if name != MARATHON_UNLIMITED:
                        btn.setChecked(False)
                        self.marathon_preference[name] = False
            else:
                for name, btn in self.band_buttons.items():
                    if name != MARATHON_UNLIMITED and name in self._previous_band_states:
                        btn.setChecked(self._previous_band_states[name])
                        self.marathon_preference[name] = self._previous_band_states[name]
        else:
            if checked:
                self.band_buttons[MARATHON_UNLIMITED].setChecked(False)
                self.band_buttons[MARATHON_UNLIMITED].setEnabled(True)
                self.marathon_preference[MARATHON_UNLIMITED] = False

        if checked:
            button.updateStyle(band_name, STATUS_TRX_COLOR, "#FFFFFF")
        else:
            button.resetStyle()

        self.marathon_preference[band_name] = checked

        self.populate_priority_list()

    def on_dxcc_band_toggled(self, button, band_name, checked):
        if not hasattr(self, "_previous_dxcc_band_states"):
            self._previous_dxcc_band_states = {}

        if band_name == MARATHON_UNLIMITED:
            if checked:
                self._previous_dxcc_band_states = {
                    name: btn.isChecked() for name, btn in self.dxcc_band_buttons.items() if name != MARATHON_UNLIMITED
                }
                for name, btn in self.dxcc_band_buttons.items():
                    if name != MARATHON_UNLIMITED:
                        btn.setChecked(False)
                        self.dxcc_preference[name] = False
            else:
                for name, btn in self.dxcc_band_buttons.items():
                    if name != MARATHON_UNLIMITED and name in self._previous_dxcc_band_states:
                        btn.setChecked(self._previous_dxcc_band_states[name])
                        self.dxcc_preference[name] = self._previous_dxcc_band_states[name]
        else:
            if checked:
                self.dxcc_band_buttons[MARATHON_UNLIMITED].setChecked(False)
                self.dxcc_band_buttons[MARATHON_UNLIMITED].setEnabled(True)
                self.dxcc_preference[MARATHON_UNLIMITED] = False

        if checked:
            button.updateStyle(band_name, STATUS_TRX_COLOR, "#FFFFFF")
        else:
            button.resetStyle()

        self.dxcc_preference[band_name] = checked

        self.populate_priority_list()

    def on_grid_tracker_band_toggled(self, button, band_name, checked):
        if checked:
            button.updateStyle(band_name, STATUS_TRX_COLOR, "#FFFFFF")
        else:
            button.resetStyle()

        self.grid_tracker_preference[band_name] = checked

        self.populate_priority_list()

    def add_pstrotator_schedule_row(self, hour=0, minute=0, azimuth=0):
        # Signals from clicked() may pass a bool; ignore non-int defaults.
        if not isinstance(hour, int):
            hour = 0
        if not isinstance(minute, int):
            minute = 0
        if not isinstance(azimuth, int):
            azimuth = 0

        row = self.pstrotator_schedule_table.rowCount()
        self.pstrotator_schedule_table.insertRow(row)
        self.pstrotator_schedule_table.setRowHeight(row, 30)

        # Populate both cells before the itemChanged-driven sort can run, so the
        # two columns of a row stay paired.
        self.pstrotator_schedule_table.blockSignals(True)

        # Plain editable cells (double-click to edit), no spinbox arrows.
        time_item = QTableWidgetItem(f"{hour:02d}:{minute:02d}")
        time_item.setFont(CUSTOM_FONT)
        time_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.pstrotator_schedule_table.setItem(row, 0, time_item)

        azimuth_item = QTableWidgetItem(str(azimuth))
        azimuth_item.setFont(CUSTOM_FONT)
        azimuth_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.pstrotator_schedule_table.setItem(row, 1, azimuth_item)

        self.pstrotator_schedule_table.blockSignals(False)

    def on_pstrotator_schedule_item_changed(self, _item):
        # Sort by time whenever the user finishes editing a cell.
        self.sort_pstrotator_schedule_table()

    def sort_pstrotator_schedule_table(self):
        # Avoid re-entrancy: rebuilding the rows fires itemChanged again.
        if self._pstrotator_sorting:
            return
        self._pstrotator_sorting = True
        try:
            table = self.pstrotator_schedule_table

            rows = []
            for row in range(table.rowCount()):
                time_item    = table.item(row, 0)
                azimuth_item = table.item(row, 1)
                time_text    = time_item.text() if time_item else ""
                azimuth_text = azimuth_item.text() if azimuth_item else ""

                match = re.match(r'^(\d{1,2})[:hH.]?(\d{2})$', time_text.strip())
                # Unparseable times sort last, keeping their on-screen order.
                sort_key = (int(match.group(1)), int(match.group(2))) if match else (99, 99)
                rows.append((sort_key, time_text, azimuth_text))

            rows.sort(key=lambda r: r[0])

            for row, (_key, time_text, azimuth_text) in enumerate(rows):
                time_item    = table.item(row, 0)
                azimuth_item = table.item(row, 1)
                if time_item is not None:
                    time_item.setText(time_text)
                if azimuth_item is not None:
                    azimuth_item.setText(azimuth_text)
        finally:
            self._pstrotator_sorting = False

    def update_pstrotator_schedule_enabled(self, enabled=None):
        if enabled is None:
            enabled = self.enable_pstrotator_schedule.isChecked()
        # Keep the values but grey out the controls when the schedule is disabled.
        # setEnabled(False) already dims widgets; we avoid QGraphicsOpacityEffect
        # which causes ghost-rendering artefacts on a QStackedWidget page.
        self.pstrotator_schedule_body.setEnabled(enabled)

    def update_pstrotator_park_enabled(self, _checked=None):
        # The whole group depends on Wanted Tracking; the delay field also
        # depends on the park checkbox itself.
        wanted_on = self.enable_pstrotator_wanted.isChecked()
        self.pstrotator_park_group.setEnabled(wanted_on)
        self.pstrotator_park_body.setEnabled(wanted_on and self.enable_pstrotator_park.isChecked())

    def done(self, result):
        # Detach from the persistent rotator poller before the dialog is destroyed.
        if getattr(self, 'pst_rotator', None) is not None:
            try:
                self.pst_rotator.azimuth_read.disconnect(self.update_pstrotator_current_azimuth)
            except (TypeError, RuntimeError):
                pass
        super().done(result)

    def update_pstrotator_current_azimuth(self, azimuth):
        if azimuth is None:
            self.pstrotator_current_azimuth_value.setText(
                SettingsStrings.PSTROTATOR_AZIMUTH_UNKNOWN()
            )
        else:
            self.pstrotator_current_azimuth_value.setText(
                SettingsStrings.PSTROTATOR_AZIMUTH_VALUE(round(azimuth))
            )

    def remove_pstrotator_schedule_row(self):
        row = self.pstrotator_schedule_table.currentRow()
        if row < 0:
            row = self.pstrotator_schedule_table.rowCount() - 1
        if row >= 0:
            self.pstrotator_schedule_table.removeRow(row)

    def get_pstrotator_schedule(self):
        schedule = []
        for row in range(self.pstrotator_schedule_table.rowCount()):
            time_item    = self.pstrotator_schedule_table.item(row, 0)
            azimuth_item = self.pstrotator_schedule_table.item(row, 1)
            if time_item is None or azimuth_item is None:
                continue

            time_text = time_item.text().strip()
            match = re.match(r'^(\d{1,2})[:hH.]?(\d{2})$', time_text)
            if not match:
                continue
            hour, minute = int(match.group(1)), int(match.group(2))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                continue

            azimuth_text = azimuth_item.text().strip().rstrip('°').strip()
            if not azimuth_text.isdigit():
                continue
            azimuth = int(azimuth_text)
            if not (0 <= azimuth <= 359):
                continue

            schedule.append({
                'hour'   : hour,
                'minute' : minute,
                'azimuth': azimuth
            })
        return schedule

    def on_table_row_selected(self, row, _column):
        # Get the radio button for this row
        button = self.row_to_radio.get(row)

        if button:
            button.setChecked(True)
            # Ensure the row stays selected
            self.mode_table_widget.selectRow(row)

            # If Custom row is selected, restore the custom frequency values
            if button == self.radio_custom:
                # Temporarily disconnect signals to avoid triggering on_frequency_changed
                self.min_freq.valueChanged.disconnect(self.on_frequency_changed)
                self.max_freq.valueChanged.disconnect(self.on_frequency_changed)

                # Restore the stored custom values
                self.min_freq.setValue(self.custom_min_freq_value)
                self.max_freq.setValue(self.custom_max_freq_value)

                # Reconnect signals
                self.min_freq.valueChanged.connect(self.on_frequency_changed)
                self.max_freq.valueChanged.connect(self.on_frequency_changed)
            else:
                # For preset rows, update frequency inputs from the preset values
                if button in self.freq_range:
                    preset_min, preset_max = self.freq_range[button]
                    # Temporarily disconnect signals to avoid triggering on_frequency_changed
                    self.min_freq.valueChanged.disconnect(self.on_frequency_changed)
                    self.max_freq.valueChanged.disconnect(self.on_frequency_changed)

                    self.min_freq.setValue(preset_min)
                    self.max_freq.setValue(preset_max)

                    # Reconnect signals
                    self.min_freq.valueChanged.connect(self.on_frequency_changed)
                    self.max_freq.valueChanged.connect(self.on_frequency_changed)

    def on_frequency_changed(self):
        """Called when frequency spinbox values change - auto-select Custom and update table"""
        min_freq = self.min_freq.value()
        max_freq = self.max_freq.value()

        # Check if current frequencies match any preset
        matches_preset = False
        for radio, (preset_min, preset_max) in self.freq_range.items():
            if min_freq == preset_min and max_freq == preset_max:
                radio.setChecked(True)
                matches_preset = True

                # Highlight the matching preset row in the table
                for row, button in self.row_to_radio.items():
                    if button == radio:
                        self.mode_table_widget.selectRow(row)
                        break
                break

        # If no preset matches, select Custom and update its table row
        if not matches_preset:
            # Store the custom values
            self.custom_min_freq_value = min_freq
            self.custom_max_freq_value = max_freq

            self.radio_custom.setChecked(True)
            # Update the table display for the Custom row only
            self.update_custom_table_display()

            # Highlight the Custom row in the table
            custom_row = 3  # Custom is the 4th row (0-indexed)
            self.mode_table_widget.selectRow(custom_row)

    def update_custom_table_display(self):
        custom_row = 3  # Custom is the 4th row (0-indexed)
        freq_min_item = self.mode_table_widget.item(custom_row, 0)  # Column 0 now
        freq_max_item = self.mode_table_widget.item(custom_row, 1)  # Column 1 now
        if freq_min_item and freq_max_item:
            freq_min_item.setText(f"{self.custom_min_freq_value}Hz")
            freq_max_item.setText(f"{self.custom_max_freq_value}Hz")

    def highlight_selected_mode_row(self):
        selected_radio = None
        if self.radio_normal.isChecked():
            selected_radio = self.radio_normal
        elif self.radio_foxhound.isChecked():
            selected_radio = self.radio_foxhound
        elif self.radio_superfox.isChecked():
            selected_radio = self.radio_superfox
        elif self.radio_custom.isChecked():
            selected_radio = self.radio_custom

        if selected_radio:
            for row, button in self.row_to_radio.items():
                if button == selected_radio:
                    self.mode_table_widget.selectRow(row)
                    break

    def on_page_changed(self, index):
        # Clear focus from any widget to prevent unwanted field focus
        if self.focusWidget():
            self.focusWidget().clearFocus()

        if sys.platform == 'darwin':
            current_page = self.stacked_widget.widget(index)

            page_size           = current_page.sizeHint()
            button_box_height   = self.button_box.sizeHint().height()
            margins             = self.layout().contentsMargins()
            total_height        = page_size.height() + button_box_height + margins.top() + margins.bottom()

            final_height = max(total_height, 700)
            self.setFixedHeight(final_height)


    def get_backup_file_status(self, file_path):
        if not os.path.exists(file_path):
            return "File not found", 0, 0, "N/A", "N/A"

        try:
            if os.path.getsize(file_path) == 0:
                return "Empty file", 0, 0, "N/A", "N/A"
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            total_entries = content.upper().count('<EOR>')

            callsigns = set()
            first_entry_date = None
            records = re.split(r'<EOR>', content, flags=re.IGNORECASE)

            for record in records:
                if record.strip():  # Skip empty records
                    fields = {
                        field.upper(): value.strip()
                        for field, value in ADIF_FIELD_RE.findall(record)
                    }
                    call = fields.get('CALL')
                    if call:
                        callsigns.add(call.upper())

                    # Extract date for first entry
                    if first_entry_date is None:
                        qso_date = fields.get('QSO_DATE')
                        if qso_date and len(qso_date) >= 8:
                            try:
                                # Parse ADIF date format (YYYYMMDD)
                                year = qso_date[0:4]
                                month = qso_date[4:6]
                                day = qso_date[6:8]
                                first_entry_date = f"{year}-{month}-{day}"
                            except:
                                pass

            unique_calls = len(callsigns)

            mod_time = os.path.getmtime(file_path)
            last_update = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")

            return "Ready", total_entries, unique_calls, last_update, first_entry_date or "N/A"

        except Exception as e:
            print(f"Error parsing ADIF file {file_path}: {e}")
            return "Error reading file", 0, 0, "N/A", "N/A"

    def update_backup_file_status(self):
        file_path = self.show_backup_file_path.text().strip()
        if not file_path:
            status_text = SettingsStrings.BACKUP_STATUS_NO_FILE()
        else:
            status, total_entries, unique_calls, last_update, first_entry = self.get_backup_file_status(file_path)
            if status == "Ready":
                status_text = SettingsStrings.BACKUP_STATUS_READY(
                    status, total_entries, unique_calls, first_entry, last_update
                )
            else:
                status_text = SettingsStrings.BACKUP_STATUS_OTHER(status)

        self.backup_file_status_info.setText(status_text)

    def open_backup_file_dialog(self):
        dialog = QFileDialog(self, SettingsStrings.DIALOG_SELECT_BACKUP())
        dialog.setNameFilter(SettingsStrings.FILE_FILTER_ADIF())
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setOptions(
            QFileDialog.Option.DontUseCustomDirectoryIcons
        )

        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            selected_files = dialog.selectedFiles()
            if selected_files:
                self.show_backup_file_path.setText(selected_files[0])
                self.update_backup_file_status()

    def add_adif_file(self):
        dialog = QFileDialog(self, SettingsStrings.DIALOG_SELECT_ADIF())
        dialog.setNameFilter(SettingsStrings.FILE_FILTER_ADIF())
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setOptions(
            QFileDialog.Option.DontUseCustomDirectoryIcons
        )

        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            selected_files = dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]

                # Check if file is already added
                if file_path in self.selected_adif_files:
                    QtWidgets.QMessageBox.information(
                        self,
                        SettingsStrings.MESSAGE_FILE_ALREADY_ADDED(),
                        SettingsStrings.MESSAGE_FILE_ALREADY_IN_LIST(os.path.basename(file_path))
                    )
                    return

                processing_time, parsed_data = parse_adif(file_path)
                if parsed_data:
                    self.selected_adif_files.append(file_path)
                    self.add_file_to_list(file_path)
                    self.adif_wkb4_group.setVisible(True)

                    summary_dialog = AdifSummaryDialog(processing_time, parsed_data['wkb4'], self.dark_mode, file_path, self)
                    summary_dialog.exec()
                else:
                    QtWidgets.QMessageBox.warning(
                        self,
                        SettingsStrings.MESSAGE_NO_DATA_FOUND(),
                        SettingsStrings.MESSAGE_FILE_EMPTY_OR_CORRUPTED()
                    )
        else:
            print("No file selected.")

    def test_lotw_download_qsls(self):
        username = self.lotw_username.text().strip()
        password = self.lotw_password.text().strip()

        if not username or not password:
            log.warning("LoTW test download: username or password missing")
            WindowController.show_test_result_dialog(self, {
                'title': 'Missing Information',
                'message': 'Please enter your LoTW username and password.'
            })
            return

        qso_since_str = self.lotw_qso_since_date.dateTime().toString('yyyy-MM-dd HH:mm:ss')
        log.info(f"Starting LoTW test download for {username} since {qso_since_str}")

        self.test_lotw_download_button.setEnabled(False)
        self.test_lotw_download_button.setText("Downloading...")

        thread = QtCore.QThread(self)
        self._lotw_test_worker = LoTWDownloadWorker(username, password, qso_since_str)
        self._lotw_test_thread = thread
        self._lotw_test_worker.moveToThread(thread)
        thread.started.connect(self._lotw_test_worker.run)

        def on_finished(success, result):
            QtWidgets.QApplication.restoreOverrideCursor()
            self.test_lotw_download_button.setEnabled(True)
            self.test_lotw_download_button.setText(SettingsStrings.BUTTON_TEST_LOTW_DOWNLOAD())
            thread.quit()
            self._lotw_test_worker = None
            self._lotw_test_thread = None

            if not success:
                log.error(f"LoTW test download failed: {result}")
                WindowController.show_test_result_dialog(self, {
                    'title': 'Download Failed',
                    'message': f'Download failed:\n\n{result}'
                })
                return

            log.info("LoTW test download successful, showing results")
            dialog = LoTWIncomingDialog(result, since_date=qso_since_str, dark_mode=self.dark_mode, parent=self)
            dialog.exec()

        self._lotw_test_worker.finished.connect(on_finished)
        thread.start()

    def browse_tqsl_path(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

        # Show hidden files while keeping native dialog
        dialog.setFilter(QtCore.QDir.Filter.Hidden | QtCore.QDir.Filter.AllDirs | QtCore.QDir.Filter.Files)

        if platform.system() == 'Windows':
            dialog.setNameFilter("Executable Files (*.exe);;All Files (*.*)")
        elif platform.system() == 'Darwin':
            # On macOS, TQSL is inside the app bundle
            dialog.setDirectory("/Applications")
            dialog.setNameFilter("All Files (*);;Applications (*.app)")
        else:
            dialog.setNameFilter("All Files (*)")

        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            selected_files = dialog.selectedFiles()
            if selected_files:
                selected_path = selected_files[0]

                # If on macOS and user selected the .app bundle, point to the actual executable
                if platform.system() == 'Darwin' and selected_path.endswith('.app'):
                    tqsl_executable = os.path.join(selected_path, 'Contents', 'MacOS', 'tqsl')
                    if os.path.exists(tqsl_executable):
                        selected_path = tqsl_executable

                self.tqsl_path.setText(selected_path)

    def browse_tqsl_dir(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.Directory)

        # Show hidden files while keeping native dialog
        dialog.setFilter(QtCore.QDir.Filter.Hidden | QtCore.QDir.Filter.AllDirs | QtCore.QDir.Filter.Files)

        # Set default directory to user's home
        dialog.setDirectory(os.path.expanduser("~"))

        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            selected_dirs = dialog.selectedFiles()
            if selected_dirs:
                self.tqsl_dir.setText(selected_dirs[0])

    def browse_tqsl_dir(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.Directory)

        # Show hidden files while keeping native dialog
        dialog.setFilter(QtCore.QDir.Filter.Hidden | QtCore.QDir.Filter.AllDirs)

        # Start in home directory
        home_dir = os.path.expanduser("~")
        dialog.setDirectory(home_dir)

        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            selected_dirs = dialog.selectedFiles()
            if selected_dirs:
                self.tqsl_dir.setText(selected_dirs[0])

    def test_lotw_upload_last_qso(self):
        username = self.lotw_username.text().strip()
        password = self.lotw_password.text().strip()
        location = self.lotw_location.text().strip()
        signing_password = self.lotw_signing_password.text().strip()
        tqsl_path = self.tqsl_path.text().strip()

        if not username:
            log.warning("LoTW test upload failed: No username provided")
            WindowController.show_test_result_dialog(self, {
                'title': 'Missing Information',
                'message': 'Please enter your LoTW username.'
            })
            return

        # Get the last QSO from the log file
        from constants import ADIF_WORKED_CALLSIGNS_FILE

        if not os.path.exists(ADIF_WORKED_CALLSIGNS_FILE):
            log.warning(f"LoTW test upload failed: Log file not found at {ADIF_WORKED_CALLSIGNS_FILE}")
            WindowController.show_test_result_dialog(self, {
                'title': 'No Log File',
                'message': f'No QSO log file found at:\n{ADIF_WORKED_CALLSIGNS_FILE}\n\nMake at least one QSO first.'
            })
            return

        try:
            log.info(f"Starting LoTW test upload for user: {username}")

            # Read the last QSO from the ADIF file (errors='replace' — user logs may contain Latin-1 chars)
            with open(ADIF_WORKED_CALLSIGNS_FILE, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read().strip()

            if not content:
                log.warning("LoTW test upload failed: Log file is empty")
                WindowController.show_test_result_dialog(self, {
                    'title': 'Empty Log File',
                    'message': 'The log file is empty. Make at least one QSO first.'
                })
                return

            # Split by <eor> tags (case insensitive)
            import re
            records = re.split(r'<eor>', content, flags=re.IGNORECASE)

            # Filter out empty records
            records = [r.strip() for r in records if r.strip()]

            if not records:
                log.warning("LoTW test upload failed: No QSO records found in log file")
                WindowController.show_test_result_dialog(self, {
                    'title': 'No QSOs Found',
                    'message': f'No QSO records found in log file:\n{ADIF_WORKED_CALLSIGNS_FILE}'
                })
                return

            # Get the last QSO record and add back the <eor> tag
            last_qso = records[-1] + ' <eor>'

            # Prepend a minimal ADIF header
            adif_with_header = "ADIF Export\n<ADIF_VER:5>3.1.0\n<PROGRAMID:17>Wait and Pounce\n<EOH>\n" + last_qso

            # Extract callsign for display
            call_match = re.search(r'<call:\d+>([^\s<]+)', last_qso, re.IGNORECASE)
            callsign = call_match.group(1) if call_match else 'Unknown'

            log.info(f"Attempting to upload QSO with {callsign} to LoTW")

            # Get tqsl_dir from settings
            tqsl_dir = self.tqsl_dir.text().strip()

            log.info(f"Starting LoTW upload for QSO with {callsign}")

            # Create uploader instance
            uploader = LoTWClient(
                username=username,
                password=password,
                tqsl_path=tqsl_path if tqsl_path else None,
                tqsl_dir=tqsl_dir if tqsl_dir else None,
                location=location if location else None,
                signing_password=signing_password if signing_password else None
            )

            # Try to upload (this will take a few seconds)
            success, message = uploader.upload_qso(adif_with_header)

            if success:
                log.info(f"LoTW upload successful for QSO with {callsign}")
                WindowController.show_test_result_dialog(self, {
                    'title': 'Upload Successful',
                    'message': f'Last QSO with {callsign} uploaded successfully to LoTW!'
                })
            else:
                log.error(f"LoTW upload failed for QSO with {callsign}: {message}")
                WindowController.show_test_result_dialog(self, {
                    'title': 'Upload Failed',
                    'message': f'Upload failed:\n\n{message}'
                })

        except Exception as e:
            log.error(f"LoTW test upload exception: {str(e)}", exc_info=True)
            WindowController.show_test_result_dialog(self, {
                'title': 'Error',
                'message': f'An error occurred while uploading:\n\n{str(e)}'
            })

    def test_club_log_upload_last_qso(self):
        email = self.club_log_email.text().strip()
        password = self.club_log_password.text().strip()
        callsign = self.club_log_callsign.text().strip()
        api_key = self.club_log_api_key.text().strip()

        if not email or not password or not api_key:
            log.warning("Club Log test upload failed: Missing email, password or API key")
            WindowController.show_test_result_dialog(self, {
                'title': 'Missing Information',
                'message': 'Please enter your Club Log email, application password and API key.'
            })
            return

        # Get the last QSO from the log file
        from constants import ADIF_WORKED_CALLSIGNS_FILE

        if not os.path.exists(ADIF_WORKED_CALLSIGNS_FILE):
            log.warning(f"Club Log test upload failed: Log file not found at {ADIF_WORKED_CALLSIGNS_FILE}")
            WindowController.show_test_result_dialog(self, {
                'title': 'No Log File',
                'message': f'No QSO log file found at:\n{ADIF_WORKED_CALLSIGNS_FILE}\n\nMake at least one QSO first.'
            })
            return

        try:
            log.info(f"Starting Club Log test upload for email: {email}")

            # Read the last QSO from the ADIF file (errors='replace' — user logs may contain Latin-1 chars)
            with open(ADIF_WORKED_CALLSIGNS_FILE, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read().strip()

            if not content:
                log.warning("Club Log test upload failed: Log file is empty")
                WindowController.show_test_result_dialog(self, {
                    'title': 'Empty Log File',
                    'message': 'The log file is empty. Make at least one QSO first.'
                })
                return

            # Split by <eor> tags (case insensitive)
            import re
            records = re.split(r'<eor>', content, flags=re.IGNORECASE)

            # Filter out empty records
            records = [r.strip() for r in records if r.strip()]

            if not records:
                log.warning("Club Log test upload failed: No QSO records found in log file")
                WindowController.show_test_result_dialog(self, {
                    'title': 'No QSOs Found',
                    'message': f'No QSO records found in log file:\n{ADIF_WORKED_CALLSIGNS_FILE}'
                })
                return

            # Get the last QSO record and add back the <EOR> tag (Club Log expects a single ADIF record)
            last_qso = records[-1] + ' <EOR>'

            # Extract callsign for display
            call_match = re.search(r'<call:\d+>([^\s<]+)', last_qso, re.IGNORECASE)
            qso_callsign = call_match.group(1) if call_match else 'Unknown'

            log.info(f"Attempting to upload QSO with {qso_callsign} to Club Log")

            # Create uploader instance with the user's own credentials
            uploader = ClubLogUploader(email, password, api_key, callsign)

            # Try to upload (this will take a few seconds)
            success, message = uploader.upload_qso(last_qso)

            if success:
                log.info(f"Club Log upload successful for QSO with {qso_callsign}")
                WindowController.show_test_result_dialog(self, {
                    'title': 'Upload Successful',
                    'message': f'Last QSO with {qso_callsign} uploaded successfully to Club Log!'
                })
            else:
                log.error(f"Club Log upload failed for QSO with {qso_callsign}: {message}")
                WindowController.show_test_result_dialog(self, {
                    'title': 'Upload Failed',
                    'message': f'Upload failed:\n\n{message}'
                })

        except Exception as e:
            log.error(f"Club Log test upload exception: {str(e)}", exc_info=True)
            WindowController.show_test_result_dialog(self, {
                'title': 'Error',
                'message': f'An error occurred while uploading:\n\n{str(e)}'
            })

    def add_file_to_list(self, file_path):
        """Add a file entry to the table"""
        row_position = self.adif_files_table.rowCount()
        self.adif_files_table.insertRow(row_position)

        # Create counter item for first column
        counter_item = QtWidgets.QTableWidgetItem(str(row_position + 1))
        counter_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        counter_item.setFlags(counter_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)  # Make read-only
        self.adif_files_table.setItem(row_position, 0, counter_item)

        # Create item with full file path for second column
        file_item = QtWidgets.QTableWidgetItem(file_path)
        file_item.setToolTip(file_path)  # Show full path on hover
        file_item.setFlags(file_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)  # Make read-only
        self.adif_files_table.setItem(row_position, 1, file_item)

    def remove_adif_file(self, file_path, row=None):
        """Remove a file from the list and table"""
        if file_path in self.selected_adif_files:
            self.selected_adif_files.remove(file_path)

        # Find and remove the row from table if row not provided
        if row is None:
            for i in range(self.adif_files_table.rowCount()):
                item = self.adif_files_table.item(i, 1)  # Check column 1 (file path column)
                if item and item.text() == file_path:
                    row = i
                    break

        # Remove the row from table
        if row is not None:
            self.adif_files_table.removeRow(row)
            # Renumber the counter column after removing a row
            self.renumber_counter_column()

        # Hide the WKB4 group if no files are selected
        if not self.selected_adif_files:
            self.adif_wkb4_group.setVisible(False)

    def renumber_counter_column(self):
        for i in range(self.adif_files_table.rowCount()):
            counter_item = self.adif_files_table.item(i, 0)
            if counter_item:
                counter_item.setText(str(i + 1))

    def on_table_selection_changed(self):
        selected_rows = self.adif_files_table.selectionModel().selectedRows()
        has_selection = len(selected_rows) > 0
        self.summary_file_button.setEnabled(has_selection)
        self.clear_file_button.setEnabled(has_selection)

    def clear_selected_file(self):
        selected_rows = self.adif_files_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            item = self.adif_files_table.item(row, 1)  # Get file path from column 1
            if item:
                file_path = item.text()
                self.remove_adif_file(file_path, row)

    def show_selected_file_summary(self):
        selected_rows = self.adif_files_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            item = self.adif_files_table.item(row, 1)  # Get file path from column 1
            if item:
                file_path = item.text()

                # Check if file exists
                if not os.path.exists(file_path):
                    QtWidgets.QMessageBox.warning(
                        self,
                        "File Not Found",
                        f"The file '{os.path.basename(file_path)}' no longer exists."
                    )
                    return

                # Parse the ADIF file
                try:
                    processing_time, parsed_data = parse_adif(file_path)
                    if parsed_data:
                        summary_dialog = AdifSummaryDialog(processing_time, parsed_data['wkb4'], self.dark_mode, file_path, self)
                        summary_dialog.exec()
                    else:
                        QtWidgets.QMessageBox.warning(
                            self,
                            "No Data Found",
                            f"No valid data found in '{os.path.basename(file_path)}'"
                        )
                except Exception as e:
                    QtWidgets.QMessageBox.critical(
                        self,
                        "Error Parsing File",
                        f"Error parsing '{os.path.basename(file_path)}':\n{str(e)}"
                    )

    def open_backup_file_location(self):
        backup_file_path = os.path.abspath(ADIF_WORKED_CALLSIGNS_FILE)

        if not os.path.exists(backup_file_path):
            QtWidgets.QMessageBox.warning(self, "File not found", f"File doesn't exist:\n{backup_file_path}")
            return

        if platform.system() == 'Darwin':
            backup_dir = os.path.dirname(backup_file_path)
            subprocess.call(['open', backup_dir])
        elif platform.system() == 'Windows':
            subprocess.run(['explorer', '/select,', backup_file_path])
        elif os.name == 'posix':
            backup_dir = os.path.dirname(backup_file_path)
            subprocess.call(['xdg-open', backup_dir])

    def open_windows_monitoring_test(self):
        dialog = WindowMonitoringDialog(self, self.dark_mode)
        dialog.exec()

    def open_log_folder_clicked(self):
        from utils import get_app_data_dir
        log_folder = get_app_data_dir()

        if not os.path.exists(log_folder):
            QtWidgets.QMessageBox.warning(self, "Folder not found", f"Log folder doesn't exist:\n{log_folder}")
            return

        if platform.system() == 'Darwin':
            subprocess.call(['open', log_folder])
        elif platform.system() == 'Windows':
            subprocess.run(['explorer', log_folder])
        elif os.name == 'posix':
            subprocess.call(['xdg-open', log_folder])

    def test_jtdx_log_qso_window(self):        
        controller = WindowController()
        result = controller.find_and_click_jtdx_log_qso()
        WindowController.show_test_result_dialog(self, result)

    def load_params(self):
        local_ip_address = get_local_ip_address()

        freq_range_mode = self.params.get("freq_range_mode", MODE_NORMAL)

        if freq_range_mode == "Normal":
            self.radio_normal.setChecked(True)
        elif freq_range_mode == "Hound":
            self.radio_foxhound.setChecked(True)
        elif freq_range_mode == "SuperFox":
            self.radio_superfox.setChecked(True)
        elif freq_range_mode == "Custom":
            self.radio_custom.setChecked(True)
        else:
            self.radio_normal.setChecked(True)

        # Load frequency values
        min_freq = self.params.get("min_freq", FREQ_MINIMUM)
        max_freq = self.params.get("max_freq", FREQ_MAXIMUM)

        # Load the saved custom frequency values (separate from current min/max)
        self.custom_min_freq_value = self.params.get("custom_min_freq", FREQ_MINIMUM)
        self.custom_max_freq_value = self.params.get("custom_max_freq", FREQ_MAXIMUM)

        # Temporarily disconnect signals to avoid triggering on_frequency_changed during load
        self.min_freq.valueChanged.disconnect(self.on_frequency_changed)
        self.max_freq.valueChanged.disconnect(self.on_frequency_changed)

        self.min_freq.setValue(min_freq)
        self.max_freq.setValue(max_freq)

        # Reconnect signals
        self.min_freq.valueChanged.connect(self.on_frequency_changed)
        self.max_freq.valueChanged.connect(self.on_frequency_changed)

        # Always update custom table display with loaded custom values
        self.update_custom_table_display()

        # Highlight the currently selected row in the table
        self.highlight_selected_mode_row()

        self.primary_udp_server_address.setText(
            self.params.get('primary_udp_server_address') or local_ip_address
        )
        self.primary_udp_server_port.setText(
            str(self.params.get('primary_udp_server_port') or DEFAULT_UDP_PORT)
        )
        self.enable_auto_start_monitoring.setChecked(
            self.params.get('enable_auto_start_monitoring', DEFAULT_AUTO_START_MONITORING)
        )
        self.secondary_udp_server_address.setText(
            self.params.get('secondary_udp_server_address') or local_ip_address
        )
        self.secondary_udp_server_port.setText(
            str(self.params.get('secondary_udp_server_port') or DEFAULT_UDP_PORT)
        )
        self.enable_secondary_udp_server.setChecked(
            self.params.get('enable_secondary_udp_server', DEFAULT_SECONDARY_UDP_SERVER)
        )
        self.logging_udp_server_address.setText(
            self.params.get('logging_udp_server_address') or local_ip_address
        )
        self.logging_udp_server_port.setText(
            str(self.params.get('logging_udp_server_port') or DEFAULT_UDP_PORT)
        )
        self.enable_logging_udp_server.setChecked(
            self.params.get('enable_logging_udp_server', DEFAULT_SECONDARY_UDP_SERVER)
        )
        self.enable_sending_reply.setChecked(
            self.params.get('enable_sending_reply', DEFAULT_SENDING_REPLY)
        )
        self.enable_polite_reply.setChecked(
            self.params.get('enable_polite_reply', DEFAULT_POLITE_REPLY)
        )
        self.enable_gap_finder.setChecked(
            self.params.get('enable_gap_finder', DEFAULT_GAP_FINDER)
        )
        self.enable_watchdog.setChecked(
            self.params.get('enable_watchdog', DEFAULT_WATCHDOG)
        )
        self.watchdog_number_of_attempts.setText(
            str(self.params.get('watchdog_number_of_attempts', DEFAULT_WATCHDOG_NUMBER_OF_ATTEMPTS))
        )
        self.watchdog_retry_time.setText(
            str(self.params.get('watchdog_retry_time', DEFAULT_WATCHDOG_RETRY_TIME))
        )
        self.enable_jtdx_click_log_qso.setChecked(
            self.params.get('enable_jtdx_click_log_qso', DEFAULT_JTDX_CLICK_PROMPT_LOG_QSO)
        )
        delay_value = self.params.get('jtdx_click_delay', DEFAULT_JTDX_CLICK_DELAY)
        self.jtdx_click_delay_slider.setValue(delay_value)
        self.jtdx_click_delay_value_label.setText(f"{delay_value} s")

        # PstRotatorAz antenna rotator
        self.pstrotator_host.setText(
            str(self.params.get('pstrotator_host', DEFAULT_PSTROTATOR_HOST))
        )
        self.pstrotator_port.setText(
            str(self.params.get('pstrotator_port', DEFAULT_PSTROTATOR_PORT))
        )
        self.enable_pstrotator_wanted.setChecked(
            self.params.get('enable_pstrotator_wanted', DEFAULT_ENABLE_PSTROTATOR_WANTED)
        )
        self.pstrotator_threshold.setValue(
            self.params.get('pstrotator_threshold', DEFAULT_PSTROTATOR_THRESHOLD)
        )
        self.enable_pstrotator_park.setChecked(
            self.params.get('enable_pstrotator_park', DEFAULT_ENABLE_PSTROTATOR_PARK)
        )
        self.pstrotator_park_delay.setValue(
            self.params.get('pstrotator_park_delay', DEFAULT_PSTROTATOR_PARK_DELAY)
        )
        self.update_pstrotator_park_enabled()
        self.enable_pstrotator_schedule.setChecked(
            self.params.get('enable_pstrotator_schedule', DEFAULT_ENABLE_PSTROTATOR_SCHEDULE)
        )
        for entry in self.params.get('pstrotator_schedule', []):
            try:
                self.add_pstrotator_schedule_row(
                    int(entry.get('hour', 0)),
                    int(entry.get('minute', 0)),
                    int(entry.get('azimuth', 0))
                )
            except (AttributeError, TypeError, ValueError):
                continue
        self.update_pstrotator_schedule_enabled()

        self.enable_debug_output.setChecked(
            self.params.get('enable_debug_output', DEFAULT_DEBUG_OUTPUT)
        )
        self.enable_extra_gui_debug_output.setChecked(
            self.params.get('enable_extra_gui_debug_output', False)
        )
        self.enable_pounce_log.setChecked(
            self.params.get('enable_pounce_log', DEFAULT_POUNCE_LOG)
        )
        self.enable_log_packet_data.setChecked(
            self.params.get('enable_log_packet_data', DEFAULT_LOG_PACKET_DATA)
        )
        self.enable_log_all_valid_contact.setChecked(
            self.params.get('enable_log_all_valid_contact', True)
        )
        self.enable_reply_to_valid_callsign.setChecked(
            self.params.get('enable_reply_to_valid_callsign', True)
        )
        self.enable_reply_to_valid_direction.setChecked(
            self.params.get('enable_reply_to_valid_direction', True)
        )
        self.enable_reply_to_lotw_only.setChecked(
            self.params.get('enable_reply_to_lotw_only', True)
        )
        self.enable_grid_reply_new_grid.setChecked(
            self.params.get('enable_grid_reply_new_grid', False)
        )
        self.enable_grid_reply_unconfirmed.setChecked(
            self.params.get('enable_grid_reply_unconfirmed', False)
        )
        self.enable_dxcc_reply_unconfirmed.setChecked(
            self.params.get('enable_dxcc_reply_unconfirmed', False)
        )
        self.delay_between_sound_for_monitored.setText(
            str(self.params.get('delay_between_sound_for_monitored', DEFAULT_DELAY_BETWEEN_SOUND))
        )
        self.enable_sound_wanted_callsigns.setChecked(
            self.params.get('enable_sound_wanted_callsigns', True)
        )
        self.enable_sound_directed_my_callsign.setChecked(
            self.params.get('enable_sound_directed_my_callsign', True)
        )
        self.enable_sound_monitored_callsigns.setChecked(
            self.params.get('enable_sound_monitored_callsigns', True)
        )
        self.show_backup_file_path.setText(
            self.params.get('adif_worked_backup_file_path', ADIF_WORKED_CALLSIGNS_FILE)
        )

        # Load Club Log settings
        self.enable_club_log_synch.setChecked(
            self.params.get('enable_club_log_synch', False)
        )
        self.club_log_email.setText(
            self.params.get('club_log_email', '')
        )
        self.club_log_password.setText(
            self.params.get('club_log_password', '')
        )
        self.club_log_callsign.setText(
            self.params.get('club_log_callsign', '')
        )
        self.club_log_api_key.setText(
            self.params.get('club_log_api_key', '')
        )

        # Load LoTW Upload settings
        self.enable_lotw_upload.setChecked(
            self.params.get('enable_lotw_upload', False)
        )
        self.lotw_username.setText(
            self.params.get('lotw_username', '')
        )
        self.lotw_password.setText(
            self.params.get('lotw_password', '')
        )
        self.lotw_location.setText(
            self.params.get('lotw_location', '')
        )
        self.lotw_signing_password.setText(
            self.params.get('lotw_signing_password', '')
        )
        self.tqsl_path.setText(
            self.params.get('tqsl_path', '')
        )
        self.tqsl_dir.setText(
            self.params.get('tqsl_dir', '')
        )

        # Load LoTW QSO since date
        lotw_qso_since_str = self.params.get('lotw_qso_since_date', '')
        if lotw_qso_since_str:
            try:
                from datetime import datetime
                lotw_qso_since = datetime.strptime(lotw_qso_since_str, '%Y-%m-%d %H:%M:%S')
                self.lotw_qso_since_date.setDateTime(lotw_qso_since)
            except:
                pass  # Keep default value if parsing fails

        self.lotw_download_interval.setValue(
            self.params.get('lotw_download_interval', 10)
        )

        # Load ADIF files (support both single file and multiple files for backward compatibility)
        selected_files = self.params.get('adif_file_paths')
        if selected_files is None:
            # Backward compatibility - check for single file only if new parameter doesn't exist
            single_file = self.params.get('adif_file_path', None)
            if single_file:
                selected_files = [single_file]
            else:
                selected_files = []
        # If selected_files is an empty list [], respect that choice (user cleared all files)

        # Load the files into the UI
        self.selected_adif_files = []
        for file_path in selected_files:
            if file_path and os.path.exists(file_path):
                self.selected_adif_files.append(file_path)
                self.add_file_to_list(file_path)

        if self.selected_adif_files:
            self.adif_wkb4_group.setVisible(True)
            reply_mode = self.params.get('worked_before_preference', WKB4_REPLY_MODE_ALWAYS)
            if reply_mode == WKB4_REPLY_MODE_ALWAYS:
                self.radio_reply_always.setChecked(True)
            elif reply_mode == WKB4_REPLY_MODE_CURRENT_YEAR:
                self.radio_reply_current_year.setChecked(True)
            elif reply_mode == WKB4_REPLY_MODE_NEVER:
                self.radio_reply_never.setChecked(True)
            else:
                self.radio_reply_always.setChecked(True)
        else:
            self.adif_wkb4_group.setVisible(False)

        max_reply_attempts = self.params.get('max_reply_attempts_to_callsign', DEFAULT_REPLY_ATTEMPTS)

        index = self.max_reply_attempts_combo.findText(str(max_reply_attempts))
        if index != -1:
            self.max_reply_attempts_combo.setCurrentIndex(index)
        else:
            self.max_reply_attempts_combo.setCurrentIndex(0)

        max_waiting_delay = self.params.get('max_waiting_delay', DEFAULT_MAX_WAITING_DELAY)
        if isinstance(max_waiting_delay, int):
            max_waiting_delay = str(max_waiting_delay)
        if max_waiting_delay in [self.max_waiting_delay_combo.itemText(i) for i in range(self.max_waiting_delay_combo.count())]:
            self.max_waiting_delay_combo.setCurrentText(max_waiting_delay)
        else:
            self.max_waiting_delay_combo.setCurrentText(str(DEFAULT_MAX_WAITING_DELAY))

        minimum_report = self.params.get('minimum_report_for_reply', DEFAULT_MINIMUM_REPORT)
        minimum_report_index = 10 - minimum_report
        if 0 <= minimum_report_index < self.minimum_report_combo.count():
            self.minimum_report_combo.setCurrentIndex(minimum_report_index)
        else:
            self.minimum_report_combo.setCurrentIndex(10 - DEFAULT_MINIMUM_REPORT)

        self.marathon_preference = self.params.get('marathon_preference', {})

        if isinstance(self.marathon_preference, bool):
            self.marathon_preference = {}
        for band_name, btn in self.band_buttons.items():
            checked = self.marathon_preference.get(band_name, False)
            btn.setChecked(checked)

        self.dxcc_preference = self.params.get('dxcc_preference', {})

        if isinstance(self.dxcc_preference, bool):
            self.dxcc_preference = {}
        for band_name, btn in self.dxcc_band_buttons.items():
            checked = self.dxcc_preference.get(band_name, False)
            btn.setChecked(checked)

        self.grid_tracker_preference = self.params.get('grid_tracker_preference', {})

        if isinstance(self.grid_tracker_preference, bool):
            self.grid_tracker_preference = {}
        for band_name, btn in self.grid_tracker_band_buttons.items():
            checked = self.grid_tracker_preference.get(band_name, False)
            btn.setChecked(checked)

        self.populate_priority_list()

        # Apply theme after UI is fully initialized
        self.apply_palette(self.dark_mode)

    def apply_palette(self, dark_mode):
        self.dark_mode = dark_mode

        # Force macOS title bar appearance to match theme
        set_macos_window_appearance(self, dark_mode)

        # Update all QGroupBox widgets
        groupbox_qss = get_groupbox_qss(dark_mode)
        for groupbox in self.group_boxes:
            groupbox.setStyleSheet(groupbox_qss)

        # Update all table widgets
        table_qss = get_table_setting_qss(dark_mode)
        for table in self.table_widgets:
            table.setStyleSheet(table_qss)

    def get_result(self):
        freq_range_mode = MODE_NORMAL
        if self.radio_foxhound.isChecked():
            freq_range_mode = MODE_FOX_HOUND
        elif self.radio_superfox.isChecked():
            freq_range_mode = MODE_SUPER_FOX
        elif self.radio_custom.isChecked():
            freq_range_mode = MODE_CUSTOM

        if self.radio_reply_always.isChecked():
            worked_before_preference = WKB4_REPLY_MODE_ALWAYS
        elif self.radio_reply_current_year.isChecked():
            worked_before_preference = WKB4_REPLY_MODE_CURRENT_YEAR
        elif self.radio_reply_never.isChecked():
            worked_before_preference = WKB4_REPLY_MODE_NEVER
        else:
            worked_before_preference = WKB4_REPLY_MODE_ALWAYS

        max_reply_attempts = int(self.max_reply_attempts_combo.currentText())
        max_waiting_delay = int(self.max_waiting_delay_combo.currentText())

        # Get minimum report for reply (convert combo index back to dB value)
        minimum_report_index = self.minimum_report_combo.currentIndex()
        minimum_report_for_reply = 10 - minimum_report_index  # +10dB is index 0, so +10 - 0 = +10

        marathon_preference = {}
        for band_name, btn in self.band_buttons.items():
            marathon_preference[band_name] = btn.isChecked()

        dxcc_preference = {}
        for band_name, btn in self.dxcc_band_buttons.items():
            dxcc_preference[band_name] = btn.isChecked()

        grid_tracker_preference = {}
        for band_name, btn in self.grid_tracker_band_buttons.items():
            grid_tracker_preference[band_name] = btn.isChecked()

        pstrotator_port_text = self.pstrotator_port.text()
        pstrotator_port = int(pstrotator_port_text) if pstrotator_port_text.isdigit() else DEFAULT_PSTROTATOR_PORT

        # Get priority order - convert display names to property keys
        priority_order = []
        for i in range(self.priority_table.rowCount()):
            feature_item = self.priority_table.item(i, 1)
            if feature_item:
                display_name = feature_item.text()
                property_key = PRIORITY_LIST.get(display_name, display_name)
                priority_order.append(property_key)

        return {
            'primary_udp_server_address'                 : self.primary_udp_server_address.text(),
            'primary_udp_server_port'                    : self.primary_udp_server_port.text(),
            'enable_auto_start_monitoring'               : self.enable_auto_start_monitoring.isChecked(),
            'secondary_udp_server_address'               : self.secondary_udp_server_address.text(),
            'secondary_udp_server_port'                  : self.secondary_udp_server_port.text(),
            'enable_secondary_udp_server'                : self.enable_secondary_udp_server.isChecked(),
            'logging_udp_server_address'                 : self.logging_udp_server_address.text(),
            'logging_udp_server_port'                    : self.logging_udp_server_port.text(),
            'enable_logging_udp_server'                  : self.enable_logging_udp_server.isChecked(),
            'enable_sending_reply'                       : self.enable_sending_reply.isChecked(),
            'enable_polite_reply'                        : self.enable_polite_reply.isChecked(),
            'enable_log_all_valid_contact'               : self.enable_log_all_valid_contact.isChecked(),
            'enable_reply_to_valid_callsign'             : self.enable_reply_to_valid_callsign.isChecked(),
            'enable_reply_to_valid_direction'            : self.enable_reply_to_valid_direction.isChecked(),
            'enable_reply_to_lotw_only'                  : self.enable_reply_to_lotw_only.isChecked(),
            'max_reply_attempts_to_callsign'             : max_reply_attempts,
            'max_waiting_delay'                          : max_waiting_delay,
            'minimum_report_for_reply'                   : minimum_report_for_reply,
            'enable_gap_finder'                          : self.enable_gap_finder.isChecked(),
            'enable_watchdog'                            : self.enable_watchdog.isChecked(),
            'watchdog_number_of_attempts'                : int(self.watchdog_number_of_attempts.text()) if self.watchdog_number_of_attempts.text().isdigit() else DEFAULT_WATCHDOG_NUMBER_OF_ATTEMPTS,
            'watchdog_retry_time'                        : int(self.watchdog_retry_time.text()) if self.watchdog_retry_time.text().isdigit() else DEFAULT_WATCHDOG_RETRY_TIME,
            'enable_jtdx_click_log_qso'                  : self.enable_jtdx_click_log_qso.isChecked(),
            'jtdx_click_delay'                           : self.jtdx_click_delay_slider.value(),
            'pstrotator_host'                            : self.pstrotator_host.text() or DEFAULT_PSTROTATOR_HOST,
            'pstrotator_port'                            : pstrotator_port,
            'enable_pstrotator_wanted'                   : self.enable_pstrotator_wanted.isChecked(),
            'pstrotator_threshold'                       : self.pstrotator_threshold.value(),
            'enable_pstrotator_park'                     : self.enable_pstrotator_park.isChecked(),
            'pstrotator_park_delay'                      : self.pstrotator_park_delay.value(),
            'enable_pstrotator_schedule'                 : self.enable_pstrotator_schedule.isChecked(),
            'pstrotator_schedule'                        : self.get_pstrotator_schedule(),
            'enable_debug_output'                        : self.enable_debug_output.isChecked(),
            'enable_extra_gui_debug_output'              : self.enable_extra_gui_debug_output.isChecked(),
            'enable_pounce_log'                          : self.enable_pounce_log.isChecked(),
            'enable_log_packet_data'                     : self.enable_log_packet_data.isChecked(),
            'enable_sound_wanted_callsigns'              : self.enable_sound_wanted_callsigns.isChecked(),
            'enable_sound_directed_my_callsign'          : self.enable_sound_directed_my_callsign.isChecked(),
            'enable_sound_monitored_callsigns'           : self.enable_sound_monitored_callsigns.isChecked(),
            'delay_between_sound_for_monitored'          : self.delay_between_sound_for_monitored.text(),
            'adif_file_paths'                            : self.selected_adif_files,
            'adif_worked_backup_file_path'               : self.show_backup_file_path.text(),
            'freq_range_mode'                            : freq_range_mode,
            'min_freq'                                   : self.min_freq.value(),
            'max_freq'                                   : self.max_freq.value(),
            'custom_min_freq'                            : self.custom_min_freq_value,
            'custom_max_freq'                            : self.custom_max_freq_value,
            'worked_before_preference'                   : worked_before_preference,
            'marathon_preference'                        : marathon_preference,
            'dxcc_preference'                            : dxcc_preference,
            'enable_dxcc_reply_unconfirmed'              : self.enable_dxcc_reply_unconfirmed.isChecked(),
            'grid_tracker_preference'                    : grid_tracker_preference,
            'enable_grid_reply_new_grid'                 : self.enable_grid_reply_new_grid.isChecked(),
            'enable_grid_reply_unconfirmed'              : self.enable_grid_reply_unconfirmed.isChecked(),
            'priority_order'                             : priority_order,
            'enable_club_log_synch'                      : self.enable_club_log_synch.isChecked(),
            'club_log_email'                             : self.club_log_email.text(),
            'club_log_password'                          : self.club_log_password.text(),
            'club_log_callsign'                          : self.club_log_callsign.text(),
            'club_log_api_key'                           : self.club_log_api_key.text(),
            'enable_lotw_upload'                         : self.enable_lotw_upload.isChecked(),
            'lotw_username'                              : self.lotw_username.text(),
            'lotw_password'                              : self.lotw_password.text(),
            'lotw_location'                              : self.lotw_location.text(),
            'lotw_signing_password'                      : self.lotw_signing_password.text(),
            'lotw_qso_since_date'                        : self.lotw_qso_since_date.dateTime().toString('yyyy-MM-dd HH:mm:ss'),
            'lotw_download_interval'                     : self.lotw_download_interval.value(),
            'tqsl_path'                                  : self.tqsl_path.text(),
            'tqsl_dir'                                   : self.tqsl_dir.text()
        }
