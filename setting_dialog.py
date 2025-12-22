# setting_dialog

import platform
import subprocess
import os
import sys
import re

from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import QFileDialog, QTableWidgetItem
from PyQt6.QtCore import Qt

from custom_button import CustomButton
from priority_table import PriorityTableWidget
from adif_summary_dialog import AdifSummaryDialog
from lotw_manager import LoTWManager
from clublog import ClubLogUploader

from datetime import datetime

from utils import get_local_ip_address, get_log_filename
from utils import parse_adif
from utils import AMATEUR_BANDS, ADIF_FIELD_RE

from style import get_setting_qss, get_table_setting_qss, get_odd_color, get_groupbox_qss
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
    DEFAULT_WATCHDOG_BYPASS,
    DEFAULT_DEBUG_OUTPUT,
    DEFAULT_POUNCE_LOG,
    DEFAULT_LOG_PACKET_DATA,
    DEFAULT_REPLY_ATTEMPTS,
    DEFAULT_DELAY_BETWEEN_SOUND,
    DEFAULT_MAX_WAITING_DELAY,
    DEFAULT_MINIMUM_REPORT,
    # Fonts
    CUSTOM_FONT,
    CUSTOM_FONT_SMALL,
    # ADIF
    ADIF_WORKED_CALLSIGNS_FILE,
    CLUB_LOG_CACHE_FILE,
    CLUB_LOG_API_KEY
)

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, params=None, dark_mode=False):
        super().__init__(parent)
        self.setWindowTitle("Settings")

        self.params = params or {}
        self.dark_mode = dark_mode

        # Collections for widgets that need theme updates
        self.notice_labels = []
        self.group_boxes = []
        self.table_widgets = []

        self.marathon_preference     = self.params.get('marathon_preference', {})
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
            "Server",
            "General Settings",
            "Offset Updater",
            "Sound Alerts",
            "Logbook of The World",
            "DX Marathon",
            "Grid Tracker",
            "Priority Manager",
            "Logbook Analysis",
            "Worked before",
            "Club Log",
            "Logbook Backup",
            "Debugging"
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
        offset_page       = QtWidgets.QWidget()
        sound_page        = QtWidgets.QWidget()
        lotw_page         = QtWidgets.QWidget()
        marathon_page     = QtWidgets.QWidget()
        grid_tracker_page = QtWidgets.QWidget()
        priority_page     = QtWidgets.QWidget()
        log_analysis_page = QtWidgets.QWidget()
        worked_b4_page    = QtWidgets.QWidget()
        club_log_page     = QtWidgets.QWidget()
        backup_page       = QtWidgets.QWidget()
        debugging_page    = QtWidgets.QWidget()
        debugging_page.setMinimumHeight(250)

        self.stacked_widget.addWidget(server_page)
        self.stacked_widget.addWidget(general_page)
        self.stacked_widget.addWidget(offset_page)
        self.stacked_widget.addWidget(sound_page)
        self.stacked_widget.addWidget(lotw_page)
        self.stacked_widget.addWidget(marathon_page)
        self.stacked_widget.addWidget(grid_tracker_page)
        self.stacked_widget.addWidget(priority_page)
        self.stacked_widget.addWidget(log_analysis_page)
        self.stacked_widget.addWidget(worked_b4_page)
        self.stacked_widget.addWidget(club_log_page)
        self.stacked_widget.addWidget(backup_page)
        self.stacked_widget.addWidget(debugging_page)
        
        server_layout        = QtWidgets.QVBoxLayout(server_page)
        general_layout       = QtWidgets.QVBoxLayout(general_page)
        offset_layout        = QtWidgets.QVBoxLayout(offset_page)
        sound_layout         = QtWidgets.QVBoxLayout(sound_page)
        priority_layout      = QtWidgets.QVBoxLayout(priority_page)
        lotw_layout          = QtWidgets.QVBoxLayout(lotw_page)
        marathon_layout      = QtWidgets.QVBoxLayout(marathon_page)
        grid_tracker_layout  = QtWidgets.QVBoxLayout(grid_tracker_page)
        log_analysis_layout  = QtWidgets.QVBoxLayout(log_analysis_page)
        worked_b4_layout     = QtWidgets.QVBoxLayout(worked_b4_page)
        club_log_layout      = QtWidgets.QVBoxLayout(club_log_page)
        backup_layout        = QtWidgets.QVBoxLayout(backup_page)
        debugging_layout     = QtWidgets.QVBoxLayout(debugging_page)
        
        self.menu_list.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)
        self.menu_list.setCurrentRow(0)  # Select first item by default
        
        self.setMinimumWidth(700)
        self.resize(700, 700)
        
        """
            Server Settings
        """
        jtdx_notice_text = (
            "<p>For JTDX users, you have to disable automatic logging of QSO (Make sure <u>Settings > Reporting > Logging > Enable automatic logging of QSO</u> is unchecked).</p><p>You might also need to accept UDP Reply messages from any messages (<u>Misc Menu > Accept UDP Reply Messages > any messages</u>).</p>"
        )
        jtdx_notice_label = QtWidgets.QLabel(jtdx_notice_text)
        jtdx_notice_label.setWordWrap(True)
        jtdx_notice_label.setFont(CUSTOM_FONT_SMALL)
        jtdx_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        jtdx_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))

        print(f"EVEN_COLOR value: {EVEN_COLOR}")                                     
        stylesheet = get_setting_qss(EVEN_COLOR)                                     
        print(f"Generated stylesheet: {stylesheet}")                                 
        jtdx_notice_label.setStyleSheet(stylesheet)              
        
        self.notice_labels.append(jtdx_notice_label)
        jtdx_notice_label.setAutoFillBackground(True)

        primary_group = QtWidgets.QGroupBox("Main UDP instance (the one set as Primary UDP Server on JTDX)")
        self.group_boxes.append(primary_group)
        primary_group.setFont(CUSTOM_FONT_SMALL)
        primary_layout = QtWidgets.QGridLayout()

        self.primary_udp_server_address = QtWidgets.QLineEdit()
        self.primary_udp_server_address.setFont(CUSTOM_FONT)
        self.primary_udp_server_port = QtWidgets.QLineEdit()
        self.primary_udp_server_port.setFont(CUSTOM_FONT)

        self.enable_auto_start_monitoring = QtWidgets.QCheckBox("Enable auto start monitoring when program launched")
        self.enable_auto_start_monitoring.setFont(CUSTOM_FONT)
        self.enable_auto_start_monitoring.setChecked(DEFAULT_AUTO_START_MONITORING)

        udp_server_label = QtWidgets.QLabel("UDP Server:")
        udp_server_label.setFont(CUSTOM_FONT)
        primary_layout.addWidget(udp_server_label, 0, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        primary_layout.addWidget(self.primary_udp_server_address, 0, 1)
        udp_server_port_label = QtWidgets.QLabel("UDP Server port number:")
        udp_server_port_label.setFont(CUSTOM_FONT)
        primary_layout.addWidget(udp_server_port_label, 1, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        primary_layout.addWidget(self.primary_udp_server_port, 1, 1)
        primary_layout.addWidget(self.enable_auto_start_monitoring, 2, 0, 1, 2)
        primary_layout.setColumnMinimumWidth(0, 200)
        primary_layout.setColumnStretch(0, 0)

        primary_group.setLayout(primary_layout)

        secondary_group = QtWidgets.QGroupBox("Secondary UDP Server (used to forward UDP packets)")
        self.group_boxes.append(secondary_group)
        secondary_group.setFont(CUSTOM_FONT_SMALL)
        secondary_layout = QtWidgets.QGridLayout()

        self.secondary_udp_server_address = QtWidgets.QLineEdit()
        self.secondary_udp_server_address.setFont(CUSTOM_FONT)
        self.secondary_udp_server_port = QtWidgets.QLineEdit()
        self.secondary_udp_server_port.setFont(CUSTOM_FONT)

        self.enable_secondary_udp_server = QtWidgets.QCheckBox("Enable forwarding to Secondary UDP Server")
        self.enable_secondary_udp_server.setFont(CUSTOM_FONT)
        self.enable_secondary_udp_server.setChecked(DEFAULT_SECONDARY_UDP_SERVER)

        secondary_udp_server_label = QtWidgets.QLabel("UDP Server:")
        secondary_udp_server_label.setFont(CUSTOM_FONT)
        secondary_layout.addWidget(secondary_udp_server_label, 0, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        secondary_layout.addWidget(self.secondary_udp_server_address, 0, 1)
        secondary_udp_server_port_label = QtWidgets.QLabel("UDP Server port number:")
        secondary_udp_server_port_label.setFont(CUSTOM_FONT)
        secondary_layout.addWidget(secondary_udp_server_port_label, 1, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        secondary_layout.addWidget(self.secondary_udp_server_port, 1, 1)
        secondary_layout.addWidget(self.enable_secondary_udp_server, 2, 0, 1, 2)
        secondary_layout.setColumnMinimumWidth(0, 200)
        secondary_layout.setColumnStretch(0, 0)

        secondary_group.setLayout(secondary_layout)

        logging_group = QtWidgets.QGroupBox("UDP instance for external logging program (e.g. Logger32, RUMlogNG)")
        self.group_boxes.append(logging_group)
        logging_group.setFont(CUSTOM_FONT_SMALL)
        logging_layout = QtWidgets.QGridLayout()

        self.logging_udp_server_address = QtWidgets.QLineEdit()
        self.logging_udp_server_address.setFont(CUSTOM_FONT)
        self.logging_udp_server_port = QtWidgets.QLineEdit()
        self.logging_udp_server_port.setFont(CUSTOM_FONT)

        self.enable_logging_udp_server = QtWidgets.QCheckBox("Enable sending QSO data for logging program")
        self.enable_logging_udp_server.setFont(CUSTOM_FONT)
        self.enable_logging_udp_server.setChecked(DEFAULT_SECONDARY_UDP_SERVER)

        logging_udp_server_label = QtWidgets.QLabel("UDP Server:")
        logging_udp_server_label.setFont(CUSTOM_FONT)
        logging_layout.addWidget(logging_udp_server_label, 0, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        logging_layout.addWidget(self.logging_udp_server_address, 0, 1)
        logging_udp_server_port_label = QtWidgets.QLabel("UDP Server port number:")
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
        general_notice_text = (
            f"<p>{GUI_LABEL_NAME} won't trigger a reply unless you enable <u>Enable reply</u> or <u>Enable polite reply</u>.</p><p>If you disable these settings, {GUI_LABEL_NAME} will still run as a monitoring tool with different visual or sound alerts depending on your preference.</p><p>If you enable them, this program will double-click on any of the lines of decoded text in the Band Activity window of your WSJT-X/JTDX instance which match with your preferences.</p>"
        )
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
        offset_notice_text = (
            f"<p>The frequency offset updater helps to find a free frequency offset from nominal (DF).</p><p>Select one of the pre-defined  operating modes from <u>Normal</u>, <u>Fox/Hound</u>, or <u>SuperFox</u>.</p><p>You can also set your own custom frequency range.</p>"
        )
        offset_notice_label = QtWidgets.QLabel(offset_notice_text)
        offset_notice_label.setWordWrap(True)
        offset_notice_label.setFont(CUSTOM_FONT_SMALL)
        offset_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        offset_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(offset_notice_label)
        offset_notice_label.setAutoFillBackground(True)

        offset_settings_group = QtWidgets.QGroupBox("Frequency Offset Settings")
        self.group_boxes.append(offset_settings_group)
        offset_settings_group.setFont(CUSTOM_FONT_SMALL)
        
        offset_settings_widget = QtWidgets.QWidget()
        offset_settings_layout = QtWidgets.QGridLayout(offset_settings_widget)
        offset_settings_layout.setVerticalSpacing(15)

        self.enable_gap_finder = QtWidgets.QCheckBox("Enable frequencies offset updater")
        self.enable_gap_finder.setFont(CUSTOM_FONT)
        self.enable_gap_finder.setChecked(DEFAULT_GAP_FINDER)

        offset_settings_layout.addWidget(self.enable_gap_finder, 0, 0, 1, 2)

        offset_settings_group.setLayout(QtWidgets.QVBoxLayout())
        offset_settings_group.layout().setContentsMargins(0, 0, 0, 0)
        offset_settings_group.layout().addWidget(offset_settings_widget)

        general_settings_group = QtWidgets.QGroupBox(f"General {GUI_LABEL_NAME} Settings")
        self.group_boxes.append(general_settings_group)
        general_settings_group.setFont(CUSTOM_FONT_SMALL)
        
        general_settings_widget = QtWidgets.QWidget()
        general_settings_layout = QtWidgets.QGridLayout(general_settings_widget)
        general_settings_layout.setVerticalSpacing(15)
        
        self.enable_sending_reply = QtWidgets.QCheckBox("Enable reply")
        self.enable_sending_reply.setFont(CUSTOM_FONT)
        self.enable_sending_reply.setChecked(DEFAULT_SENDING_REPLY)
        
        self.enable_polite_reply = QtWidgets.QCheckBox("Enable polite reply")
        self.enable_polite_reply.setFont(CUSTOM_FONT)
        self.enable_polite_reply.setChecked(DEFAULT_POLITE_REPLY)
        self.enable_polite_reply.toggled.connect(self.populate_priority_list)
        

        self.enable_watchdog_bypass = QtWidgets.QCheckBox("Enable watchdog bypass")
        self.enable_watchdog_bypass.setFont(CUSTOM_FONT)
        self.enable_watchdog_bypass.setChecked(DEFAULT_WATCHDOG_BYPASS)

        self.enable_log_all_valid_contact = QtWidgets.QCheckBox("Log all valid contacts (not only from Wanted)")
        self.enable_log_all_valid_contact.setFont(CUSTOM_FONT)
        self.enable_log_all_valid_contact.setChecked(True)

        self.enable_reply_to_valid_callsign = QtWidgets.QCheckBox("Ignore callsign if prefix is invalid")
        self.enable_reply_to_valid_callsign.setFont(CUSTOM_FONT)
        self.enable_reply_to_valid_callsign.setChecked(True)

        self.enable_reply_to_valid_direction = QtWidgets.QCheckBox("Ignore callsign if it targets another continent")
        self.enable_reply_to_valid_direction.setFont(CUSTOM_FONT)
        self.enable_reply_to_valid_direction.setChecked(True)

        general_settings_layout.addWidget(self.enable_sending_reply, 0, 0, 1, 2)
        general_settings_layout.addWidget(self.enable_polite_reply, 1, 0, 1, 2)
        general_settings_layout.addWidget(self.enable_watchdog_bypass, 2, 0, 1, 2)
        general_settings_layout.addWidget(self.enable_log_all_valid_contact, 3, 0, 1, 2)
        general_settings_layout.addWidget(self.enable_reply_to_valid_callsign, 4, 0, 1, 2)
        general_settings_layout.addWidget(self.enable_reply_to_valid_direction, 5, 0, 1, 2)

        general_settings_group.setLayout(QtWidgets.QVBoxLayout())
        general_settings_group.layout().setContentsMargins(0, 0, 0, 0)
        general_settings_group.layout().addWidget(general_settings_widget)


        self.freq_range_type_group = QtWidgets.QGroupBox("Select range of frequency being used for offset updater")
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

        headers = ["Min Frequency", "Max Frequency", "Mode"]
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
        self.custom_range_group = QtWidgets.QGroupBox("Custom frequency range")
        self.group_boxes.append(self.custom_range_group)
        self.custom_range_group.setFont(CUSTOM_FONT_SMALL)
        
        custom_range_widget = QtWidgets.QWidget()
        custom_range_layout = QtWidgets.QHBoxLayout(custom_range_widget)
        custom_range_layout.setContentsMargins(0, 5, 0, 0)
        
        # Labels and input fields for frequency range
        min_label = QtWidgets.QLabel("Min Freq (Hz):")
        min_label.setFont(CUSTOM_FONT_SMALL)
        self.min_freq = QtWidgets.QSpinBox()
        self.min_freq.setRange(0, 10000)
        self.min_freq.setValue(FREQ_MINIMUM)
        self.min_freq.setSuffix("Hz")
        self.min_freq.setFont(CUSTOM_FONT_SMALL)
        
        max_label = QtWidgets.QLabel("Max Freq (Hz):")
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

        minimum_report_text = (
            f"<p>{GUI_LABEL_NAME} won't trigger reply unless decoded message reach a minimal signal report.</p>"
        )
        minimum_report_notice = QtWidgets.QLabel(minimum_report_text)
        minimum_report_notice.setWordWrap(True)
        minimum_report_notice.setFont(CUSTOM_FONT_SMALL)
        minimum_report_notice.setTextFormat(QtCore.Qt.TextFormat.RichText)
        minimum_report_notice.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(minimum_report_notice)
        minimum_report_notice.setAutoFillBackground(True)

        minimum_report_group = QtWidgets.QGroupBox("Minimum dB signal for reply (FT8/FT4 Mode only)")
        self.group_boxes.append(minimum_report_group)
        minimum_report_group.setFont(CUSTOM_FONT_SMALL)
        minimum_report_layout = QtWidgets.QHBoxLayout()
        
        minimum_report_label = QtWidgets.QLabel("Minimum report")
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
            Priority Manager Group
        """
        self.priority_manager_group = QtWidgets.QGroupBox("Priority Manager")
        self.group_boxes.append(self.priority_manager_group)
        self.priority_manager_group.setFont(CUSTOM_FONT_SMALL)
        priority_group_layout = QtWidgets.QVBoxLayout()
        
        priority_notice_text = (
            "<p>Set the priority order for reply decisions when decoding several potential callsigns for a same period.</p><p>Drag and drop blocks to reorder them. The first row has the highest priority, and the last row refers to the lowest priority.</p>"
        )
        priority_notice_label = QtWidgets.QLabel(priority_notice_text)
        priority_notice_label.setWordWrap(True)
        priority_notice_label.setFont(CUSTOM_FONT_SMALL)
        priority_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        priority_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(priority_notice_label)
        
        max_reply_text = (
            "<p>When several Wanted callsigns are detected during the same sequence and if program starts to reply to one specific callsign, it has a limited <u>number of attempts</u> before moving on to the next detected callsign.</p><p>The maximum <u>waiting delay</u> is used to halt TX and stop calling a station that the program has started to call but is no longer decoded. However, if another Wanted callsign is detected, this setting has no effect.</p>"
        )
        max_reply_notice_label = QtWidgets.QLabel(max_reply_text)
        max_reply_notice_label.setWordWrap(True)
        max_reply_notice_label.setFont(CUSTOM_FONT_SMALL)
        max_reply_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        max_reply_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(max_reply_notice_label)
        max_reply_notice_label.setAutoFillBackground(True)

        self.max_reply_group = QtWidgets.QGroupBox(f"Sequencing")
        self.group_boxes.append(self.max_reply_group)
        self.max_reply_group.setFont(CUSTOM_FONT_SMALL)

        max_reply_layout = QtWidgets.QVBoxLayout()

        max_reply_label = QtWidgets.QLabel("Maximum number of attempts")
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
        times_label = QtWidgets.QLabel("times")
        times_label.setFont(CUSTOM_FONT)
        reply_attempts_layout.addWidget(times_label)

        max_reply_layout.addLayout(reply_attempts_layout)

        max_waiting_delay_label = QtWidgets.QLabel("Maximum waiting delay")
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
        minutes_label = QtWidgets.QLabel("minutes")
        minutes_label.setFont(CUSTOM_FONT)
        waiting_delay_layout.addWidget(minutes_label)

        max_reply_layout.addLayout(waiting_delay_layout)

        max_reply_layout.addStretch()

        self.max_reply_group.setLayout(max_reply_layout)
        self.max_reply_group.layout().setSpacing(5)

        self.priority_table = PriorityTableWidget()
        self.priority_table.setColumnCount(2)
        self.priority_table.setShowGrid(False)
        self.priority_table.setHorizontalHeaderLabels(["Priority", "Reply to"])
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
            lotw_cache_text = f"LoTW Cache Status: {entry_count: } callsigns<br />Last updated: {last_update}"
        else:
            lotw_cache_text = "No LoTW data available yet"
        
        lotw_notice_text = f"<p>LoTW (Logbook of The World®) is ARRL's online QSO confirmation system.</p><p>Enable it to limit sound alerts and only respond to callsigns who use LoTW especially <u>if you use a Wildcard in your Wanted callsigns</u>.</p><p>{GUI_LABEL_NAME} will always respond to the callsign if it exactly matches a wanted callsign that is not LoTW.</p><p><u>This setting is ignored for Marathon</u> but is used for GridTracker and if you make use of Wildcard.</p>"
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

        lotw_settings_group = QtWidgets.QGroupBox("LoTW Settings")
        self.group_boxes.append(lotw_settings_group)
        lotw_settings_group.setFont(CUSTOM_FONT_SMALL)
        
        lotw_settings_widget = QtWidgets.QWidget()
        lotw_settings_layout = QtWidgets.QGridLayout(lotw_settings_widget)
        
        self.enable_reply_to_lotw_only = QtWidgets.QCheckBox("Enable reply only for callsigns that use LoTW")
        self.enable_reply_to_lotw_only.setFont(CUSTOM_FONT)
        self.enable_reply_to_lotw_only.setChecked(False)
        
        lotw_settings_layout.addWidget(self.enable_reply_to_lotw_only, 0, 0, 1, 2)
        
        lotw_settings_group.setLayout(QtWidgets.QVBoxLayout())
        lotw_settings_group.layout().setContentsMargins(0, 0, 0, 0)
        lotw_settings_group.layout().addWidget(lotw_settings_widget)
        
        lotw_layout.addWidget(lotw_notice_label)
        lotw_layout.addWidget(lotw_cache_info)        
        lotw_layout.addWidget(lotw_settings_group)
        lotw_layout.addStretch()
        
        """
            Sound Settings
        """
        sound_notice_text = (
            "<p>You can enable or disable the sounds as per your requirement. You can even set a delay between each sound triggered by a message where a monitored callsign has been found. This mainly helps you to be notified when the band opens or when you have a callsign on the air that you want to monitor.</p><p>Monitored callsigns will never get reply from this program. Only <u>Wanted callsigns will get a reply</u>.</p>"
        )

        sound_notice_label = QtWidgets.QLabel(sound_notice_text)
        sound_notice_label.setWordWrap(True)
        sound_notice_label.setFont(CUSTOM_FONT_SMALL)
        sound_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        sound_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(sound_notice_label)
        sound_notice_label.setAutoFillBackground(True)

        sound_settings_group = QtWidgets.QGroupBox("Sound Alert Settings")
        self.group_boxes.append(sound_settings_group)
        sound_settings_group.setFont(CUSTOM_FONT_SMALL)
        sound_settings_layout = QtWidgets.QGridLayout()

        play_sound_notice_label = QtWidgets.QLabel("Play Sounds when:")
        play_sound_notice_label.setFont(CUSTOM_FONT)
        play_sound_notice_label.setFont(CUSTOM_FONT_SMALL)

        self.enable_sound_wanted_callsigns = QtWidgets.QCheckBox("Message from any Wanted Callsign")
        self.enable_sound_wanted_callsigns.setFont(CUSTOM_FONT)
        self.enable_sound_wanted_callsigns.setChecked(True)

        self.enable_sound_directed_my_callsign = QtWidgets.QCheckBox("Message directed to my Callsign")
        self.enable_sound_directed_my_callsign.setFont(CUSTOM_FONT)
        self.enable_sound_directed_my_callsign.setChecked(True)

        self.enable_sound_monitored_callsigns = QtWidgets.QCheckBox("Message from any Monitored Callsign")
        self.enable_sound_monitored_callsigns.setFont(CUSTOM_FONT)
        self.enable_sound_monitored_callsigns.setChecked(True)

        self.delay_between_sound_for_monitored = QtWidgets.QLineEdit()
        self.delay_between_sound_for_monitored.setFixedWidth(50)
        self.delay_between_sound_for_monitored.setFont(CUSTOM_FONT)

        delay_layout = QtWidgets.QHBoxLayout()
        delay_layout.addWidget(self.delay_between_sound_for_monitored)
        seconds_label = QtWidgets.QLabel("seconds")
        seconds_label.setFont(CUSTOM_FONT)
        delay_layout.addWidget(seconds_label)
        delay_layout.addStretch()

        sound_settings_layout.addWidget(play_sound_notice_label, 0, 0, 1, 2)
        sound_settings_layout.addWidget(self.enable_sound_wanted_callsigns, 1, 0, 1, 2)
        sound_settings_layout.addWidget(self.enable_sound_directed_my_callsign, 2, 0, 1, 2)
        sound_settings_layout.addWidget(self.enable_sound_monitored_callsigns, 3, 0, 1, 2)
        delay_between_label = QtWidgets.QLabel("Delay between each monitored callsigns detected:")
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
        log_analysis_notice_text = (
            f"<p>While using {GUI_LABEL_NAME}, you can let this program analyze your working ADIF files from WSJT-x or JTDX.<p><p>{GUI_LABEL_NAME} won't update your ADIF files. Still, it can read, parse and analyse them. You can set several ADIF files, for exemple your main WSJT-X ADIF and a full export of your log.</p>"
        )

        log_analysis_notice_label = QtWidgets.QLabel(log_analysis_notice_text)
        log_analysis_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(log_analysis_notice_label)
        log_analysis_notice_label.setWordWrap(True)
        log_analysis_notice_label.setFont(CUSTOM_FONT_SMALL)
        log_analysis_notice_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        file_selection_group = QtWidgets.QGroupBox("ADIF Files for log analysis")
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
        self.add_file_button = QtWidgets.QPushButton("Select new ADIF File for analysis")
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

        self.adif_files_table.setHorizontalHeaderLabels(["", "ADIF Files for analysis"])                
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
        self.summary_file_button = QtWidgets.QPushButton("Summary")
        self.summary_file_button.setFont(CUSTOM_FONT)
        self.summary_file_button.setFixedWidth(80)
        self.summary_file_button.clicked.connect(self.show_selected_file_summary)
        self.summary_file_button.setEnabled(False)  # Initially disabled
        
        # Clear button
        self.clear_file_button = QtWidgets.QPushButton("Clear")
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
        worked_b4_notice_text = (
            f"<p>{GUI_LABEL_NAME}, will show the year of the Worked B4 stations you decode.<p><p>You can select from this panel, how the program will behave when it decodes some already worked callsign on the same band.</p>"
        )

        worked_b4_notice_label = QtWidgets.QLabel(worked_b4_notice_text)
        worked_b4_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(worked_b4_notice_label)
        worked_b4_notice_label.setWordWrap(True)
        worked_b4_notice_label.setFont(CUSTOM_FONT_SMALL)
        worked_b4_notice_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        self.adif_wkb4_group = QtWidgets.QGroupBox("What should we do with Worked B4?")
        self.group_boxes.append(self.adif_wkb4_group)
        self.adif_wkb4_group.setFont(CUSTOM_FONT_SMALL)
        adif_wkb4_layout = QtWidgets.QVBoxLayout()
        adif_wkb4_layout.setSpacing(10)

        self.radio_reply_always = QtWidgets.QRadioButton("Reply to any Wanted Callsign even if Worked B4")        
        self.radio_reply_current_year = QtWidgets.QRadioButton("Reply to Wanted Callsign if not Worked B4 in current year ({})".format(datetime.now().year))
        self.radio_reply_never = QtWidgets.QRadioButton("Do not reply to any Callsign Worked B4")
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
        marathon_notice_text = (
            f"<p>Marathon feature has to be used with caution.</p><p>{GUI_LABEL_NAME} will analyze your log and check for any missing entities you haven't worked on selected band. If a missing entity is decoded, {GUI_LABEL_NAME} will reply to this callsign.</p><p>Note that rules set for <u>Worked Before</u> will remain in effect.</p>"
        )
        marathon_notice_label = QtWidgets.QLabel(marathon_notice_text)
        marathon_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(marathon_notice_label)
        marathon_notice_label.setWordWrap(True)
        marathon_notice_label.setFont(CUSTOM_FONT_SMALL)
        marathon_notice_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        self.marathon_group = QtWidgets.QGroupBox("Enable Marathon for selected bands")
        self.group_boxes.append(self.marathon_group)
        self.marathon_group.setFont(CUSTOM_FONT_SMALL)
        marathon_select_layout = QtWidgets.QGridLayout()

        self.band_buttons = {}
        max_cols = 3
        row = 0
        col = 0

        for amateur_band in list(AMATEUR_BANDS.keys())[:-3]:
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
        club_log_notice_text = (
            "<p>Wait and Pounce can upload individual QSOs in real-time to Club Log.</p>"
        )

        club_log_notice_label = QtWidgets.QLabel(club_log_notice_text)
        club_log_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(club_log_notice_label)
        club_log_notice_label.setWordWrap(True)
        club_log_notice_label.setFont(CUSTOM_FONT_SMALL)
        club_log_notice_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        last_sync, total_qsos, last_callsign, last_band = ClubLogUploader.get_cache_info()
        if last_sync:
            club_log_cache_text = f"Club Log Status: {total_qsos} QSOs uploaded<br />Last upload: {last_sync}<br />Last QSO: {last_callsign} on {last_band}"
        else:
            club_log_cache_text = "No Club Log uploads yet"

        self.club_log_cache_info = QtWidgets.QLabel(club_log_cache_text)
        self.club_log_cache_info.setWordWrap(True)
        self.club_log_cache_info.setFont(CUSTOM_FONT_SMALL)
        self.club_log_cache_info.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.club_log_cache_info.setStyleSheet(get_setting_qss(ODD_COLOR))
        self.notice_labels.append(self.club_log_cache_info)
        self.club_log_cache_info.setAutoFillBackground(True)

        club_log_settings_group = QtWidgets.QGroupBox("Club Log Upload Settings")
        self.group_boxes.append(club_log_settings_group)
        club_log_settings_group.setFont(CUSTOM_FONT_SMALL)

        club_log_settings_widget = QtWidgets.QWidget()
        club_log_settings_layout = QtWidgets.QGridLayout(club_log_settings_widget)

        self.enable_club_log_synch = QtWidgets.QCheckBox("Enable real-time QSO uploads to Club Log")
        self.enable_club_log_synch.setFont(CUSTOM_FONT)
        self.enable_club_log_synch.setChecked(False)

        club_log_email_label = QtWidgets.QLabel("Club Log Email:")
        club_log_email_label.setFont(CUSTOM_FONT)
        self.club_log_email = QtWidgets.QLineEdit()
        self.club_log_email.setFont(CUSTOM_FONT)
        self.club_log_email.setPlaceholderText("Registered email address in Club Log")

        club_log_password_label = QtWidgets.QLabel("Password:")
        club_log_password_label.setFont(CUSTOM_FONT)
        self.club_log_password = QtWidgets.QLineEdit()
        self.club_log_password.setFont(CUSTOM_FONT)
        self.club_log_password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.club_log_password.setPlaceholderText("Application password")

        club_log_callsign_label = QtWidgets.QLabel("Callsign:")
        club_log_callsign_label.setFont(CUSTOM_FONT)
        self.club_log_callsign = QtWidgets.QLineEdit()
        self.club_log_callsign.setFont(CUSTOM_FONT)
        self.club_log_callsign.setPlaceholderText("Your callsign")

        club_log_settings_layout.addWidget(self.enable_club_log_synch, 0, 0, 1, 2)
        club_log_settings_layout.addWidget(club_log_email_label, 1, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        club_log_settings_layout.addWidget(self.club_log_email, 1, 1)
        club_log_settings_layout.addWidget(club_log_password_label, 2, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        club_log_settings_layout.addWidget(self.club_log_password, 2, 1)
        club_log_settings_layout.addWidget(club_log_callsign_label, 3, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        club_log_settings_layout.addWidget(self.club_log_callsign, 3, 1)

        club_log_settings_group.setLayout(QtWidgets.QVBoxLayout())
        club_log_settings_group.layout().setContentsMargins(0, 0, 0, 0)
        club_log_settings_group.layout().addWidget(club_log_settings_widget)

        club_log_layout.addWidget(club_log_notice_label)
        club_log_layout.addWidget(self.club_log_cache_info)
        club_log_layout.addWidget(club_log_settings_group)
        club_log_layout.addStretch()

        """
            Grid Tracker Settings
        """
        grid_tracker_notice_text = (
            f"<p>{GUI_LABEL_NAME} will analyze your log and check for any missing grids you haven't worked on selected band.</p><p>If a callsign with a missing grid is decoded, {GUI_LABEL_NAME} will reply to this callsign for this grid.</p>"
        )
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
        self.enable_grid_reply_new_grid = QtWidgets.QCheckBox("Enable grid tracker to reply to callsign if new grid regardless of band")
        self.enable_grid_reply_new_grid.setFont(CUSTOM_FONT_SMALL)
        self.enable_grid_reply_new_grid.setChecked(False)

        grid_tracker_per_band_notice_text = (
            f"<p>Select band for which {GUI_LABEL_NAME} will reply to callsign, if callsign is a new grid for the selected band.</p>"
        )

        grid_tracker_per_band_notice_label = QtWidgets.QLabel(grid_tracker_per_band_notice_text)
        grid_tracker_per_band_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(grid_tracker_per_band_notice_label)
        grid_tracker_per_band_notice_label.setWordWrap(True)
        grid_tracker_per_band_notice_label.setFont(CUSTOM_FONT_SMALL)
        grid_tracker_per_band_notice_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        self.grid_tracker_group = QtWidgets.QGroupBox("Select bands")
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
        self.enable_grid_reply_unconfirmed = QtWidgets.QCheckBox("Reply to callsign if grid not yet confirmed and not worked before")
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
        adif_backup_selection_group = QtWidgets.QGroupBox(f"{GUI_LABEL_NAME} Backup File")
        self.group_boxes.append(adif_backup_selection_group)
        adif_backup_selection_group.setFont(CUSTOM_FONT_SMALL)
        adif_backup_selection_group.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        working_log_notice_text = (
            f"<p>{GUI_LABEL_NAME} will write a new entry on a dedicated and specific ADIF File for each logged QSO.</p><p>This file can be used as a backup of your main logging sequence with JTDX or WSJT-x.</p><p>This log will always be analyzed even if you have an empty list of ADIF files for logbook analysis.</p>"
        )

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
            Debug Settings
        """
        debug_notice_text = (
            "<p>There is no need to enable <u>Save all received Packet</u> unless you want to study every packet data received from your WSJT-X/JTDX instance.</p><p>If issue encountered while using this program, please provide the <u>pounce.log</u> as reference.</p>"
        )
        debug_notice_label = QtWidgets.QLabel(debug_notice_text)
        debug_notice_label.setWordWrap(True)
        debug_notice_label.setFont(CUSTOM_FONT_SMALL)
        debug_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        debug_notice_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        self.notice_labels.append(debug_notice_label)
        debug_notice_label.setAutoFillBackground(True)

        log_settings_group = QtWidgets.QGroupBox("Log Settings")
        self.group_boxes.append(log_settings_group)
        log_settings_group.setFont(CUSTOM_FONT_SMALL)
        log_settings_layout = QtWidgets.QVBoxLayout()
        log_settings_layout.setSpacing(15) 

        self.enable_debug_output = QtWidgets.QCheckBox("Show debug output")
        self.enable_debug_output.setFont(CUSTOM_FONT)
        self.enable_debug_output.setChecked(DEFAULT_DEBUG_OUTPUT)

        self.enable_extra_gui_debug_output = QtWidgets.QCheckBox("Save GUI debug output (Not recommended)")
        self.enable_extra_gui_debug_output.setFont(CUSTOM_FONT)
        self.enable_extra_gui_debug_output.setChecked(False)

        self.enable_pounce_log = QtWidgets.QCheckBox(f"Save log to {get_log_filename()}")
        self.enable_pounce_log.setFont(CUSTOM_FONT)
        self.enable_pounce_log.setChecked(DEFAULT_POUNCE_LOG)

        self.enable_log_packet_data = QtWidgets.QCheckBox("Save all received Packet Data to log")
        self.enable_log_packet_data.setFont(CUSTOM_FONT)
        self.enable_log_packet_data.setChecked(DEFAULT_LOG_PACKET_DATA)

        log_settings_layout.addWidget(self.enable_pounce_log)
        log_settings_layout.addWidget(self.enable_log_packet_data)
        log_settings_layout.addWidget(self.enable_extra_gui_debug_output)
        log_settings_layout.addWidget(self.enable_debug_output)
    
        log_settings_group.setLayout(log_settings_layout)

        # Add debug settings to debugging page
        debugging_layout.addWidget(debug_notice_label)
        debugging_layout.addWidget(log_settings_group)
        debugging_layout.addStretch()
        
        self.load_params()

        self.button_box = QtWidgets.QDialogButtonBox()
        self.ok_button = CustomButton("OK")
        self.cancel_button = CustomButton("Cancel")

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

    def on_grid_tracker_band_toggled(self, button, band_name, checked):
        if checked:
            button.updateStyle(band_name, STATUS_TRX_COLOR, "#FFFFFF")
        else:
            button.resetStyle()

        self.grid_tracker_preference[band_name] = checked 

        self.populate_priority_list()            

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

            self.setFixedHeight(total_height)


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
            status_text = "<p>Backup File Status: No file selected</p>"
        else:
            status, total_entries, unique_calls, last_update, first_entry = self.get_backup_file_status(file_path)
            if status == "Ready":
                status_text = f"""
                Backup File Status: {status}
                <br />
                Total Entries: {total_entries:,}
                <br />
                Unique Callsigns: {unique_calls:,}
                <br />
                First Entry: {first_entry}
                <br />
                Last Updated: {last_update}
                """
            else:
                status_text = f"<p>Backup File Status: {status}</p>"

        self.backup_file_status_info.setText(status_text)

    def open_backup_file_dialog(self):
        dialog = QFileDialog(self, "Select ADIF Backup File")
        dialog.setNameFilter("ADIF Files (*.adif *.adi);;All Files (*)")
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
        dialog = QFileDialog(self, "Select ADIF File")
        dialog.setNameFilter("ADIF Files (*.adif *.adi);;All Files (*)")
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
                        "File Already Added",
                        f"The file '{os.path.basename(file_path)}' is already in the list."
                    )
                    return
                
                processing_time, parsed_data = parse_adif(file_path)
                if parsed_data:
                    self.selected_adif_files.append(file_path)
                    self.add_file_to_list(file_path)
                    self.adif_wkb4_group.setVisible(True)

                    summary_dialog = AdifSummaryDialog(processing_time, parsed_data['wkb4'], self)
                    summary_dialog.exec()
                else:
                    QtWidgets.QMessageBox.warning(
                        self,
                        "No Data found",
                        "Seems your file is either empty or corrupted"
                    )
        else:
            print("No file selected.")

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
                        summary_dialog = AdifSummaryDialog(processing_time, parsed_data['wkb4'], self)
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
                        f"Error parsing '{os.path.basename(file_path)}':\\n{str(e)}"
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
        self.enable_watchdog_bypass.setChecked(
            self.params.get('enable_watchdog_bypass', DEFAULT_WATCHDOG_BYPASS)
        )
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

        grid_tracker_preference = {}
        for band_name, btn in self.grid_tracker_band_buttons.items():
            grid_tracker_preference[band_name] = btn.isChecked()
            
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
            'enable_gap_finder'                           : self.enable_gap_finder.isChecked(),
            'enable_watchdog_bypass'                     : self.enable_watchdog_bypass.isChecked(),
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
            'grid_tracker_preference'                    : grid_tracker_preference,
            'enable_grid_reply_new_grid'                 : self.enable_grid_reply_new_grid.isChecked(),
            'enable_grid_reply_unconfirmed'              : self.enable_grid_reply_unconfirmed.isChecked(),
            'priority_order'                             : priority_order,
            'enable_club_log_synch'                      : self.enable_club_log_synch.isChecked(),
            'club_log_email'                             : self.club_log_email.text(),
            'club_log_password'                          : self.club_log_password.text(),
            'club_log_callsign'                          : self.club_log_callsign.text()
        }