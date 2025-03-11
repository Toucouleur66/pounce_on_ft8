# setting_dialog

import platform
import subprocess
import os
import sys

from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import QFileDialog, QTableWidgetItem

from custom_button import CustomButton
from adif_summary_dialog import AdifSummaryDialog

from datetime import datetime

from utils import get_local_ip_address, get_log_filename
from utils import parse_adif
from utils import AMATEUR_BANDS

from constants import (
    # Colors
    BG_COLOR_BLACK_ON_PURPLE,
    FG_COLOR_BLACK_ON_PURPLE,
    STATUS_TRX_COLOR,
    # Labels
    GUI_LABEL_NAME,
    # Modes
    MODE_NORMAL,
    MODE_FOX_HOUND,
    MODE_SUPER_FOX,
    WKB4_REPLY_MODE_ALWAYS,
    WKB4_REPLY_MODE_CURRENT_YEAR,
    WKB4_REPLY_MODE_NEVER,
    FREQ_MINIMUM,
    FREQ_MAXIMUM,
    FREQ_MINIMUM_FOX_HOUND,
    FREQ_MAXIMUM_SUPER_FOX,
    # UDP related
    DEFAULT_UDP_PORT,
    DEFAULT_SECONDARY_UDP_SERVER,
    DEFAULT_SENDING_REPLY,
    DEFAULT_GAP_FINDER,
    DEFAULT_WATCHDOG_BYPASS,
    DEFAULT_DEBUG_OUTPUT,
    DEFAULT_POUNCE_LOG,
    DEFAULT_LOG_PACKET_DATA,
    DEFAULT_REPLY_ATTEMPTS,
    DEFAULT_DELAY_BETWEEN_SOUND,
    DEFAULT_MAX_WAITING_DELAY,
    # Fonts
    CUSTOM_FONT_SMALL,
    SETTING_QSS,
    # ADIF
    ADIF_WORKED_CALLSIGNS_FILE
)

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, params=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")

        self.params = params or {}

        layout = QtWidgets.QVBoxLayout(self)

        self.tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(self.tab_widget)

        tab_1 = QtWidgets.QWidget()
        tab_2 = QtWidgets.QWidget()
        tab_3 = QtWidgets.QWidget()
        tab_4 = QtWidgets.QWidget()
        tab_5 = QtWidgets.QWidget()
        tab_6 = QtWidgets.QWidget()

        self.tab_widget.addTab(tab_1, "Server")
        self.tab_widget.addTab(tab_2, "General")
        self.tab_widget.addTab(tab_3, "Sound Alerts")
        self.tab_widget.addTab(tab_4, "Log Analysis")
        self.tab_widget.addTab(tab_5, "Backup")
        self.tab_widget.addTab(tab_6, "Debugging")

        tab_1_layout = QtWidgets.QVBoxLayout(tab_1)
        tab_2_layout = QtWidgets.QVBoxLayout(tab_2)
        tab_3_layout = QtWidgets.QVBoxLayout(tab_3)
        tab_4_layout = QtWidgets.QVBoxLayout(tab_4)
        tab_5_layout = QtWidgets.QVBoxLayout(tab_5)
        tab_6_layout = QtWidgets.QVBoxLayout(tab_6)
        
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
        jtdx_notice_label.setStyleSheet(SETTING_QSS)
        jtdx_notice_label.setAutoFillBackground(True)

        primary_group = QtWidgets.QGroupBox("Primary UDP Server")
        primary_layout = QtWidgets.QGridLayout()

        self.primary_udp_server_address = QtWidgets.QLineEdit()
        self.primary_udp_server_port = QtWidgets.QLineEdit()

        primary_layout.addWidget(QtWidgets.QLabel("UDP Server:"), 0, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        primary_layout.addWidget(self.primary_udp_server_address, 0, 1)
        primary_layout.addWidget(QtWidgets.QLabel("UDP Server port number:"), 1, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        primary_layout.addWidget(self.primary_udp_server_port, 1, 1)
        primary_layout.setColumnMinimumWidth(0, 200)
        primary_layout.setColumnStretch(0, 0)

        primary_group.setLayout(primary_layout)

        secondary_group = QtWidgets.QGroupBox("Second UDP Server (Send logged QSO ADIF data)")
        secondary_layout = QtWidgets.QGridLayout()

        self.secondary_udp_server_address = QtWidgets.QLineEdit()
        self.secondary_udp_server_port = QtWidgets.QLineEdit()

        self.enable_secondary_udp_server = QtWidgets.QCheckBox("Enable sending to secondary UDP server")
        self.enable_secondary_udp_server.setChecked(DEFAULT_SECONDARY_UDP_SERVER)

        secondary_layout.addWidget(QtWidgets.QLabel("UDP Server:"), 0, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        secondary_layout.addWidget(self.secondary_udp_server_address, 0, 1)
        secondary_layout.addWidget(QtWidgets.QLabel("UDP Server port number:"), 1, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        secondary_layout.addWidget(self.secondary_udp_server_port, 1, 1)
        secondary_layout.addWidget(self.enable_secondary_udp_server, 2, 0, 1, 2)
        secondary_layout.setColumnMinimumWidth(0, 200)
        secondary_layout.setColumnStretch(0, 0)

        secondary_group.setLayout(secondary_layout)

        tab_1_layout.addWidget(jtdx_notice_label)
        tab_1_layout.addWidget(primary_group)
        tab_1_layout.addWidget(secondary_group)
        tab_1_layout.addStretch() 

        """
            Main Settings
        """

        general_settings_group = QtWidgets.QGroupBox(f"General {GUI_LABEL_NAME} Settings")
        
        general_settings_widget = QtWidgets.QWidget()
        general_settings_layout = QtWidgets.QGridLayout(general_settings_widget)
        
        self.enable_sending_reply = QtWidgets.QCheckBox("Enable reply")
        self.enable_sending_reply.setChecked(DEFAULT_SENDING_REPLY)
        
        self.enable_gap_finder = QtWidgets.QCheckBox("Enable frequencies offset updater")
        self.enable_gap_finder.setChecked(DEFAULT_GAP_FINDER)

        self.enable_watchdog_bypass = QtWidgets.QCheckBox("Enable watchdog bypass")
        self.enable_watchdog_bypass.setChecked(DEFAULT_WATCHDOG_BYPASS)

        self.enable_log_all_valid_contact = QtWidgets.QCheckBox("Log all valid contacts (not only from Wanted)")
        self.enable_log_all_valid_contact.setChecked(True)

        general_settings_layout.addWidget(self.enable_sending_reply, 0, 0, 1, 2)
        general_settings_layout.addWidget(self.enable_gap_finder, 1, 0, 1, 2)
        general_settings_layout.addWidget(self.enable_watchdog_bypass, 2, 0, 1, 2)
        general_settings_layout.addWidget(self.enable_log_all_valid_contact, 3, 0, 1, 2)

        max_reply_text = (
            "<p>When several Wanted callsigns are detected during the same sequence and if program starts to reply to one specific callsign, it has a limited <u>number of attempts</u> before moving on to the next detected callsign.</p><p>The maximum <u>waiting delay</u> is used to halt TX and stop calling a station that the program has started to call but is no longer decoded. However, if another Wanted callsign is detected, this setting has no effect.</p>"
        )
        max_reply_notice_label = QtWidgets.QLabel(max_reply_text)
        max_reply_notice_label.setWordWrap(True)
        max_reply_notice_label.setFont(CUSTOM_FONT_SMALL)
        max_reply_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        max_reply_notice_label.setStyleSheet(SETTING_QSS)
        max_reply_notice_label.setAutoFillBackground(True)

        self.max_reply_group = QtWidgets.QGroupBox(f"Sequencing")

        max_reply_layout = QtWidgets.QVBoxLayout()

        max_reply_label = QtWidgets.QLabel("Maximum number of attempts for a Wanted Callsign")
        max_reply_label.setFixedWidth(400)

        self.max_reply_attemps_combo = QtWidgets.QComboBox()
        self.max_reply_attemps_combo.setEditable(False)  
        self.max_reply_attemps_combo.setMinimumWidth(100)

        self.max_reply_attemps_combo.addItems([str(i) for i in range(4, 31)])
        self.max_reply_attemps_combo.setCurrentIndex(DEFAULT_REPLY_ATTEMPTS)

        reply_attempts_layout = QtWidgets.QHBoxLayout()
        reply_attempts_layout.addWidget(max_reply_label)
        reply_attempts_layout.addWidget(self.max_reply_attemps_combo)
        reply_attempts_layout.addWidget(QtWidgets.QLabel("times"))

        max_reply_layout.addLayout(reply_attempts_layout)

        max_waiting_delay_label = QtWidgets.QLabel("Maximum waiting delay")
        max_waiting_delay_label.setFixedWidth(400)
        
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
        waiting_delay_layout.addWidget(QtWidgets.QLabel("minutes"))

        max_reply_layout.addLayout(waiting_delay_layout)

        max_reply_layout.addStretch()

        self.max_reply_group.setLayout(max_reply_layout)
        self.max_reply_group.layout().setSpacing(5)

        general_settings_group.setLayout(QtWidgets.QVBoxLayout())
        general_settings_group.layout().setContentsMargins(0, 0, 0, 0)
        general_settings_group.layout().addWidget(general_settings_widget)

        self.freq_range_type_group = QtWidgets.QGroupBox("Select range of frequency being used for offset updater")

        udp_freq_range_type_widget = QtWidgets.QWidget()
        udp_freq_range_type_layout = QtWidgets.QVBoxLayout(udp_freq_range_type_widget)

        self.radio_normal   = QtWidgets.QRadioButton()
        self.radio_foxhound = QtWidgets.QRadioButton()
        self.radio_superfox = QtWidgets.QRadioButton()

        self.freq_range_mode_var = QtWidgets.QButtonGroup()
        self.freq_range_mode_var.addButton(self.radio_normal)
        self.freq_range_mode_var.addButton(self.radio_foxhound)
        self.freq_range_mode_var.addButton(self.radio_superfox)        

        modes = [
            (self.radio_normal, MODE_NORMAL, FREQ_MINIMUM, FREQ_MAXIMUM),
            (self.radio_foxhound, MODE_FOX_HOUND, FREQ_MINIMUM_FOX_HOUND, FREQ_MAXIMUM),
            (self.radio_superfox, MODE_SUPER_FOX, FREQ_MINIMUM, FREQ_MAXIMUM_SUPER_FOX),
        ]

        self.mode_table_widget = QtWidgets.QTableWidget()
        self.mode_table_widget.setRowCount(len(modes))
        self.mode_table_widget.setColumnCount(4)

        self.mode_table_widget.setColumnWidth(0, 40)
        self.mode_table_widget.setColumnWidth(1, 95)
        self.mode_table_widget.setColumnWidth(2, 195)

        self.mode_table_widget.horizontalHeader().setStretchLastSection(True)
        self.mode_table_widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)

        self.mode_table_widget.setShowGrid(False)
        self.mode_table_widget.horizontalHeader().setVisible(False)
        self.mode_table_widget.verticalHeader().setVisible(False)
        self.mode_table_widget.setAlternatingRowColors(True)

        headers = ["", "Min Frequency", "Max Frequency", "Mode"]
        self.mode_table_widget.setHorizontalHeaderLabels(headers)
        self.mode_table_widget.horizontalHeader().setVisible(True)

        self.mode_table_widget.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

        self.mode_table_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed
        )

        self.mode_table_widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        row_height = 22
        for row, (button, label, freq_min, freq_max) in enumerate(modes):
            self.mode_table_widget.setRowHeight(row, row_height)

            self.mode_table_widget.setCellWidget(row, 0, button)

            freq_min_item = QTableWidgetItem(f"{freq_min}Hz")
            freq_min_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            freq_min_item.setFont(CUSTOM_FONT_SMALL)
            self.mode_table_widget.setItem(row, 1, freq_min_item)

            freq_max_item = QTableWidgetItem(f"{freq_max}Hz")
            freq_max_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            freq_max_item.setFont(CUSTOM_FONT_SMALL)
            self.mode_table_widget.setItem(row, 2, freq_max_item)

            label_item = QTableWidgetItem(f"{label}")
            label_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            label_item.setFont(CUSTOM_FONT_SMALL)
            self.mode_table_widget.setItem(row, 3, label_item)

        total_height = row_height * len(modes) + 2
        self.mode_table_widget.setMaximumHeight(total_height + row_height + 10)

        self.mode_table_widget.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                font-weight: normal; 
                border: none; 
                padding: 4px; 
            }
        """)

        self.mode_table_widget.setStyleSheet(f"""
            QTableWidget {{
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: {BG_COLOR_BLACK_ON_PURPLE}; 
                color: {FG_COLOR_BLACK_ON_PURPLE};
            }}
            QTableWidget::item {{
                selection-background-color: transparent;  
            }}
        """)
        self.mode_table_widget.verticalHeader().setVisible(False)
        self.mode_table_widget.cellClicked.connect(self.on_table_row_selected)

        udp_freq_range_type_layout.addWidget(self.mode_table_widget)

        self.freq_range_type_group.setLayout(QtWidgets.QVBoxLayout())
        self.freq_range_type_group.layout().setContentsMargins(0, 0, 0, 0)
        self.freq_range_type_group.layout().addWidget(udp_freq_range_type_widget)

        tab_2_layout.addWidget(max_reply_notice_label)
        tab_2_layout.addWidget(self.max_reply_group)        
        tab_2_layout.addWidget(general_settings_group)
        tab_2_layout.addWidget(self.freq_range_type_group)

        tab_2_layout.addStretch() 

        """
            Sound Settings
        """
        sound_notice_text = (
            "<p>You can enable or disable the sounds as per your requirement. You can even set a delay between each sound triggered by a message where a monitored callsign has been found. This mainly helps you to be notified when the band opens or when you have a callsign on the air that you want to monitor.</p><p>Monitored callsigns will never get reply from this program. Only <u>Wanted callsigns will get a reply</u>.</p>"
        )

        sound_notice_label = QtWidgets.QLabel(sound_notice_text)
        sound_notice_label.setStyleSheet(SETTING_QSS)
        sound_notice_label.setWordWrap(True)
        sound_notice_label.setFont(CUSTOM_FONT_SMALL)

        sound_settings_group = QtWidgets.QGroupBox("Sound Alerts Settings")
        sound_settings_layout = QtWidgets.QGridLayout()

        play_sound_notice_label = QtWidgets.QLabel("Play Sounds when:")
        play_sound_notice_label.setFont(CUSTOM_FONT_SMALL)

        self.enable_sound_wanted_callsigns = QtWidgets.QCheckBox("Message from any Wanted Callsign")
        self.enable_sound_wanted_callsigns.setChecked(True)

        self.enable_sound_directed_my_callsign = QtWidgets.QCheckBox("Message directed to my Callsign")
        self.enable_sound_directed_my_callsign.setChecked(True)

        self.enable_sound_monitored_callsigns = QtWidgets.QCheckBox("Message from any Monitored Callsign")
        self.enable_sound_monitored_callsigns.setChecked(True)

        self.delay_between_sound_for_monitored = QtWidgets.QLineEdit()
        self.delay_between_sound_for_monitored.setFixedWidth(50)

        delay_layout = QtWidgets.QHBoxLayout()
        delay_layout.addWidget(self.delay_between_sound_for_monitored)
        delay_layout.addWidget(QtWidgets.QLabel("seconds"))
        delay_layout.addStretch()

        sound_settings_layout.addWidget(play_sound_notice_label, 0, 0, 1, 2)
        sound_settings_layout.addWidget(self.enable_sound_wanted_callsigns, 1, 0, 1, 2)
        sound_settings_layout.addWidget(self.enable_sound_directed_my_callsign, 2, 0, 1, 2)
        sound_settings_layout.addWidget(self.enable_sound_monitored_callsigns, 3, 0, 1, 2)
        sound_settings_layout.addWidget(QtWidgets.QLabel("Delay between each monitored callsigns detected:"), 4, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        sound_settings_layout.addLayout(delay_layout, 4, 1, 1, 2)

        sound_settings_group.setLayout(sound_settings_layout)

        sound_notice_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        sound_settings_group.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        tab_3_layout.addWidget(sound_notice_label)
        tab_3_layout.addWidget(sound_settings_group)
        tab_3_layout.addStretch()  

        """
            Worked B4 Settings
        """

        worked_b4_notice_text = (
            f"<p>While using {GUI_LABEL_NAME}, you can let this program <u>analyze your working ADIF file from WSJT-x or JTDX</u>. {GUI_LABEL_NAME} won't update your main ADIF file. Still, it can read and parse it.</p>"
        )

        worked_b4_notice_label = QtWidgets.QLabel(worked_b4_notice_text)
        worked_b4_notice_label.setStyleSheet(SETTING_QSS)
        worked_b4_notice_label.setWordWrap(True)
        worked_b4_notice_label.setFont(CUSTOM_FONT_SMALL)
        worked_b4_notice_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        file_selection_group = QtWidgets.QGroupBox("ADIF File to check Worked B4 Callsigns")
        file_selection_group.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        file_selection_widget = QtWidgets.QWidget()
        file_selection_layout = QtWidgets.QGridLayout(file_selection_widget)
        
        self.select_file_button = QtWidgets.QPushButton("Select File")
        self.select_file_button.setFixedWidth(120)
        self.select_file_button.clicked.connect(self.open_adif_file_dialog)

        self.adif_file_path = QtWidgets.QLineEdit()
        self.adif_file_path.setReadOnly(True) 

        file_selection_layout.addWidget(self.adif_file_path, 0, 0)
        file_selection_layout.addWidget(self.select_file_button, 0, 1)

        file_selection_group.setLayout(QtWidgets.QVBoxLayout())
        file_selection_group.layout().setContentsMargins(0, 0, 0, 0)
        file_selection_group.layout().addWidget(file_selection_widget)
               
        self.adif_wkb4_group = QtWidgets.QGroupBox("What should we do with Worked B4?")
        adif_wkb4_layout = QtWidgets.QVBoxLayout()
        adif_wkb4_layout.setSpacing(10)

        self.radio_reply_always = QtWidgets.QRadioButton("Reply to any Wanted Callsign even if Worked B4")
        self.radio_reply_current_year = QtWidgets.QRadioButton("Reply to Wanted Callsign if not Worked B4 in current year ({})".format(datetime.now().year))
        self.radio_reply_never = QtWidgets.QRadioButton("Do not reply to any Callsign Worked B4")
        self.radio_reply_never.setChecked(True)
        
        adif_wkb4_layout.addWidget(self.radio_reply_always)
        adif_wkb4_layout.addWidget(self.radio_reply_current_year)
        adif_wkb4_layout.addWidget(self.radio_reply_never)

        self.adif_wkb4_group.setLayout(adif_wkb4_layout)
        self.adif_wkb4_group.setVisible(False)

        """
            Marathon Settings
        """
        marathon_notice_text = (
            f"<p>Marathon feature has to be used with caution.</p><p>{GUI_LABEL_NAME} will analyze your log and check for any missing entities you haven't worked on selected band. If a missing entity is decoded, <u>it will automatically add the callsign to your Wanted Callsigns</u>. Once entity is worked, {GUI_LABEL_NAME} will remove all entries automatically added to your Wanted Callsigns which refer to this entity.</p><p>Note that rules set for Worked B4 will remain in effect.</p>"
        )
        marathon_notice_label = QtWidgets.QLabel(marathon_notice_text)
        marathon_notice_label.setStyleSheet(SETTING_QSS)
        marathon_notice_label.setWordWrap(True)
        marathon_notice_label.setFont(CUSTOM_FONT_SMALL)
        marathon_notice_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        self.marathon_group = QtWidgets.QGroupBox("Enable Marathon for selected bands")
        marathon_layout = QtWidgets.QGridLayout()

        self.band_buttons = {}
        max_cols = 4
        row = 0
        col = 0

        for band_name in list(AMATEUR_BANDS.keys())[:-1]:
            btn = CustomButton(band_name)
            btn.setCheckable(True)         
            btn.toggled.connect(lambda checked, btn=btn, name=band_name: self.on_band_toggled(btn, name, checked))
            self.band_buttons[band_name] = btn
            marathon_layout.addWidget(btn, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        self.marathon_group.setLayout(marathon_layout)

        tab_4_layout.addWidget(worked_b4_notice_label)
        tab_4_layout.addWidget(file_selection_group)
        tab_4_layout.addWidget(self.adif_wkb4_group)
        tab_4_layout.addWidget(marathon_notice_label)
        tab_4_layout.addWidget(self.marathon_group)
        tab_4_layout.addStretch()  

        """
            Backup Settings
        """

        adif_backup_selection_group = QtWidgets.QGroupBox(f"{GUI_LABEL_NAME} Backup File")
        adif_backup_selection_group.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        working_log_notice_text = (
            f"{GUI_LABEL_NAME} program will write a new entry on a dedicated and specific ADIF File for each monitored QSO.<br /><br />This file can be used as a backup of your main logging sequence with JTDX or WSJT-x."
        )

        working_log_notice_label = QtWidgets.QLabel(working_log_notice_text)
        working_log_notice_label.setStyleSheet(SETTING_QSS)
        working_log_notice_label.setWordWrap(True)
        working_log_notice_label.setFont(CUSTOM_FONT_SMALL)
        working_log_notice_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        adif_backup_widget = QtWidgets.QWidget()
        adif_backup_layout = QtWidgets.QGridLayout(adif_backup_widget)

        self.show_backup_file_path = QtWidgets.QLineEdit()
        self.show_backup_file_path.setText(ADIF_WORKED_CALLSIGNS_FILE)
        self.show_backup_file_path.setReadOnly(False)  

        self.select_backup_file_button = QtWidgets.QPushButton("Select File")
        self.select_backup_file_button.setFixedWidth(120)
        self.select_backup_file_button.clicked.connect(self.open_backup_file_dialog)

        """
        self.open_backup_file_button = QtWidgets.QPushButton("Open Folder")
        self.open_backup_file_button.setFixedWidth(120)
        self.open_backup_file_button.clicked.connect(self.open_backup_file_location) 
        """
        adif_backup_layout.addWidget(self.show_backup_file_path, 0, 0)
        adif_backup_layout.addWidget(self.select_backup_file_button, 0, 1)
        
        """
        adif_backup_layout.addWidget(self.open_backup_file_button, 0, 2)
        """
        adif_backup_selection_group.setLayout(QtWidgets.QVBoxLayout())
        adif_backup_selection_group.layout().setContentsMargins(0, 0, 0, 0)
        adif_backup_selection_group.layout().addWidget(adif_backup_widget)

        tab_5_layout.addWidget(working_log_notice_label)
        tab_5_layout.addWidget(adif_backup_selection_group)
        tab_5_layout.addStretch()  
        
        """
            Debug Settings
        """

        log_settings_group = QtWidgets.QGroupBox("Log Settings")
        log_settings_layout = QtWidgets.QGridLayout()

        self.enable_debug_output = QtWidgets.QCheckBox("Show debug output")
        self.enable_debug_output.setChecked(DEFAULT_DEBUG_OUTPUT)

        self.enable_pounce_log = QtWidgets.QCheckBox(f"Save log to {get_log_filename()}")
        self.enable_pounce_log.setChecked(DEFAULT_POUNCE_LOG)

        self.enable_log_packet_data = QtWidgets.QCheckBox("Save all received Packet Data to log")
        self.enable_log_packet_data.setChecked(DEFAULT_LOG_PACKET_DATA)

        log_settings_layout.addWidget(self.enable_pounce_log, 0, 0, 1, 2)
        log_settings_layout.addWidget(self.enable_log_packet_data, 1, 0, 1, 2)
        log_settings_layout.addWidget(self.enable_debug_output, 2, 0, 1, 2)

        log_settings_group.setLayout(log_settings_layout)

        log_settings_group.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        tab_6_layout.addWidget(log_settings_group)
        tab_6_layout.addStretch()  

        self.load_params()

        self.button_box = QtWidgets.QDialogButtonBox()
        self.ok_button = CustomButton("OK")
        self.cancel_button = CustomButton("Cancel")

        self.button_box.addButton(self.ok_button, QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        self.button_box.addButton(self.cancel_button, QtWidgets.QDialogButtonBox.ButtonRole.RejectRole)
        
        layout.addWidget(self.button_box)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        self.on_tab_changed(self.tab_widget.currentIndex())  
        self.tab_widget.currentChanged.connect(self.on_tab_changed)        

    def on_band_toggled(self, button, band_name, checked):
        if checked:
            button.updateStyle(band_name, STATUS_TRX_COLOR, "#FFFFFF")
        else:
            button.resetStyle()        

    def on_table_row_selected(self, row, column):
        button = self.mode_table_widget.cellWidget(row, 0)
        
        if isinstance(button, QtWidgets.QRadioButton):
            button.setChecked(True)        

    def on_tab_changed(self, index):
        if sys.platform == 'darwin':
            current_tab = self.tab_widget.widget(index)
            current_tab.adjustSize()  

            tab_size            = current_tab.sizeHint()
            tab_bar_height      = self.tab_widget.tabBar().sizeHint().height()
            button_box_height   = self.button_box.sizeHint().height()
            margins             = self.layout().contentsMargins()
            total_height        = tab_size.height() + tab_bar_height + button_box_height + margins.top() + margins.bottom()

            self.setFixedHeight(total_height)


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

    def open_adif_file_dialog(self):
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
                processing_time, parsed_data = parse_adif(file_path)
                if parsed_data:
                    self.adif_file_path.setText(file_path)
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
        else:
            self.radio_normal.setChecked(True)

        self.primary_udp_server_address.setText(
            self.params.get('primary_udp_server_address') or local_ip_address
        )
        self.primary_udp_server_port.setText(
            str(self.params.get('primary_udp_server_port') or DEFAULT_UDP_PORT)
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
        self.enable_sending_reply.setChecked(
            self.params.get('enable_sending_reply', DEFAULT_SENDING_REPLY)
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
        self.enable_pounce_log.setChecked(
            self.params.get('enable_pounce_log', DEFAULT_POUNCE_LOG)
        )
        self.enable_log_packet_data.setChecked(
            self.params.get('enable_log_packet_data', DEFAULT_LOG_PACKET_DATA)
        )
        self.enable_log_all_valid_contact.setChecked(
            self.params.get('enable_log_all_valid_contact', True)
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
        selected_file = self.params.get('adif_file_path', None)
        self.adif_file_path.setText(selected_file)

        if selected_file:
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

        max_reply_attemps = self.params.get('max_reply_attemps_to_callsign', DEFAULT_REPLY_ATTEMPTS)
       
        index = self.max_reply_attemps_combo.findText(str(max_reply_attemps))
        if index != -1:
            self.max_reply_attemps_combo.setCurrentIndex(index)
        else:
            self.max_reply_attemps_combo.setCurrentIndex(0)  

        max_waiting_delay = self.params.get('max_waiting_delay', DEFAULT_MAX_WAITING_DELAY)
        if isinstance(max_waiting_delay, int):
            max_waiting_delay = str(max_waiting_delay)
        if max_waiting_delay in [self.max_waiting_delay_combo.itemText(i) for i in range(self.max_waiting_delay_combo.count())]:
            self.max_waiting_delay_combo.setCurrentText(max_waiting_delay)
        else:
            self.max_waiting_delay_combo.setCurrentText(str(DEFAULT_MAX_WAITING_DELAY))    

        self.marathon_preference = self.params.get('marathon_preference', {})

        if isinstance(self.marathon_preference, bool):
            self.marathon_preference = {}
        for band_name, btn in self.band_buttons.items():
            checked = self.marathon_preference.get(band_name, False)
            btn.setChecked(checked)
    
    def get_result(self):
        freq_range_mode = MODE_NORMAL 
        if self.radio_foxhound.isChecked():
            freq_range_mode = MODE_FOX_HOUND
        elif self.radio_superfox.isChecked():
            freq_range_mode = MODE_SUPER_FOX

        if self.radio_reply_always.isChecked():
            worked_before_preference = WKB4_REPLY_MODE_ALWAYS
        elif self.radio_reply_current_year.isChecked():
            worked_before_preference = WKB4_REPLY_MODE_CURRENT_YEAR
        elif self.radio_reply_never.isChecked():
            worked_before_preference = WKB4_REPLY_MODE_NEVER
        else:
            worked_before_preference = WKB4_REPLY_MODE_ALWAYS            

        max_reply_attemps = int(self.max_reply_attemps_combo.currentText())
        max_waiting_delay = int(self.max_waiting_delay_combo.currentText())

        marathon_preference = {}
        for band_name, btn in self.band_buttons.items():
            marathon_preference[band_name] = btn.isChecked()

        return {
            'primary_udp_server_address'                 : self.primary_udp_server_address.text(),
            'primary_udp_server_port'                    : self.primary_udp_server_port.text(),
            'secondary_udp_server_address'               : self.secondary_udp_server_address.text(),
            'secondary_udp_server_port'                  : self.secondary_udp_server_port.text(),
            'enable_secondary_udp_server'                : self.enable_secondary_udp_server.isChecked(),
            'enable_sending_reply'                       : self.enable_sending_reply.isChecked(),
            'max_reply_attemps_to_callsign'              : max_reply_attemps,
            'max_waiting_delay'                          : max_waiting_delay,
            'enable_gap_finder'                           : self.enable_gap_finder.isChecked(),
            'enable_watchdog_bypass'                     : self.enable_watchdog_bypass.isChecked(),
            'enable_debug_output'                        : self.enable_debug_output.isChecked(),
            'enable_pounce_log'                          : self.enable_pounce_log.isChecked(),
            'enable_log_packet_data'                     : self.enable_log_packet_data.isChecked(),
            'enable_sound_wanted_callsigns'              : self.enable_sound_wanted_callsigns.isChecked(),
            'enable_sound_directed_my_callsign'          : self.enable_sound_directed_my_callsign.isChecked(),
            'enable_sound_monitored_callsigns'           : self.enable_sound_monitored_callsigns.isChecked(),
            'delay_between_sound_for_monitored'          : self.delay_between_sound_for_monitored.text(),
            'adif_file_path'                              : self.adif_file_path.text(),      
            'adif_worked_backup_file_path'                       : self.show_backup_file_path.text(),
            'freq_range_mode'                            : freq_range_mode,
            'worked_before_preference'                   : worked_before_preference,
            'marathon_preference'                        : marathon_preference            
        }