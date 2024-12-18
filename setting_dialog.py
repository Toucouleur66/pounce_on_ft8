# setting_dialog

import platform
import subprocess
import os

from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QGridLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PyQt6.QtGui import QFont

from custom_button import CustomButton
from clickable_label import ClickableLabel
from adif_summary_dialog import AdifSummaryDialog

from datetime import datetime

from utils import get_local_ip_address, get_log_filename, get_app_data_dir
from utils import parse_adif_record, parse_adif

from constants import (
    # Colors
    BG_COLOR_BLACK_ON_PURPLE,
    FG_COLOR_BLACK_ON_PURPLE,
    # Labels
    GUI_LABEL_NAME,
    # Modes
    MODE_NORMAL,
    MODE_FOX_HOUND,
    MODE_SUPER_FOX,
    REPLY_WKB4_MODE_ALWAYS,
    REPLY_WKB4_MODE_CURRENT_YEAR,
    REPLY_WKB4_MODE_NEVER,
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
    DEFAULT_SHOW_ALL_DECODED,
    DEFAULT_DELAY_BETWEEN_SOUND,
    # Fonts
    CUSTOM_FONT_SMALL,
    CUSTOM_FONT_MONO,
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

        tab1 = QtWidgets.QWidget()
        tab2 = QtWidgets.QWidget()
        tab3 = QtWidgets.QWidget()
        tab4 = QtWidgets.QWidget()

        self.tab_widget.addTab(tab1, "General")
        self.tab_widget.addTab(tab2, "Sounds")
        self.tab_widget.addTab(tab3, "ADIF file")
        self.tab_widget.addTab(tab4, "Debug")

        tab1_layout = QtWidgets.QVBoxLayout(tab1)
        tab2_layout = QtWidgets.QVBoxLayout(tab2)
        tab3_layout = QtWidgets.QVBoxLayout(tab3)
        tab4_layout = QtWidgets.QVBoxLayout(tab4)
        
        jtdx_notice_text = (
            "For JTDX users, you have to disable automatic logging of QSO (Make sure <u>Settings > Reporting > Logging > Enable automatic logging of QSO</u> is unchecked)<br /><br />You might also need to accept UDP Reply messages from any messages (<u>Misc Menu > Accept UDP Reply Messages > any messages</u>)."
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

        secondary_group.setLayout(secondary_layout)

        udp_settings_group = QtWidgets.QGroupBox(f"{GUI_LABEL_NAME} Main settings")
        
        udp_settings_widget = QtWidgets.QWidget()
        udp_settings_widget.setStyleSheet(f"background-color: {BG_COLOR_BLACK_ON_PURPLE}; color: {FG_COLOR_BLACK_ON_PURPLE}; ")
        udp_settings_layout = QtWidgets.QGridLayout(udp_settings_widget)
        
        self.enable_sending_reply = QtWidgets.QCheckBox("Enable reply")
        self.enable_sending_reply.setChecked(DEFAULT_SENDING_REPLY)

        self.enable_gap_finder = QtWidgets.QCheckBox("Enable frequencies offset updater")
        self.enable_gap_finder.setChecked(DEFAULT_GAP_FINDER)

        self.enable_watchdog_bypass = QtWidgets.QCheckBox("Enable watchdog bypass")
        self.enable_watchdog_bypass.setChecked(DEFAULT_WATCHDOG_BYPASS)

        self.enable_show_all_decoded = QtWidgets.QCheckBox("Show all decoded messages (do not filter on Wanted or Monitored)")
        self.enable_show_all_decoded.setChecked(DEFAULT_SHOW_ALL_DECODED)

        self.enable_log_all_valid_contact = QtWidgets.QCheckBox("Log all valid contacts (not only from Wanted)")
        self.enable_log_all_valid_contact.setChecked(True)

        udp_settings_layout.addWidget(self.enable_sending_reply, 0, 0, 1, 2)
        udp_settings_layout.addWidget(self.enable_gap_finder, 1, 0, 1, 2)
        udp_settings_layout.addWidget(self.enable_watchdog_bypass, 2, 0, 1, 2)
        udp_settings_layout.addWidget(self.enable_show_all_decoded, 3, 0, 1, 2)
        udp_settings_layout.addWidget(self.enable_log_all_valid_contact, 4, 0, 1, 2)

        udp_settings_group.setLayout(QtWidgets.QVBoxLayout())
        udp_settings_group.layout().setContentsMargins(0, 0, 0, 0)
        udp_settings_group.layout().addWidget(udp_settings_widget)

        self.udp_freq_range_type_group = QtWidgets.QGroupBox("Select range of frequency being used for offset updater")

        udp_freq_range_type_widget = QtWidgets.QWidget()
        udp_freq_range_type_layout = QtWidgets.QVBoxLayout(udp_freq_range_type_widget)

        self.radio_normal = QtWidgets.QRadioButton()
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
        self.mode_table_widget.setColumnWidth(2, 95)

        self.mode_table_widget.horizontalHeader().setStretchLastSection(True)
        self.mode_table_widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)

        self.mode_table_widget.setShowGrid(False)
        self.mode_table_widget.horizontalHeader().setVisible(False)
        self.mode_table_widget.verticalHeader().setVisible(False)
        self.mode_table_widget.setAlternatingRowColors(True)

        headers = ["", "Min Frequency", "Max Frequency", "Mode"]
        self.mode_table_widget.setHorizontalHeaderLabels(headers)
        self.mode_table_widget.horizontalHeader().setVisible(True)

        # Ajuster l'alignement des en-têtes si nécessaire
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

            freq_min_widget = QtWidgets.QLabel(f"{freq_min}Hz")
            freq_min_widget.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            freq_min_widget.setFont(CUSTOM_FONT_SMALL)

            self.mode_table_widget.setCellWidget(row, 1, freq_min_widget)

            freq_max_widget = QtWidgets.QLabel(f"{freq_max}Hz")
            freq_max_widget.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            freq_max_widget.setFont(CUSTOM_FONT_SMALL)
            
            self.mode_table_widget.setCellWidget(row, 2, freq_max_widget)

            label_widget = QtWidgets.QLabel(f"{label}")
            label_widget.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            label_widget.setFont(CUSTOM_FONT_SMALL)

            self.mode_table_widget.setCellWidget(row, 3, label_widget)

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

        self.udp_freq_range_type_group.setLayout(QtWidgets.QVBoxLayout())
        self.udp_freq_range_type_group.layout().setContentsMargins(0, 0, 0, 0)
        self.udp_freq_range_type_group.layout().addWidget(udp_freq_range_type_widget)

        tab1_layout.addWidget(jtdx_notice_label)
        tab1_layout.addWidget(primary_group)
        tab1_layout.addWidget(secondary_group)
        tab1_layout.addWidget(udp_settings_group)
        tab1_layout.addWidget(self.udp_freq_range_type_group)
        tab1_layout.addStretch() 

        sound_notice_text = (
            "You can enable or disable the sounds as per your requirement. You can even set a delay between each sound triggered by a message where a monitored callsign has been found. This mainly helps you to be notified when the band opens or when you have a callsign on the air that you want to monitor.<br /><br />Monitored callsigns will never get reply from this program. Only <u>Wanted callsigns will get a reply</u>."
        )

        sound_notice_label = QtWidgets.QLabel(sound_notice_text)
        sound_notice_label.setStyleSheet(SETTING_QSS)
        sound_notice_label.setWordWrap(True)
        sound_notice_label.setFont(CUSTOM_FONT_SMALL)

        sound_settings_group = QtWidgets.QGroupBox("Sounds Settings")
        sound_settings_layout = QtWidgets.QGridLayout()

        play_sound_notice_label = QtWidgets.QLabel("Play Sounds when:")
        play_sound_notice_label.setFont(CUSTOM_FONT_SMALL)

        self.enable_sound_wanted_callsigns = QtWidgets.QCheckBox("Message from any Wanted Callsign")
        self.enable_sound_wanted_callsigns.setChecked(True)

        self.enable_sound_directed_my_callsign = QtWidgets.QCheckBox("Message directed to my Callsign")
        self.enable_sound_directed_my_callsign.setChecked(True)

        self.enable_sound_monitored_callsigns = QtWidgets.QCheckBox("Message from any Monitored Callsign")
        self.enable_sound_monitored_callsigns.setChecked(True)

        self.delay_between_sound_for_monitored_callsign = QtWidgets.QLineEdit()
        self.delay_between_sound_for_monitored_callsign.setFixedWidth(50)

        delay_layout = QtWidgets.QHBoxLayout()
        delay_layout.addWidget(self.delay_between_sound_for_monitored_callsign)
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

        tab2_layout.addWidget(sound_notice_label)
        tab2_layout.addWidget(sound_settings_group)
        tab2_layout.addStretch()  

        adif_notice_text = (
            f"{GUI_LABEL_NAME} program will write specific ADIF file for each valid QSO monitored. This is mainly a backup for your main ADIF file. <br /><br />In addition, you can also <u>set your working ADIF file from WSJT-x or JTDX</u>. {GUI_LABEL_NAME} won't update your main ADIF file. Still, it can read and parse it, and will allow you to check which station was worked before (Wkb4). Then you can ask {GUI_LABEL_NAME} to not reply to any station worked before. But you can also ask {GUI_LABEL_NAME} to reply to station not worked on the current year."
        )

        adif_notice_label = QtWidgets.QLabel(adif_notice_text)
        adif_notice_label.setStyleSheet(SETTING_QSS)
        adif_notice_label.setWordWrap(True)
        adif_notice_label.setFont(CUSTOM_FONT_SMALL)

        adif_backup_selection_group = QtWidgets.QGroupBox(f"{GUI_LABEL_NAME} ADIF File")

        adif_backup_widget = QtWidgets.QWidget()
        adif_backup_layout = QtWidgets.QGridLayout(adif_backup_widget)

        show_backup_file_path = QtWidgets.QLineEdit(f"{ADIF_WORKED_CALLSIGNS_FILE}")
        show_backup_file_path.setReadOnly(True) 

        open_backup_file_button = CustomButton("Show File")
        open_backup_file_button.setFixedWidth(120)
        open_backup_file_button.clicked.connect(self.open_backup_file_location) 

        adif_backup_layout.addWidget(show_backup_file_path, 0, 0)
        adif_backup_layout.addWidget(open_backup_file_button, 0, 1)

        adif_backup_selection_group.setLayout(QtWidgets.QVBoxLayout())
        adif_backup_selection_group.layout().setContentsMargins(0, 0, 0, 0)
        adif_backup_selection_group.layout().addWidget(adif_backup_widget)

        file_selection_group = QtWidgets.QGroupBox("ADIF File to check Worked Before")

        file_selection_widget = QtWidgets.QWidget()
        file_selection_layout = QtWidgets.QGridLayout(file_selection_widget)

        self.selected_file_path = QtWidgets.QLineEdit()
        self.selected_file_path.setReadOnly(True) 

        self.select_file_button = CustomButton("Select File")
        self.select_file_button.setFixedWidth(120)
        self.select_file_button.clicked.connect(self.open_file_dialog)

        file_selection_layout.addWidget(self.selected_file_path, 0, 0)
        file_selection_layout.addWidget(self.select_file_button, 0, 1)

        file_selection_group.setLayout(QtWidgets.QVBoxLayout())
        file_selection_group.layout().setContentsMargins(0, 0, 0, 0)
        file_selection_group.layout().addWidget(file_selection_widget)
       
        adif_notice_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        adif_backup_selection_group.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        file_selection_group.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        self.adif_action_group = QtWidgets.QGroupBox("What should we do with your ADIF file?")
        adif_action_layout = QtWidgets.QVBoxLayout()

        self.radio_reply_always = QtWidgets.QRadioButton("Reply to Wanted Callsign even if Worked before")
        self.radio_reply_current_year = QtWidgets.QRadioButton("Reply to Wanted Callsign if not worked in {}".format(datetime.now().year))
        self.radio_reply_never = QtWidgets.QRadioButton("Never reply to callsign worked before")
        
        self.adif_action_button_group = QtWidgets.QButtonGroup()
        self.adif_action_button_group.addButton(self.radio_reply_always)
        self.adif_action_button_group.addButton(self.radio_reply_current_year)
        self.adif_action_button_group.addButton(self.radio_reply_never)

        adif_action_layout.addWidget(self.radio_reply_always)
        adif_action_layout.addWidget(self.radio_reply_current_year)
        adif_action_layout.addWidget(self.radio_reply_never)

        self.adif_action_group.setLayout(adif_action_layout)
        self.adif_action_group.setVisible(False)

        tab3_layout.addWidget(adif_notice_label)
        tab3_layout.addWidget(adif_backup_selection_group)
        tab3_layout.addWidget(file_selection_group)
        tab3_layout.addWidget(self.adif_action_group)
        tab3_layout.addStretch()  

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

        tab4_layout.addWidget(log_settings_group)
        tab4_layout.addStretch()  

        self.load_params()

        self.button_box = QtWidgets.QDialogButtonBox()
        self.ok_button = CustomButton("OK")
        self.cancel_button = CustomButton("Cancel")

        self.button_box.addButton(self.ok_button, QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        self.button_box.addButton(self.cancel_button, QtWidgets.QDialogButtonBox.ButtonRole.RejectRole)
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        layout.addWidget(self.button_box)
        self.enable_gap_finder.stateChanged.connect(self.update_table_frequency_state)
        self.update_table_frequency_state()

        self.on_tab_changed(self.tab_widget.currentIndex())  
        self.tab_widget.currentChanged.connect(self.on_tab_changed)        

    def on_table_row_selected(self, row, column):
        button = self.mode_table_widget.cellWidget(row, 0)
        
        if isinstance(button, QtWidgets.QRadioButton):
            button.setChecked(True)         

    def update_table_frequency_state(self):
        if self.enable_gap_finder.isChecked():
            self.udp_freq_range_type_group.show()  
        else:
            self.udp_freq_range_type_group.hide()

        self.on_tab_changed(self.tab_widget.currentIndex()) 

    def on_tab_changed(self, index):
        current_tab = self.tab_widget.widget(index)
        current_tab.adjustSize()  

        tab_size            = current_tab.sizeHint()
        tab_bar_height      = self.tab_widget.tabBar().sizeHint().height()
        button_box_height   = self.button_box.sizeHint().height()
        margins             = self.layout().contentsMargins()
        total_height        = tab_size.height() + tab_bar_height + button_box_height + margins.top() + margins.bottom()

        self.setFixedHeight(total_height)

    def open_file_dialog(self):
        options = QtWidgets.QFileDialog.Option.ReadOnly | QtWidgets.QFileDialog.Option.DontUseNativeDialog
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select ADIF File",
            "",
            "ADIF File (*.adif)",
            options=options
        )
        if file_path:
            parsed_data, processing_time = parse_adif(file_path)

            if parsed_data:
                self.selected_file_path.setText(file_path)
                self.adif_action_group.setVisible(True)  

                summary_dialog = AdifSummaryDialog(parsed_data, processing_time, self)
                summary_dialog.exec()
            else:
                QMessageBox.warning(
                    self,
                    "No Data found",
                    "Seems your file is either empty or corrupted"
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

        freq_range_mode = self.params.get("selected_mode", MODE_NORMAL)

        if freq_range_mode == "Normal":
            self.radio_normal.setChecked(True)
        elif freq_range_mode == "Fox/Hound":
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
        self.enable_show_all_decoded.setChecked(
            self.params.get('enable_show_all_decoded', DEFAULT_SHOW_ALL_DECODED)
        )
        self.enable_log_all_valid_contact.setChecked(
            self.params.get('enable_log_all_valid_contact', True)
        )        
        self.delay_between_sound_for_monitored_callsign.setText(
            str(self.params.get('delay_between_sound_for_monitored_callsign', DEFAULT_DELAY_BETWEEN_SOUND))
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
        selected_file = self.params.get('selected_file_path', get_app_data_dir())
        self.selected_file_path.setText(selected_file)

        if selected_file:
            self.adif_action_group.setVisible(True)
            reply_mode = self.params.get('reply_worked_before_mode', REPLY_WKB4_MODE_ALWAYS)  
            if reply_mode == REPLY_WKB4_MODE_ALWAYS:
                self.radio_reply_always.setChecked(True)
            elif reply_mode == REPLY_WKB4_MODE_CURRENT_YEAR:
                self.radio_reply_current_year.setChecked(True)
            elif reply_mode == REPLY_WKB4_MODE_NEVER:
                self.radio_reply_never.setChecked(True)
            else:
                self.radio_reply_always.setChecked(True)  
        else:
            self.adif_action_group.setVisible(False)

    def get_result(self):
        selected_mode = MODE_NORMAL 
        if self.radio_foxhound.isChecked():
            selected_mode = MODE_FOX_HOUND
        elif self.radio_superfox.isChecked():
            selected_mode = MODE_SUPER_FOX

        if self.radio_reply_always.isChecked():
            reply_worked_before_mode = REPLY_WKB4_MODE_ALWAYS
        elif self.radio_reply_current_year.isChecked():
            reply_worked_before_mode = REPLY_WKB4_MODE_CURRENT_YEAR
        elif self.radio_reply_never.isChecked():
            reply_worked_before_mode = REPLY_WKB4_MODE_NEVER
        else:
            reply_worked_before_mode = REPLY_WKB4_MODE_ALWAYS            

        return {
            'primary_udp_server_address'                 : self.primary_udp_server_address.text(),
            'primary_udp_server_port'                    : self.primary_udp_server_port.text(),
            'secondary_udp_server_address'               : self.secondary_udp_server_address.text(),
            'secondary_udp_server_port'                  : self.secondary_udp_server_port.text(),
            'enable_secondary_udp_server'                : self.enable_secondary_udp_server.isChecked(),
            'enable_sending_reply'                       : self.enable_sending_reply.isChecked(),
            'enable_gap_finder'                           : self.enable_gap_finder.isChecked(),
            'enable_watchdog_bypass'                     : self.enable_watchdog_bypass.isChecked(),
            'enable_debug_output'                        : self.enable_debug_output.isChecked(),
            'enable_pounce_log'                          : self.enable_pounce_log.isChecked(),
            'enable_log_packet_data'                     : self.enable_log_packet_data.isChecked(),
            'enable_show_all_decoded'                    : self.enable_show_all_decoded.isChecked(),
            'enable_sound_wanted_callsigns'              : self.enable_sound_wanted_callsigns.isChecked(),
            'enable_sound_directed_my_callsign'          : self.enable_sound_directed_my_callsign.isChecked(),
            'enable_sound_monitored_callsigns'           : self.enable_sound_monitored_callsigns.isChecked(),
            'delay_between_sound_for_monitored_callsign' : self.delay_between_sound_for_monitored_callsign.text(),
            'selected_mode'                              : selected_mode,
            'selected_file_path'                          : self.selected_file_path.text(),
            'reply_worked_before_mode'                   : reply_worked_before_mode
        }