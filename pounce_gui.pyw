# pounce_gui.pyw

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QApplication, QStyleFactory
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QEasingCurve, QPointF
from PyQt6.QtMultimedia import QSoundEffect

import platform
import re
import sys
import traceback
import pickle
import os
import queue
import threading
import pyperclip
import logging

from datetime import datetime, timezone, timedelta
from collections import deque
from functools import partial

# Custom classes 
from tray_icon import TrayIcon
from activity_bar import ActivityBar
from tooltip import ToolTip
from worker import Worker
from monitoring_setting import MonitoringSettings

from utils import get_local_ip_address, get_log_filename, matches_any
from utils import get_mode_interval, get_amateur_band
from utils import force_uppercase, force_numbers_and_commas, text_to_array

from logger import get_logger, add_file_handler, remove_file_handler
from gui_handler import GUIHandler

from constants import (
    EXPIRATION_DATE,
    DEFAULT_UDP_PORT,
    # Colors
    EVEN_COLOR,
    ODD_COLOR,
    FG_COLOR_FOCUS_MY_CALL,
    BG_COLOR_FOCUS_MY_CALL,
    FG_COLOR_REGULAR_FOCUS,
    BG_COLOR_REGULAR_FOCUS,
    BG_COLOR_BLACK_ON_YELLOW,
    FG_COLOR_BLACK_ON_YELLOW,
    BG_COLOR_WHITE_ON_BLUE,
    FG_COLOR_WHITE_ON_BLUE,
    BG_COLOR_BLACK_ON_PURPLE,
    FG_COLOR_BLACK_ON_PURPLE,
    BG_COLOR_BLACK_ON_CYAN,
    FG_COLOR_BLACK_ON_CYAN,
    # Status button
    STATUS_MONITORING_COLOR,
    STATUS_DECODING_COLOR,
    STATUS_TRX_COLOR,
    # Parameters
    PARAMS_FILE,
    POSITION_FILE,
    WANTED_CALLSIGNS_FILE,
    WANTED_CALLSIGNS_HISTORY_SIZE,
    # Labels
    GUI_LABEL_VERSION,
    STATUS_BUTTON_LABEL_MONITORING,
    STATUS_BUTTON_LABEL_DECODING,
    STATUS_BUTTON_LABEL_START,
    STATUS_BUTTON_LABEL_TRX,
    STATUS_BUTTON_LABEL_NOTHING_YET,
    WAITING_DATA_PACKETS_LABEL,
    WANTED_CALLSIGNS_HISTORY_LABEL,
    CALLSIGN_NOTICE_LABEL,
    # Modes
    MODE_FOX_HOUND,
    MODE_NORMAL,
    MODE_SUPER_FOX,
    DEFAULT_MODE_TIMER_VALUE,
    # Working directory
    CURRENT_DIR,
    # UDP related
    DEFAULT_SECONDARY_UDP_SERVER,
    DEFAULT_SENDING_REPLY,
    # Default settings
    DEFAULT_GAP_FINDER,
    DEFAULT_WATCHDOG_BYPASS,
    DEFAULT_DEBUG_OUTPUT,
    DEFAULT_POUNCE_LOG,
    DEFAULT_LOG_PACKET_DATA,
    DEFAULT_SHOW_ALL_DECODED,
    DEFAULT_DELAY_BETWEEN_SOUND,
    ACTIVITY_BAR_MAX_VALUE,
    # Style
    CONTEXT_MENU_DARWIN_STYLE
    )

stop_event = threading.Event()

tray_icon = None

gui_queue = queue.Queue()

if platform.system() == 'Windows':
    custom_font             = QtGui.QFont("Segoe UI", 12)
    custom_font_mono        = QtGui.QFont("Consolas", 12)
    custom_font_mono_lg     = QtGui.QFont("Consolas", 18)
    custom_font_bold        = QtGui.QFont("Consolas", 12, QtGui.QFont.Weight.Bold)
elif platform.system() == 'Darwin':
    custom_font             = QtGui.QFont(".AppleSystemUIFont", 13)
    custom_font_mono        = QtGui.QFont("Monaco", 13)
    custom_font_mono_lg     = QtGui.QFont("Monaco", 18)
    custom_font_bold        = QtGui.QFont("Monaco", 12, QtGui.QFont.Weight.Bold)

    menu_font               = QtGui.QFont(".AppleSystemUIFont")

small_font                  = QtGui.QFont()
small_font.setPointSize(11)      

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, params=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(750, 900)

        self.params = params or {}

        layout = QtWidgets.QVBoxLayout(self)

        jtdx_notice_text = (
            "For JTDX users, you have to disable automatic logging of QSO (Make sure <u>Settings > Reporting > Logging > Enable automatic logging of QSO</u> is unchecked)<br /><br />You might also need to accept UDP Reply messages from any messages (<u>Misc Menu > Accept UDP Reply Messages > any messages</u>)."
        )
        jtdx_notice_label = QtWidgets.QLabel(jtdx_notice_text)
        jtdx_notice_label.setWordWrap(True)
        jtdx_notice_label.setFont(small_font)
        jtdx_notice_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        jtdx_notice_label.setStyleSheet("background-color: #9dfffe; color: #555bc2; padding: 5px; font-size: 12px;")
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

        udp_settings_group = QtWidgets.QGroupBox("UDP Settings")

        udp_settings_widget = QtWidgets.QWidget()
        udp_settings_layout = QtWidgets.QGridLayout(udp_settings_widget)
        
        self.enable_sending_reply = QtWidgets.QCheckBox("Enable reply")
        self.enable_sending_reply.setChecked(DEFAULT_SENDING_REPLY)

        self.enable_gap_finder = QtWidgets.QCheckBox("Enable frequencies offset updater")
        self.enable_gap_finder.setChecked(DEFAULT_GAP_FINDER)

        self.enable_watchdog_bypass = QtWidgets.QCheckBox("Enable watchdog bypass")
        self.enable_watchdog_bypass.setChecked(DEFAULT_WATCHDOG_BYPASS)
        
        udp_settings_layout.addWidget(self.enable_sending_reply, 0, 0, 1, 2)       
        udp_settings_layout.addWidget(self.enable_gap_finder, 1, 0, 1, 2)       
        udp_settings_layout.addWidget(self.enable_watchdog_bypass, 2, 0, 1, 2)
        
        udp_settings_widget.setStyleSheet(f"background-color: {BG_COLOR_BLACK_ON_PURPLE}; color: {FG_COLOR_BLACK_ON_PURPLE};")
        udp_settings_group.setLayout(QtWidgets.QVBoxLayout())
        udp_settings_group.layout().setContentsMargins(0, 0, 0, 0)
        udp_settings_group.layout().addWidget(udp_settings_widget)

        sound_notice_text = (
            "You can enable or disable the sounds as per your requirement. You can even set a delay between each sound triggered by a message where a monitored callsign has been found. This mainly helps you to be notified when the band opens or when you have a callsign on the air that you want to monitor.<br /><br />Monitored callsigns will never get reply from this program. Only <u>Wanted callsigns will get a reply</u>."
        )
    
        sound_notice_label = QtWidgets.QLabel(sound_notice_text)
        sound_notice_label.setStyleSheet("background-color: #9dfffe; color: #555bc2; padding: 5px; font-size: 12px;")
        sound_notice_label.setWordWrap(True)
        sound_notice_label.setFont(small_font)

        sound_settings_group = QtWidgets.QGroupBox("Sounds Settings")
        sound_settings_layout = QtWidgets.QGridLayout()

        play_sound_notice_label = QtWidgets.QLabel("Play Sounds when:")
        play_sound_notice_label.setFont(small_font)

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

        log_settings_group = QtWidgets.QGroupBox("Log Settings")
        log_settings_layout = QtWidgets.QGridLayout()

        self.enable_debug_output = QtWidgets.QCheckBox("Show debug output")                
        self.enable_debug_output.setChecked(DEFAULT_DEBUG_OUTPUT)
        
        self.enable_pounce_log = QtWidgets.QCheckBox(f"Save log to {get_log_filename()}")
        self.enable_pounce_log.setChecked(DEFAULT_POUNCE_LOG)

        self.enable_log_packet_data = QtWidgets.QCheckBox("Save all received Packet Data to log")
        self.enable_log_packet_data.setChecked(DEFAULT_LOG_PACKET_DATA)
        
        self.enable_show_all_decoded = QtWidgets.QCheckBox("Show all decoded messages (not only Wanted or Monitored)")
        self.enable_show_all_decoded.setChecked(DEFAULT_SHOW_ALL_DECODED)
    
        log_settings_layout.addWidget(self.enable_pounce_log, 0, 0, 1, 2)
        log_settings_layout.addWidget(self.enable_log_packet_data, 1, 0, 1, 2)        
        log_settings_layout.addWidget(self.enable_debug_output, 2, 0, 1, 2)        
        log_settings_layout.addWidget(self.enable_show_all_decoded, 3, 0, 1, 2)

        log_settings_group.setLayout(log_settings_layout)

        self.load_params()

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(jtdx_notice_label)
        layout.addWidget(primary_group)
        layout.addWidget(secondary_group)
        layout.addWidget(udp_settings_group)
        layout.addWidget(sound_notice_label)
        layout.addWidget(sound_settings_group)
        layout.addWidget(log_settings_group)
        layout.addWidget(button_box)

    def load_params(self):
        local_ip_address = get_local_ip_address()

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

    def get_result(self):
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
            'delay_between_sound_for_monitored_callsign' : self.delay_between_sound_for_monitored_callsign.text()   
        }

class UpdateWantedDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, selected_callsign=""):
        super().__init__(parent)

        self.setWindowTitle("Update Wanted Callsigns")
        self.resize(450, 100)
        self.selected_callsign = selected_callsign

        layout = QtWidgets.QVBoxLayout(self)
        
        message_label = QtWidgets.QLabel('Do you want to update Wanted Callsign(s) with:')
        layout.addWidget(message_label)
        
        self.entry = QtWidgets.QWidget()
        self.entry = QtWidgets.QLabel(self.selected_callsign)
        self.entry.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.entry.setWordWrap(True)
        self.entry.setFont(custom_font_mono)
        self.entry.setStyleSheet("background-color: white;")
        self.entry.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.entry)
        
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Yes | QtWidgets.QDialogButtonBox.StandardButton.No
        )
        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        self.adjust_dialog_size()

    def adjust_dialog_size(self):
        self.entry.adjustSize()
    
        self.adjustSize()
        
        min_width = max(450, self.entry.width() + 40)  
        min_height = max(50, self.entry.height() + 120)
        
        self.setMinimumSize(min_width, min_height)        

class EditWantedDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, initial_value="", title="Edit Wanted Callsigns"):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.resize(600, 200)

        layout = QtWidgets.QVBoxLayout(self)

        message_label = QtWidgets.QLabel("Wanted Callsign(s) (Comma separated list):")
        layout.addWidget(message_label)

        self.entry = QtWidgets.QTextEdit()
        self.entry.setAcceptRichText(False)
        self.entry.setText(initial_value)
        self.entry.setFont(custom_font_mono)
        self.entry.textChanged.connect(lambda: force_uppercase(self.entry))
        layout.addWidget(self.entry)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    def get_result(self):
        return ",".join(text_to_array(self.entry.toPlainText().strip()))

class GuiHandler(logging.Handler, QObject):
    log_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
    
    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg)

class MainApp(QtWidgets.QMainWindow):
    error_occurred = QtCore.pyqtSignal(str)    
    message_received = QtCore.pyqtSignal(object)

    def __init__(self):
        super(MainApp, self).__init__()

        self.worker = None
        self.monitoring_settings = MonitoringSettings()        

        # Window size, title and icon
        self.setGeometry(100, 100, 900, 700)
        self.base_title = GUI_LABEL_VERSION
        self.setWindowTitle(self.base_title)

        if platform.system() == 'Windows':
            if getattr(sys, 'frozen', False): 
                icon_path = os.path.join(sys._MEIPASS, "pounce.ico")
            else:
                icon_path = "pounce.ico"

            self.setWindowIcon(QtGui.QIcon(icon_path))    

        self.stop_event = threading.Event()
        self.error_occurred.connect(self.add_message_to_table)
        self.message_received.connect(self.handle_message_received)
        
        self._running = False

        self.message_times = deque()

        self.activity_timer = QtCore.QTimer()
        self.activity_timer.timeout.connect(self.update_activity_bar)
        self.activity_timer.start(100)

        self.theme_timer = QtCore.QTimer(self)
        self.theme_timer.timeout.connect(self.check_theme_change)
        self.theme_timer.start(1_000) 

        self.network_check_status_interval = 5_000
        self.network_check_status = QtCore.QTimer()
        self.network_check_status.timeout.connect(self.check_connection_status)

        self.decode_packet_count                = 0
        self.last_decode_packet_time            = None
        self.last_heartbeat_time                = None
        self.last_sound_played_time             = datetime.min
        self.mode                               = None
        self.transmitting                       = False
        self.band                               = None
        self.last_frequency                     = None
        self.frequency                          = None
        self.enable_show_all_decoded            = None

        self.wanted_callsign_detected_sound     = QSoundEffect()
        self.directed_to_my_call_sound          = QSoundEffect()
        self.ready_to_log_sound                 = QSoundEffect()
        self.error_occurred_sound               = QSoundEffect()
        self.monitored_callsign_detected_sound  = QSoundEffect()

        self.wanted_callsign_detected_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/495650__matrixxx__supershort-ping-or-short-notification.wav"))
        self.directed_to_my_call_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/716445__scottyd0es__tone12_error.wav"))
        self.ready_to_log_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/709072__scottyd0es__aeroce-dualtone-5.wav"))
        self.error_occurred_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/142608__autistic-lucario__error.wav"))
        self.monitored_callsign_detected_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/716442__scottyd0es__tone12_alert_3.wav"))
        
        # Main layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        outer_layout = QtWidgets.QHBoxLayout()
        central_widget.setLayout(outer_layout)

        main_layout = QtWidgets.QGridLayout()
        outer_layout.addLayout(main_layout)

        # Variables
        self.wanted_callsigns_var = QtWidgets.QLineEdit()
        self.wanted_callsigns_var.setFont(custom_font)
        self.monitored_callsigns_var = QtWidgets.QLineEdit()
        self.monitored_callsigns_var.setFont(custom_font)
        self.monitored_cq_zones_var = QtWidgets.QLineEdit()
        self.monitored_cq_zones_var.setFont(custom_font)        
        self.excluded_callsigns_var = QtWidgets.QLineEdit()
        self.excluded_callsigns_var.setFont(custom_font)

        # Mode buttons (radio buttons)
        self.special_mode_var = QtWidgets.QButtonGroup()

        radio_normal = QtWidgets.QRadioButton(MODE_NORMAL)
        radio_foxhound = QtWidgets.QRadioButton(MODE_FOX_HOUND)
        radio_superfox = QtWidgets.QRadioButton(MODE_SUPER_FOX)

        self.special_mode_var.addButton(radio_normal)
        self.special_mode_var.addButton(radio_foxhound)
        self.special_mode_var.addButton(radio_superfox)

        radio_normal.setChecked(True)

        params = self.load_params()

        special_mode = params.get("special_mode", "Normal")
        if special_mode == "Normal":
            radio_normal.setChecked(True)
        elif special_mode == "Fox/Hound":
            radio_foxhound.setChecked(True)
        elif special_mode == "SuperFox":
            radio_superfox.setChecked(True)

        self.wanted_callsigns_history = self.load_wanted_callsigns()

        self.wanted_callsigns_var.setText(params.get("wanted_callsigns", ""))
        self.monitored_callsigns_var.setText(params.get("monitored_callsigns", ""))
        self.monitored_cq_zones_var.setText(params.get("monitored_cq_zones", ""))
        self.excluded_callsigns_var.setText(params.get("excluded_callsigns", ""))

        """
            2.0.9: New behavior with Monitoring
        """
        self.monitoring_settings.set_wanted_callsigns(self.wanted_callsigns_var.text())
        self.monitoring_settings.set_monitored_callsigns(self.monitored_callsigns_var.text())
        self.monitoring_settings.set_excluded_callsigns(self.excluded_callsigns_var.text())
        self.monitoring_settings.set_monitored_cq_zones(self.monitored_cq_zones_var.text())

        # Signals
        self.wanted_callsigns_var.textChanged.connect(lambda: force_uppercase(self.wanted_callsigns_var))
        self.wanted_callsigns_var.textChanged.connect(self.on_wanted_callsigns_changed)

        self.monitored_callsigns_var.textChanged.connect(lambda: force_uppercase(self.monitored_callsigns_var))
        self.monitored_callsigns_var.textChanged.connect(self.on_monitored_callsigns_changed)

        self.excluded_callsigns_var.textChanged.connect(lambda: force_uppercase(self.excluded_callsigns_var))
        self.excluded_callsigns_var.textChanged.connect(self.on_excluded_callsigns_changed)

        self.monitored_cq_zones_var.textChanged.connect(lambda: force_numbers_and_commas(self.monitored_cq_zones_var))
        self.monitored_cq_zones_var.textChanged.connect(self.on_monitored_cq_zones_changed)

        # Wanted callsigns label
        self.wanted_callsigns_history_label = QtWidgets.QLabel(WANTED_CALLSIGNS_HISTORY_LABEL % len(self.wanted_callsigns_history))

        # Listbox (wanted callsigns)
        self.listbox = QtWidgets.QListWidget()
        self.listbox.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.listbox.setFont(custom_font)
        self.listbox.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.listbox.itemClicked.connect(self.on_listbox_double_click)
        self.listbox.itemDoubleClicked.connect(self.on_listbox_double_click)

        # Context menu for listbox
        self.listbox.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.listbox.customContextMenuRequested.connect(self.on_right_click)

        main_layout.addWidget(self.wanted_callsigns_history_label, 1, 2, 1, 2)
        main_layout.addWidget(self.listbox, 2, 2, 5, 2)

        self.update_listbox()

        # ToolTip
        self.tooltip_wanted     = ToolTip(self.wanted_callsigns_var)
        self.tooltip_monitored  = ToolTip(self.monitored_callsigns_var)
        self.tooltip_excluded   = ToolTip(self.excluded_callsigns_var)

        # Focus value (sequence)
        self.focus_frame = QtWidgets.QFrame()
        self.focus_frame_layout = QtWidgets.QHBoxLayout()
        self.focus_frame.setLayout(self.focus_frame_layout)
        self.focus_value_label = QtWidgets.QLabel("")
        self.focus_value_label.setFont(custom_font_mono_lg)
        self.focus_value_label.setStyleSheet("padding: 10px;")
        self.focus_frame_layout.addWidget(self.focus_value_label)
        self.focus_frame.hide()
        self.focus_value_label.mousePressEvent = self.copy_to_clipboard

        # Timer value
        self.timer_value_label = QtWidgets.QLabel(DEFAULT_MODE_TIMER_VALUE)
        self.timer_value_label.setFont(custom_font_mono_lg)
        self.timer_value_label.setStyleSheet("background-color: #9dfffe; color: #555bc2; padding: 10px;")

        # Log analysis label and value
        self.status_label = QtWidgets.QLabel(STATUS_BUTTON_LABEL_NOTHING_YET)
        self.status_label.setFont(custom_font_mono)
        self.status_label.setStyleSheet("background-color: #D3D3D3; border: 1px solid #bbbbbb; border-radius: 10px; padding: 10px;")

        header_labels = ['Time', 'Band', 'Report', 'DT', 'Freq', 'Message', 'Country', 'CQ', 'Continent']
        self.output_table = QTableWidget(self)
        self.output_table.setColumnCount(len(header_labels))
        for i, label in enumerate(header_labels):
            header_item = QTableWidgetItem(label)
            if label in ['Band', 'Report', 'DT', 'Freq']:
                header_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            elif label in ['CQ', 'Continent']:
                header_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)                
            else:
                header_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self.output_table.setHorizontalHeaderItem(i, header_item)
        
        self.output_table.setFont(custom_font)
        self.output_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.output_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)

        self.output_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.output_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)        
        self.output_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                font-weight: normal;
            }
        """)
        self.output_table.verticalHeader().setVisible(False)
        self.output_table.verticalHeader().setDefaultSectionSize(24)
        self.output_table.setAlternatingRowColors(True)
        self.output_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.output_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.output_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.output_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.output_table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.output_table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.output_table.horizontalHeader().setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.output_table.horizontalHeader().setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.output_table.horizontalHeader().setSectionResizeMode(7, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.output_table.horizontalHeader().setSectionResizeMode(8, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.output_table.horizontalHeader().setStretchLastSection(False)
        self.output_table.setColumnWidth(0, 160)
        self.output_table.setColumnWidth(1, 45)
        self.output_table.setColumnWidth(2, 60)
        self.output_table.setColumnWidth(3, 60)
        self.output_table.setColumnWidth(4, 80)
        self.output_table.setColumnWidth(5, 400)
        self.output_table.setColumnWidth(7, 50)
        self.output_table.setColumnWidth(8, 70)

        self.output_table.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.output_table.customContextMenuRequested.connect(self.on_table_context_menu)
        self.output_table.cellClicked.connect(self.on_table_row_clicked)

        self.dark_mode = self.is_dark_apperance()
        self.apply_palette(self.dark_mode)

        self.clear_button = QtWidgets.QPushButton("Clear History")
        self.clear_button.setEnabled(False)
        self.clear_button.clicked.connect(self.clear_output_table)

        self.settings = QtWidgets.QPushButton("Settings")
        self.settings.clicked.connect(self.open_settings)

        self.disable_alert_checkbox = QtWidgets.QCheckBox("Disable all Sounds")
        self.disable_alert_checkbox.setChecked(False)
        self.disable_alert_checkbox.stateChanged.connect(self.update_alert_label_style)

        self.quit_button = QtWidgets.QPushButton("Quit")
        self.quit_button.clicked.connect(self.quit_application)

        self.inputs_enabled = True

        if platform.system() == 'Darwin':
            self.restart_button = QtWidgets.QPushButton("Restart")
            self.restart_button.clicked.connect(self.restart_application)

        # Timer and start/stop buttons
        self.status_button = QtWidgets.QPushButton(STATUS_BUTTON_LABEL_START)
        self.status_button.clicked.connect(self.start_monitoring)
        self.stop_button = QtWidgets.QPushButton("Stop all")
        self.stop_button.clicked.connect(self.stop_monitoring)

        # Organize UI components
        main_layout.addWidget(self.focus_frame, 0, 0, 1, 4)

        self.callsign_notice = QtWidgets.QLabel(CALLSIGN_NOTICE_LABEL)
        self.callsign_notice.setStyleSheet("background-color: #9dfffe; color: #555bc2;")
    
        main_layout.addWidget(self.callsign_notice, 1, 1)

        self.wanted_callsigns_label = QtWidgets.QLabel("Wanted Callsign(s):")
        self.monitored_callsigns_label = QtWidgets.QLabel("Monitored Callsign(s):")
        self.monitored_cq_zones_label = QtWidgets.QLabel("Monitored CQ Zone(s):")
        self.excluded_callsigns_label = QtWidgets.QLabel("Excluded Callsign(s):")

        self.wanted_callsigns_label.setStyleSheet("border-radius: 6px; padding: 3px;")
        self.monitored_callsigns_label.setStyleSheet("border-radius: 6px; padding: 3px;")
        self.monitored_cq_zones_label.setStyleSheet("border-radius: 6px; padding: 3px;")
        self.excluded_callsigns_label.setStyleSheet("border-radius: 6px; padding: 3px;")

        main_layout.addWidget(self.wanted_callsigns_label, 2, 0)
        main_layout.addWidget(self.wanted_callsigns_var, 2, 1)
        main_layout.addWidget(self.monitored_callsigns_label, 3, 0)
        main_layout.addWidget(self.monitored_callsigns_var, 3, 1)
    
        main_layout.addWidget(self.monitored_cq_zones_label, 4, 0)
        main_layout.addWidget(self.monitored_cq_zones_var, 4, 1)
        main_layout.addWidget(self.excluded_callsigns_label, 5, 0)
        main_layout.addWidget(self.excluded_callsigns_var, 5, 1)

        # Mode section
        mode_layout = QtWidgets.QHBoxLayout()
        mode_layout.addWidget(radio_normal)
        mode_layout.addWidget(radio_foxhound)
        mode_layout.addWidget(radio_superfox)
        main_layout.addLayout(mode_layout, 6, 1)

        # Timer label and log analysis
        main_layout.addWidget(self.timer_value_label, 0, 3)
        main_layout.addWidget(QtWidgets.QLabel("Status:"), 8, 0)
        main_layout.addWidget(self.status_label, 8, 1)

        main_layout.addWidget(self.status_button, 8, 2)
        main_layout.addWidget(self.stop_button, 8, 3)

        main_layout.addWidget(self.output_table, 9, 0, 1, 4)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.settings)
        button_layout.addWidget(self.clear_button)

        if platform.system() == 'Darwin':
            button_layout.addWidget(self.restart_button)

        button_layout.addWidget(self.quit_button)

        bottom_layout = QtWidgets.QHBoxLayout()
        bottom_layout.addWidget(self.disable_alert_checkbox)
        bottom_layout.addStretch()  
        bottom_layout.addLayout(button_layout)

        main_layout.addLayout(bottom_layout, 10, 0, 1, 4)

        self.activity_bar = ActivityBar(max_value=ACTIVITY_BAR_MAX_VALUE)
        self.activity_bar.setFixedWidth(30)

        outer_layout.addWidget(self.activity_bar)

        # Initialize the stdout redirection
        self.enable_pounce_log = params.get('enable_pounce_log', True)
        
        # Get sound configuration
        self.enable_sound_wanted_callsigns = params.get('enable_sound_wanted_callsigns', True)
        self.enable_sound_directed_my_callsign = params.get('enable_sound_directed_my_callsign', True)
        self.enable_sound_monitored_callsigns = params.get('enable_sound_monitored_callsigns', True)
       
        self.file_handler = None
        if self.enable_pounce_log:
            self.file_handler = add_file_handler(get_log_filename())

        self.gui_handler = GUIHandler(self.message_received.emit)
        self.gui_handler.setFormatter(logging.Formatter("%(message)s"))

        gui_logger = get_logger('gui')
        gui_logger.addHandler(self.gui_handler)
        gui_logger.setLevel(logging.DEBUG)

        self.load_window_position()
        self.init_activity_bar()

        # Close event to save position
        self.closeEvent = self.on_close

    @QtCore.pyqtSlot(str)
    def add_message_to_table(self, message, fg_color='white', bg_color=STATUS_TRX_COLOR):
        self.clear_button.setEnabled(True)

        row_position = self.output_table.rowCount()
        self.output_table.insertRow(row_position)

        error_item = QTableWidgetItem(message)
        error_item.setForeground(QtGui.QBrush(QtGui.QColor(fg_color)))
        error_item.setBackground(QtGui.QBrush(QtGui.QColor(bg_color)))
        error_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        error_item.setFont(custom_font_mono)

        self.output_table.setItem(row_position, 0, error_item)
        self.output_table.setSpan(row_position, 0, 1, self.output_table.columnCount())
        error_item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
        self.output_table.scrollToBottom()

    @QtCore.pyqtSlot(object)
    def handle_message_received(self, message):
        if isinstance(message, dict):
            message_type = message.get('type', None)

            if message_type == 'update_mode':
                self.mode = message.get('mode')            
            elif message_type == 'update_frequency':
                self.frequency = message.get('frequency')
                if self.frequency != self.last_frequency:
                    self.last_frequency = self.frequency
                    self.band = get_amateur_band(self.frequency)
                    frequency = str(message.get('frequency') / 1_000) + 'Khz'
                    self.add_message_to_table(f"Freq: {frequency} ({self.band})")             
            elif message_type == 'update_status':
                self.check_connection_status(
                    message.get('decode_packet_count', 0),
                    message.get('last_decode_packet_time'),
                    message.get('last_heartbeat_time'),
                    message.get('transmitting')
                )
            elif message_type is not None:
                formatted_message = message.get('formatted_message')
                if formatted_message is not None:
                    contains_my_call = message.get('contains_my_call')
                    self.set_value_to_focus(formatted_message, contains_my_call)

                play_sound = False
                if not self.disable_alert_checkbox.isChecked():      
                    if message_type == 'wanted_callsign_detected' and self.enable_sound_wanted_callsigns:
                        play_sound = True
                    elif message_type == 'directed_to_my_call' and self.enable_sound_directed_my_callsign:
                        play_sound = True
                    elif message_type == 'ready_to_log' and self.enable_sound_directed_my_callsign:
                        play_sound = True
                    elif message_type == 'error_occurred':
                        play_sound = True
                    elif (
                        message_type == 'monitored_callsign_detected' 
                    ) and self.enable_sound_monitored_callsigns:
                        current_time = datetime.now()
                        delay = 600                   
                        if (current_time - self.last_sound_played_time).total_seconds() > delay:                                                 
                            play_sound = True
                            self.last_sound_played_time = current_time               
                
                if play_sound:
                    self.play_sound(message_type)

            elif 'decode_time_str' in message:
                self.message_times.append(datetime.now())    

                callsign            = message.get('callsign')
                callsign_info       = message.get('callsign_info', None)
                directed            = message.get('directed')
                my_call             = message.get('my_call')
                wanted              = message.get('wanted')
                monitored           = message.get('monitored')
                monitored_cq_zone   = message.get('monitored_cq_zone')

                empty_str           = ''
                entity              = empty_str
                cq_zone             = empty_str
                continent           = empty_str
                
                if directed == my_call:
                    message_color      = "bright_for_my_call"
                elif wanted is True:
                    message_color      = "black_on_yellow"
                elif monitored is True:
                    message_color      = "black_on_purple" 
                elif monitored_cq_zone is True:
                    message_color      = "black_on_cyan"
                elif (
                    directed is not None and 
                    matches_any(text_to_array(self.wanted_callsigns_var.text()), directed)
                ):                    
                    message_color      = "white_on_blue"
                else:
                    message_color      = None
                
                if callsign_info:
                    entity    = (callsign_info.get("entity") or callsign_info.get("name", "Unknown")).title()
                    cq_zone   = callsign_info["cqz"]
                    continent = callsign_info["cont"]
                elif callsign_info is None:
                    entity    = "Where?"
                 
                if self.enable_show_all_decoded or message_color:
                    self.add_row_to_table(
                        callsign,
                        directed,
                        message.get('decode_time_str'),
                        self.band,
                        message.get('snr', 0),
                        message.get('delta_time', 0.0),
                        message.get('delta_freq', 0),
                        message.get('message', ''),
                        message.get('formatted_message'),
                        entity,
                        cq_zone,
                        continent,
                        message_color
                    )            

        elif isinstance(message, str):
            if message.startswith("wsjtx_id:"):
                wsjtx_id = message.split("wsjtx_id:")[1].strip()
                self.update_window_title(wsjtx_id)
            else:             
                self.add_message_to_table(message)
        else:
            pass

    def on_table_row_clicked(self, row, column):
        position = self.output_table.visualRect(self.output_table.model().index(row, column)).center()
        self.on_table_context_menu(position)        

    def on_table_context_menu(self, position):
        index = self.output_table.indexAt(position)
        if not index.isValid():
            return

        row = index.row()

        item = self.output_table.item(row, 0)
        data = item.data(QtCore.Qt.ItemDataRole.UserRole)

        if not data:
            return

        formatted_message   = data.get('formatted_message')
        callsign            = data.get('callsign')
        directed            = data.get('directed')
        cq_zone             = data.get('cq_zone')

        if not callsign:
            return

        menu = QtWidgets.QMenu()
        if sys.platform == 'darwin':
            menu.setStyleSheet(CONTEXT_MENU_DARWIN_STYLE)
            menu.setFont(menu_font)

        actions = {}

        """
            Wanted Callsigns
        """
        if callsign not in self.wanted_callsigns_var.text():
            actions['add_callsign_to_wanted'] = menu.addAction(f"Add {callsign} to Wanted Callsigns")
        else:
            actions['remove_callsign_from_wanted'] = menu.addAction(f"Remove {callsign} from Wanted Callsigns")

        if callsign != self.wanted_callsigns_var.text():
            actions['replace_wanted_with_callsign'] = menu.addAction(f"Make {callsign} your only Wanted Callsign")
        menu.addSeparator()

        """
            Monitored Callsigns
        """
        if callsign not in self.monitored_callsigns_var.text():
            actions['add_callsign_to_monitored'] = menu.addAction(f"Add {callsign} to Monitored Callsigns")
        else:
            actions['remove_callsign_from_monitored'] = menu.addAction(f"Remove {callsign} from Monitored Callsigns")
        menu.addSeparator()

        """
            Directed Callsigns
        """
        if directed:
            if directed not in self.wanted_callsigns_var.text():
                actions['add_directed_to_wanted'] = menu.addAction(f"Add {directed} to Wanted Callsigns")
            else:
                actions['remove_directed_from_wanted'] = menu.addAction(f"Remove {directed} from Wanted Callsigns")

            if directed != self.wanted_callsigns_var.text():
                actions['replace_wanted_with_directed'] = menu.addAction(f"Make {directed} your only Monitored Callsign")                

            if directed not in self.monitored_callsigns_var.text():
                actions['add_directed_to_monitored'] = menu.addAction(f"Add {directed} to Monitored Callsigns")
            else:
                actions['remove_directed_from_monitored'] = menu.addAction(f"Remove {directed} from Monitored Callsigns")
            menu.addSeparator()

        """
            Monitored CQ Zones
        """
        if cq_zone:
            try:
                if str(cq_zone) not in self.monitored_cq_zones_var.text():
                    actions['add_to_cq_zone'] = menu.addAction(f"Add Zone {cq_zone} to Monitored CQ Zones")
                else:
                    actions['remove_from_cq_zone'] = menu.addAction(f"Remove Zone {cq_zone} from Monitored CQ Zones")
            except ValueError:
                pass 
        menu.addSeparator()

        """
            Copy message
        """
        actions['copy_message'] = menu.addAction("Copy message to Clipboard")

        action = menu.exec(self.output_table.viewport().mapToGlobal(position))

        if action is None:
            return

        if action == actions.get('copy_message'):
            if formatted_message:
                pyperclip.copy(formatted_message)
                print(f"Copied to clipboard: {formatted_message}")
            else:
                print("No formatted message to copy")
        else:
            update_actions = {
                'add_callsign_to_wanted'         : lambda: self.update_var(self.wanted_callsigns_var, callsign),
                'remove_callsign_from_wanted'    : lambda: self.update_var(self.wanted_callsigns_var, callsign, "remove"),
                'replace_wanted_with_callsign'   : lambda: self.update_var(self.wanted_callsigns_var, callsign, "replace"),
                'add_callsign_to_monitored'      : lambda: self.update_var(self.monitored_callsigns_var, callsign),
                'remove_callsign_from_monitored' : lambda: self.update_var(self.monitored_callsigns_var, callsign, "remove"),
                'add_directed_to_wanted'         : lambda: self.update_var(self.wanted_callsigns_var, directed),
                'remove_directed_from_wanted'    : lambda: self.update_var(self.wanted_callsigns_var, directed, "remove"),
                'replace_wanted_with_directed'   : lambda: self.update_var(self.wanted_callsigns_var, directed, "replace"),
                'add_directed_to_monitored'      : lambda: self.update_var(self.monitored_callsigns_var, directed),
                'remove_directed_from_monitored' : lambda: self.update_var(self.monitored_callsigns_var, directed, "remove"),
                'add_to_cq_zone'                 : lambda: self.update_var(self.monitored_cq_zones_var, cq_zone),
                'remove_from_cq_zone'            : lambda: self.update_var(self.monitored_cq_zones_var, cq_zone, "remove"),
            }

            for key, act in actions.items():
                if action == act:
                    update_func = update_actions.get(key)
                    if update_func:
                        update_func()
                        break

    def update_var(self, var, value, action="add"):
        current_text = var.text()
        
        if current_text.strip() == "":
            items = []
        elif re.fullmatch(r'[0-9,\s]*', current_text):
            items = [int(num) for num in re.findall(r'\d+', current_text)]
            value = int(value)
        else:
            items = [c.strip().upper() for c in current_text.split(',') if c.strip()]
            value = value.strip().upper()

        if action == "replace":
            items = [value]
        elif action == "add" and value not in items:
            items.append(value)
        elif action == "remove" and value in items:
            items.remove(value)

        items.sort()
        var.setText(','.join(map(str, items)))

    def update_window_title(self, wsjtx_id):
            new_title = f"{self.base_title} - Connected to {wsjtx_id}"
            self.setWindowTitle(new_title)

    def reset_window_title(self):
        self.setWindowTitle(self.base_title)  

    def on_listbox_double_click(self, item):
        if self._running:
            selected_callsign = item.text()
            dialog = UpdateWantedDialog(self, selected_callsign=selected_callsign)
            result = dialog.exec()
            if result == QtWidgets.QDialog.DialogCode.Accepted:
                self.wanted_callsigns_var.setText(selected_callsign)
                if self._running:
                    self.stop_monitoring()
                    self.start_monitoring()

    def init_activity_bar(self):
        self.activity_bar.setValue(ACTIVITY_BAR_MAX_VALUE)

    def update_activity_bar(self):
        time_delta_in_seconds = get_mode_interval(self.mode)
        # We need to double time_delta_to_be_used the time transmitting == 1 
        # otherwise we are loosing accuracy of activity bar
        if self.transmitting:
            time_delta_in_seconds*= 2

        cutoff_time = datetime.now() - timedelta(seconds=time_delta_in_seconds)
        while self.message_times and self.message_times[0] < cutoff_time:
            self.message_times.popleft()

        message_count = len(self.message_times)

        self.activity_bar.setValue(message_count)                                     

    def start_blinking_status_button(self):
        if self.is_status_button_label_blinking is False:
            self.blink_timer.start(500)
            self.is_status_button_label_blinking = True

    def stop_blinking_status_button(self):    
        self.is_status_button_label_blinking = False
        self.blink_timer.stop()
        self.status_button.setVisible(True)

    def toggle_label_visibility(self):
        self.is_status_button_label_visible = not self.is_status_button_label_visible
        self.status_button.setVisible(self.is_status_button_label_visible)    

    def update_current_callsign_highlight(self):
        for index in range(self.listbox.count()):
            item = self.listbox.item(index)
            if item.text() == self.wanted_callsigns_var.text() and self._running:
                item.setBackground(QtGui.QBrush(QtGui.QColor('yellow')))
                item.setForeground(QtGui.QBrush(QtGui.QColor('black')))
            else:
                item.setBackground(QtGui.QBrush())
                item.setForeground(QtGui.QBrush())   

    def update_status_label_style(self, background_color, text_color):
        style = f"""
            background-color: {background_color};
            color: {text_color};
            border: 1px solid #bbbbbb;
            border-radius: 5px;
            padding: 5px;
        """
        self.status_label.setStyleSheet(style)            

    def set_value_to_focus(self, formatted_message, contains_my_call):
        self.focus_value_label.setText(formatted_message)
        if contains_my_call:
            bg_color_hex = BG_COLOR_FOCUS_MY_CALL
            fg_color_hex = FG_COLOR_FOCUS_MY_CALL
        else:
            bg_color_hex = BG_COLOR_REGULAR_FOCUS
            fg_color_hex = FG_COLOR_REGULAR_FOCUS
            
        self.focus_value_label.setStyleSheet(f"background-color: {bg_color_hex}; color: {fg_color_hex}; padding: 10px;")
        self.focus_frame.show()                

    def play_sound(self, sound_name):
        try:           
            if sound_name == 'wanted_callsign_detected':
                self.wanted_callsign_detected_sound.play()
            elif sound_name == 'directed_to_my_call':
                self.directed_to_my_call_sound.play()
            elif sound_name == 'monitored_callsign_detected':
                self.monitored_callsign_detected_sound.play()                        
            elif sound_name == 'ready_to_log':
                self.ready_to_log_sound.play()
            elif sound_name == 'error_occurred':
                self.error_occurred_sound.play()                
            else:
                print(f"Unknown sound: {sound_name}")            
        except Exception as e:
            print(f"Failed to play alert sound: {e}")            

    def check_connection_status(
        self,
        decode_packet_count     = None,
        last_decode_packet_time = None,
        last_heartbeat_time     = None,
        transmitting            = None
    ):
        if decode_packet_count is not None:
            self.decode_packet_count = decode_packet_count
        if last_decode_packet_time is not None:
            self.last_decode_packet_time = last_decode_packet_time
        if last_heartbeat_time is not None:
            self.last_heartbeat_time = last_heartbeat_time
        if transmitting is not None:
            self.transmitting = transmitting

        now                 = datetime.now(timezone.utc)
        current_mode        = ""
        connection_lost     = False
        nothing_to_decode   = False

        status_text_array   = []
        default_style       = "background-color: red; color: #ffffff"

        if self.mode is not None:
            current_mode = f"({self.mode})"

        status_text_array.append(f"DecodePacket #{self.decode_packet_count}")

        HEARTBEAT_TIMEOUT_THRESHOLD     = 30  # secondes
        DECODE_PACKET_TIMEOUT_THRESHOLD = 60  # secondes

        if self.last_decode_packet_time:
            time_since_last_decode = (now - self.last_decode_packet_time).total_seconds()
            network_check_status_interval = 5_000

            if time_since_last_decode > DECODE_PACKET_TIMEOUT_THRESHOLD:
                status_text_array.append(f"No DecodePacket for more than {DECODE_PACKET_TIMEOUT_THRESHOLD} seconds.")
                nothing_to_decode = True                
            else:      
                if time_since_last_decode < 3:
                    network_check_status_interval = 100
                    time_since_last_decode_text = f"{time_since_last_decode:.1f}s" 
                    self.update_status_button(STATUS_BUTTON_LABEL_DECODING, STATUS_DECODING_COLOR)                                  
                else:
                    if time_since_last_decode < 15:
                        network_check_status_interval = 1_000
                    time_since_last_decode_text = f"{int(time_since_last_decode)}s"                  
                    self.update_status_button(STATUS_BUTTON_LABEL_MONITORING, STATUS_MONITORING_COLOR) 

                status_text_array.append(f"Last DecodePacket {current_mode}: {time_since_last_decode_text} ago")    

            # Update new interval if necessary
            if network_check_status_interval != self.network_check_status_interval:
                self.network_check_status_interval = network_check_status_interval
                self.network_check_status.setInterval(self.network_check_status_interval)                               
        else:
            status_text_array.append("No DecodePacket received yet.")
            if self._running:
                self.update_status_button(STATUS_BUTTON_LABEL_MONITORING, STATUS_MONITORING_COLOR) 

        if self.transmitting:
            self.start_blinking_status_button()
            network_check_status_interval = 100
            self.update_status_button(STATUS_BUTTON_LABEL_TRX, STATUS_TRX_COLOR)
        else:
            self.stop_blinking_status_button()
        
        if self.last_heartbeat_time:
            time_since_last_heartbeat = (now - self.last_heartbeat_time).total_seconds()
            if time_since_last_heartbeat > HEARTBEAT_TIMEOUT_THRESHOLD:
                status_text_array.append(f"No HeartBeat for more than {HEARTBEAT_TIMEOUT_THRESHOLD} seconds.")
                connection_lost = True
            else:
                last_heartbeat_str = self.last_heartbeat_time.strftime('%Y-%m-%d <u>%H:%M:%S</u>')
                status_text_array.append(f"Last HeartBeat @ {last_heartbeat_str}")
        else:
            status_text_array.append("No HeartBeat received yet.")

        self.status_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.status_label.setText('<br>'.join(status_text_array))

        if connection_lost:
            self.update_status_label_style("red", "white")
            if not self.connection_lost_shown:
                self.connection_lost_shown = True
        elif nothing_to_decode: 
            self.update_status_label_style("white", "black")
        else:
            self.connection_lost_shown = False
            self.update_status_label_style("yellow", "black")

    def on_close(self, event):        
        self.save_window_position()
        if self._running:
            self.stop_monitoring()
        event.accept()

    def open_settings(self):
        params = self.load_params()

        dialog = SettingsDialog(self, params)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            new_params = dialog.get_result()
        
            previous_enable_pounce_log = self.enable_pounce_log
            self.enable_pounce_log = new_params.get('enable_pounce_log', True)

            params.update(new_params)
            self.save_params(params)

            log_filename = get_log_filename()

            self.enable_sound_wanted_callsigns = params.get('enable_sound_wanted_callsigns', True)
            self.enable_sound_directed_my_callsign = params.get('enable_sound_directed_my_callsign', True)
            self.enable_sound_monitored_callsigns = params.get('enable_sound_monitored_callsigns', True)

            if self.enable_pounce_log and not previous_enable_pounce_log:
                self.file_handler = add_file_handler(log_filename)
            elif not self.enable_pounce_log and previous_enable_pounce_log:
                remove_file_handler(self.file_handler)
                self.file_handler = None

            if self._running:
                self.stop_monitoring()
                self.start_monitoring()

    def quit_application(self):
        self.save_window_position()
        QtWidgets.QApplication.quit()

    def restart_application(self):
        self.save_window_position()

        QtCore.QProcess.startDetached(sys.executable, sys.argv)
        QtWidgets.QApplication.quit()

    def is_dark_apperance(self):
        try:
            if sys.platform == 'darwin':
                from Foundation import NSUserDefaults
                defaults = NSUserDefaults.standardUserDefaults()
                osx_appearance = defaults.stringForKey_("AppleInterfaceStyle")
                return osx_appearance == 'Dark'
            elif sys.platform == 'win32':
                import winreg
                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return value == 0
        except Exception as e:
            print(f"Can't know if we are either using Dark or Light mode: {e}")
            return False
        
    def check_theme_change(self):
        current_dark_mode = self.is_dark_apperance()
        if current_dark_mode != self.dark_mode:
            self.dark_mode = current_dark_mode
            self.apply_palette(self.dark_mode)
        
    def apply_palette(self, dark_mode):
        self.dark_mode = dark_mode
        
        if dark_mode:
            qt_bg_color = QtGui.QColor("#181818")
            qt_fg_color = QtGui.QColor("#ECECEC")

            palette = QtGui.QPalette()
            palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor('#3C3C3C'))
            palette.setColor(QtGui.QPalette.ColorRole.WindowText, qt_fg_color)
            palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor('#353535'))
            palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor('#454545'))
            palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, qt_fg_color)
            palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, qt_fg_color)
            palette.setColor(QtGui.QPalette.ColorRole.Text, qt_fg_color)
            palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor('#4A4A4A'))
            palette.setColor(QtGui.QPalette.ColorRole.ButtonText, qt_fg_color)
            palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtCore.Qt.GlobalColor.red)
            palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor('#2A82DA'))
            palette.setColor(QtGui.QPalette.ColorRole.Highlight, qt_fg_color)
            palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, qt_bg_color)
            palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.Text, QtGui.QColor('#6C6C6C'))
        else:

            qt_bg_color = QtGui.QColor("#ECECEC")
            qt_fg_color = QtGui.QColor("#000000")
        
            palette = QtGui.QPalette()
            palette.setColor(QtGui.QPalette.ColorRole.Window, qt_bg_color)
            palette.setColor(QtGui.QPalette.ColorRole.WindowText, qt_fg_color)
            palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor('white'))
            palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor('#B6B6B6'))
            palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, qt_bg_color)
            palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, qt_bg_color)
            palette.setColor(QtGui.QPalette.ColorRole.Text, QtCore.Qt.GlobalColor.black)
            palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor('#E0E0E0'))
            palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtCore.Qt.GlobalColor.black)
            palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtCore.Qt.GlobalColor.red)
            palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor('#2A82DA'))
            palette.setColor(QtGui.QPalette.ColorRole.Highlight, qt_bg_color)
            palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, qt_fg_color)
            palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.Text, QtGui.QColor('#7F7F7F'))

        
        self.setPalette(palette)
        table_palette = self.output_table.palette()
        
        if dark_mode:
            table_palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor('#353535'))
            table_palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor('#454545'))
            table_palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor('white'))
        else:
            table_palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor('white'))
            table_palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor('#f4f5f5'))
            table_palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor('black'))
        
        self.output_table.setPalette(table_palette)
                
        # self.update_stylesheet(dark_mode)

    def disable_inputs(self):
        self.inputs_enabled = False
        self.monitored_callsigns_var.setEnabled(False)
        self.monitored_cq_zones_var.setEnabled(False)
        self.excluded_callsigns_var.setEnabled(False)
        self.wanted_callsigns_var.setEnabled(False)

    def enable_inputs(self):
        self.inputs_enabled = True
        self.monitored_callsigns_var.setEnabled(True)
        self.monitored_cq_zones_var.setEnabled(True)
        self.excluded_callsigns_var.setEnabled(True)
        self.wanted_callsigns_var.setEnabled(True)

    def save_params(self, params):
        with open(PARAMS_FILE, "wb") as f:
            pickle.dump(params, f)

    def load_params(self):
        if os.path.exists(PARAMS_FILE):
            with open(PARAMS_FILE, "rb") as f:
                return pickle.load(f)
        return {}

    def save_wanted_callsigns(self, wanted_callsigns_history):
        with open(WANTED_CALLSIGNS_FILE, "wb") as f:
            pickle.dump(wanted_callsigns_history, f)

    def load_wanted_callsigns(self):
        if os.path.exists(WANTED_CALLSIGNS_FILE):
            with open(WANTED_CALLSIGNS_FILE, "rb") as f:
                return pickle.load(f)
        return []

    """
        Used for MonitoringSetting
    """

    def on_wanted_callsigns_changed(self):
        self.monitoring_settings.set_wanted_callsigns(self.wanted_callsigns_var.text())
        if self.worker is not None:
            self.worker.update_settings_signal.emit()

    def on_monitored_callsigns_changed(self):
        self.monitoring_settings.set_monitored_callsigns(self.monitored_callsigns_var.text())
        if self.worker is not None:
            self.worker.update_settings_signal.emit()

    def on_excluded_callsigns_changed(self):
        self.monitoring_settings.set_excluded_callsigns(self.excluded_callsigns_var.text())
        if self.worker is not None:
            self.worker.update_settings_signal.emit()

    def on_monitored_cq_zones_changed(self):
        self.monitoring_settings.set_monitored_cq_zones(self.monitored_cq_zones_var.text())
        if self.worker is not None:
            self.worker.update_settings_signal.emit()

    def update_wanted_callsigns_history(self, new_callsign):
        if new_callsign:
            if new_callsign not in self.wanted_callsigns_history:
                self.wanted_callsigns_history.append(new_callsign)
                if len(self.wanted_callsigns_history) > WANTED_CALLSIGNS_HISTORY_SIZE:
                    self.wanted_callsigns_history.pop(0)
                self.save_wanted_callsigns(self.wanted_callsigns_history)
                self.update_listbox()

    def update_listbox(self):
        self.listbox.clear()
        self.listbox.addItems(self.wanted_callsigns_history)
        self.update_wanted_callsigns_history_counter()

    def update_wanted_callsigns_history_counter(self):
        self.wanted_callsigns_history_label.setText(WANTED_CALLSIGNS_HISTORY_LABEL % len(self.wanted_callsigns_history))

    def update_alert_label_style(self):
        if self.disable_alert_checkbox.isChecked():
            self.disable_alert_checkbox.setStyleSheet(f"background-color: {BG_COLOR_BLACK_ON_CYAN};")
        else:
            self.disable_alert_checkbox.setStyleSheet("")

    def on_right_click(self, position):
        menu = QtWidgets.QMenu()
        if sys.platform == 'darwin':
            menu.setStyleSheet(CONTEXT_MENU_DARWIN_STYLE)
            menu.setFont(menu_font)
        
        remove_action = menu.addAction("Remove entry")

        menu.addSeparator()
        edit_action = menu.addAction("Edit entry")

        action = menu.exec(self.listbox.mapToGlobal(position))
        if action == remove_action:
            self.remove_callsign_from_history()
        elif action == edit_action:
            self.edit_callsigns()

    def remove_callsign_from_history(self):
        selected_items = self.listbox.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            self.wanted_callsigns_history.remove(item.text())
            self.listbox.takeItem(self.listbox.row(item))
        self.save_wanted_callsigns(self.wanted_callsigns_history)
        self.update_wanted_callsigns_history_counter()

    def edit_callsigns(self):
        selected_items = self.listbox.selectedItems()
        if not selected_items:
            return
        current_entry = selected_items[0].text()
        dialog = EditWantedDialog(self, initial_value=current_entry)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            new_callsigns = dialog.get_result()
            index = self.listbox.row(selected_items[0])
            self.wanted_callsigns_history[index] = new_callsigns
            self.listbox.item(index).setText(new_callsigns)
            self.save_wanted_callsigns(self.wanted_callsigns_history)
            self.update_wanted_callsigns_history_counter()

    def copy_to_clipboard(self, event):
        message = self.focus_value_label.text()
        pyperclip.copy(message)
        print(f"Copied to clipboard: {message}")

    def add_row_to_table(
            self,
            callsign,
            directed,
            date_str,
            band,
            snr,
            delta_time,
            delta_freq,
            message,
            formatted_message,
            entity,
            cq_zone,
            continent,
            row_color         = None
        ):
        self.clear_button.setEnabled(True)
        row_position = self.output_table.rowCount()
        self.output_table.insertRow(row_position)
        
        item_date = QTableWidgetItem(date_str)
        item_date.setData(QtCore.Qt.ItemDataRole.UserRole, {
            'callsign'          : callsign, 
            'directed'          : directed,
            'cq_zone'           : cq_zone,
            'formatted_message' : formatted_message.strip()
        })
        self.output_table.setItem(row_position, 0, item_date)

        item_band = QTableWidgetItem(band)
        item_band.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        item_band.setFont(small_font)
        self.output_table.setItem(row_position, 1, item_band)
            
        item_snr = QTableWidgetItem(f"{snr:+3d} dB")
        item_snr.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        item_snr.setFont(small_font)
        self.output_table.setItem(row_position, 2, item_snr)
        
        item_dt = QTableWidgetItem(f"{delta_time:+5.1f}s")
        item_dt.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        item_dt.setFont(small_font)
        self.output_table.setItem(row_position, 3, item_dt)
        
        item_freq = QTableWidgetItem(f"{delta_freq:+6d}Hz")
        item_freq.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        item_freq.setFont(small_font)
        self.output_table.setItem(row_position, 4, item_freq)
        
        # Make sure to let an extra space to "message" to add left padding
        item_msg = QTableWidgetItem(f" {message}")
        # item_msg.setFont(custom_font_mono)
        self.output_table.setItem(row_position, 5, item_msg)
        
        item_country = QTableWidgetItem(entity)
        self.output_table.setItem(row_position, 6, item_country)

        item_cq_zone = QTableWidgetItem(f"{cq_zone}")
        item_cq_zone.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.output_table.setItem(row_position, 7, item_cq_zone)

        item_continent = QTableWidgetItem(continent)
        item_continent.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.output_table.setItem(row_position, 8, item_continent)        
        
        if row_color:
            self.apply_row_format(row_position, row_color)
        
        self.output_table.scrollToBottom()
        
    def apply_row_format(self, row, row_color):
        if row_color == 'bright_for_my_call':
            bg_color = QtGui.QColor(BG_COLOR_FOCUS_MY_CALL)
            fg_color = QtGui.QColor(FG_COLOR_FOCUS_MY_CALL)
        elif row_color == 'black_on_yellow':
            bg_color = QtGui.QColor(BG_COLOR_BLACK_ON_YELLOW)
            fg_color = QtGui.QColor(FG_COLOR_BLACK_ON_YELLOW)
        elif row_color == 'black_on_purple':
            bg_color = QtGui.QColor(BG_COLOR_BLACK_ON_PURPLE)
            fg_color = QtGui.QColor(FG_COLOR_BLACK_ON_PURPLE)
        elif row_color == 'white_on_blue':
            bg_color = QtGui.QColor(BG_COLOR_WHITE_ON_BLUE)
            fg_color = QtGui.QColor(FG_COLOR_WHITE_ON_BLUE)
        elif row_color == 'black_on_cyan':
            bg_color = QtGui.QColor(BG_COLOR_BLACK_ON_CYAN)
            fg_color = QtGui.QColor(FG_COLOR_BLACK_ON_CYAN)
        else:
            bg_color = None
            fg_color = None

        if bg_color and fg_color:
            for col in range(self.output_table.columnCount()):
                item = self.output_table.item(row, col)
                if item:
                    item.setBackground(bg_color)
                    item.setForeground(fg_color)

    def clear_output_table(self):
        self.output_table.setRowCount(0)
        self.clear_button.setEnabled(False)
        self.focus_frame.hide()

    def save_window_position(self):
        position = self.geometry()
        position_data = {
            'x': position.x(),
            'y': position.y(), 
            'width': position.width(),
            'height': position.height()
        }
        with open(POSITION_FILE, "wb") as f:
            pickle.dump(position_data, f)

    def load_window_position(self):
        if os.path.exists(POSITION_FILE):
            with open(POSITION_FILE, "rb") as f:
                position_data = pickle.load(f)
                if 'width' in position_data and 'height' in position_data:
                    self.setGeometry(position_data['x'], position_data['y'], position_data['width'], position_data['height'])
                else:
                    self.setGeometry(100, 100, 900, 700) 
                    os.remove(POSITION_FILE)
        else:
            self.setGeometry(100, 100, 900, 700) 

    def update_mode_timer(self):
        current_time = datetime.now(timezone.utc)
        utc_time = current_time.strftime("%H:%M:%S")

        if (current_time.second // get_mode_interval(self.mode)) % 2 == 0:
            background_color = EVEN_COLOR
        else:
            background_color = ODD_COLOR

        self.timer_value_label.setText(utc_time)
        self.timer_value_label.setStyleSheet(f"background-color: {background_color}; color: #3d25fb; padding: 10px;")

    def update_status_button(self, text, bg_color, fg_color="#ffffff"):
        self.status_button.setEnabled(False)
        self.status_button.setText(text)
        self.status_button.setStyleSheet(f"background-color: {bg_color}; color: {fg_color}; padding: 5px; border-radius: 5px; border: none;")

    def start_monitoring(self):
        global tray_icon

        self._running = True   

        self.network_check_status.start(self.network_check_status_interval)

         # Timer to update time every second
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_mode_timer)
        self.timer.start(200)

        # self.output_text.clear()
        self.update_status_button(STATUS_BUTTON_LABEL_MONITORING, STATUS_MONITORING_COLOR)

        self.blink_timer = QtCore.QTimer()
        self.blink_timer.timeout.connect(self.toggle_label_visibility)

        self.is_status_button_label_visible = True
        self.is_status_button_label_blinking = False

        # self.disable_inputs()
        self.stop_event.clear()
        self.focus_frame.hide()
        self.callsign_notice.hide()

        # For decorative purpose only and to match with color being used on output_text 
        self.wanted_callsigns_label.setStyleSheet(f"background-color: {BG_COLOR_BLACK_ON_YELLOW}; color: {FG_COLOR_BLACK_ON_YELLOW}; border-radius: 6px; padding: 3px;")
        self.monitored_callsigns_label.setStyleSheet(f"background-color: {BG_COLOR_BLACK_ON_PURPLE}; color: {FG_COLOR_BLACK_ON_PURPLE}; border-radius: 6px; padding: 3px;")
        self.monitored_cq_zones_label.setStyleSheet(f"background-color: {BG_COLOR_BLACK_ON_CYAN}; color: {FG_COLOR_BLACK_ON_CYAN}; border-radius: 6px; padding: 3px;")

        if platform.system() == 'Windows':
            tray_icon = TrayIcon()
            tray_icon_thread = threading.Thread(target=tray_icon.start, daemon=True)
            tray_icon_thread.start()

        monitored_callsigns                 = self.monitored_callsigns_var.text()
        monitored_cq_zones                  = self.monitored_cq_zones_var.text()
        excluded_callsigns                  = self.excluded_callsigns_var.text()
        wanted_callsigns                    = self.wanted_callsigns_var.text()
        special_mode                        = self.special_mode_var.checkedButton().text()

        params                              = self.load_params()
        local_ip_address                    = get_local_ip_address()

        primary_udp_server_address          = params.get('primary_udp_server_address') or local_ip_address
        primary_udp_server_port             = int(params.get('primary_udp_server_port') or DEFAULT_UDP_PORT)
        secondary_udp_server_address        = params.get('secondary_udp_server_address') or local_ip_address
        secondary_udp_server_port           = int(params.get('secondary_udp_server_port') or DEFAULT_UDP_PORT)
        enable_secondary_udp_server         = params.get('enable_secondary_udp_server', DEFAULT_SECONDARY_UDP_SERVER)
        enable_sending_reply                = params.get('enable_sending_reply', DEFAULT_SENDING_REPLY)
        enable_gap_finder                    = params.get('enable_gap_finder', DEFAULT_GAP_FINDER)
        enable_watchdog_bypass              = params.get('enable_watchdog_bypass', DEFAULT_WATCHDOG_BYPASS)
        enable_debug_output                 = params.get('enable_debug_output', DEFAULT_DEBUG_OUTPUT)
        enable_pounce_log                   = params.get('enable_pounce_log', DEFAULT_POUNCE_LOG)
        enable_log_packet_data              = params.get('enable_log_packet_data', DEFAULT_LOG_PACKET_DATA)
        
        self.enable_show_all_decoded        = params.get('enable_show_all_decoded', DEFAULT_SHOW_ALL_DECODED)

        self.update_wanted_callsigns_history(wanted_callsigns)
        self.update_current_callsign_highlight()

        params.update({
            "monitored_callsigns"           : monitored_callsigns,
            "monitored_cq_zones"            : monitored_cq_zones,
            "excluded_callsigns"            : excluded_callsigns,
            "wanted_callsigns"              : wanted_callsigns,
            "special_mode"                  : special_mode
        })
        self.save_params(params)

        self.status_label.setText(WAITING_DATA_PACKETS_LABEL)    
        self.update_status_label_style("yellow", "black")

        # Create a QThread and a Worker object
        self.thread = QThread()
        self.worker = Worker(
            self.monitoring_settings,
            monitored_callsigns,
            monitored_cq_zones,
            excluded_callsigns,
            wanted_callsigns,
            special_mode,
            self.stop_event,
            primary_udp_server_address,
            primary_udp_server_port,
            secondary_udp_server_address,
            secondary_udp_server_port,
            enable_secondary_udp_server,
            enable_sending_reply,
            enable_gap_finder,
            enable_watchdog_bypass,
            enable_debug_output,
            enable_pounce_log,
            enable_log_packet_data          
        )
        self.worker.moveToThread(self.thread)

        # Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # Connect worker's signals to the GUI slots
        # self.worker.finished.connect(self.stop_monitoring)
        self.worker.error.connect(self.add_message_to_table)
        self.worker.message.connect(self.handle_message_received)

        self.thread.start()    

    def stop_monitoring(self):
        global tray_icon

        self.network_check_status.stop()
        self.activity_bar.setValue(0) 
        
        self.timer.stop()
        self.timer_value_label.setText(DEFAULT_MODE_TIMER_VALUE)

        if tray_icon:
            tray_icon.stop()
            tray_icon = None

        if self._running:
            self.stop_event.set()

            if hasattr(self, 'thread') and self.thread is not None:
                try:
                    if self.thread.isRunning():
                        self.thread.quit()
                        self.thread.wait()
                        self.thread = None
                except RuntimeError as e:
                    print(f"RuntimeError when stopping thread: {e}")                        
                finally:
                    self.thread = None                        

            self.worker = None
            self._running = False

            self.status_button.setEnabled(True)
            self.status_button.setText(STATUS_BUTTON_LABEL_START)
            self.status_button.setStyleSheet("")

            self.stop_blinking_status_button()

            self.wanted_callsigns_label.setStyleSheet("")
            self.monitored_callsigns_label.setStyleSheet("")
            self.monitored_cq_zones_label.setStyleSheet("")

            self.callsign_notice.show()
            self.transmitting = False

            self.update_status_label_style("grey", "white")
            
            self.update_current_callsign_highlight()
            # self.enable_inputs()
            self.reset_window_title()

    def log_exception_to_file(self, filename, message):
        timestamp = datetime.now(timezone.utc).strftime("%y%m%d_%H%M%S")
        with open(filename, "a") as log_file:
            log_file.write(f"{timestamp} {message}\n")

def check_expiration():
    current_date = datetime.now()
    if current_date > EXPIRATION_DATE:      
        expiration_date_str = EXPIRATION_DATE.strftime('%B %d, %Y')

        msg_box = QtWidgets.QMessageBox()
        msg_box.setWindowTitle("Program Expired")

        label = QtWidgets.QLabel(f"{GUI_LABEL_VERSION} expired on <u>{expiration_date_str}</u>. Please contact author.")
        label.setFont(small_font)
        label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        
        msg_box.setText("")
        msg_box.layout().addWidget(label, 0, 1)
        
        msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        msg_box.resize(450, 650)
        msg_box.exec()
        sys.exit()

def main():
    check_expiration()

    app = QtWidgets.QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
