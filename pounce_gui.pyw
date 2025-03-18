# pounce_gui.pyw

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import QPropertyAnimation
from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtMultimedia import QSoundEffect

import platform
import re
import sys
import pickle
import os
import threading
import pyperclip
import sys
import threading
import uuid

"""
    Not to be deleted because it allows for one-off debugging
"""
import inspect
import traceback

from datetime import datetime, timezone, timedelta
from collections import deque, defaultdict
from queue import Queue
from functools import partial

# Custom classes 
from animated_toggle import AnimatedToggle
from custom_tab_widget import CustomTabWidget
from custom_button import CustomButton
from custom_qlabel import CustomQLabel
from adif_summary_dialog import AdifSummaryDialog
from time_ago_delegate import TimeAgoDelegate
from color_row_delegate import ColorRowDelegate
from search_field_input import SearchFilterInput
from tray_icon import TrayIcon
from activity_bar import ActivityBar
from tooltip import ToolTip
from worker import Worker
from monitoring_setting import MonitoringSettings
from theme_manager import ThemeManager
from clublog import ClubLogManager
from setting_dialog import SettingsDialog
from updater import Updater, UpdateManager
from raw_data_model import RawDataModel
from raw_data_filter_proxy_model import RawDataFilterProxyModel

if sys.platform == 'darwin':
    from status_menu import StatusMenuAgent

from utils import get_local_ip_address, get_log_filename, matches_any
from utils import get_mode_interval, get_amateur_band, display_frequency
from utils import force_input, focus_out_event, text_to_array, has_significant_change
from utils import parse_adif

from version import is_first_launch_or_new_version, save_current_version

from logger import get_logger, add_file_handler, remove_file_handler

from utils import(
    AMATEUR_BANDS
)

from constants import (
    CURRENT_VERSION_NUMBER,
    MASTER,
    SLAVE,
    # Colors
    EVEN_COLOR,
    ODD_COLOR,
    FG_TIMER_COLOR,
    FG_COLOR_FOCUS_MY_CALL,
    BG_COLOR_FOCUS_MY_CALL,
    FG_COLOR_REGULAR_FOCUS,
    BG_COLOR_REGULAR_FOCUS,
    BG_COLOR_BLACK_ON_YELLOW,
    FG_COLOR_BLACK_ON_YELLOW,
    BG_COLOR_WHITE_ON_BLUE,
    FG_COLOR_BLACK_ON_WHITE,
    BG_COLOR_BLACK_ON_PURPLE,
    FG_COLOR_BLACK_ON_PURPLE,
    BG_COLOR_BLACK_ON_CYAN,
    FG_COLOR_BLACK_ON_CYAN,    
    # Status buttons
    STATUS_MONITORING_COLOR,
    STATUS_DECODING_COLOR,
    STATUS_TRX_COLOR,
    STATUS_COLOR_LABEL_SELECTED,
    # Actions
    ACTION_RESTART,
    # Parameters
    PARAMS_FILE,
    POSITION_FILE,
    WORKED_CALLSIGNS_FILE,
    # Labels
    GUI_LABEL_NAME,
    GUI_LABEL_VERSION,
    STATUS_BUTTON_LABEL_MONITORING,
    STATUS_BUTTON_LABEL_DECODING,
    STATUS_BUTTON_LABEL_START,
    STATUS_BUTTON_LABEL_TRX,
    STATUS_BUTTON_LABEL_NOTHING_YET,
    STOP_BUTTON_LABEL,
    WAITING_DATA_PACKETS_LABEL,
    WORKED_CALLSIGNS_HISTORY_LABEL,
    CALLSIGN_NOTICE_LABEL,
    CQ_ZONE_NOTICE_LABEL,
    # Datetime column
    DATE_COLUMN_DATETIME,
    DATE_COLUMN_AGE,
    # Timer
    DEFAULT_MODE_TIMER_VALUE,
    # Band,
    DEFAULT_SELECTED_BAND,
    # Needed for filtering
    DEFAULT_FILTER_VALUE,
    DEFAULT_REPLY_ATTEMPTS,
    # Working directory
    CURRENT_DIR,
    # UDP related
    DEFAULT_UDP_PORT,
    DEFAULT_SECONDARY_UDP_SERVER,
    DEFAULT_SENDING_REPLY,
    # Default settings
    DEFAULT_GAP_FINDER,
    DEFAULT_WATCHDOG_BYPASS,
    DEFAULT_DEBUG_OUTPUT,
    DEFAULT_POUNCE_LOG,
    DEFAULT_LOG_PACKET_DATA,
    DEFAULT_SHOW_ALL_DECODED,
    DEFAULT_LOG_ALL_VALID_CONTACT,
    DEFAULT_DELAY_BETWEEN_SOUND,
    DEFAULT_MAX_WAITING_DELAY,
    ACTIVITY_BAR_MAX_VALUE,
    WKB4_REPLY_MODE_ALWAYS,
    # QSS
    CONTEXT_MENU_DARWIN_QSS,
    CONTEXT_MENU_HEADER_QSS,
    # Fonts
    CUSTOM_FONT,
    CUSTOM_FONT_MONO,
    CUSTOM_FONT_MONO_LG,
    CUSTOM_FONT_SMALL,
    MENU_FONT,
    # URL
    DISCORD_SECTION,
    DONATION_SECTION,
    # Threshold
    HEARTBEAT_TIMEOUT_THRESHOLD,
    DECODE_PACKET_TIMEOUT_THRESHOLD
)

log         = get_logger(__name__)
stop_event  = threading.Event()


""""
    Need to be provided for showing the icon in the taskbar for Windows 11
"""
try:
    from ctypes import windll  
    myappid = f"f5ukw.waitandpounce.{CURRENT_VERSION_NUMBER}"
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass

"""
    Main Application
"""
class MainApp(QtWidgets.QMainWindow):
    error_occurred = QtCore.pyqtSignal(str)    
    message_received = QtCore.pyqtSignal(object)

    def __init__(self):
        super(MainApp, self).__init__()


        self.base_title          = GUI_LABEL_VERSION
        self.window_title        = None

        self.worker              = None
        self.timer               = None
        self.tray_icon           = None

        self.monitoring_settings = MonitoringSettings()       
        self.clublog_manager     = ClubLogManager(self) 
        self.status_menu_agent   = None

        self.updater             = Updater()
        params                   = self.load_params()  

        """
            Status bar for MacOsx
        """
        if sys.platform == 'darwin':
            self.status_menu_agent = StatusMenuAgent()
            self.status_menu_agent.clicked.connect(self.on_status_menu_clicked)
            self.status_menu_agent.run()
            
            self.pobjc_timer = QtCore.QTimer(self)
            self.pobjc_timer.timeout.connect(self.status_menu_agent.process_events)
            self.pobjc_timer.start(10) 
        
        """
            Store data from update_model_data
        """
        self.output_model           = RawDataModel()
        self.filter_proxy_model      = RawDataFilterProxyModel()
        self.filter_proxy_model.setSourceModel(self.output_model)

        self.combo_box_values       = {
            "band"      : set(),
            "continent" : set(),
            "cq_zone"   : set(),
        }
                
        self.setGeometry(100, 100, 1_000, 700)
        self.setMinimumSize(900, 600)
        self.setWindowTitle(self.base_title)      

        if platform.system() == 'Windows':
            if getattr(sys, 'frozen', False): 
                icon_path = os.path.join(sys._MEIPASS, "pounce.ico")
            else:
                icon_path = "pounce.ico"

            self.setWindowIcon(QtGui.QIcon(icon_path))    

        self.stop_event = threading.Event()
        self.error_occurred.connect(self.set_notice_to_focus_value_label)
        self.message_received.connect(self.on_message_received)

        self.message_times = deque()
        
        self.activity_bar_timer = QtCore.QTimer()
        self.activity_bar_timer.timeout.connect(self.update_activity_bar)
        self.activity_bar_timer.start(100)
        self.theme_manager = ThemeManager()
        self.theme_manager.theme_changed.connect(self.apply_theme_to_all)

        self.theme_timer = QtCore.QTimer(self)
        self.theme_timer.timeout.connect(self.theme_manager.check_theme_change)
        self.theme_timer.start(1_000) 

        self.network_check_status_interval = 5_000
        self.network_check_status = QtCore.QTimer()
        self.network_check_status.timeout.connect(self.check_connection_status)

        self._running                           = False
        self._instance                          = MASTER
        self._connected                         = True

        self.decode_packet_count                = 0
        self.last_decode_packet_time            = None
        self.last_heartbeat_time                = None
        self.last_focus_value_message_uid       = None 
        self.last_transmit_time                 = False               
        self.last_sound_played_time             = datetime.min
        self.mode                               = None
        self.my_call                            = None
        self.last_targeted_call                 = None
        self.my_wsjtx_id                        = None
        self.transmitting                       = False
        self.band                               = None
        self.last_frequency                     = None
        self.frequency                          = None
        self.gui_selected_band                  = None
        self.operating_band                     = None
        self.enable_show_all_decoded            = None
        self.message_buffer                     = deque()        
                
        self.menu_bar                           = self.menuBar() 

        self.sound_queue                        = Queue()
        self.sound_timer                        = QtCore.QTimer()
        self.sound_timer.timeout.connect(self.play_next_sound)
        self.currently_playing = False

        self.wanted_callsign_detected_sound     = QSoundEffect()
        self.wanted_callsign_being_called_sound = QSoundEffect()
        self.directed_to_my_call_sound          = QSoundEffect()
        self.ready_to_log_sound                 = QSoundEffect()
        self.error_occurred_sound               = QSoundEffect()
        self.band_change_sound                  = QSoundEffect()
        self.updated_settings                   = QSoundEffect()
        self.monitored_callsign_detected_sound  = QSoundEffect()
        self.enabled_global_sound               = QSoundEffect()

        self.wanted_callsign_detected_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/495650__matrixxx__supershort-ping-or-short-notification.wav"))
        self.wanted_callsign_being_called_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/716444__scottyd0es__tone12_alert_5.wav"))
        self.directed_to_my_call_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/716445__scottyd0es__tone12_error.wav"))
        self.ready_to_log_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/709072__scottyd0es__aeroce-dualtone-5.wav"))
        self.error_occurred_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/142608__autistic-lucario__error.wav"))
        self.monitored_callsign_detected_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/716442__scottyd0es__tone12_alert_3.wav"))
        self.band_change_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/342759__rhodesmas__score-counter-01.wav"))
        self.updated_settings.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/342757__rhodesmas__searching-03.wav"))
        self.enabled_global_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/342754__rhodesmas__searching-01.wav"))
        
        self.enable_pounce_log                  = params.get('enable_pounce_log', True)
        self.enable_filter_gui                   = params.get('enable_filter_gui', False)        
        self.enable_global_sound                = params.get('enable_global_sound', True)
        self.datetime_column_setting            = params.get('datetime_column_setting', DATE_COLUMN_DATETIME)
        self.enable_show_all_decoded            = params.get('enable_show_all_decoded', DEFAULT_SHOW_ALL_DECODED)

        self.adif_file_path                      = params.get('adif_file_path', None)
        self.worked_before_preference           = params.get('worked_before_preference', WKB4_REPLY_MODE_ALWAYS)
        self.enable_marathon                    = params.get('enable_marathon', False)
        self.marathon_preference                = params.get('marathon_preference', {})
        
        # Get sound configuration
        self.enable_sound_wanted_callsigns      = params.get('enable_sound_wanted_callsigns', True)
        self.enable_sound_directed_my_callsign  = params.get('enable_sound_directed_my_callsign', True)
        self.enable_sound_monitored_callsigns   = params.get('enable_sound_monitored_callsigns', True)
        self.delay_between_sound_for_monitored  = params.get('delay_between_sound_for_monitored', DEFAULT_DELAY_BETWEEN_SOUND)
       
        """
            Central, Outer and Main Layout
        """
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        outer_layout = QtWidgets.QHBoxLayout()
        central_widget.setLayout(outer_layout)

        main_layout = QtWidgets.QGridLayout()
        outer_layout.addLayout(main_layout)

        """
            Wait and Pounce History
        """
        self.worked_callsigns_history = [] 

        self.wait_pounce_history_table = self.init_wait_pounce_history_table_ui()
        self.wait_pounce_history_table.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        #self.wait_pounce_history_table.setItemDelegate(ColorRowDelegate(self.wait_pounce_history_table))

        refresh_history_table_timer = QtCore.QTimer(self)
        refresh_history_table_timer.start(1_000)        
        refresh_history_table_timer.timeout.connect(lambda: self.wait_pounce_history_table.viewport().update())

        self.worked_history_callsigns_label = QtWidgets.QLabel()
        self.worked_history_callsigns_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignLeft
        )
        self.worked_history_callsigns_label.setFont(CUSTOM_FONT)
        self.worked_history_callsigns_label.setMinimumHeight(25)
        """
            Top layout for focus_frame and timer_value_label
        """
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 5)
        top_layout.setSpacing(0)
        self.focus_frame = QtWidgets.QFrame()
        self.focus_frame_layout = QtWidgets.QHBoxLayout()
        self.focus_frame_layout.setContentsMargins(0, 0, 0, 0)
        self.focus_frame.setLayout(self.focus_frame_layout)
        self.focus_value_label = QtWidgets.QLabel()
        self.focus_value_label.setFont(CUSTOM_FONT_MONO_LG)
        self.focus_value_label.setFixedHeight(50)
        self.focus_value_label.setStyleSheet("padding: 10px;")
        self.focus_value_label.mousePressEvent = self.on_focus_value_label_clicked        
        self.focus_frame_layout.addWidget(self.focus_value_label) 
        self.focus_frame.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        
        top_layout.addWidget(self.focus_frame)
        top_layout.addSpacing(15)

        """
            Timer label
        """
        self.timer_value_label = QtWidgets.QLabel(DEFAULT_MODE_TIMER_VALUE)
        self.timer_value_label.setFont(CUSTOM_FONT_MONO_LG)
        self.timer_value_label.setStyleSheet("""
            background-color: #9dfffe;
            color: #555bc2;
            padding: 10px;
            border-radius: 8px;
        """)
        self.timer_value_label.setMaximumWidth(150)
        self.timer_value_label.setFixedHeight(50)        
        self.timer_value_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.timer_value_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)

        top_layout.addWidget(self.timer_value_label)
  
        """
            Widget Tab
        """
        self.tab_widget = self.init_tab_widget_ui(params)

        """
            Status layout
        """
        status_layout = QtWidgets.QGridLayout()

        status_static_label = CustomQLabel("Status:")
        status_static_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        status_static_label.setStyleSheet("padding-right: 30px;")
        status_static_label.setMinimumWidth(150)

        self.status_label = QtWidgets.QLabel(STATUS_BUTTON_LABEL_NOTHING_YET)
        self.status_label.setFont(CUSTOM_FONT_MONO)
        self.status_label.setStyleSheet(f"""
            background-color: {STATUS_COLOR_LABEL_SELECTED}; 
            border-radius: 5px;
            color: white;
            padding: 5px;
        """)
        self.status_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        
        status_layout.addWidget(status_static_label, 0, 0) 
        status_layout.addWidget(self.status_label, 0, 1, 1, 3) 

        status_layout.setColumnStretch(0, 0) 
        status_layout.setColumnStretch(1, 1) 

        """
            Main output table
        """
        self.output_table          = self.init_output_table_ui()
        self.output_table.setItemDelegate(ColorRowDelegate(self.output_table))

        """
            Filter layout
        """
        self.filter_widget_visible  = False
        self.filter_widget          = self.init_filter_ui()
        self.filter_widget.setMaximumHeight(0)
        self.filter_widget.setMinimumHeight(0)

        """
            Toggle buttons
        """
        self.clear_button = CustomButton("Erase")
        self.clear_button.setEnabled(False)
        self.clear_button.clicked.connect(self.clear_output_and_filters)

        self.settings = CustomButton("Settings")
        self.settings.clicked.connect(self.open_settings)

        self.global_sound_toggle = AnimatedToggle(
            checked_color=STATUS_MONITORING_COLOR,
            pulse_checked_color=f"{STATUS_MONITORING_COLOR}FF"
        )
        self.global_sound_toggle.stateChanged.connect(self.toggle_global_sound_preference)
        self.global_sound_toggle.setFixedSize(self.global_sound_toggle.sizeHint())
        self.global_sound_toggle.setChecked(self.enable_global_sound)

        self.show_all_decoded_toggle = AnimatedToggle(
            checked_color=STATUS_MONITORING_COLOR,
            pulse_checked_color=f"{STATUS_MONITORING_COLOR}FF"
        )
        self.show_all_decoded_toggle.stateChanged.connect(self.update_show_all_decoded_preference)
        self.show_all_decoded_toggle.setFixedSize(self.show_all_decoded_toggle.sizeHint())
        self.show_all_decoded_toggle.setChecked(self.enable_show_all_decoded)

        self.filter_gui_toggle = AnimatedToggle(
            checked_color=STATUS_MONITORING_COLOR,
            pulse_checked_color=f"{STATUS_MONITORING_COLOR}FF"
        )
        self.filter_gui_toggle.stateChanged.connect(self.update_filter_gui_preference)
        self.filter_gui_toggle.setFixedSize(self.filter_gui_toggle.sizeHint())
        self.filter_gui_toggle.setChecked(self.enable_filter_gui)

        self.toggle_buttons_layout = QtWidgets.QWidget()
        horizontal_layout = QtWidgets.QHBoxLayout()
        horizontal_layout.setContentsMargins(0, 0, 0, 0)
        horizontal_layout.setSpacing(0)  

        horizontal_layout.addWidget(CustomQLabel("Sound Alerts"))
        
        horizontal_layout.addWidget(self.global_sound_toggle)
        horizontal_layout.addSpacing(20)
        horizontal_layout.addWidget(CustomQLabel("View All Messages"))  
        horizontal_layout.addWidget(self.show_all_decoded_toggle)
        horizontal_layout.addSpacing(20)
        horizontal_layout.addWidget(CustomQLabel("Filters"))  
        horizontal_layout.addWidget(self.filter_gui_toggle)

        # Apply layout to the widget
        self.toggle_buttons_layout.setLayout(horizontal_layout)
        self.toggle_buttons_layout.setFixedHeight(42)
        
        """
            Bottom layout
        """
        bottom_layout = QtWidgets.QHBoxLayout()

        self.quit_button = CustomButton("Quit")
        self.quit_button.clicked.connect(self.quit_application)

        self.inputs_enabled = True

        if sys.platform == 'darwin':
            self.restart_button = CustomButton(ACTION_RESTART)
            self.restart_button.clicked.connect(self.restart_application)

        # Timer and start/stop buttons
        self.status_button = CustomButton(STATUS_BUTTON_LABEL_START)
        self.status_button.clicked.connect(self.start_monitoring)
        self.status_button.setFixedWidth(150)
        
        self.stop_button = CustomButton(STOP_BUTTON_LABEL)
        self.stop_button.setEnabled(False)        
        self.stop_button.clicked.connect(self.stop_monitoring)        
        self.stop_button.setFixedWidth(100)
        
        """
            Button layout
        """
        button_layout = QtWidgets.QHBoxLayout()

        button_layout.addWidget(self.settings)
        button_layout.addWidget(self.clear_button)

        if sys.platform == 'darwin':
            button_layout.addWidget(self.restart_button)

        button_layout.addWidget(self.quit_button)

        bottom_layout.addWidget(self.toggle_buttons_layout)
        bottom_layout.addStretch()  
        bottom_layout.addLayout(button_layout)

        bottom_widget = QtWidgets.QWidget()
        bottom_widget.setLayout(bottom_layout)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_widget.setFixedHeight(40)    

        """
            Activity Bar
        """
        self.activity_bar = ActivityBar(max_value=ACTIVITY_BAR_MAX_VALUE)
        self.activity_bar.setFixedWidth(30)

        outer_layout.addWidget(self.activity_bar)

        spacer = QtWidgets.QSpacerItem(0, 10, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)        

        """
            Main layout
        """
        worked_history_layout = QtWidgets.QVBoxLayout()

        worked_history_layout.addWidget(self.worked_history_callsigns_label)
        worked_history_layout.addWidget(self.wait_pounce_history_table, 1)  
        main_layout.addLayout(top_layout, 0, 0, 1, 5) 
        
        main_layout.addWidget(self.tab_widget, 2, 0, 4, 3)                
        main_layout.addLayout(worked_history_layout, 2, 3, 5, 2)
        main_layout.addLayout(status_layout, 8, 1, 1, 1)
        main_layout.addWidget(self.status_button, 8, 3)
        main_layout.addWidget(self.stop_button, 8, 4)
        main_layout.addItem(spacer, 9, 0, 1, 5)
        main_layout.addWidget(self.output_table, 10, 0, 1, 5)
        main_layout.addWidget(self.filter_widget, 11, 0, 1, 5)
        main_layout.addWidget(bottom_widget, 12, 0, 1, 5)
        

        self.file_handler = None
        if self.enable_pounce_log:
            self.file_handler = add_file_handler(get_log_filename())

        """
            self.operating_band might be overided as soon as check_connection_status is used
        """
        self.gui_selected_band = params.get('last_band_used', DEFAULT_SELECTED_BAND)
       
        QtCore.QTimer.singleShot(100, lambda: self.tab_widget.set_selected_tab(self.gui_selected_band))

        self.load_worked_history_callsigns()
        self.apply_theme_to_all(self.theme_manager.dark_mode)
        self.load_window_position()
        self.create_main_menu() 
        self.toggle_wkb4_column_visibility()        

        QtCore.QTimer.singleShot(100, lambda: self.wait_pounce_history_table.scrollToBottom())

        if self.datetime_column_setting == DATE_COLUMN_AGE:
            self.enable_age_column()
        else:
            self.enable_datetime_column()

        QtCore.QTimer.singleShot(1_000, lambda: self.init_activity_bar())   

        self.process_timer = False

        self.enforce_size_limit_timer = QtCore.QTimer()
        self.enforce_size_limit_timer.timeout.connect(self.output_model.enforce_size_limit)
        self.enforce_size_limit_timer.start(60_000) 
                
        # Close event to save position
        self.closeEvent = self.on_close
        # self.add_border_to_widgets(color="blue")

    """
        For debugging purpose only
    """
    def add_border_to_widgets(widget, color="red"):
        for child in widget.findChildren(QtWidgets.QWidget):
            current_style = child.styleSheet()
            child.setStyleSheet(f"{current_style}; border: 1px solid {color};")

    @QtCore.pyqtSlot()
    def on_status_menu_clicked(self):
        self.show()
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.on_focus_value_label_clicked()
        self.hide_status_menu()
            
        try:
            from AppKit import NSRunningApplication, NSApplicationActivateIgnoringOtherApps
            NSRunningApplication.currentApplication().activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
        except ImportError:
            pass

    def update_status_menu_message(self, text, bg_color, fg_color):
        if self.status_menu_agent:
            self.status_menu_agent.set_text_and_colors(text, bg_color, fg_color)  

    def hide_status_menu(self):
        if self.status_menu_agent:
            self.status_menu_agent.hide_status_bar()

    def init_tab_widget_ui(self, params):
        tab_widget = CustomTabWidget()

        tab_widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        
        self.wanted_callsigns_vars              = {}
        self.monitored_callsigns_vars           = {}
        self.excluded_callsigns_vars            = {}
        self.monitored_cq_zones_vars            = {}
        self.excluded_cq_zones_vars             = {}        

        self.tooltip_wanted_vars                = {}
        self.tooltip_monitored_vars             = {}
        self.tooltip_excluded_callsigns_vars    = {}
        self.tooltip_excluded_cd_zones_vars      = {}
        self.tooltip_monitored_cq_zones_vars    = {}

        self.band_indices                       = {}
        self.band_content_widgets               = {}

        wanted_dict = {
            'wanted_callsigns'      : self.wanted_callsigns_vars,
            'monitored_callsigns'   : self.monitored_callsigns_vars,            
            'monitored_cq_zones'    : self.monitored_cq_zones_vars,
            'excluded_callsigns'    : self.excluded_callsigns_vars,            
            'excluded_cq_zones'     : self.excluded_cq_zones_vars,
        }

        tooltip_wanted_dict = {
            'wanted_callsigns'      : self.tooltip_wanted_vars,
            'monitored_callsigns'   : self.tooltip_monitored_vars,
            'monitored_cq_zones'    : self.tooltip_monitored_cq_zones_vars,
            'excluded_callsigns'    : self.tooltip_excluded_callsigns_vars,
            'excluded_cq_zones'     : self.tooltip_excluded_cd_zones_vars,
        }

        sought_variables = [
            {
                'name'             : 'wanted_callsigns',
                'label'            : 'Wanted Callsign(s):',
                'function'         : partial(force_input, mode="uppercase"),
                'placeholder'      : CALLSIGN_NOTICE_LABEL,
                'on_changed_method': self.on_wanted_callsigns_changed,
            },
            {
                'name'             : 'monitored_callsigns',
                'label'            : 'Monitored Callsign(s):',
                'function'         : partial(force_input, mode="uppercase"),
                'placeholder'      : CALLSIGN_NOTICE_LABEL,                
                'on_changed_method': self.on_monitored_callsigns_changed,
            },
            {
                'name'             : 'monitored_cq_zones',
                'label'            : 'Monitored CQ Zone(s):',
                'function'         : partial(force_input, mode="numbers"),
                'placeholder'      : CALLSIGN_NOTICE_LABEL,                
                'on_changed_method': self.on_monitored_cq_zones_changed,
            },
            {
                'name'             : 'excluded_callsigns',
                'label'            : 'Excluded Callsign(s):',
                'function'         : partial(force_input, mode="uppercase"),
                'placeholder'      : CQ_ZONE_NOTICE_LABEL,                
                'on_changed_method': self.on_excluded_callsigns_changed,
            },
            {
                'name'             : 'excluded_cq_zones',
                'label'            : 'Excluded CQ Zone(s):',
                'function'         : partial(force_input, mode="numbers"),
                'placeholder'      : CQ_ZONE_NOTICE_LABEL,                
                'on_changed_method': self.on_excluded_cq_zones_changed,
            }
        ]

        for band in AMATEUR_BANDS.keys():
            tab_content = QtWidgets.QWidget()
            layout = QtWidgets.QGridLayout(tab_content)

            band_params = params.get(band, {})

            for idx, variable_info in enumerate(sought_variables):
                line_edit = QtWidgets.QLineEdit()
                line_edit.setFont(CUSTOM_FONT)
                line_edit.setPlaceholderText(variable_info['placeholder'])

                wanted_dict[variable_info['name']][band] = line_edit

                tooltip_wanted_dict[variable_info['name']][band] = ToolTip(line_edit)

                line_edit.setText(band_params.get(variable_info['name'], ""))

                line_label = CustomQLabel(variable_info['label'])
                line_label.setStyleSheet("border-radius: 6px; padding: 3px;")
                line_label.setMinimumWidth(100)

                ToolTip(line_label, CALLSIGN_NOTICE_LABEL)

                layout.addWidget(line_label, idx+1, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
                layout.addWidget(line_edit, idx+1, 1)

                line_edit.textChanged.connect(partial(variable_info['function'], line_edit))
                focus_out_event(line_edit, mode=variable_info['function'].keywords.get('mode', 'uppercase'))
                line_edit.textChanged.connect(variable_info['on_changed_method'])

            tab_content.setLayout(layout)
            self.band_content_widgets[band] = tab_content
            tab_widget.addTab(tab_content, band)

        tab_widget.tabClicked.connect(self.on_tab_clicked)     

        return tab_widget

    def init_wait_pounce_history_table_ui(self):
        wait_pounce_history_table = QtWidgets.QTableWidget()
        wait_pounce_history_table.setColumnCount(3)  

        header_item = QTableWidgetItem('Age')
        header_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)     
        wait_pounce_history_table.setHorizontalHeaderItem(0, header_item)            

        header_item = QTableWidgetItem('Callsign')
        header_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)   
        wait_pounce_history_table.setHorizontalHeaderItem(1, header_item)            

        header_item = QTableWidgetItem('Band')
        header_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)     
        wait_pounce_history_table.setHorizontalHeaderItem(2, header_item)            

        wait_pounce_history_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        wait_pounce_history_table.setFont(CUSTOM_FONT_SMALL)

        wait_pounce_history_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        wait_pounce_history_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)

        wait_pounce_history_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        wait_pounce_history_table.verticalHeader().setVisible(False)
        wait_pounce_history_table.verticalHeader().setDefaultSectionSize(24)
        wait_pounce_history_table.setAlternatingRowColors(True)

        wait_pounce_history_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        wait_pounce_history_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        wait_pounce_history_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Fixed)

        wait_pounce_history_table.setColumnWidth(0, 45)
        wait_pounce_history_table.setColumnWidth(1, 40)
        wait_pounce_history_table.setColumnWidth(2, 45)
        
        wait_pounce_history_table.customContextMenuRequested.connect(
            lambda position: self.on_table_context_menu(self.wait_pounce_history_table, position)
        )
        wait_pounce_history_table.cellClicked.connect(
            lambda row, column: self.on_table_row_clicked(self.wait_pounce_history_table, row, column)
        )
        wait_pounce_history_table.setItemDelegateForColumn(0, TimeAgoDelegate())
        wait_pounce_history_table.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        wait_pounce_history_table.setObjectName("history_table")        
        wait_pounce_history_table.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)

        return wait_pounce_history_table

    def init_output_table_ui(self):
        output_table = QtWidgets.QTableView(self)
        output_table.setModel(self.filter_proxy_model)

        output_table.setFont(CUSTOM_FONT)
        output_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        output_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        output_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        output_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)
        output_table.verticalHeader().setVisible(False)
        output_table.verticalHeader().setDefaultSectionSize(24)
        output_table.setAlternatingRowColors(True)
        output_table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        column_widths = [160, 45, 60, 60, 80, 400, 50, 70, 60, 60]
        for i, width in enumerate(column_widths):
            if i < output_table.model().columnCount():                
                output_table.setColumnWidth(i, width)
                if i in [5, 6]:
                    output_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        output_table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)

        self.refresh_table_timer = QtCore.QTimer(self)
        self.refresh_table_timer.timeout.connect(lambda: self.output_table.viewport().update())

        output_table.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        output_table.setObjectName("output_table")
        output_table.customContextMenuRequested.connect(
            lambda position: self.on_table_context_menu(self.output_table, position)
        )
        output_table.clicked.connect(
            lambda index: self.on_table_row_clicked(self.output_table, index.row(), index.column())
        )
        output_table.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        return output_table

    def init_filter_ui(self):
        filter_widget = QtWidgets.QWidget()
        filter_widget.setObjectName("FilterWidget")

        filter_widget.setMinimumHeight(60)
        filter_widget.setMaximumHeight(60)

        inner_widget = QtWidgets.QWidget()

        inner_widget.setMinimumHeight(60)
        inner_widget.setMaximumHeight(60)
        inner_layout = QtWidgets.QGridLayout(inner_widget)
        inner_layout.setContentsMargins(10, 10, 10, 10)
        inner_layout.setVerticalSpacing(2)

        search_filter = SearchFilterInput()

        self.callsign_input = search_filter.create_search_field("Callsign")
        self.country_input = search_filter.create_search_field("Country")

        self.callsign_input.textChanged.connect(self.apply_filters)
        self.country_input.textChanged.connect(self.apply_filters)

        self.cq_combo = self.create_combo_box()
        self.continent_combo = self.create_combo_box()
        self.band_combo = self.create_combo_box()
        """
        self.cq_combo = self.create_combo_box([str(i) for i in range(1, 41)])
        self.continent_combo = self.create_combo_box(['AS', 'AF', 'EU', 'OC', 'NA', 'SA'])
        self.band_combo = self.create_combo_box(list(AMATEUR_BANDS.keys()))
        """
        self.color_combo = self.create_color_combo_box("Color")

        fields = [
            ("Callsign", self.callsign_input),
            ("Band", self.band_combo),
            ("Color", self.color_combo),
            ("Zone", self.cq_combo),
            ("Continent", self.continent_combo),
            ("Country", self.country_input),
        ]

        for idx, (label_text, widget) in enumerate(fields):
            label = CustomQLabel(label_text)
            label.setFont(CUSTOM_FONT_SMALL)
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            inner_layout.addWidget(widget, 0, idx)
            inner_layout.addWidget(label, 1, idx)

        outer_layout = QtWidgets.QVBoxLayout(filter_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(inner_widget, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)

        return filter_widget

    def update_marathon_preference(self, checked):  
        if self.enable_marathon != checked:
            self.enable_marathon = checked
            self.save_unique_param('enable_marathon', checked)   

            if self._running:
                self.stop_monitoring()
                self.start_monitoring()    

    def update_global_sound_preference(self, checked):  
        if self.enable_global_sound != checked:
            self.enable_global_sound = checked
            self.global_sound_toggle.setChecked(checked)
            self.save_unique_param('enable_global_sound', checked)      

    def toggle_global_sound_preference(self, checked):        
        if checked:
            QtCore.QTimer.singleShot(500, lambda: self.play_sound('enable_global_sound'))

        self.update_global_sound_preference(checked)

    def update_show_all_decoded_preference(self, checked):
        self.filter_proxy_model.setEnableShowAllDecoded(checked)
        self.filter_proxy_model.invalidateFilter()
    
        if self.enable_show_all_decoded != checked:
            self.enable_show_all_decoded = checked
            self.show_all_decoded_toggle.setChecked(checked)
            
            self.save_unique_param('enable_show_all_decoded', checked)   

        self.output_table.scrollToBottom()            

    def update_filter_gui_preference(self, checked):
        if checked:
            self.show_filter_layout()
        else:
            self.clear_filters()
            self.hide_filter_layout()            
        
        if self.enable_filter_gui != checked:
            self.enable_filter_gui = checked
            self.filter_gui_toggle.setChecked(checked)
            self.save_unique_param('enable_filter_gui', checked)        

    def toggle_wkb4_column_visibility(self):
        if self.worked_before_preference == WKB4_REPLY_MODE_ALWAYS:
            self.output_table.setColumnHidden(9, True)
        else:
            self.output_table.setColumnHidden(9, False)

    def hide_filter_layout(self):
        self.filter_widget_visible = False
        self.callsign_input.clearFocus()
        self.animate_layout_height(self.filter_widget, target_height=0)

    def show_filter_layout(self):
        self.filter_widget_visible = True
        self.animate_layout_height(self.filter_widget, target_height=60)  
        QtCore.QTimer.singleShot(0, self.callsign_input.setFocus)

    def animate_layout_height(self, widget, target_height):
        widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        widget.setMinimumHeight(0)
        widget.setMaximumHeight(widget.height())

        animation = QPropertyAnimation(widget, b"maximumHeight")
        animation.setDuration(300)
        animation.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)

        animation.setStartValue(widget.height())
        animation.setEndValue(target_height)

        def on_value_changed(value):
            widget.setMaximumHeight(value)  
            widget.updateGeometry() 
            if widget.parentWidget():
                widget.parentWidget().updateGeometry()

        animation.valueChanged.connect(on_value_changed)

        def on_finished():
            if target_height == 0:
                widget.updateGeometry() 

        animation.finished.connect(on_finished)

        self.current_animation = animation
        animation.start(QtCore.QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def toggle_clear_button_visibility(self, button, text):
        button.setVisible(bool(text.strip()))

    def on_header_clicked(self, column_index):
        if column_index == 0:  
            self.toggle_time_mode()

    def toggle_time_mode(self):
        if self.datetime_column_setting == DATE_COLUMN_AGE:
            self.enable_datetime_column()
        else:
            self.enable_age_column()

    def enable_age_column(self):
        self.datetime_column_setting = DATE_COLUMN_AGE   
        self.set_time_mode_header(self.datetime_column_setting)

        self.output_table.viewport().update()
        self.output_table.setColumnWidth(0, 60)

        self.refresh_table_timer.start(1_000)
        self.update_date_mode_param()

    def enable_datetime_column(self):
        self.datetime_column_setting = DATE_COLUMN_DATETIME
        self.set_time_mode_header(self.datetime_column_setting)

        self.output_table.viewport().update()
        self.output_table.setColumnWidth(0, 130)

        self.refresh_table_timer.stop()
        self.update_date_mode_param()

    def set_time_mode_header(self, value):
        self.output_model.setTimeMode(value)
        self.output_model.setHeaderData(0, QtCore.Qt.Orientation.Horizontal, value, QtCore.Qt.ItemDataRole.DisplayRole)

    def update_date_mode_param(self):
        self.datetime_column_action.setChecked(self.datetime_column_setting == DATE_COLUMN_DATETIME)
        self.age_column_action.setChecked(self.datetime_column_setting == DATE_COLUMN_AGE)

        self.save_unique_param('datetime_column_setting', self.datetime_column_setting)  

    def clear_line_edit(self, line_edit, button):
        line_edit.clear()
        button.setVisible(False)
        self.apply_filters()

    def create_combo_box(self, values=None, default_value=None):
        combo_box = QtWidgets.QComboBox()
        combo_box.setEditable(False)
        combo_box.setFixedWidth(150)
        combo_box.setFont(CUSTOM_FONT_SMALL)
        
        if default_value is None:
            default_value = DEFAULT_FILTER_VALUE
        combo_box.addItem(default_value)

        if values:
            combo_box.addItems(values)

        combo_box.currentIndexChanged.connect(self.apply_filters)
        combo_box.setStyleSheet("""
                QComboBox {
                    font-size: 11px;
                }
            """)
        return combo_box
    
    def update_combo_box_values(self, raw_data):
        keys_to_update = set()

        for key in self.combo_box_values.keys():
            if key in raw_data:
                new_value = str(raw_data[key]).strip()
                if (
                    new_value and 
                    new_value not in self.combo_box_values[key]
                ):
                    self.combo_box_values[key].add(new_value)
                    keys_to_update.add(key)

        if keys_to_update:
            self.populate_combo_boxes(keys_to_update)

    def populate_combo_boxes(self, keys_to_update):
        if "cq_zone" in keys_to_update:
            self.add_new_items_to_combo(self.cq_combo, self.combo_box_values["cq_zone"])

        if "continent" in keys_to_update:
            self.add_new_items_to_combo(self.continent_combo, self.combo_box_values["continent"])

        if "band" in keys_to_update:
            self.add_new_items_to_combo(self.band_combo, self.combo_box_values["band"])
        
    def add_new_items_to_combo(self, combo, new_items, default_value=DEFAULT_FILTER_VALUE):
        combo.blockSignals(True)

        existing_items      = [combo.itemText(i) for i in range(combo.count()) if combo.itemText(i) != default_value]
        combined_items      = set(existing_items).union(new_items)

        numeric_items       = sorted((item for item in combined_items if item.isdigit()), key=int)
        non_numeric_items   = sorted(item for item in combined_items if not item.isdigit())

        sorted_items        = [default_value] + numeric_items + non_numeric_items

        combo.clear()
        combo.addItems(sorted_items)
        combo.blockSignals(False)

    def create_color_combo_box(self, placeholder_text):
        color_combo = QtWidgets.QComboBox()
        color_combo.setFixedWidth(150)
        color_combo.setIconSize(QtCore.QSize(120, 10))  
        color_combo.setFont(CUSTOM_FONT_SMALL)

        color_combo.addItem(DEFAULT_FILTER_VALUE, userData=None)

        # Liste des couleurs et noms associés
        colors = [
            ("bright_for_my_call", BG_COLOR_FOCUS_MY_CALL),
            ("black_on_yellow",    BG_COLOR_BLACK_ON_YELLOW),
            ("black_on_purple",    BG_COLOR_BLACK_ON_PURPLE),
            ("white_on_blue",      BG_COLOR_WHITE_ON_BLUE),
            ("black_on_cyan",      BG_COLOR_BLACK_ON_CYAN),
        ]

        for row_color, bg_color in colors:
            pixmap = QtGui.QPixmap(120, 10)  
            pixmap.fill(QtGui.QColor(bg_color))
            icon = QtGui.QIcon(pixmap)
            color_combo.addItem(icon, "", userData=row_color)

        color_combo.setEditable(False)
        color_combo.currentIndexChanged.connect(self.apply_filters)

        return color_combo

    def apply_theme_to_all(self, dark_mode):
        self.apply_palette(dark_mode)

    def on_tab_clicked(self, tab_band):
        self.gui_selected_band = tab_band
        self.tab_widget.set_selected_tab(self.gui_selected_band)

        if self.gui_selected_band != self.operating_band and self._running:
            self.tab_widget.set_operating_tab(self.operating_band)

        self.save_unique_param('last_band_used', self.gui_selected_band)  
        
    def apply_band_change(self, band):
        if band != 'Invalid' and band != self.operating_band:    
            self.restore_slave_settings(blocSignals=True)

            self.operating_band = band
            self.monitoring_settings.set_wanted_callsigns(self.wanted_callsigns_vars[self.operating_band].text())
            self.monitoring_settings.set_monitored_callsigns(self.monitored_callsigns_vars[self.operating_band].text())
            self.monitoring_settings.set_excluded_callsigns(self.excluded_callsigns_vars[self.operating_band].text())
            self.monitoring_settings.set_monitored_cq_zones(self.monitored_cq_zones_vars[self.operating_band].text())
            self.monitoring_settings.set_excluded_cq_zones(self.excluded_cq_zones_vars[self.operating_band].text())

            self.monitoring_settings.set_operating_band(band)
            
            self.update_tab_widget_labels_style()
        
            if self.global_sound_toggle.isChecked():      
                self.play_sound("band_change")

        if self._running:            
            self.send_worker_signal()
            """
                Make sure to reset last_sound_played_time if we switch band
            """
            self.last_sound_played_time = datetime.min
            self.last_targeted_call = None
            self.hide_focus_value_label(visible=False)
            self.gui_selected_band = self.operating_band
            self.tab_widget.set_operating_tab(self.operating_band)

    def hide_focus_value_label(self, visible: bool):
        if visible:
            self.focus_value_label.setStyleSheet("")  
            self.focus_value_label.clear() 
        else:    
            self.focus_value_label.setStyleSheet("background-color: transparent; border: none;")
            self.focus_value_label.clear()        

    """
        Used for MonitoringSetting
    """
    def on_wanted_callsigns_changed(self):
        if self.operating_band:
            self.monitoring_settings.set_wanted_callsigns(self.wanted_callsigns_vars[self.operating_band].text())
            self.send_worker_signal()

    def on_monitored_callsigns_changed(self):
        if self.operating_band:
            self.monitoring_settings.set_monitored_callsigns(self.monitored_callsigns_vars[self.operating_band].text())
            self.send_worker_signal()

    def on_excluded_callsigns_changed(self):
        if self.operating_band:
            self.monitoring_settings.set_excluded_callsigns(self.excluded_callsigns_vars[self.operating_band].text())
            self.send_worker_signal()

    def on_excluded_cq_zones_changed(self):
        if self.operating_band:
            self.monitoring_settings.set_excluded_cq_zones(self.excluded_cq_zones_vars[self.operating_band].text())
            self.send_worker_signal()           

    def on_monitored_cq_zones_changed(self):
        if self.operating_band:
            self.monitoring_settings.set_monitored_cq_zones(self.monitored_cq_zones_vars[self.operating_band].text())
            self.send_worker_signal()
            
    def send_worker_signal(self):
        if self.worker is not None:            
            self.worker.update_listener_settings_signal.emit()
            if self._instance == MASTER:
                self.worker.synch_settings_signal.emit()  
            
    @QtCore.pyqtSlot(object)
    def on_message_received(self, message):        
        if isinstance(message, dict):
            if (
                self.window_title is None and 
                self.my_call is None and                 
                message.get('wsjtx_id')
            ):
                self.my_call = message.get('my_call')
                self.my_wsjtx_id = message.get('wsjtx_id')
                self.update_window_title()

            message_type = message.get('type', None)

            if message_type == 'update_mode':
                self.mode = message.get('mode')          
            elif message_type == 'master_status':
                self.check_instance(
                        message.get('addr_port'),
                        message.get('status')
                    )          
            elif message_type == 'master_slave_settings':
                self.apply_master_settings(message.get('settings'))                  
            elif message_type == 'update_frequency':
                self.frequency = message.get('frequency')                
                if self.frequency != self.last_frequency:
                    self.last_frequency = self.frequency
                    band      = get_amateur_band(self.frequency)
                    if band != 'Invalid':
                        self.set_notice_to_focus_value_label(f"{band} {self.mode} {display_frequency(self.last_frequency)} {self.my_wsjtx_id or ''}")                     
                        self.tab_widget.set_selected_tab(band)   
            elif message_type == 'stop_monitoring':
                log.warning("Received Stop monitoring request")
                self.play_sound("error_occurred")
                self.stop_monitoring()     

            elif message_type == 'upate_wanted_callsign':
                log.debug(f"Received request to update ({message.get('action')}) Wanted Callsigns with [ {message.get('callsign')} ]")
                self.update_var(self.wanted_callsigns_vars[self.operating_band], message.get('callsign'), message.get('action'))  
            elif message_type == 'update_status':
                if self._running:
                    self.check_connection_status(
                        message.get('decode_packet_count', 0),
                        message.get('last_decode_packet_time'),
                        message.get('last_heartbeat_time'),
                        message.get('frequency'),
                        message.get('transmitting')
                    )          
            elif 'decode_time_str' in message:
                formatted_message   = message.get('formatted_message')
                message_type        = message.get('message_type')

                callsign            = message.get('callsign')
                callsign_info       = message.get('callsign_info', None)
                directed            = message.get('directed')
                my_call             = message.get('my_call')
                wanted              = message.get('wanted')
                monitored           = message.get('monitored')
                monitored_cq_zone   = message.get('monitored_cq_zone')
                wkb4_year           = message.get('wkb4_year')

                empty_str           = ''
                entity              = empty_str
                cq_zone             = empty_str
                continent           = empty_str
                                                
                """
                    Handle GUI output
                """
                self.message_times.append(datetime.now())    

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
                    self.operating_band and 
                    matches_any(text_to_array(self.wanted_callsigns_vars[self.operating_band].text()), directed)
                ):                    
                    message_color      = "white_on_blue"
                else:
                    message_color      = None
                
                if callsign_info:
                    entity    = (callsign_info.get("entity") or callsign_info.get("name", "Unknown")).title()
                    cq_zone   = callsign_info.get("cqz")
                    continent = callsign_info.get("cont")
                elif callsign_info is None:
                    entity    = "Where?"
                 
                self.update_model_data(
                    wanted,
                    callsign,
                    wkb4_year,
                    directed,
                    message.get('decode_time_str'),
                    self.operating_band,
                    message.get('snr', 0),
                    message.get('delta_time', 0.0),
                    message.get('delta_freq', 0),
                    message.get('message', ''),
                    formatted_message,
                    entity,
                    cq_zone,
                    continent,
                    message_type,
                    message_color,
                    message.get('message_uid'),                     
                )   

                message['message_uid']  = uuid.uuid4()
                self.message_buffer.append(message)         

                if not self.process_timer:
                    self.process_timer = True
                    QtCore.QTimer.singleShot(300, lambda: self.process_message_buffer())            
        else:
            pass

    def apply_master_settings(self, master_settings):
        master_operating_band = master_settings.get('band')
        if master_operating_band:
            """
                Check if need to play sound if
            """
            play_sound = False
            master_wanted_callsigns = master_settings.get('wanted_callsigns')

            if(
                self.global_sound_toggle.isChecked() and
                has_significant_change(
                    self.wanted_callsigns_vars[master_operating_band].text(),
                    ",".join(master_wanted_callsigns)
                )
            ):
                play_sound = True

            """
                Restore band and save wanted_callsigns_vars per band
            """
            self.restore_slave_settings(blocSignals=True)
            for band in AMATEUR_BANDS.keys():                
                self.slave_wanted_callsigns[band] = self.wanted_callsigns_vars[band].text()   
          
            if not master_wanted_callsigns:
                self.wanted_callsigns_vars[master_operating_band].clear()
            else:
                self.wanted_callsigns_vars[master_operating_band].setText(", ".join(master_wanted_callsigns))

            if play_sound:
                self.play_sound("updated_settings")     

    """
    def restore_slave_settings(self):
        if self._instance == SLAVE:            
            for band in AMATEUR_BANDS.keys():
                if self.slave_wanted_callsigns.get(band):
                    slave_wanted_callsigns_band = self.slave_wanted_callsigns[band]
                    if not slave_wanted_callsigns_band:
                        self.wanted_callsigns_vars[band].clear()
                    else:
                        self.wanted_callsigns_vars[band].setText(slave_wanted_callsigns_band)  
    """                              

    def restore_slave_settings(self, blocSignals=False):
        if self._instance == SLAVE:            
            for band in AMATEUR_BANDS.keys():
                if blocSignals:
                    self.wanted_callsigns_vars[band].blockSignals(True)
                if self.slave_wanted_callsigns.get(band):
                    slave_wanted_callsigns_band = self.slave_wanted_callsigns[band]                    

                    if not slave_wanted_callsigns_band:
                        self.wanted_callsigns_vars[band].clear()
                    else:
                        self.wanted_callsigns_vars[band].setText(slave_wanted_callsigns_band)
                if blocSignals:
                    self.wanted_callsigns_vars[band].blockSignals(False)
        
    def process_message_buffer(self):     
        if not self.message_buffer:
            return None
        else:
            max_decode_time_str = max(message['decode_time_str'] for message in self.message_buffer)            
            latest_messages = [message for message in self.message_buffer if message['decode_time_str'] == max_decode_time_str]
            selected_message = max(latest_messages, key=lambda message: message['priority'], default=None)

        # log.error(selected_message)

        if (
            selected_message and
            selected_message.get('message_uid') != self.last_focus_value_message_uid
        ):            
            current_time = datetime.now()
            """
                Handle sound notification
            """
            play_sound = False
            message_type = selected_message.get('message_type')

            if self.global_sound_toggle.isChecked():      
                if message_type == 'wanted_callsign_detected' and self.enable_sound_wanted_callsigns:
                    play_sound = True
                elif message_type == 'wanted_callsign_being_called' and self.enable_sound_wanted_callsigns:
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
                    delay = int(self.delay_between_sound_for_monitored)                   
                    if (current_time - self.last_sound_played_time).total_seconds() > delay:                                                 
                        play_sound = True
                        self.last_sound_played_time = current_time               
            
                if play_sound:
                    self.play_sound(message_type)

                if message_type == 'wanted_callsign_being_called':
                    self.last_targeted_call = selected_message.get('callsign')
                elif (
                    message_type == 'ready_to_log' or 
                    message_type == 'lost_targeted_callsign'
                ):
                    self.last_targeted_call = None    

            if message_type:
                self.set_message_to_focus_value_label(selected_message)          

        """
            Clear buffer
        """
        if selected_message:
            self.message_buffer = deque(
                [same_time_message for same_time_message in self.message_buffer
                    if abs((same_time_message['decode_time'] - selected_message['decode_time']).total_seconds()) <= 120]
            )  

        """
            Reset timer
        """
        self.process_timer = False     
        self.update_activity_bar()  

    def on_table_row_clicked(self, table, row, column):
        position = table.visualRect(table.model().index(row, column)).center()
        self.on_table_context_menu(table, position)        

    def on_table_context_menu(self, table, position):
        """
            Fetch data to build menu
        """
        index = table.indexAt(position)
        if not index.isValid():
            return 
        row = index.row()

        if table.objectName() == 'history_table':
            item = table.item(row, 0)
            data = item.data(QtCore.Qt.ItemDataRole.UserRole)
        elif table.objectName() == 'output_table':    
            source_index = self.filter_proxy_model.mapToSource(table.model().index(row, 0))
            data = self.output_model.data(source_index, QtCore.Qt.ItemDataRole.UserRole)

        if not data:
            return

        """
            Menu builder
        """
        menu = QtWidgets.QMenu()
        if sys.platform == 'darwin':
            menu.setStyleSheet(CONTEXT_MENU_DARWIN_QSS)
            menu.setFont(MENU_FONT)

        if not index.isValid() or (
            self.operating_band is None and
            self.gui_selected_band is None
        ):
            return

        if self.gui_selected_band is not None:
            context_menu_band = self.gui_selected_band
        else:
            context_menu_band = self.operating_band
        
        formatted_message   = data.get('formatted_message')
        callsign            = data.get('callsign')
        directed            = data.get('directed')
        cq_zone             = data.get('cq_zone')
        history_band        = data.get('band')

        if not callsign:
            return        

        actions = {}        

        if table.objectName() == 'history_table':
            actions['remove_entry_from_worked_history'] = menu.addAction(f"Remove {callsign} on {history_band} from Worked History")            
            callsign_bands = defaultdict(set)
            for entry in self.worked_callsigns_history:
                callsign_bands[entry['callsign']].add(entry['band'])

            if len(callsign_bands[callsign]) > 1:
                actions['remove_callsign_from_worked_history'] = menu.addAction(f"Remove {callsign} on all bands from Worked History ({", ".join(sorted(callsign_bands[callsign]))})")
            menu.addSeparator()

        label = QtWidgets.QLabel(f"Apply to {context_menu_band}")
        label.setStyleSheet(CONTEXT_MENU_HEADER_QSS)

        widget_action = QtWidgets.QWidgetAction(menu)
        widget_action.setDefaultWidget(label)

        menu.addAction(widget_action)
        menu.addSeparator()
        
        """
            Wanted Callsigns
        """
        if callsign not in self.wanted_callsigns_vars[context_menu_band].text():
            actions['add_callsign_to_wanted'] = menu.addAction(f"Add {callsign} to Wanted Callsigns")
            if self._instance == SLAVE:
                actions['add_callsign_to_wanted'].setEnabled(False)
        else:
            actions['remove_callsign_from_wanted'] = menu.addAction(f"Remove {callsign} from Wanted Callsigns")
            if self._instance == SLAVE:
                actions['remove_callsign_from_wanted'].setEnabled(False)

        if callsign != self.wanted_callsigns_vars[context_menu_band].text():
            actions['replace_wanted_with_callsign'] = menu.addAction(f"Make {callsign} your only Wanted Callsign")
            if self._instance == SLAVE:
                actions['replace_wanted_with_callsign'].setEnabled(False)
        menu.addSeparator()

        """
            Monitored Callsigns
        """
        if callsign not in self.monitored_callsigns_vars[context_menu_band].text():
            actions['add_callsign_to_monitored'] = menu.addAction(f"Add {callsign} to Monitored Callsigns")
        else:
            actions['remove_callsign_from_monitored'] = menu.addAction(f"Remove {callsign} from Monitored Callsigns")
        menu.addSeparator()

        """
            Directed Callsigns
        """
        if table.objectName() == 'output_table':
            if directed and directed != self.my_call:
                if directed not in self.wanted_callsigns_vars[context_menu_band].text():
                    actions['add_directed_to_wanted'] = menu.addAction(f"Add {directed} to Wanted Callsigns")
                    if self._instance == SLAVE:
                        actions['add_directed_to_wanted'].setEnabled(False)
                else:
                    actions['remove_directed_from_wanted'] = menu.addAction(f"Remove {directed} from Wanted Callsigns")
                    if self._instance == SLAVE:
                        actions['remove_directed_from_wanted'].setEnabled(False)

                if directed != self.wanted_callsigns_vars[context_menu_band].text():
                    actions['replace_wanted_with_directed'] = menu.addAction(f"Make {directed} your only Monitored Callsign")                

                if directed not in self.monitored_callsigns_vars[context_menu_band].text():
                    actions['add_directed_to_monitored'] = menu.addAction(f"Add {directed} to Monitored Callsigns")
                else:
                    actions['remove_directed_from_monitored'] = menu.addAction(f"Remove {directed} from Monitored Callsigns")
                menu.addSeparator()

        """
            Monitored CQ Zones
        """
        if cq_zone:
            try:
                if str(cq_zone) not in self.monitored_cq_zones_vars[context_menu_band].text():
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

        action = menu.exec(table.viewport().mapToGlobal(position))

        if action is None:
            return

        """
            Context menu actions
        """
        if action == actions.get('copy_message'):
            if formatted_message:
                self.copy_message_to_clipboard(formatted_message)
        else:
            update_actions = {
                'remove_entry_from_worked_history'    : lambda: self.remove_worked_callsign(callsign, history_band),
                'remove_callsign_from_worked_history' : lambda: self.remove_worked_callsign(callsign),
                'add_callsign_to_wanted'              : lambda: self.update_var(self.wanted_callsigns_vars[context_menu_band], callsign),
                'remove_callsign_from_wanted'         : lambda: self.update_var(self.wanted_callsigns_vars[context_menu_band], callsign, "remove"),
                'replace_wanted_with_callsign'        : lambda: self.update_var(self.wanted_callsigns_vars[context_menu_band], callsign, "replace"),
                'add_callsign_to_monitored'           : lambda: self.update_var(self.monitored_callsigns_vars[context_menu_band], callsign),
                'remove_callsign_from_monitored'      : lambda: self.update_var(self.monitored_callsigns_vars[context_menu_band], callsign, "remove"),
                'add_directed_to_wanted'              : lambda: self.update_var(self.wanted_callsigns_vars[context_menu_band], directed),
                'remove_directed_from_wanted'         : lambda: self.update_var(self.wanted_callsigns_vars[context_menu_band], directed, "remove"),
                'replace_wanted_with_directed'        : lambda: self.update_var(self.wanted_callsigns_vars[context_menu_band], directed, "replace"),
                'add_directed_to_monitored'           : lambda: self.update_var(self.monitored_callsigns_vars[context_menu_band], directed),
                'remove_directed_from_monitored'      : lambda: self.update_var(self.monitored_callsigns_vars[context_menu_band], directed, "remove"),
                'add_to_cq_zone'                      : lambda: self.update_var(self.monitored_cq_zones_vars[context_menu_band], cq_zone),
                'remove_from_cq_zone'                 : lambda: self.update_var(self.monitored_cq_zones_vars[context_menu_band], cq_zone, "remove"),
            }

            for key, act in actions.items():
                if action == act:
                    update_func = update_actions.get(key)
                    if update_func:
                        update_func()
                        break

    def update_var(self, var, value, action='add'):
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

        self.message_buffer = deque()

    def update_window_title(self):
            self.window_title = f"{self.base_title} - Connected to {self.my_wsjtx_id}"
            if self._instance and self._instance == SLAVE:
                self.window_title+= f" - Running as {self._instance}"
            self.setWindowTitle(self.window_title)

    def reset_window_title(self):
        self.window_title = None
        self.setWindowTitle(self.base_title)  

    def init_activity_bar(self):
        self.activity_bar.setValue(ACTIVITY_BAR_MAX_VALUE)

    def update_activity_bar(self):
        time_delta_in_seconds = get_mode_interval(self.mode)
        # We need to double time_delta_to_be_used the time transmitting == 1 
        # otherwise we are loosing accuracy of activity bar
        if not self.transmitting:
            cutoff_time = datetime.now() - timedelta(seconds=time_delta_in_seconds)
            while self.message_times and self.message_times[0] < cutoff_time:
                self.message_times.popleft()

        self.activity_bar.setValue(len(self.message_times))                                     

    def start_blinking_status_button(self):
        # log.error("Start blinking status button")
        if self.is_status_button_label_blinking is False:
            self.is_status_button_label_blinking = True
            self.blink_timer.start(500)

    def stop_blinking_status_button(self):    
        # log.error("Stop blinking status button")
        if self.is_status_button_label_blinking is True:
            self.is_status_button_label_blinking = False
            self.blink_timer.stop()
            self.status_button.setVisibleState(True)        

    @QtCore.pyqtSlot()
    def toggle_label_visibility(self):
        if self.is_status_button_label_visible:
            self.status_button.setVisibleState(False)                    
            self.is_status_button_label_visible = False
        else:                    
            self.status_button.setVisibleState(True)        
            self.is_status_button_label_visible = True

    def update_status_label_style(self, background_color, text_color):
        style = f"""
            background-color: {background_color};
            color: {text_color};            
            border-radius: 5px;
            padding: 5px;
        """

        self.status_label.setStyleSheet(style)            

    def set_notice_to_focus_value_label(self, notice_message, fg_color_hex=FG_COLOR_BLACK_ON_WHITE, bg_color_hex=STATUS_TRX_COLOR):           
        self.message_buffer = deque()                 
        self.update_status_menu_message(notice_message, bg_color_hex, fg_color_hex)
        self.output_table.scrollToBottom()
        self.last_focus_value_message_uid = None

    def set_message_to_focus_value_label(self, message):   
        formatted_message = message.get('formatted_message').strip()

        self.focus_value_label.setText(formatted_message)

        contains_my_call = message.get('directed') == message.get('my_call')

        if contains_my_call:
            bg_color_hex = BG_COLOR_FOCUS_MY_CALL
            fg_color_hex = FG_COLOR_FOCUS_MY_CALL
        else:
            bg_color_hex = BG_COLOR_REGULAR_FOCUS
            fg_color_hex = FG_COLOR_REGULAR_FOCUS
                    
        self.focus_value_label.setStyleSheet(f"""
            background-color: {bg_color_hex};
            color: {fg_color_hex};
            padding: 10px;
            border-radius: 8px;
        """)

        self.last_focus_value_message_uid = message.get('message_uid')

        self.update_status_menu_message(message.get('message', ''), bg_color_hex, fg_color_hex)

    @QtCore.pyqtSlot(object)
    def play_sound(self, sound_name):
        try:           
            sound_mapping = {
                'wanted_callsign_detected'      : self.wanted_callsign_detected_sound,
                'wanted_callsign_being_called'  : self.wanted_callsign_being_called_sound,
                'directed_to_my_call'           : self.directed_to_my_call_sound,
                'monitored_callsign_detected'   : self.monitored_callsign_detected_sound,
                'ready_to_log'                  : self.ready_to_log_sound,
                'band_change'                   : self.band_change_sound,
                'updated_settings'              : self.updated_settings,
                'error_occurred'                : self.error_occurred_sound,
                'enable_global_sound'           : self.enabled_global_sound
            }

            sound = sound_mapping.get(sound_name)
            if sound:
                log.debug(f"Queued sound: [{sound_name}]")
                self.sound_queue.put(sound)
                self.start_sound_queue()
            else:
                log.error(f"Unknown sound: [{sound_name}]") 

        except Exception as e:
            log.error(f"Failed to queue alert sound: {e}")

    def stop_sound_queue(self):
        self.sound_timer.stop()
        while not self.sound_queue.empty():
            self.sound_queue.get()  

        self.currently_playing = False
    
    def start_sound_queue(self):
        if not self.currently_playing and not self.sound_queue.empty():
            self.play_next_sound()

    def play_next_sound(self):
        if not self.sound_queue.empty():
            self.currently_playing = True
            sound = self.sound_queue.get()
            sound.play()
            
            duration = sound.duration() if hasattr(sound, "duration") else 500
            self.sound_timer.start(duration)
        else:
            self.currently_playing = False            

    def get_size_of_output_model(self):
        output_model_size_bytes = self.output_model._current_size_bytes

        if output_model_size_bytes:
            if output_model_size_bytes > 1_048_576:  
                size_mo = output_model_size_bytes / (1024 * 1024)
                formatted_size = f"~ {size_mo:.1f} Mo"
            else:
                formatted_size = f"~ {output_model_size_bytes:.1f} Ko"

            return formatted_size
        else:
            return ''
        
    def check_instance(
        self,
        addr_port   = None,
        status      = None
    ):        
        if status != self._instance:
            if (
                self._instance == MASTER and
                status == SLAVE
            ):
                self.master_slave_addr_port     = addr_port     
                self.slave_wanted_callsigns     = {}

            if (
                self._instance == SLAVE and
                status == MASTER
            ):
                self.restore_slave_settings()

        self._instance = status    
        self.update_tab_widget_labels_style()            

    def check_connection_status(
        self,
        decode_packet_count     = None,
        last_decode_packet_time = None,
        last_heartbeat_time     = None,
        frequency               = None,
        transmitting            = None,
    ):
        if decode_packet_count is not None:
            self.decode_packet_count = decode_packet_count
        if last_decode_packet_time is not None:
            self.last_decode_packet_time = last_decode_packet_time
        if last_heartbeat_time is not None:
            self.last_heartbeat_time = last_heartbeat_time
        if transmitting is not None:
            self.transmitting = transmitting

        current_time        = datetime.now(timezone.utc)
        current_mode        = ""
        connection_lost     = False
        nothing_to_decode   = False

        status_text_array   = []

        # Check band and control used tab
        if frequency is not None:
            operating_band = get_amateur_band(frequency)     
            if operating_band != 'Invalid' and self.operating_band != operating_band:
                self.apply_band_change(operating_band)
           
        if self.mode is not None:
            current_mode = f"{self.mode}"

        if self.last_heartbeat_time:
            time_since_last_heartbeat = (current_time - self.last_heartbeat_time).total_seconds()
            if time_since_last_heartbeat > HEARTBEAT_TIMEOUT_THRESHOLD:
                status_text_array.append(f"No HeartBeat for more than {HEARTBEAT_TIMEOUT_THRESHOLD} seconds.")
                connection_lost = True
            else:
                last_heartbeat_str = self.last_heartbeat_time.strftime('%Y-%m-%d <u>%H:%M:%S</u>')
                status_text_array.append(f"Last HeartBeat @ {last_heartbeat_str}")
        else:
            status_text_array.append("No HeartBeat received yet.")

        if self._instance == SLAVE and not connection_lost:
            status_text_array.append(f"Slave connected ~ {self.master_slave_addr_port[0]}:{self.master_slave_addr_port[1]}")

        decoded_packet_text = f"Message Packet #{self.output_model.rowCount()} {self.get_size_of_output_model()}"
        if self.last_targeted_call:
            decoded_packet_text += f" ~ Focus on <u>{self.last_targeted_call}</u>"
        
        status_text_array.append(decoded_packet_text)

        if self.last_decode_packet_time:
            time_since_last_decode = (current_time - self.last_decode_packet_time).total_seconds()
            network_check_status_interval = 5_000

            status_mode_frequency = f"({current_mode} <u>{display_frequency(self.last_frequency)}</u>)"

            if time_since_last_decode > DECODE_PACKET_TIMEOUT_THRESHOLD:
                status_text_array.append(f"No DecodePacket for more than {DECODE_PACKET_TIMEOUT_THRESHOLD} seconds {status_mode_frequency}.")
                nothing_to_decode = True                
            else:      
                if time_since_last_decode < 3:
                    network_check_status_interval = 500
                    time_since_last_decode_text = f"{time_since_last_decode:.1f}s" 
                    self.update_status_button(STATUS_BUTTON_LABEL_DECODING, STATUS_DECODING_COLOR)                                  
                else:
                    if time_since_last_decode < 15:
                        network_check_status_interval = 1_000
                    time_since_last_decode_text = f"{int(time_since_last_decode)}s"                  
                    self.update_status_button(STATUS_BUTTON_LABEL_MONITORING, STATUS_MONITORING_COLOR) 

                status_text_array.append(f"Last DecodePacket {status_mode_frequency}: {time_since_last_decode_text} ago")  

            # Update new interval if necessary
            if network_check_status_interval != self.network_check_status_interval:
                self.network_check_status_interval = network_check_status_interval
                self.network_check_status.setInterval(self.network_check_status_interval)                               
        else:
            status_text_array.append("No DecodePacket received yet.")
        
        self.status_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.status_label.setText('<br>'.join(status_text_array))

        if connection_lost:            
            self.reset_window_title()
            self.update_status_label_style("red", "white")
            if self._connected:
                if self.global_sound_toggle.isChecked():      
                    self.play_sound("error_occurred")
                self.on_lost_connection()
                self.update_tab_widget_labels_style()
        elif nothing_to_decode: 
            self.update_status_label_style("white", "black")
        else:
            if not self._connected:  
                self.on_resume_connection()
            if self._instance == SLAVE:
                self.update_status_label_style(FG_TIMER_COLOR, EVEN_COLOR)
            else:
                self.update_status_label_style(BG_COLOR_BLACK_ON_YELLOW, FG_COLOR_BLACK_ON_CYAN)

        """
            Handle change for status_button when transmitting
        """
        if self.transmitting and not connection_lost:            
            self.update_status_button(STATUS_BUTTON_LABEL_TRX, STATUS_TRX_COLOR)
            self.last_transmit_time = datetime.now(timezone.utc)
            self.start_blinking_status_button()
            network_check_status_interval = 100            
        elif self.last_transmit_time:
            if self._running:
                self.update_status_button(STATUS_BUTTON_LABEL_MONITORING, STATUS_MONITORING_COLOR) 
            self.last_transmit_time = None
            self.stop_blinking_status_button()   

    def on_lost_connection(self):
        log.warning("Lost connection")
        self._connected = False
        self.operating_band = None
        
        self.stop_blinking_status_button()  
        self.activity_bar_timer.stop()
        self.blink_timer.stop()
        self.enforce_size_limit_timer.stop()

        if sys.platform == 'darwin':
            self.pobjc_timer.stop() 

        self.restore_slave_settings()  
                    
    def on_resume_connection(self):
        log.warning("Resume connection")
        self.worker.reset_settings_signal.emit()   
        self._connected = True    
        self.activity_bar_timer.start(100)
        self.enforce_size_limit_timer.start(60_000) 
        if sys.platform == 'darwin':
            self.pobjc_timer.start(10) 
            
    def on_close(self, event):        
        self.save_window_position()
        if self._running:
            self.stop_monitoring()
        event.accept()

    def open_settings(self):
        log.warning("Settings opened")

        self.last_targeted_call = None
        self.hide_focus_value_label(visible=False)
        
        params = self.load_params()

        dialog = SettingsDialog(self, params)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            new_params = dialog.get_result()
        
            previous_enable_pounce_log = self.enable_pounce_log
            self.enable_pounce_log = new_params.get('enable_pounce_log', True)

            params.update(new_params)
            self.save_params(params)

            log_filename = get_log_filename()

            self.enable_sound_wanted_callsigns      = params.get('enable_sound_wanted_callsigns', True)
            self.enable_sound_directed_my_callsign  = params.get('enable_sound_directed_my_callsign', True)
            self.enable_sound_monitored_callsigns   = params.get('enable_sound_monitored_callsigns', True)
            
            self.adif_file_path                      = params.get('adif_file_path', None)
            self.worked_before_preference           = params.get('worked_before_preference', WKB4_REPLY_MODE_ALWAYS)

            self.toggle_wkb4_column_visibility()

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
        log.debug("Quit")

    def restart_application(self):
        self.restore_slave_settings()
        self.save_window_position()

        self.save_band_settings()
        self.save_worked_callsigns()

        QtCore.QProcess.startDetached(sys.executable, sys.argv)
        QtWidgets.QApplication.quit()
    
    def check_theme_change(self):
        current_dark_mode = ThemeManager.is_dark_apperance()
        if current_dark_mode != self.dark_mode:
            self.dark_mode = current_dark_mode
            self.apply_palette(self.dark_mode)
        
    def apply_palette(self, dark_mode):
        self.dark_mode = dark_mode
        
        if dark_mode:
            qt_bg_color = "#181818"
        else:
            qt_bg_color = "#E0E0E0"
        
        self.filter_widget.setStyleSheet(f"""
            QWidget#FilterWidget {{
                background-color: {qt_bg_color};
                border-radius: 8px;
            }}
        """)

        table_palette = QtGui.QPalette()          

        if dark_mode:
            table_palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor('#353535'))
            table_palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor('#454545'))
            table_palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor('#FFFFFF'))

            self.activity_bar.setColors("#3D3D3D", "#FFFFFF", "#101010")
        else:
            table_palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor('#FFFFFF'))
            table_palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor('#F4F5F5'))
            table_palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor('#000000'))

            self.activity_bar.setColors("#FFFFFF", "#000000", "#C6C6C6")
        
        self.output_table.setPalette(table_palette)

        gridline_color      = '#D3D3D3' if not dark_mode else '#171717'
        background_color    = '#FFFFFF' if not dark_mode else '#353535'

        table_qss           = f"""
            QTableView {{ 
                background-color: {background_color};
                gridline-color: {gridline_color}; 
            }}
            QTableView::item {{
                padding: 5px;
            }}            
            QHeaderView::section {{
                font-weight: normal;
                border: none;
                font: {CUSTOM_FONT_SMALL.pointSize()}pt '{CUSTOM_FONT_SMALL.family() }';
                padding: 0 3px 0 3px;
                border-right: 1px solid {gridline_color};
            }}
            QHeaderView::section:horizontal:last {{
                border-right: none;
            }}
        """

        self.output_table.setStyleSheet(table_qss)
        self.output_table.setPalette(table_palette)
        self.output_table.setShowGrid(False)
        self.wait_pounce_history_table.setStyleSheet(table_qss)
        self.wait_pounce_history_table.setPalette(table_palette)
        self.wait_pounce_history_table.setShowGrid(False)

        self.update_tab_widget_labels_style()

    def save_unique_param(self, key, value):
        """
        frame = inspect.currentframe()
        try:
            caller = frame.f_back
            co_name = caller.f_code.co_name        
            log.warning(f"save_unique_param: '{co_name}' from '{caller}'")
        finally:
            del frame
        """

        params      = self.load_params()
        params[key] = value
        self.save_params(params)  

    def save_params(self, params):
        """
        frame = inspect.currentframe()
        try:
            caller = frame.f_back
            co_name = caller.f_code.co_name        
            log.warning(f"save_params: '{co_name}' from '{caller}'")
        finally:
            del frame
        """

        with open(PARAMS_FILE, "wb") as f:
            pickle.dump(params, f)

    def load_params(self):
        if os.path.exists(PARAMS_FILE):
            try:
                with open(PARAMS_FILE, "rb") as f:
                    return pickle.load(f)
            except (EOFError, pickle.UnpicklingError):
                print(f"Warning: {PARAMS_FILE} is empty or corrupted. Deleting it.")
                os.remove(PARAMS_FILE) 
                return {}
        return {}
    
    def clear_worked_callsigns(self):
        self.worked_callsigns_history = []
        self.save_worked_callsigns()
        self.wait_pounce_history_table.setRowCount(0)            
        self.clear_worked_history_action.setEnabled(False)
        self.update_worked_callsigns_history_counter()

    def remove_worked_callsign(self, callsign, band = None):
        updated_history = [
            entry for entry in self.worked_callsigns_history
            if not (entry.get("callsign") == callsign and (band is None or entry.get("band") == band))
        ]

        if len(updated_history) < len(self.worked_callsigns_history):
            self.worked_callsigns_history = updated_history
            self.save_worked_callsigns()
            self.wait_pounce_history_table.setRowCount(0)
            self.load_worked_history_callsigns()
        
        self.clear_worked_history_action.setEnabled(len(self.worked_callsigns_history) > 0)

    def save_worked_callsigns(self):
        with open(WORKED_CALLSIGNS_FILE, "wb") as f:
            pickle.dump(self.worked_callsigns_history, f)

    def load_worked_history_callsigns(self):
        if os.path.exists(WORKED_CALLSIGNS_FILE):
            try:
                if os.path.getsize(WORKED_CALLSIGNS_FILE) > 0: 
                    with open(WORKED_CALLSIGNS_FILE, "rb") as f:
                        self.worked_callsigns_history = pickle.load(f)

                    for raw_data in self.worked_callsigns_history:
                        self.add_row_to_history_table(raw_data, add_to_history=False)
                    self.update_worked_callsigns_history_counter()
                else:
                    self.worked_callsigns_history = []
            except (EOFError, pickle.UnpicklingError) as e:
                self.worked_callsigns_history = []
        else:        
            self.worked_callsigns_history = []          

    def update_worked_callsigns_history_counter(self):
        self.worked_history_callsigns_label.setText(WORKED_CALLSIGNS_HISTORY_LABEL % len(self.worked_callsigns_history))

    def on_focus_value_label_clicked(self, event= None):
        message = self.focus_value_label.text()

        if message:
            self.scroll_to_message_uid(self.last_focus_value_message_uid)
            self.copy_message_to_clipboard(message)

    def copy_message_to_clipboard(self, message):
        pyperclip.copy(message)
        log.warning(f"Copied to clipboard: {message}")

    def update_model_data(
            self,
            wanted,
            callsign,
            wkb4_year,
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
            message_type,
            row_color         = None,
            message_uid       = None
        ):

        """
            Store data for filter use
        """
        raw_data = {
            "wanted"            : wanted, 
            "callsign"          : callsign,
            "wkb4_year"         : wkb4_year,
            "directed"          : directed,
            "date_str"          : date_str,
            "band"              : band,
            "snr"               : snr,
            "delta_time"        : delta_time,
            "delta_freq"        : delta_freq,
            "message"           : message,
            "formatted_message" : formatted_message,
            "entity"            : entity,
            "cq_zone"           : cq_zone,
            "continent"         : continent,
            "row_datetime"      : datetime.now(timezone.utc),
            "row_color"         : row_color,
            "uid"               : message_uid,
        }

        """"
            Adding data to model then scroll to bottom
        """
        self.output_model.add_raw_data(raw_data)
        self.output_table.scrollToBottom()

        # Update values for filter
        self.update_combo_box_values(raw_data)

        if message_type == 'ready_to_log':
            self.add_row_to_history_table(raw_data)
            self.update_var(self.wanted_callsigns_vars[band], callsign, "remove")

        self.clear_button.setEnabled(True)

    def scroll_to_message_uid(self, uid, column=0, scroll_hint=QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter):
        row = self.output_model.findRowByUid(uid)
        if row == -1:
            return  

        source_index = self.output_model.index(row, column)
        if not source_index.isValid():
            return
        
        proxy_index = self.filter_proxy_model.mapFromSource(source_index)

        self.output_table.scrollTo(proxy_index, scroll_hint)        
        self.output_table.setCurrentIndex(proxy_index)

    def add_row_to_history_table(self, raw_data, add_to_history=True):
        row_id = self.wait_pounce_history_table.rowCount()
        self.wait_pounce_history_table.insertRow(row_id)

        band            = raw_data["band"]

        item_date = QTableWidgetItem(raw_data["date_str"])

        item_date.setData(QtCore.Qt.ItemDataRole.UserRole, {
            'row_datetime'      : raw_data["row_datetime"],
            'callsign'          : raw_data["callsign"], 
            'band'              : raw_data["band"], 
            'directed'          : raw_data["directed"],
            'wanted'            : raw_data["directed"],
            'cq_zone'           : raw_data["cq_zone"],
            'formatted_message' : raw_data["formatted_message"].strip()
        })       

        item_date.setData(QtCore.Qt.ItemDataRole.DisplayRole, raw_data["date_str"])
        item_date.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.wait_pounce_history_table.setItem(row_id, 0, item_date)

        item_callsign = QtWidgets.QTableWidgetItem(raw_data["callsign"])
        self.wait_pounce_history_table.setItem(row_id, 1, item_callsign)

        item_band = QtWidgets.QTableWidgetItem(band)
        item_band.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.wait_pounce_history_table.setItem(row_id, 2, item_band)

        if add_to_history:
            self.worked_callsigns_history.append(raw_data)
            self.clear_worked_history_action.setEnabled(True)
            self.update_worked_callsigns_history_counter()     

        self.wait_pounce_history_table.scrollToBottom()    

    def apply_filters(self):
        callsign_filter   = self.callsign_input.text().strip().upper()
        country_filter    = self.country_input.text().strip().upper()
        continent_filter  = self.continent_combo.currentText()
        selected_color   = self.color_combo.currentData()
        selected_band    = self.band_combo.currentText()
        cq_filter         = self.cq_combo.currentText()

        filters_map = [
            ('callsign',   callsign_filter,  ""),
            ('country',    country_filter,   ""),
            ('cq_zone',    cq_filter,        DEFAULT_FILTER_VALUE),
            ('continent',  continent_filter, DEFAULT_FILTER_VALUE),
            ('row_color',  selected_color,  None),
            ('band',       selected_band,   DEFAULT_FILTER_VALUE),
        ]

        show_all_messages = False

        for key, user_value, default_value in filters_map:
            if user_value and user_value != default_value:
                self.filter_proxy_model.setFilter(key, user_value)
                show_all_messages = True
            else:
                self.filter_proxy_model.setFilter(key, default_value)

        if show_all_messages:
            self.filter_proxy_model.showAllData()

    def clear_output_and_filters(self):
        self.hide_focus_value_label(visible=False)
        self.hide_status_menu()
        self.clear_filters()
        self.filter_proxy_model.clearTableView()
        self.wait_pounce_history_table.scrollToBottom()  
        self.output_table.scrollToBottom() 

    def clear_filters(self):
        self.filter_proxy_model.hideErasedData()

        self.callsign_input.clear()
        self.country_input.clear()

        self.cq_combo.setCurrentIndex(0)
        self.continent_combo.setCurrentIndex(0)
        self.band_combo.setCurrentIndex(0)
        self.color_combo.setCurrentIndex(0)    

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

    def get_timer_bg_color(self, current_time):
        if (current_time.second // get_mode_interval(self.mode)) % 2 == 0:
            return EVEN_COLOR
        else:
            return ODD_COLOR

    def update_mode_timer(self):
        current_time = datetime.now(timezone.utc)        

        self.timer_value_label.setText(current_time.strftime("%H:%M:%S"))
        self.timer_value_label.setStyleSheet(f"""
            background-color: {self.get_timer_bg_color(current_time)};
            color: {FG_TIMER_COLOR};
            padding: 10px;
            border-radius: 8px;
        """)

    def update_status_button(
            self,        
            text = "",
            bg_color = "black",
            fg_color = "white",
        ):
            # log.error(f"Update status button to : [ {text} ]")
            if (
                self.status_button.current_text     != text     or
                self.status_button.current_bg_color != bg_color or
                self.status_button.current_fg_color != fg_color
            ):      
                self.status_button.updateStyle(text, bg_color, fg_color)

    def update_tab_widget_labels_style(self):
        # Définition des styles de base
        styles = [
            (BG_COLOR_BLACK_ON_YELLOW, FG_COLOR_BLACK_ON_YELLOW),
            (BG_COLOR_BLACK_ON_PURPLE, FG_COLOR_BLACK_ON_PURPLE),
            (BG_COLOR_BLACK_ON_CYAN, FG_COLOR_BLACK_ON_CYAN),
            ("transparent", "palette(text)")
        ]

        # Styles réutilisables
        active_style_template = """
            background-color: {bg_color};
            color: {fg_color};
            border-radius: 6px;
            padding: 3px;
        """
        default_style = """
            border-radius: 6px;
            color: palette(text);
            padding: 3px;
        """
        slave_style = f"""
            background-color: {FG_TIMER_COLOR};
            color: {EVEN_COLOR};
        """

        for band in AMATEUR_BANDS.keys():
            content_widget = self.tab_widget.get_content_widget(band)
            layout = content_widget.layout()

            for idx, (bg_color, fg_color) in enumerate(styles, start=1):
                label_widget = layout.itemAtPosition(idx, 0).widget()
                input_widget = layout.itemAtPosition(idx, 1).widget()

                if band == self.operating_band and self._running:
                    label_widget.setStyleSheet(active_style_template.format(bg_color=bg_color, fg_color=fg_color))
                    if idx == 1 and self._instance == SLAVE:
                        input_widget.setEnabled(False)
                        input_widget.setStyleSheet(slave_style)
                    else:
                        input_widget.setEnabled(True)
                        input_widget.setStyleSheet("")
                else:
                    label_widget.setStyleSheet(default_style)
                    if idx == 1:
                        input_widget.setEnabled(True)
                        input_widget.setStyleSheet("")

    def create_main_menu(self):
        self.menu_bar.setStyleSheet(f"""
            QMenuBar {{
                font: {CUSTOM_FONT.pointSize()}pt '{CUSTOM_FONT.family() }';
            }}
            QMenu {{
                font: {CUSTOM_FONT.pointSize()}pt '{CUSTOM_FONT.family() }';
            }}""")

        main_menu = self.menu_bar.addMenu(GUI_LABEL_NAME)

        about_action = QtGui.QAction(f"About {GUI_LABEL_NAME}", self)
        about_action.triggered.connect(self.show_about_dialog)
        main_menu.addAction(about_action)
        
        main_menu.addSeparator()

        self.monitoring_action = QtGui.QAction(self.get_monitoring_action_text(), self)
        self.monitoring_action.setShortcut(QtGui.QKeySequence("Ctrl+M"))
        self.update_monitoring_action()
        main_menu.addAction(self.monitoring_action)
        
        if sys.platform == 'darwin':
            restart_action = QtGui.QAction(ACTION_RESTART, self)
            restart_action.setShortcut(QtGui.QKeySequence("Ctrl+R"))
            restart_action.triggered.connect(self.restart_application)
            main_menu.addAction(restart_action)

        main_menu.addSeparator()

        enable_sound_action = QtGui.QAction("Enable Sounds", self)
        enable_sound_action.setShortcut(QtGui.QKeySequence("Ctrl+S"))
        enable_sound_action.triggered.connect(self.update_global_sound_preference)
        enable_sound_action.setCheckable(True)  
        enable_sound_action.setChecked(self.enable_global_sound)  
        main_menu.addAction(enable_sound_action)

        enable_marathon_action = QtGui.QAction("Enable Marathon", self)
        enable_marathon_action.setShortcut(QtGui.QKeySequence("Ctrl+H"))
        enable_marathon_action.triggered.connect(self.update_marathon_preference)
        enable_marathon_action.setCheckable(True)  
        enable_marathon_action.setChecked(self.enable_marathon)  
        main_menu.addAction(enable_marathon_action)

        settings_action = QtGui.QAction("Settings...", self)
        settings_action.setShortcut("Ctrl+,")  # Default shortcut for macOS
        settings_action.triggered.connect(self.open_settings)
        main_menu.addAction(settings_action)

        check_update_action = QtGui.QAction("Check for Updates...", self)
        check_update_action.setShortcut("Ctrl+I")  
        check_update_action.triggered.connect(lambda: self.updater.check_expiration_or_update(True))
        main_menu.addAction(check_update_action)

        # Add Online menu
        self.online_menu = self.menu_bar.addMenu("Online")

        load_clublog_action = QtGui.QAction("Update DXCC Info", self)
        load_clublog_action.triggered.connect(self.clublog_manager.load_clublog_info)
        
        self.online_menu.addAction(load_clublog_action)

        # Add Window menu
        self.window_menu = self.menu_bar.addMenu("Window")

        show_all_messages_action = QtGui.QAction("Show All Messages", self)
        show_all_messages_action.setShortcut(QtGui.QKeySequence("Ctrl+T"))
        show_all_messages_action.setCheckable(True)  
        show_all_messages_action.setChecked(self.enable_show_all_decoded)  
        show_all_messages_action.triggered.connect(self.update_show_all_decoded_preference)

        self.show_all_messages_action = show_all_messages_action
        
        self.window_menu.addAction(show_all_messages_action)
        
        filter_visibility_action = QtGui.QAction("Show Filters", self)
        filter_visibility_action.setShortcut(QtGui.QKeySequence("Ctrl+F"))
        filter_visibility_action.setCheckable(True)  
        filter_visibility_action.setChecked(self.enable_filter_gui)  
        filter_visibility_action.triggered.connect(self.update_filter_gui_preference)

        self.filter_visibility_action = filter_visibility_action
        
        self.window_menu.addAction(filter_visibility_action)

        self.window_menu.addSeparator()

        clear_filters_action = QtGui.QAction("Clear Filters", self)
        clear_filters_action.setShortcut(QtGui.QKeySequence("Ctrl+W")) 
        clear_filters_action.triggered.connect(self.clear_filters)  
        self.window_menu.addAction(clear_filters_action)

        clear_output_action = QtGui.QAction("Clear rows from Table", self)
        clear_output_action.setShortcut(QtGui.QKeySequence("Ctrl+K")) 
        clear_output_action.triggered.connect(self.clear_output_and_filters)  
        self.window_menu.addAction(clear_output_action)
        
        format_time_menu = self.window_menu.addMenu("Format Time")

        self.age_column_action = QtGui.QAction("Show Age", self)
        self.age_column_action.setCheckable(True)
        self.age_column_action.setChecked(self.datetime_column_setting == DATE_COLUMN_AGE)
        self.age_column_action.triggered.connect(self.enable_age_column)

        self.datetime_column_action = QtGui.QAction("Show Time", self)
        self.datetime_column_action.setCheckable(True)
        self.datetime_column_action.setChecked(self.datetime_column_setting == DATE_COLUMN_DATETIME)
        self.datetime_column_action.triggered.connect(self.enable_datetime_column)

        format_time_menu.addAction(self.age_column_action)
        format_time_menu.addAction(self.datetime_column_action)        

        action_group = QtGui.QActionGroup(self)
        action_group.addAction(self.age_column_action)
        action_group.addAction(self.datetime_column_action)
        action_group.setExclusive(True)

        self.window_menu.addSeparator()
        self.clear_worked_history_action = QtGui.QAction("Clear Worked Callsigns History", self)
        self.clear_worked_history_action.setEnabled(len(self.worked_callsigns_history) > 0)
        self.clear_worked_history_action.triggered.connect(self.clear_worked_callsigns)

        self.window_menu.addAction(self.clear_worked_history_action)

        self.window_menu.addSeparator()

        show_adif_summary_action = QtGui.QAction("Show ADIF stats", self)
        show_adif_summary_action.setEnabled(self.adif_file_path is not None)
        show_adif_summary_action.triggered.connect(self.show_adif_summary_dialog)

        show_adif_summary_action.setShortcut(QtGui.QKeySequence("Ctrl+P"))

        self.show_adif_summary_action = show_adif_summary_action

        self.window_menu.addAction(show_adif_summary_action)

    def show_adif_summary_dialog(self):   
        if self.adif_file_path:
            if not os.path.exists(self.adif_file_path):                
                return
            
            try:
                log.warning(f"Read File {self.adif_file_path}")
                processing_time, parsed_data = parse_adif(self.adif_file_path)

                summary_dialog = AdifSummaryDialog(processing_time, parsed_data['wkb4'], self)
                summary_dialog.exec()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to process the ADIF file.\n\n{str(e)}")
        else:
            QtWidgets.QMessageBox.warning(self, "Warning", "No ADIF file path specified.")

    def get_monitoring_action_text(self):
        return STOP_BUTTON_LABEL if self._running else STATUS_BUTTON_LABEL_START

    def update_monitoring_action(self):
        try:
            self.monitoring_action.triggered.disconnect()
        except TypeError:
            pass

        if self._running:
            self.monitoring_action.setText(STOP_BUTTON_LABEL)
            self.monitoring_action.triggered.connect(self.stop_monitoring)
        else:
            self.monitoring_action.setText(STATUS_BUTTON_LABEL_START)
            self.monitoring_action.triggered.connect(self.start_monitoring)
        
    def show_about_dialog(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(f"About {GUI_LABEL_NAME}")
        dialog.setFixedWidth(400)

        layout = QtWidgets.QVBoxLayout(dialog)

        icon_path = os.path.join(CURRENT_DIR, "pounce.png")
        icon_label = CustomQLabel()
        icon_pixmap = QtGui.QPixmap(icon_path)
        if not icon_pixmap.isNull(): 
            icon_pixmap = icon_pixmap.scaled(
                300,  
                icon_pixmap.height(),  
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,  
                QtCore.Qt.TransformationMode.SmoothTransformation  
            )

        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        program_name = CustomQLabel(f"<b>{GUI_LABEL_NAME}</b>")
        program_name.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        program_name.setStyleSheet("font-size: 14px;")
        layout.addWidget(program_name)

        version_label = CustomQLabel(f"Version: {CURRENT_VERSION_NUMBER}")
        version_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(version_label)

        first_separator = QtWidgets.QFrame()
        first_separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        first_separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        layout.addWidget(first_separator)

        discord_section = CustomQLabel(DISCORD_SECTION)
        discord_section.setOpenExternalLinks(True)
        discord_section.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(discord_section)

        layout.addStretch()

        current_year = datetime.now().year
        copyright_label = CustomQLabel(f'Copyright {current_year} Cédric Morelle <a href="https://qrz.com/db/f5ukw">F5UKW</a>')
        copyright_label.setOpenExternalLinks(True)
        copyright_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(copyright_label)

        thanks_label = CustomQLabel("With special thanks to:")
        thanks_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(thanks_label)

        thanks_names = CustomQLabel("Rick, DU6/PE1NSQ, Vincent F4BKV, Juan TG9AJR, Neil G0JHC")
        thanks_names.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(thanks_names)

        layout.addStretch()

        second_separator = QtWidgets.QFrame()
        second_separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        second_separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        layout.addWidget(second_separator)

        donation_link = CustomQLabel(DONATION_SECTION)
        donation_link.setOpenExternalLinks(True)
        donation_link.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(donation_link)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        ok_button = CustomButton("OK")
        ok_button.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        dialog.exec()        

    def save_band_settings(self):
        params = self.load_params()

        for band in AMATEUR_BANDS.keys():
            wanted_callsigns                    = self.wanted_callsigns_vars[band].text()
            monitored_callsigns                 = self.monitored_callsigns_vars[band].text()
            monitored_cq_zones                  = self.monitored_cq_zones_vars[band].text()
            excluded_callsigns                  = self.excluded_callsigns_vars[band].text()
            excluded_cq_zones                   = self.excluded_cq_zones_vars[band].text()
            
            params.setdefault(band, {}).update({
                "monitored_callsigns"           : monitored_callsigns,
                "monitored_cq_zones"            : monitored_cq_zones,
                "excluded_callsigns"            : excluded_callsigns,
                "excluded_cq_zones"             : excluded_cq_zones,
                "wanted_callsigns"              : wanted_callsigns
            })
        self.save_params(params)               

    def start_monitoring(self):
        self._running = True   
        self.update_monitoring_action()   

        self.network_check_status.start(self.network_check_status_interval)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_mode_timer)
        self.timer.start(200)

        self.is_status_button_label_visible = True
        self.is_status_button_label_blinking = False

        self.update_status_button(STATUS_BUTTON_LABEL_MONITORING, STATUS_MONITORING_COLOR)
        self.status_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        self.blink_timer = QtCore.QTimer()
        self.blink_timer.timeout.connect(self.toggle_label_visibility)

        self.stop_event.clear()
        self.hide_focus_value_label(visible=False)  

        # self.apply_band_change(self.gui_selected_band)
        
        params                              = self.load_params()
        local_ip_address                    = get_local_ip_address()

        freq_range_mode                     = params.get('freq_range_mode')
        primary_udp_server_address          = params.get('primary_udp_server_address') or local_ip_address
        primary_udp_server_port             = int(params.get('primary_udp_server_port') or DEFAULT_UDP_PORT)
        secondary_udp_server_address        = params.get('secondary_udp_server_address') or local_ip_address
        secondary_udp_server_port           = int(params.get('secondary_udp_server_port') or DEFAULT_UDP_PORT)
        enable_secondary_udp_server         = params.get('enable_secondary_udp_server', DEFAULT_SECONDARY_UDP_SERVER)
        logging_udp_server_address          = params.get('logging_udp_server_address') or local_ip_address
        logging_udp_server_port             = int(params.get('logging_udp_server_port') or DEFAULT_UDP_PORT)
        enable_logging_udp_server           = params.get('enable_logging_udp_server', DEFAULT_SECONDARY_UDP_SERVER)
        enable_sending_reply                = params.get('enable_sending_reply', DEFAULT_SENDING_REPLY)
        max_reply_attemps_to_callsign       = params.get('max_reply_attemps_to_callsign', DEFAULT_REPLY_ATTEMPTS)
        max_working_delay                   = params.get('max_working_delay', DEFAULT_MAX_WAITING_DELAY)
        enable_gap_finder                    = params.get('enable_gap_finder', DEFAULT_GAP_FINDER)
        enable_watchdog_bypass              = params.get('enable_watchdog_bypass', DEFAULT_WATCHDOG_BYPASS)
        enable_debug_output                 = params.get('enable_debug_output', DEFAULT_DEBUG_OUTPUT)
        enable_pounce_log                   = params.get('enable_pounce_log', DEFAULT_POUNCE_LOG)
        enable_log_packet_data              = params.get('enable_log_packet_data', DEFAULT_LOG_PACKET_DATA)
        enable_log_all_valid_contact        = params.get('enable_log_all_valid_contact', DEFAULT_LOG_ALL_VALID_CONTACT)        

        self.adif_file_path                  = params.get('adif_file_path', None)
        self.adif_worked_backup_file_path           = params.get('adif_worked_backup_file_path', None)
        self.worked_before_preference       = params.get('worked_before_preference', WKB4_REPLY_MODE_ALWAYS)
        self.marathon_preference            = params.get('marathon_preference', {})
        
        self.save_unique_param('freq_range_mode', freq_range_mode )        

        # Create a QThread and a Worker object
        self.thread = QThread()
        self.worker = Worker(
            self.monitoring_settings,
            freq_range_mode,
            self.stop_event,
            primary_udp_server_address,
            primary_udp_server_port,
            secondary_udp_server_address,
            secondary_udp_server_port,
            enable_secondary_udp_server,
            logging_udp_server_address,
            logging_udp_server_port,
            enable_logging_udp_server,            
            enable_sending_reply,
            max_reply_attemps_to_callsign,
            max_working_delay,
            enable_log_all_valid_contact,
            enable_gap_finder,
            enable_watchdog_bypass,
            enable_debug_output,
            enable_pounce_log,
            enable_log_packet_data,
            self.adif_file_path,
            self.adif_worked_backup_file_path,
            self.worked_before_preference,
            self.enable_marathon,
            self.marathon_preference           
        )
        self.worker.moveToThread(self.thread)

        if self.worker:
            self.worker.listener_started.connect(self.on_listener_started)

        # Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.error.connect(self.set_notice_to_focus_value_label)
        self.worker.error.connect(self.handle_worker_error)

        self.worker.message.connect(self.on_message_received)

        self.thread.start()   

    def handle_worker_error(self, error_message):
        log.error(error_message)
        self.stop_worker() 
        self.stop_monitoring()

    def on_listener_started(self):
        if platform.system() == 'Windows':
            self.tray_icon = TrayIcon()
            tray_icon_thread = threading.Thread(target=self.tray_icon.start, daemon=True)
            tray_icon_thread.start()

        self.status_label.setText(WAITING_DATA_PACKETS_LABEL)    
        self.update_status_label_style("yellow", "black")

    def stop_worker(self):
        if self.worker:
            self.worker.blockSignals(True)
            self.worker = None
        if self.thread is not None:
            if self.thread.isRunning():
                self.thread.quit()
                self.thread.wait()
            self.thread = None

    def stop_tray_icon(self):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None

    def stop_monitoring(self):
        self.network_check_status.stop()
        self.activity_bar.setValue(0) 
        self.hide_status_menu()

        if self.worker:
            self.worker.finished.disconnect()
            self.worker.error.disconnect()
            self.worker.message.disconnect()

            self.worker.stop()  
            self.worker = None

        if self.thread:
            self.thread.started.disconnect()
            self.thread.finished.disconnect()
        
        if self.timer: 
            self.timer.stop()
            self.timer_value_label.setText(DEFAULT_MODE_TIMER_VALUE)        

        if self._running:
            self.stop_event.set()

            self.worker              = None
            self._running            = False       

            self.update_tab_widget_labels_style()
            self.restore_slave_settings()

            self._instance = MASTER
            self.operating_band      = None
            self.transmitting        = False
            
            self.stop_tray_icon()
            self.stop_blinking_status_button()            

            self.tab_widget.set_selected_tab(self.band_indices.get(self.operating_band))
            self.tab_widget.set_operating_tab(None)

            self.update_status_label_style(STATUS_COLOR_LABEL_SELECTED, "white")
            self.update_status_button(STATUS_BUTTON_LABEL_START, STATUS_TRX_COLOR)

            self.status_button.resetStyle()
            self.status_button.setEnabled(True)
            self.stop_button.setEnabled(False)

            # Update Windows menu            
            self.update_monitoring_action()   
            self.reset_window_title()

            log.warning(f"Running: {self._running}")

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

    def log_exception_to_file(self, filename, message):
        timestamp = datetime.now(timezone.utc).strftime("%y%m%d_%H%M%S")
        with open(filename, "a") as log_file:
            log_file.write(f"{timestamp} {message}\n")
    
    def status_menu_agent_cleaner(self):
        if sys.platform == 'darwin':
            self.status_menu_agent.hide_status_bar()
            self.status_menu_agent.deleteLater()       

def on_about_to_quit(window):
    log.info("Application is about to quit. Cleaning up...")

    if sys.platform == 'darwin':
        try:
            log.info("Calling status_menu_agent_cleaner")
            window.status_menu_agent_cleaner()
        except Exception as e:
            log.exception("Error in status_menu_agent_cleaner")

    try:
        log.info("Calling save_band_settings")
        window.save_band_settings()
    except Exception as e:
        log.exception("Error in save_band_settings")

    try:
        log.info("Calling save_worked_callsigns")
        window.save_worked_callsigns()
    except Exception as e:
        log.exception("Error in save_worked_callsigns")     

def main():
    app             = QtWidgets.QApplication(sys.argv)    
    window          = MainApp()
    update_timer    = QtCore.QTimer()

    window.updater  = UpdateManager()
    window.updater.check_expiration_or_update()

    window.show()
    window.update_status_menu_message((f'{GUI_LABEL_VERSION}').upper(), BG_COLOR_REGULAR_FOCUS, FG_COLOR_REGULAR_FOCUS)   
   
    if is_first_launch_or_new_version(CURRENT_VERSION_NUMBER):
        window.show_about_dialog() 
        save_current_version(CURRENT_VERSION_NUMBER)

    app.aboutToQuit.connect(lambda: on_about_to_quit(window))

    log.info("Starting application event loop")
    exit_code = app.exec()

    log.info("Application event loop finished with exit code %s", exit_code)
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
