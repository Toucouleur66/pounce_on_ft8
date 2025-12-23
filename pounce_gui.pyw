# pounce_gui.pyw

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from PyQt6.QtCore import QPropertyAnimation, QThread
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

import platform
import re
import sys
import pickle
import json
import os
import threading
import pyperclip
import sys
import threading
import webbrowser
import time

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
from custom_status_bar import CustomStatusBar
from adif_summary_dialog import AdifSummaryDialog
from time_ago_delegate import TimeAgoDelegate
from color_row_delegate import ColorRowDelegate
from search_field_input import SearchFilterInput
from tray_icon import TrayIcon
from activity_bar import ActivityBar
from tooltip import ToolTip, ExcludedCallsignsToolTip
from worker import Worker
from monitoring_setting import MonitoringSettings
from theme_manager import ThemeManager
from context_menu_handler import ContextMenuHandler
from clublog import ClubLogManager
from lotw_manager import LoTWManager
from country_files import CountryFilesManager
from setting_dialog import SettingsDialog
from exclusion_dialog import ExclusionDialog
from updater import Updater, UpdateManager
from raw_data_model import RawDataModel
from raw_data_filter_proxy_model import RawDataFilterProxyModel
from grid_map_viewer import GridMapWindow
from active_users_window import ActiveUsersWindow

if sys.platform == 'darwin':
    from status_menu import StatusMenuAgent

# Translation strings
from translatable_strings import MainWindowStrings, CommonStrings, ContextMenuStrings, ErrorStrings, TimeStrings

from utils import get_local_ip_address, matches_any, get_app_data_dir
from utils import get_mode_interval, get_amateur_band, display_frequency
from utils import force_input, focus_out_event, text_to_array, has_significant_change
from utils import calculate_sunrise_sunset

from version import is_first_launch_or_new_version, save_current_version

from logger import get_logger, add_timed_file_handler, remove_file_handler, cleanup_old_logs

from utils import(
    AMATEUR_BANDS
)

from style import (
    # Colors
    EVEN_COLOR,
    ODD_COLOR,
    FG_TIMER_COLOR,
    FG_COLOR_FOCUS_MY_CALL,
    BG_COLOR_FOCUS_MY_CALL,
    FG_COLOR_REGULAR_FOCUS,
    BG_COLOR_REGULAR_FOCUS,
    BG_COLOR_BLACK_ON_SAUMON,
    BG_COLOR_BLACK_ON_YELLOW,
    FG_COLOR_BLACK_ON_YELLOW,
    BG_COLOR_WHITE_ON_BLUE,
    FG_COLOR_BLACK_ON_WHITE,
    BG_COLOR_BLACK_ON_PURPLE,
    FG_COLOR_BLACK_ON_PURPLE,
    BG_COLOR_BLACK_ON_CYAN,
    FG_COLOR_BLACK_ON_CYAN,
    BG_COLOR_WHITE_ON_BLUE_VIOLET,
    FG_COLOR_WHITE_ON_BLUE_VIOLET,
    # Status buttons
    STATUS_MONITORING_COLOR,
    STATUS_DECODING_COLOR,
    STATUS_TRX_COLOR,
    # Functions
    set_macos_window_appearance,
    get_main_table_qss
)

from constants import (
    CURRENT_VERSION_NUMBER,
    MASTER,
    SLAVE,
    PRIORITY_LIST,
    # Parameters
    PARAMS_FILE,
    PARAMS_FILE_LEGACY,
    POSITION_FILE,
    WORKED_CALLSIGNS_FILE,
    TEMP_EXCLUDED_CALLSIGNS_FILE,
    # Labels
    GUI_LABEL_NAME,
    GUI_LABEL_VERSION,
    # Note: Button/status labels now in translatable_strings.py
    # Datetime column
    DATE_COLUMN_DATETIME,
    DATE_COLUMN_AGE,
    # Theme mode
    THEME_MODE_LIGHT,
    THEME_MODE_DARK,
    THEME_MODE_SYSTEM,
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
    DEFAULT_POLITE_REPLY,
    # Default settings
    DEFAULT_AUTO_START_MONITORING,
    DEFAULT_GAP_FINDER,
    DEFAULT_WATCHDOG_BYPASS,
    DEFAULT_DEBUG_OUTPUT,
    DEFAULT_POUNCE_LOG,
    DEFAULT_LOG_PACKET_DATA,
    DEFAULT_SHOW_ALL_DECODED,
    DEFAULT_LOG_ALL_VALID_CONTACT,
    DEFAULT_DELAY_BETWEEN_SOUND,
    DEFAULT_MAX_WAITING_DELAY,
    DEFAULT_MINIMUM_REPORT,
    ACTIVITY_BAR_MAX_VALUE,
    WKB4_REPLY_MODE_ALWAYS,
    convert_wkb4_reply_mode,
    # Fonts
    CUSTOM_FONT,
    CUSTOM_FONT_MONO_LG,
    CUSTOM_FONT_SMALL,
    # URL
    DISCORD_SECTION,
    DONATION_SECTION,
    DONATION_URL,
    # Threshold
    HEARTBEAT_TIMEOUT_THRESHOLD,
    DECODE_PACKET_TIMEOUT_THRESHOLD,
    # Frequency constants
    FREQ_MINIMUM,
    FREQ_MAXIMUM
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

        self.window_title        = None
        self.window_size         = None

        self.worker              = None
        self.timer               = None
        self.tray_icon           = None
        self.grid_monitor        = None
        self.active_users_window = None
        self.app_shutting_down   = False

        self.grid_monitor_geometry  = {}

        self.monitoring_settings    = MonitoringSettings()       
        self.clublog_manager        = ClubLogManager(self)
        self.lotw_manager           = LoTWManager(self) 
        self.country_files_manager  = CountryFilesManager(self)
        self.context_menu_handler   = ContextMenuHandler(self)
        self.updater                = UpdateManager()

        self.status_menu_agent      = None
        self.local_params          = self.load_params()

        # Initialize translation system
        from translations import get_translation_manager
        self.translation_manager = get_translation_manager()
        current_language = self.local_params.get('language', 'en')
        self.translation_manager.load_translation(current_language)

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
        self.setMinimumSize(780, 600)   

        if platform.system() == 'Windows':
            if getattr(sys, 'frozen', False): 
                icon_path = os.path.join(sys._MEIPASS, "pounce.ico")
            else:
                icon_path = "pounce.ico"

            self.setWindowIcon(QtGui.QIcon(icon_path))    

        self.stop_event = threading.Event()
        self.error_occurred.connect(self.set_notice_to_focus_value_label)
        self.message_received.connect(self.handle_message_received)

        self.message_times = deque()
        
        self.activity_bar_timer = QtCore.QTimer()
        self.activity_bar_timer.timeout.connect(self.update_activity_bar)
        self.activity_bar_timer.start(100)
        self.theme_manager = ThemeManager()
        self.theme_manager.theme_changed.connect(self.apply_theme_to_all)

        self.theme_timer = QtCore.QTimer(self)
        self.theme_timer.timeout.connect(self.theme_manager.check_theme_change)
        self.theme_timer.start(1_000)

        self.worker_signal_timer = QtCore.QTimer(self)
        self.worker_signal_timer.setSingleShot(True)
        self.worker_signal_timer.timeout.connect(self._emit_worker_signal) 

        self.network_check_status_interval = 5_000
        self.network_check_status = QtCore.QTimer()
        self.network_check_status.timeout.connect(self.check_connection_status)

        self._running                           = False
        self._instance                          = None
        self._connected                         = True
        self._synch_signal                      = True
        self._synched_addr_port                 = None

        self.latest_messages                    = []

        self.before_synch_wanted_callsigns      = {}
        self.before_synch_wanted_cq_zones       = {}
        self.before_synch_excluded_callsigns    = {}
        self.before_synch_excluded_cq_zones     = {}

        self.decode_packet_count                = 0
        self.last_decode_packet_time            = None
        self.last_heartbeat_time                = None
        self.last_focus_value_message_uid       = None 
        self.last_transmit_time                 = False               
        self.last_sound_played_time             = datetime.min
        self.mode                               = None
        self.my_call                            = None
        self.my_grid                            = None
        self.last_targeted_call                 = None
        self.my_wsjtx_id                        = None
        self.transmitting                       = False
        self.band                               = None
        self.last_frequency                     = None
        self.frequency                          = None
        self.gui_selected_band                  = None
        self.operating_band                     = None
        self.enable_show_all_decoded            = None
        self.message_buffer                     = deque(maxlen=500)      
                
        self.menu_bar                           = self.menuBar() 

        self.sound_queue                        = Queue()
        self.sound_timer                        = QtCore.QTimer()
        self.sound_timer.timeout.connect(self.play_next_sound)
        self.currently_playing = False

        # Initialize audio output for better macOS device handling
        self.audio_output = QAudioOutput()
        
        # Create sound players with sources
        self.sound_files = {
            'wanted_callsign_first_time_decoded': f"{CURRENT_DIR}/sounds/709060__scottyd0es__aeroce-proximity-notification.wav",
            'wanted_callsign_decoded': f"{CURRENT_DIR}/sounds/495650__matrixxx__supershort-ping-or-short-notification.wav",
            'wanted_callsign_being_called': f"{CURRENT_DIR}/sounds/716444__scottyd0es__tone12_alert_5.wav",
            'wanted_grid': f"{CURRENT_DIR}/sounds/709065__scottyd0es__aeroce-polytone-4.wav",
            'directed_to_my_call': f"{CURRENT_DIR}/sounds/716445__scottyd0es__tone12_error.wav",
            'ready_to_log': f"{CURRENT_DIR}/sounds/709072__scottyd0es__aeroce-dualtone-5.wav",
            'error_occurred': f"{CURRENT_DIR}/sounds/142608__autistic-lucario__error.wav",
            'monitored_callsign_decoded': f"{CURRENT_DIR}/sounds/716442__scottyd0es__tone12_alert_3.wav",
            'band_change': f"{CURRENT_DIR}/sounds/342759__rhodesmas__score-counter-01.wav",
            'updated_settings': f"{CURRENT_DIR}/sounds/342757__rhodesmas__searching-03.wav",
            'enable_global_sound': f"{CURRENT_DIR}/sounds/342754__rhodesmas__searching-01.wav",
            'blitz': f"{CURRENT_DIR}/sounds/blitz_mono.wav"
        }
        
        # Create media player for sound playback
        self.media_player = QMediaPlayer()
        self.media_player.setAudioOutput(self.audio_output)

        self.enable_pounce_log                  = self.local_params.get('enable_pounce_log', True)
        self.enable_extra_gui_debug_output      = self.local_params.get('enable_extra_gui_debug_output', False)
        self.enable_filter_gui                  = self.local_params.get('enable_filter_gui', False)        
        self.enable_grid_monitor                = self.local_params.get('enable_grid_monitor', False)
        self.enable_compact_view                = self.local_params.get('enable_compact_view', False)
        self.enable_alternate_compact_view      = self.local_params.get('enable_alternate_compact_view', False)
        self.enable_global_sound                = self.local_params.get('enable_global_sound', True)
        self.enable_sending_reply               = self.local_params.get('enable_sending_reply', DEFAULT_SENDING_REPLY)
        self.enable_show_all_decoded            = self.local_params.get('enable_show_all_decoded', DEFAULT_SHOW_ALL_DECODED)
        self.datetime_column_setting            = self.local_params.get('datetime_column_setting', DATE_COLUMN_DATETIME)
        self.theme_mode_setting                 = self.local_params.get('theme_mode_setting', THEME_MODE_SYSTEM)

        self.adif_file_path                     = self.local_params.get('adif_file_path', None)
        self.worked_before_preference           = convert_wkb4_reply_mode(self.local_params.get('worked_before_preference', WKB4_REPLY_MODE_ALWAYS))
        self.marathon_preference                = self.local_params.get('marathon_preference', {})
        self.grid_tracker_preference            = self.local_params.get('grid_tracker_preference', {})

        self.enable_auto_start_monitoring       = self.local_params.get('enable_auto_start_monitoring', DEFAULT_AUTO_START_MONITORING)

        # Get sound configuration
        self.enable_sound_wanted_callsigns      = self.local_params.get('enable_sound_wanted_callsigns', True)
        self.enable_sound_directed_my_callsign  = self.local_params.get('enable_sound_directed_my_callsign', True)
        self.enable_sound_monitored_callsigns   = self.local_params.get('enable_sound_monitored_callsigns', True)
        self.delay_between_sound_for_monitored  = self.local_params.get('delay_between_sound_for_monitored', DEFAULT_DELAY_BETWEEN_SOUND)

        self.file_handler = None
        if self.enable_pounce_log:
            self.file_handler = add_timed_file_handler()
              
        """
            Wait and Pounce History
        """
        self.worked_callsigns_history = [] 

        self.wait_pounce_history_table = self.init_wait_pounce_history_table_ui()
        self.wait_pounce_history_table.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)

        refresh_history_table_timer = QtCore.QTimer(self)
        refresh_history_table_timer.start(1_000)        
        refresh_history_table_timer.timeout.connect(lambda: self.wait_pounce_history_table.viewport().update())
        
        """
            Exclusion timer
        """
        self.exclusion_cleanup_timer = QtCore.QTimer(self)
        self.exclusion_cleanup_timer.start(10_000) 
        self.exclusion_cleanup_timer.timeout.connect(self.cleanup_expired_exclusions)

        """
            Top layout for focus_frame and timer_value_label
        """
        self.top_layout = QtWidgets.QHBoxLayout()
        self.top_layout.setContentsMargins(0, 0, 0, 5)
        self.top_layout.setSpacing(0)
        
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
        
        self.top_layout.addWidget(self.focus_frame)
        self.top_layout.addSpacing(15)

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

        self.top_layout.addWidget(self.timer_value_label)

        self.create_main_menu() 

        """
            Widget Tab
        """
        self.tab_widget = self.init_tab_widget_ui()

        """
            Status bar
        """
        self.status_bar_label_heartbeat     = QtWidgets.QLabel()
        self.status_bar_label_mode          = QtWidgets.QLabel()
        self.status_bar_label_connection    = QtWidgets.QLabel()
        self.status_bar_label_packet        = QtWidgets.QLabel()
        self.status_bar_label_reply         = QtWidgets.QLabel()
        self.status_bar_label_decode_packet = QtWidgets.QLabel()
        self.status_bar_label_freq          = QtWidgets.QLabel()

        self.processing_active              = False

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
            Compact mode
        """
        self.compact_mode_visible  = False

        """
            Toggle buttons
        """
        self.clear_button = CustomButton(CommonStrings.ERASE())
        self.clear_button.setEnabled(False)
        self.clear_button.clicked.connect(self.clear_output_and_filters)

        self.settings = CustomButton(CommonStrings.SETTINGS())
        self.settings.clicked.connect(self.open_settings)

        self.global_sound_toggle = AnimatedToggle(
             checked_color=STATUS_MONITORING_COLOR,
             pulse_checked_color=f"{STATUS_MONITORING_COLOR}FF"
        )
        self.global_sound_toggle.stateChanged.connect(self.toggle_global_sound_preference)
        self.global_sound_toggle.setFixedSize(self.global_sound_toggle.sizeHint())
        self.global_sound_toggle.setChecked(self.enable_global_sound)

        self.reply_toggle = AnimatedToggle(
            checked_color=STATUS_MONITORING_COLOR,
            pulse_checked_color=f"{STATUS_MONITORING_COLOR}FF"
        )
        self.reply_toggle.stateChanged.connect(self.toggle_reply_preference)
        self.reply_toggle.setFixedSize(self.reply_toggle.sizeHint())
        self.reply_toggle.setChecked(self.enable_sending_reply)

        self.show_all_toggle = AnimatedToggle(
            checked_color=STATUS_MONITORING_COLOR,
            pulse_checked_color=f"{STATUS_MONITORING_COLOR}FF"
        )
        self.show_all_toggle.stateChanged.connect(self.update_show_all_preference)
        self.show_all_toggle.setFixedSize(self.show_all_toggle.sizeHint())
        self.show_all_toggle.setChecked(self.enable_show_all_decoded)

        self.filter_gui_toggle = AnimatedToggle(
            checked_color=STATUS_MONITORING_COLOR,
            pulse_checked_color=f"{STATUS_MONITORING_COLOR}FF"
        )
        self.filter_gui_toggle.stateChanged.connect(self.update_filter_gui_preference)
        self.filter_gui_toggle.setFixedSize(self.filter_gui_toggle.sizeHint())
        self.filter_gui_toggle.setChecked(self.enable_filter_gui)

        self.grid_monitor_toggle = AnimatedToggle(
            checked_color=STATUS_MONITORING_COLOR,
            pulse_checked_color=f"{STATUS_MONITORING_COLOR}FF"
        )
        self.grid_monitor_toggle.stateChanged.connect(self.update_grid_monitor_preference)
        self.grid_monitor_toggle.setFixedSize(self.grid_monitor_toggle.sizeHint())
        self.grid_monitor_toggle.setChecked(self.enable_grid_monitor)

        self.alternate_compact_view_toggle = AnimatedToggle(
            checked_color=STATUS_MONITORING_COLOR,
            pulse_checked_color=f"{STATUS_MONITORING_COLOR}FF"
        )
        self.alternate_compact_view_toggle.stateChanged.connect(self.toggle_alternate_compact_view)
        self.alternate_compact_view_toggle.setFixedSize(self.alternate_compact_view_toggle.sizeHint())
        self.alternate_compact_view_toggle.setChecked(False)

        # Regular toggle buttons layout (shown in normal mode)
        self.toggle_buttons_layout = QtWidgets.QWidget()
        self.toggle_buttons_layout.setFixedHeight(50)

        horizontal_layout = QtWidgets.QHBoxLayout()
        horizontal_layout.setContentsMargins(0, 0, 0, 0)
        horizontal_layout.setSpacing(0)  

        # self.sounds_label = CustomQLabel("Sounds")
        # horizontal_layout.addWidget(self.sounds_label)
        # horizontal_layout.addWidget(self.global_sound_toggle)

        self.reply_label = CustomQLabel(MainWindowStrings.REPLY_LABEL())
        horizontal_layout.addWidget(self.reply_label)
        horizontal_layout.addWidget(self.reply_toggle)

        horizontal_layout_spacer = QtWidgets.QWidget()
        horizontal_layout_spacer.setFixedWidth(20)
        horizontal_layout.addWidget(horizontal_layout_spacer)

        self.all_label = CustomQLabel(MainWindowStrings.ALL_LABEL())
        horizontal_layout.addWidget(self.all_label)
        horizontal_layout.addWidget(self.show_all_toggle)

        horizontal_layout.addWidget(horizontal_layout_spacer)

        self.filters_label = CustomQLabel(MainWindowStrings.FILTERS_LABEL())
        horizontal_layout.addWidget(self.filters_label)
        horizontal_layout.addWidget(self.filter_gui_toggle)

        horizontal_layout.addWidget(horizontal_layout_spacer)

        self.map_label = CustomQLabel(MainWindowStrings.GRID_MONITOR_LABEL())
        horizontal_layout.addWidget(self.map_label)
        horizontal_layout.addWidget(self.grid_monitor_toggle)

        self.toggle_buttons_layout.setLayout(horizontal_layout)
        self.toggle_buttons_layout.setFixedHeight(44)

        self.toggle_alternate_buttons_layout = QtWidgets.QWidget()
        self.toggle_alternate_buttons_layout.setFixedHeight(50)

        horizontal_layout = QtWidgets.QHBoxLayout()
        horizontal_layout.setContentsMargins(0, 0, 0, 0)
        horizontal_layout.setSpacing(0)
        horizontal_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
        
        self.alternate_compact_view_label = CustomQLabel(MainWindowStrings.ALTERNATE_VIEW_LABEL())
        horizontal_layout.addWidget(self.alternate_compact_view_label)
        horizontal_layout.addWidget(self.alternate_compact_view_toggle)

        self.toggle_alternate_buttons_layout.setLayout(horizontal_layout)
        self.toggle_alternate_buttons_layout.setFixedHeight(44)
        self.toggle_alternate_buttons_layout.setVisible(False)

        """
            Bottom layout
        """
        bottom_layout = QtWidgets.QHBoxLayout()

        self.quit_button = CustomButton(CommonStrings.CLOSE())
        self.quit_button.clicked.connect(self.quit_application)

        self.inputs_enabled = True

        if sys.platform == 'darwin':
            self.restart_button = CustomButton(MainWindowStrings.RESTART_ACTION())
            self.restart_button.clicked.connect(self.restart_application)

        # Timer and start/stop buttons
        self.status_button = CustomButton(MainWindowStrings.START_MONITORING_LABEL())
        self.status_button.clicked.connect(self.start_monitoring)
        self.status_button.setFixedWidth(140)
        self.status_button.setMinimumWidth(140)
        
        self.stop_button = CustomButton(MainWindowStrings.STOP_BUTTON_LABEL())
        self.stop_button.setEnabled(False)        
        self.stop_button.clicked.connect(self.stop_monitoring)   
        #self.status_button.setFixedWidth(100)     
        
        """
            Button layout
        """
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(15) 

        # button_layout.addWidget(self.settings)
        button_layout.addWidget(self.clear_button)

        if sys.platform == 'darwin':
            button_layout.addWidget(self.restart_button)

        button_layout.addWidget(self.status_button)
        button_layout.addWidget(self.stop_button)
        # button_layout.addWidget(self.quit_button)

        bottom_layout.addWidget(self.toggle_buttons_layout)
        bottom_layout.addWidget(self.toggle_alternate_buttons_layout)
        bottom_layout.addStretch()  
        bottom_layout.addLayout(button_layout)

        bottom_widget = QtWidgets.QWidget()
        bottom_widget.setLayout(bottom_layout)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_widget.setFixedHeight(50)    

        """
            Bottom layout spacer (controllable widget)
        """
        self.bottom_layout_spacer = QtWidgets.QWidget()
        self.bottom_layout_spacer.setFixedHeight(10)        

        """
            Central, Outer and Main Layout
        """
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        outer_layout = QtWidgets.QHBoxLayout()
        central_widget.setLayout(outer_layout)

        self.main_layout = QtWidgets.QGridLayout()
        outer_layout.addLayout(self.main_layout)
        
        """
            Main layout
        """
        self.worked_history_widget = QtWidgets.QWidget()
        self.worked_history_widget.setContentsMargins(0, 15, 0, 0)

        worked_history_layout = QtWidgets.QVBoxLayout(self.worked_history_widget)
        worked_history_layout.setSpacing(0) 
        worked_history_layout.setContentsMargins(20, 0, 0, 0)
        worked_history_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        self.worked_callsign_label = QtWidgets.QLabel()
        self.worked_callsign_label.setFont(CUSTOM_FONT_SMALL)
        worked_history_layout.addWidget(self.worked_callsign_label)
        worked_history_layout.addItem(QtWidgets.QSpacerItem(0, 10, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed))
        worked_history_layout.addWidget(self.wait_pounce_history_table)
        worked_history_layout.addStretch()
        self.worked_history_widget.setMaximumWidth(200)
        self.worked_history_widget.setObjectName("worked_history_widget") 
        self.worked_history_widget.setMaximumWidth(220)
        self.worked_history_widget.setFixedHeight(220)
       
        self.container_tab = QtWidgets.QWidget()
        container_layout = QtWidgets.QHBoxLayout(self.container_tab)
        container_layout.setContentsMargins(0, 0, 0, 0)  
        container_layout.setSpacing(10)
        container_layout.addWidget(self.tab_widget) 
        container_layout.addWidget(self.worked_history_widget) 

        self.main_layout.setSpacing(0) 
        self.main_layout.addLayout(self.top_layout, 0, 0, 1, 1)
                
        self.top_layout_spacer = QtWidgets.QWidget()
        self.top_layout_spacer.setFixedHeight(10)
        self.main_layout.addWidget(self.top_layout_spacer, 1, 0)
        
        self.main_layout.addWidget(self.container_tab, 2, 0)
        
        # Add container layout spacer after container_tab
        self.container_layout_spacer = QtWidgets.QWidget()
        self.container_layout_spacer.setFixedHeight(8)
        self.main_layout.addWidget(self.container_layout_spacer, 3, 0)
        
        self.main_layout.addWidget(self.output_table, 4, 0)
        self.main_layout.setRowStretch(4, 1)
        self.main_layout.addWidget(self.filter_widget, 5, 0)
        
        # Add bottom spacer between filter and bottom widget
        self.main_layout.addWidget(self.bottom_layout_spacer, 6, 0)
        
        self.main_layout.addWidget(bottom_widget, 7, 0)

        self.main_layout.setContentsMargins(5, 0, 5, 0)  

        """
            Activity Bar
        """
        self.activity_bar = ActivityBar(max_value=ACTIVITY_BAR_MAX_VALUE)
        self.activity_bar.setFixedWidth(30)

        outer_layout.addWidget(self.activity_bar)

        """
            self.operating_band might be overided as soon as check_connection_status is used
        """
        self.gui_selected_band = self.local_params.get('last_band_used', DEFAULT_SELECTED_BAND)
       
        QtCore.QTimer.singleShot(100, lambda: self.tab_widget.set_selected_tab(self.gui_selected_band))

        self.load_worked_history_callsigns()
        self.load_temp_excluded_callsigns()

        if self.theme_mode_setting == THEME_MODE_LIGHT:
            self.theme_timer.stop()
            self.apply_palette(False)
        elif self.theme_mode_setting == THEME_MODE_DARK:
            self.theme_timer.stop()
            self.apply_palette(True)
        else:
            self.apply_theme_to_all(self.theme_manager.dark_mode)

        self.load_window_position()
        self.toggle_wkb4_column_visibility()        

        QtCore.QTimer.singleShot(100, lambda: self.wait_pounce_history_table.scrollToBottom())

        if self.datetime_column_setting == DATE_COLUMN_AGE:
            self.enable_age_column()
        else:
            self.enable_datetime_column()

        QtCore.QTimer.singleShot(1_000, lambda: self.init_activity_bar())   

        self.process_timer = False
        self.process_timer_timeout = QtCore.QTimer()
        self.process_timer_timeout.timeout.connect(self.reset_process_timer)
        self.process_timer_timeout.setSingleShot(True)

        self.enforce_size_limit_timer = QtCore.QTimer()
        self.enforce_size_limit_timer.timeout.connect(self.output_model.enforce_size_limit)
        self.enforce_size_limit_timer.start(60_000) 
                
        # Close event to save position
        self.closeEvent = self.on_close
        
        # Set focus policy for main window to handle keyboard events
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        if self.enable_compact_view:
            self.toggle_compact_view(True)

        if self.enable_auto_start_monitoring:
            self.start_monitoring()
        
    def init_status_bar(self):
            self.status_bar = CustomStatusBar()
            self.status_bar.clicked.connect(self.open_settings)
            self.setStatusBar(self.status_bar)

            for label in (
                self.status_bar_label_mode,
                self.status_bar_label_heartbeat,
                self.status_bar_label_connection,
                self.status_bar_label_packet,
                self.status_bar_label_reply,
                self.status_bar_label_decode_packet,
                self.status_bar_label_freq
            ):
                label.setMouseTracking(True)
                label.setCursor(QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
                label.setStyleSheet(f"""
                    QLabel {{
                        font-family: {CUSTOM_FONT_SMALL.family()};
                        font-size: {CUSTOM_FONT_SMALL.pointSize()}pt;            
                        padding-left: 5px;
                        padding-right: 5px;      
                        border: none;
                    }}
                """)
            self.status_bar.addWidget(self.status_bar_label_mode, 1)       
            self.status_bar.addWidget(self.status_bar_label_freq, 1)                         
            self.status_bar.addWidget(self.status_bar_label_packet, 2)    
            self.status_bar_label_packet.setFixedWidth(160)         
            self.status_bar.addWidget(self.status_bar_label_decode_packet, 2)          
            self.status_bar_label_decode_packet.setFixedWidth(175)     
            self.status_bar.addWidget(self.status_bar_label_heartbeat, 1)
            # self.status_bar.addWidget(self.status_bar_label_reply, 1)
            self.status_bar.addWidget(self.status_bar_label_connection, 2)            

            self.status_bar.setContentsMargins(10, 3, 10, 3)

    def blinking_grid(self):
        if (
            self.last_focus_value_message_uid
            and self.grid_monitor
            and self.grid_monitor.isVisible()
        ):            
            self.grid_monitor.map_widget.trigger_grid_blink(self.last_focus_value_message_uid)

    @QtCore.pyqtSlot()
    def on_status_menu_clicked(self):
        self.show()
        self.showNormal()
        self.raise_()
        self.activateWindow()
        
        self.blinking_grid()
        self.on_focus_value_label_clicked()
        self.hide_status_menu()
        self.scroll_to_message_uid(self.last_focus_value_message_uid)
            
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
            self.status_menu_agent.hide_status_menu_agent()

    def init_tab_widget_ui(self):
        tab_widget = CustomTabWidget()
        tab_widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        
        self.wanted_callsigns_vars              = {}
        self.monitored_callsigns_vars           = {}
        self.excluded_callsigns_vars            = {}
        self.temp_excluded_callsigns            = {}  # {band: {callsign: expiration_time}}
        self.wanted_cq_zones_vars               = {}
        self.monitored_cq_zones_vars            = {}
        self.excluded_cq_zones_vars             = {}        

        self.tooltip_wanted_vars                = {}
        self.tooltip_monitored_vars             = {}
        self.tooltip_excluded_callsigns_vars    = {}
        self.tooltip_wanted_cq_zones_vars       = {}
        self.tooltip_excluded_cq_zones_vars     = {}
        self.tooltip_monitored_cq_zones_vars    = {}

        self.band_indices                       = {}
        self.band_content_widgets               = {}

        wanted_dict = {
            'wanted_callsigns'      : self.wanted_callsigns_vars,
            'monitored_callsigns'   : self.monitored_callsigns_vars,            
            'wanted_cq_zones'       : self.wanted_cq_zones_vars,
            'monitored_cq_zones'    : self.monitored_cq_zones_vars,
            'excluded_callsigns'    : self.excluded_callsigns_vars,            
            'excluded_cq_zones'     : self.excluded_cq_zones_vars,
        }

        tooltip_wanted_dict = {
            'wanted_callsigns'      : self.tooltip_wanted_vars,
            'monitored_callsigns'   : self.tooltip_monitored_vars,
            'wanted_cq_zones'       : self.tooltip_wanted_cq_zones_vars,
            'monitored_cq_zones'    : self.tooltip_monitored_cq_zones_vars,
            'excluded_callsigns'    : self.tooltip_excluded_callsigns_vars,
            'excluded_cq_zones'     : self.tooltip_excluded_cq_zones_vars,
        }

        sought_variables = [
            {
                'name'             : 'wanted_callsigns',
                'label'            : MainWindowStrings.WANTED_CALLSIGNS_LABEL(),
                'function'         : partial(force_input, mode="uppercase"),
                'placeholder'      : MainWindowStrings.CALLSIGN_PLACEHOLDER(),
                'on_changed_method': self.on_wanted_callsigns_changed,
            },
            {
                'name'             : 'monitored_callsigns',
                'label'            : MainWindowStrings.MONITORED_CALLSIGNS_LABEL(),
                'function'         : partial(force_input, mode="uppercase"),
                'placeholder'      : MainWindowStrings.CALLSIGN_PLACEHOLDER(),
                'on_changed_method': self.on_monitored_callsigns_changed,
            },
            {
                'name'             : 'wanted_cq_zones',
                'label'            : MainWindowStrings.WANTED_CQ_ZONES_LABEL(),
                'function'         : partial(force_input, mode="numbers"),
                'placeholder'      : MainWindowStrings.CQ_ZONE_PLACEHOLDER(),
                'on_changed_method': self.on_wanted_cq_zones_changed,
            },
            {
                'name'             : 'monitored_cq_zones',
                'label'            : MainWindowStrings.MONITORED_CQ_ZONES_LABEL(),
                'function'         : partial(force_input, mode="numbers"),
                'placeholder'      : MainWindowStrings.CQ_ZONE_PLACEHOLDER(),
                'on_changed_method': self.on_monitored_cq_zones_changed,
            },
            {
                'name'             : 'excluded_callsigns',
                'label'            : MainWindowStrings.EXCLUDED_CALLSIGNS_LABEL(),
                'function'         : partial(force_input, mode="uppercase"),
                'placeholder'      : MainWindowStrings.CALLSIGN_PLACEHOLDER(),
                'on_changed_method': self.on_excluded_callsigns_changed,
            },
            {
                'name'             : 'excluded_cq_zones',
                'label'            : MainWindowStrings.EXCLUDED_CQ_ZONES_LABEL(),
                'function'         : partial(force_input, mode="numbers"),
                'placeholder'      : MainWindowStrings.CQ_ZONE_PLACEHOLDER(),
                'on_changed_method': self.on_excluded_cq_zones_changed,
            }
        ]

        for amateur_band in AMATEUR_BANDS.keys():
            tab_content = QtWidgets.QWidget()
            layout = QtWidgets.QGridLayout(tab_content)

            band_params = self.local_params.get(amateur_band, {})

            for idx, variable_info in enumerate(sought_variables):
                line_edit = QtWidgets.QLineEdit()
                line_edit.setFont(CUSTOM_FONT)
                line_edit.setPlaceholderText(variable_info['placeholder'])

                wanted_dict[variable_info['name']][amateur_band] = line_edit

                #tooltip_wanted_dict[variable_info['name']][amateur_band] = ToolTip(line_edit)

                line_edit.setText(band_params.get(variable_info['name'], ""))

                line_label = CustomQLabel(variable_info['label'])
                line_label.setStyleSheet("border-radius: 6px; padding: 3px;")
                line_label.setMinimumWidth(100)

                # Use appropriate tooltip type based on field name
                if variable_info['name'] == 'excluded_callsigns':
                    tooltip_wanted_dict[variable_info['name']][amateur_band] = ExcludedCallsignsToolTip(
                        line_label,
                        source_widget=line_edit,
                        default_text=MainWindowStrings.CALLSIGN_PLACEHOLDER(),
                        main_window=self,
                        band=amateur_band,
                        bg_color=BG_COLOR_REGULAR_FOCUS,
                        fg_color=FG_COLOR_REGULAR_FOCUS
                    )
                elif variable_info['name'] == 'excluded_cq_zones':
                    tooltip_wanted_dict[variable_info['name']][amateur_band] = ToolTip(
                        line_label,
                        source_widget=line_edit,
                        default_text=MainWindowStrings.CQ_ZONE_PLACEHOLDER(),
                        bg_color=BG_COLOR_REGULAR_FOCUS,
                        fg_color=FG_COLOR_REGULAR_FOCUS
                    )
                else:
                    tooltip_type = variable_info['name']
                    tooltip_wanted_dict[variable_info['name']][amateur_band] = ToolTip(
                        line_label,
                        source_widget=line_edit,
                        default_text=variable_info['placeholder'],
                        tooltip_type=tooltip_type
                    )

                layout.addWidget(line_label, idx+1, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
                layout.addWidget(line_edit, idx+1, 1)

                line_edit.textChanged.connect(partial(variable_info['function'], line_edit))
                focus_out_event(line_edit, mode=variable_info['function'].keywords.get('mode', 'uppercase'))
                line_edit.textChanged.connect(variable_info['on_changed_method'])

            tab_content.setLayout(layout)
            self.band_content_widgets[amateur_band] = tab_content
            tab_widget.addTab(tab_content, amateur_band)

        tab_widget.tabClicked.connect(self.on_tab_clicked)     

        return tab_widget

    def init_wait_pounce_history_table_ui(self):
        wait_pounce_history_table = QtWidgets.QTableWidget()
        wait_pounce_history_table.setColumnCount(3)

        header_item = QTableWidgetItem(MainWindowStrings.HEADER_AGE())
        header_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        wait_pounce_history_table.setHorizontalHeaderItem(0, header_item)

        header_item = QTableWidgetItem(MainWindowStrings.WORKED_CALLSIGNS_LABEL())
        header_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        wait_pounce_history_table.setHorizontalHeaderItem(1, header_item)

        header_item = QTableWidgetItem(MainWindowStrings.BAND_LABEL())
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

        wait_pounce_history_table.horizontalHeader().setVisible(False)
        wait_pounce_history_table.setFixedHeight(168)

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
        output_table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                border-top: none;
                border-right: none;
                border-left: none;
                border-bottom: 1px solid palette(Mid);
            }
        """)

        column_widths = [160, 45, 60, 60, 80, 450, 5, 140, 70, 60, 80]  
        
        header = output_table.horizontalHeader()
        header.setMinimumSectionSize(20)  # Set global minimum
        
        for i, width in enumerate(column_widths):
            if i < output_table.model().columnCount():                                        
                if i == 5:
                    output_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
                else:
                    output_table.setColumnWidth(i, width)  
        
        output_table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        output_table.horizontalHeader().sectionResized.connect(self.on_country_column_resized)

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

        self.callsign_input = search_filter.create_search_field(MainWindowStrings.FILTER_CALLSIGN())
        self.country_input = search_filter.create_search_field(MainWindowStrings.FILTER_COUNTRY())

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
            (MainWindowStrings.FILTER_CALLSIGN(), self.callsign_input),
            (MainWindowStrings.FILTER_BAND(), self.band_combo),
            (MainWindowStrings.FILTER_COLOR(), self.color_combo),
            (MainWindowStrings.FILTER_ZONE(), self.cq_combo),
            (MainWindowStrings.FILTER_CONTINENT(), self.continent_combo),
            (MainWindowStrings.FILTER_COUNTRY(), self.country_input),
        ]

        for idx, (label_text, widget) in enumerate(fields):
            label = CustomQLabel(label_text)
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            inner_layout.addWidget(widget, 0, idx)
            inner_layout.addWidget(label, 1, idx)

        outer_layout = QtWidgets.QVBoxLayout(filter_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(inner_widget, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)

        return filter_widget

    def update_global_sound_preference(self, checked):  
        if self.enable_global_sound != checked:
            self.enable_global_sound = checked
            self.global_sound_toggle.setChecked(checked)
            self.save_unique_param('enable_global_sound', checked)      

    def toggle_global_sound_preference(self, checked):
        if checked:
            QtCore.QTimer.singleShot(500, lambda: self.play_sound('enable_global_sound'))

        self.update_global_sound_preference(checked)

    def toggle_reply_preference(self, checked):
        self.enable_sending_reply = True if checked else False
        self.save_unique_param('enable_sending_reply', self.enable_sending_reply)
        
        self.monitoring_settings.set_sending_reply(self.enable_sending_reply)
        self.send_worker_signal()

        if not self.enable_sending_reply:
            self.play_sound("error_occurred")

        if self.worker:
            self.worker.enable_sending_reply = self.enable_sending_reply
            self.refresh_monitoring()

    def update_show_all_preference(self, checked):
        self.filter_proxy_model.setEnableShowAllDecoded(checked)
        self.filter_proxy_model.invalidateFilter()
    
        if self.enable_show_all_decoded != checked:
            self.enable_show_all_decoded = checked
            self.show_all_toggle.setChecked(checked)
            self.show_all_action.setChecked(checked)  
            
            self.save_unique_param('enable_show_all_decoded', checked)   

        self.output_table.scrollToBottom()            

    def update_filter_gui_preference(self, checked):
        if self.enable_alternate_compact_view:
            return 
        
        if checked:
            self.show_filter_layout()
        else:
            self.clear_filters()
            self.hide_filter_layout()            
        
        if self.enable_filter_gui != checked:
            self.enable_filter_gui = checked
            self.filter_gui_toggle.setChecked(checked)
            self.filter_gui_action.setChecked(checked)
            self.save_unique_param('enable_filter_gui', checked)     

    def toggle_wkb4_column_visibility(self):
        if self.worked_before_preference == WKB4_REPLY_MODE_ALWAYS:
            self.output_table.setColumnHidden(10, True)
        else:
            self.output_table.setColumnHidden(10, False)

    def hide_filter_layout(self):
        self.filter_widget_visible = False
        self.callsign_input.clearFocus()
        self.animate_layout_height(self.filter_widget, target_height=0)

    def show_filter_layout(self):
        self.filter_widget_visible = True
        self.animate_layout_height(self.filter_widget, target_height=60)  
        QtCore.QTimer.singleShot(0, self.callsign_input.setFocus)

    def toggle_compact_view(self, checked = True):       
        if checked:
            self.enable_compact_view = True

            self.window_size = self.size()

            self.setMinimumSize(790, 360)            
            self.setMaximumSize(2048, 360)
            
            self.hide_container_tab()     
            self.top_layout_spacer.setVisible(False)
            self.activity_bar.setVisible(False)       
            
            self.toggle_buttons_layout.setVisible(False)
            self.toggle_alternate_buttons_layout.setVisible(True)

            self.alternate_compact_view_action.setEnabled(True)
        else:
            self.enable_compact_view = False

            self.setMinimumSize(790, 600)
            self.setMaximumSize(2048, 2048) 

            if self.window_size is not None:
                self.resize(self.window_size)           
            
            self.top_layout_spacer.setVisible(True) 
            
            self.show_output_table()        
            self.show_top_layout()     
            
            self.activity_bar.setVisible(True)              
            
            self.toggle_buttons_layout.setVisible(True)
            self.toggle_alternate_buttons_layout.setVisible(False)

            self.alternate_compact_view_action.setChecked(False)            
            self.alternate_compact_view_toggle.setChecked(False)
            self.alternate_compact_view_action.setEnabled(False)
            
            self.show_container_tab()   

        self.save_unique_param('enable_compact_view', self.enable_compact_view)                       

    def toggle_alternate_compact_view(self, checked = True):
        self.enable_alternate_compact_view = checked
        
        if checked:
            self.update_filter_gui_preference(False)
            if self.filter_gui_action.isEnabled():
                self.filter_gui_action.setChecked(False)

            self.hide_output_table()
            self.hide_top_layout()
            self.show_container_tab()
            self.worked_history_widget.setVisible(False)
            self.container_layout_spacer.setVisible(False)
            self.bottom_layout_spacer.setVisible(False)
        else:
            self.show_output_table()
            self.worked_history_widget.setVisible(True)
            self.show_top_layout()
            self.hide_container_tab()
            self.container_layout_spacer.setVisible(True)
            self.filter_gui_action.setEnabled(True)
            self.bottom_layout_spacer.setVisible(True)

        self.alternate_compact_view_toggle.setChecked(checked)
        self.alternate_compact_view_action.setChecked(checked)
        
        self.save_unique_param('enable_alternate_compact_view', self.enable_alternate_compact_view)

    def toggle_grid_monitor(self, checked):    
        if checked:
            if self.grid_monitor is None:
                self.grid_monitor = GridMapWindow(self)
                self.grid_monitor.map_widget.set_parent_app(self)
                self.grid_monitor.map_widget.grid_clicked.connect(self.scroll_to_message_uid)
                self.update_window_title()
                
            if self.operating_band:
                self.grid_monitor.map_widget.update_operating_band(self.operating_band)
                self.update_grid_monitor_with_grids(self.latest_messages)
            
            if self.grid_monitor_geometry:
                self.grid_monitor.setGeometry(
                    self.grid_monitor_geometry['x'],
                    self.grid_monitor_geometry['y'], 
                    self.grid_monitor_geometry['width'],
                    self.grid_monitor_geometry['height']
                )

            if (
                self.worker and 
                self.worker.listener and
                hasattr(self.worker.listener, 'adif_data')
            ):
                self.grid_monitor.map_widget.update_adif_data(self.worker.listener.adif_data)            
            
            self.grid_monitor.show()
            self.grid_monitor.raise_()
            self.grid_monitor.activateWindow()
        else:                      
            if self.grid_monitor is not None:         
                self.grid_monitor_geometry = {
                    'x'     : self.grid_monitor.geometry().x(),
                    'y'     : self.grid_monitor.geometry().y(),
                    'width' : self.grid_monitor.geometry().width(),
                    'height': self.grid_monitor.geometry().height()
                }

                self.grid_monitor.close()
                self.grid_monitor = None

    def update_grid_monitor_preference(self, checked) :    
        self.toggle_grid_monitor(checked)

        if self.enable_grid_monitor != checked:
            self.enable_grid_monitor = checked
            self.grid_monitor_toggle.setChecked(checked)
            self.grid_monitor_action.setChecked(checked) 

            self.save_unique_param('enable_grid_monitor', checked)
            
    def update_grid_monitor_with_grids(self, messages):
        if not self.grid_monitor:
            return
            
        self.grid_monitor.map_widget.set_new_grids([message for message in messages if "grid" in message] if messages else [])
                       
    def hide_container_tab(self):
        self.compact_mode_visible = False
        self.container_tab.setVisible(False)
        # self.animate_layout_height(self.container_tab, target_height=10)

    def show_container_tab(self):
        self.compact_mode_visible = True
        self.container_tab.setVisible(True)
        # self.animate_layout_height(self.container_tab, target_height=290)

    def animate_layout_height(self, widget, target_height, duration=800):
        widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        widget.setMinimumHeight(0)
        widget.setMaximumHeight(widget.height())

        animation = QPropertyAnimation(widget, b"maximumHeight")
        animation.setDuration(duration)
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

    def hide_output_table(self):
        self.output_table.setVisible(False)
        
    def show_output_table(self):
        self.output_table.setVisible(True)
        
    def hide_top_layout(self):
        for i in range(self.top_layout.count()):
            item = self.top_layout.itemAt(i)
            if item and item.widget():
                item.widget().setVisible(False)
                
    def show_top_layout(self):
        for i in range(self.top_layout.count()):
            item = self.top_layout.itemAt(i)
            if item and item.widget():
                item.widget().setVisible(True)
                
    def hide_other_toggles(self):
        self.sounds_label.setVisible(False)
        self.global_sound_toggle.setVisible(False)
        self.toggle_buttons_layout.setVisible(False)
        
    def show_other_toggles(self):
        self.sounds_label.setVisible(True)
        self.global_sound_toggle.setVisible(True)
        self.toggle_buttons_layout.setVisible(True)

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
        # Set translated header based on mode
        if value == DATE_COLUMN_DATETIME:
            header_text = MainWindowStrings.HEADER_TIME()
        else:  # DATE_COLUMN_AGE
            header_text = MainWindowStrings.HEADER_AGE()
        self.output_model.setHeaderData(0, QtCore.Qt.Orientation.Horizontal, header_text, QtCore.Qt.ItemDataRole.DisplayRole)

    def update_date_mode_param(self):
        self.datetime_column_action.setChecked(self.datetime_column_setting == DATE_COLUMN_DATETIME)
        self.age_column_action.setChecked(self.datetime_column_setting == DATE_COLUMN_AGE)

        self.save_unique_param('datetime_column_setting', self.datetime_column_setting)

    def enable_light_theme(self):
        self.theme_mode_setting = THEME_MODE_LIGHT
        self.theme_timer.stop()
        self.apply_palette(False)
        self.update_theme_mode_param()

        # Propagate to GridMapWindow if it exists
        if self.grid_monitor and hasattr(self.grid_monitor, 'update_theme_from_main_app'):
            self.grid_monitor.update_theme_from_main_app(THEME_MODE_LIGHT, False)

    def enable_dark_theme(self):
        self.theme_mode_setting = THEME_MODE_DARK
        self.theme_timer.stop()
        self.apply_palette(True)
        self.update_theme_mode_param()

        # Propagate to GridMapWindow if it exists
        if self.grid_monitor and hasattr(self.grid_monitor, 'update_theme_from_main_app'):
            self.grid_monitor.update_theme_from_main_app(THEME_MODE_DARK, True)

    def enable_system_theme(self):
        self.theme_mode_setting = THEME_MODE_SYSTEM
        self.theme_timer.start(1_000)
        self.apply_theme_to_all(self.theme_manager.dark_mode)
        self.update_theme_mode_param()

        # Propagate to GridMapWindow if it exists
        if self.grid_monitor and hasattr(self.grid_monitor, 'update_theme_from_main_app'):
            self.grid_monitor.update_theme_from_main_app(THEME_MODE_SYSTEM, self.theme_manager.dark_mode)

    def update_theme_mode_param(self):
        self.light_theme_action.setChecked(self.theme_mode_setting == THEME_MODE_LIGHT)
        self.dark_theme_action.setChecked(self.theme_mode_setting == THEME_MODE_DARK)
        self.system_theme_action.setChecked(self.theme_mode_setting == THEME_MODE_SYSTEM)

        self.save_unique_param('theme_mode_setting', self.theme_mode_setting)

    def clear_line_edit(self, line_edit, button):
        line_edit.clear()
        button.setVisible(False)
        self.apply_filters()

    def create_combo_box(self, values=None, default_value=None):
        combo_box = QtWidgets.QComboBox()
        combo_box.setEditable(False)
        combo_box.setFont(CUSTOM_FONT_SMALL)
        
        if default_value is None:
            default_value = DEFAULT_FILTER_VALUE
        # Add translated "All" but store the identifier
        combo_box.addItem(MainWindowStrings.FILTER_ALL(), userData=DEFAULT_FILTER_VALUE)

        if values:
            combo_box.addItems(values)

        combo_box.currentIndexChanged.connect(self.apply_filters)
        combo_box.setStyleSheet("""
                QComboBox {
                    font-size: 11px;
                    width: 90px;
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

        # Get translated "All" text for comparison
        translated_all = MainWindowStrings.FILTER_ALL()
        existing_items = [combo.itemText(i) for i in range(combo.count()) if combo.itemText(i) != translated_all and combo.itemText(i) != default_value]
        combined_items = set(existing_items).union(new_items)

        if combo == self.band_combo:
            sorted_items = sorted(combined_items, key=lambda x: int(x[:-1]) if x[:-1].isdigit() else float('inf'))
        else:
            numeric_items = sorted((item for item in combined_items if item.isdigit()), key=int)
            non_numeric_items = sorted(item for item in combined_items if not item.isdigit())
            sorted_items = numeric_items + non_numeric_items

        combo.clear()
        # Add translated "All" first
        combo.addItem(translated_all)
        # Then add the rest
        combo.addItems(sorted_items)
        combo.blockSignals(False)

    def create_color_combo_box(self, placeholder_text):
        color_combo = QtWidgets.QComboBox()
        color_combo.setFixedWidth(150)
        color_combo.setIconSize(QtCore.QSize(120, 10))  
        color_combo.setFont(CUSTOM_FONT_SMALL)

        color_combo.addItem(MainWindowStrings.FILTER_ALL(), userData=None)

        for bg_color in [
            BG_COLOR_FOCUS_MY_CALL,
            BG_COLOR_BLACK_ON_YELLOW,
            BG_COLOR_BLACK_ON_SAUMON,
            BG_COLOR_BLACK_ON_PURPLE,
            BG_COLOR_WHITE_ON_BLUE,
            BG_COLOR_BLACK_ON_CYAN,
        ]:
            pixmap = QtGui.QPixmap(120, 10)  
            pixmap.fill(QtGui.QColor(bg_color))
            icon = QtGui.QIcon(pixmap)
            color_combo.addItem(icon, "", userData=bg_color)

        color_combo.setEditable(False)
        color_combo.currentIndexChanged.connect(self.apply_filters)

        return color_combo

    def apply_theme_to_all(self, dark_mode):
        if self.theme_mode_setting == THEME_MODE_SYSTEM:
            self.apply_palette(dark_mode)

    def on_tab_clicked(self, tab_band):
        self.gui_selected_band = tab_band
        self.tab_widget.set_selected_tab(self.gui_selected_band)

        if self.gui_selected_band != self.operating_band and self._running:
            self.tab_widget.set_operating_tab(self.operating_band)

        self.save_unique_param('last_band_used', self.gui_selected_band)  
        
    def apply_band_change(self, band):
        if band != 'Invalid' and band != self.operating_band:    
            self.operating_band = band
            self.monitoring_settings.set_wanted_callsigns(self.wanted_callsigns_vars[self.operating_band].text())
            self.monitoring_settings.set_monitored_callsigns(self.monitored_callsigns_vars[self.operating_band].text())
            self.monitoring_settings.set_wanted_cq_zones(self.wanted_cq_zones_vars[self.operating_band].text())
            self.monitoring_settings.set_excluded_callsigns(self.excluded_callsigns_vars[self.operating_band].text())
            self.monitoring_settings.set_monitored_cq_zones(self.monitored_cq_zones_vars[self.operating_band].text())
            self.monitoring_settings.set_excluded_cq_zones(self.excluded_cq_zones_vars[self.operating_band].text())

            self.monitoring_settings.set_operating_band(band)
            
            self.latest_messages = [] 

            if self.grid_monitor is not None:
                self.grid_monitor.map_widget.update_operating_band(band)
            
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

    def on_wanted_cq_zones_changed(self):
        if self.operating_band:
            self.monitoring_settings.set_wanted_cq_zones(self.wanted_cq_zones_vars[self.operating_band].text())
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
        """
        # Log the caller
        frame = inspect.currentframe().f_back
        caller_info = f"{frame.f_code.co_filename}:{frame.f_lineno} in {frame.f_code.co_name}"
        log.error(f"Pounce/send_worker_signal called from: {caller_info}")
        """
        # Don't schedule signal if we're in the middle of applying synched settings
        if not self._synch_signal:
            return

        # Restart the debounce timer - will only emit after 200ms of no calls
        self.worker_signal_timer.stop()
        self.worker_signal_timer.start(200)

    def _emit_worker_signal(self):
        # Actually emit the signals after debounce delay
        #log.error("Pounce/_emit_worker_signal: Emitting worker signals")
        if self.worker is not None:
            self.worker.update_listener_settings_signal.emit()
            if self._instance is not None and self._synch_signal:
                self.worker.synch_settings_signal.emit()  

    @QtCore.pyqtSlot(object)
    def handle_message_received(self, message):        
        if isinstance(message, dict):            
            window_title_changed = False
            if message.get('my_call') and message.get('my_call') != self.my_call:
                self.my_call = message.get('my_call')
                window_title_changed = True
            if message.get('my_grid') and message.get('my_grid') != self.my_grid:
                self.my_grid = message.get('my_grid')
                window_title_changed = True
            if message.get('wsjtx_id') and message.get('wsjtx_id') != self.my_wsjtx_id:
                self.my_wsjtx_id = message.get('wsjtx_id')
                window_title_changed = True
            
            if window_title_changed:
                self.update_window_title()

            message_type = message.get('type', None)

            if message_type == 'gui_alert':
                self.set_message_to_focus_value_label(message)    
                self.stop_monitoring()   
            elif message_type == 'update_mode':
                self.mode = message.get('mode')          
            elif message_type == 'instance_status':
                self.check_instance(
                        message.get('addr_port'),
                        message.get('status')
                    )          
            elif message_type == 'instance_settings':
                self.apply_instance_settings(message.get('settings'))                  
            elif message_type == 'instance_synched':
                self._synched_addr_port = message.get('addr_port')
            elif message_type == 'update_frequency':
                self.frequency = message.get('frequency')                
                if self.frequency != self.last_frequency:
                    self.last_frequency = self.frequency
                    band      = get_amateur_band(self.frequency)
                    if band != 'Invalid':
                        self.set_notice_to_focus_value_label(f"{band} {self.mode} {display_frequency(self.last_frequency)} {self.my_wsjtx_id or ''}")                     
                        self.tab_widget.set_selected_tab(band)   
                        self.update_window_title()
            elif message_type == 'stop_monitoring':
                log.warning("Received Stop monitoring request")
                self.play_sound("error_occurred")
                self.stop_monitoring()     

            elif message_type == 'update_wanted_callsign':
                log.debug(f"Received request to update ({message.get('action')}) Wanted Callsigns with [ {message.get('callsign')} ]")
                self.update_var(self.wanted_callsigns_vars[self.operating_band], message.get('callsign'), message.get('action'))  
            elif message_type == 'adif_data_updated':
                if self.grid_monitor is not None:
                    log.debug("Received request to update ADIF data in Grid Monitor")
                    self.grid_monitor.map_widget.update_adif_data(message.get('adif_data', {}))
            elif message_type == 'adif_processing_started':
                self.start_processing_animation()
            elif message_type == 'adif_processing_progress':
                self.update_processing_progress(
                    message.get('processed', 0), 
                    message.get('total', 0),
                    message.get('file_path', '')
                )
            elif message_type == 'adif_processing_finished':
                self.stop_processing_animation()
            elif message_type == 'update_status':
                if self._running:
                    self.check_connection_status(
                        message.get('decode_packet_count', 0),
                        message.get('last_decode_packet_time'),
                        message.get('last_heartbeat_time'),
                        message.get('frequency'),
                        message.get('transmitting')
                    )     
            elif message_type == 'temporarily_excluded':     
                self.add_callsign_to_exclusion_list(
                    message.get('callsign'),
                )
            elif 'decode_time_str' in message:
                formatted_message   = message.get('formatted_message')
                message_type        = message.get('message_type')

                callsign            = message.get('callsign')
                callsign_info       = message.get('callsign_info', None)
                directed            = message.get('directed')
                my_call             = message.get('my_call')
                wanted              = message.get('wanted')
                wanted_cq_zone      = message.get('wanted_cq_zone')
                wanted_grid         = message.get('wanted_grid')
                monitored           = message.get('monitored')
                monitored_cq_zone   = message.get('monitored_cq_zone')
                excluded            = message.get('excluded')
                wkb4_year           = message.get('wkb4_year')
                entity_wkb4         = message.get('entity_wkb4')

                empty_str           = ''
                entity              = empty_str
                cq_zone             = empty_str
                continent           = empty_str
                                                
                """
                    Handle GUI output
                """
                self.message_times.append(datetime.now())    

                if directed == my_call:
                    message_color      = BG_COLOR_FOCUS_MY_CALL
                elif wanted is True:
                    message_color      = BG_COLOR_BLACK_ON_YELLOW
                elif wanted_cq_zone is True:
                    message_color      = BG_COLOR_BLACK_ON_SAUMON
                elif wanted_grid is True:
                    message_color      = BG_COLOR_BLACK_ON_YELLOW
                elif monitored is True:
                    message_color      = BG_COLOR_BLACK_ON_PURPLE 
                elif monitored_cq_zone is True:
                    message_color      = BG_COLOR_BLACK_ON_CYAN
                elif (
                    directed is not None and 
                    self.operating_band and 
                    matches_any(text_to_array(self.wanted_callsigns_vars[self.operating_band].text()), directed)
                ):                    
                    message_color      = BG_COLOR_WHITE_ON_BLUE
                else:
                    message_color      = None

                
                # Extract LoTW information
                lotw = None
                if callsign_info:
                    entity      = (callsign_info.get("entity") or callsign_info.get("name", "Unknown")).title()
                    cq_zone     = callsign_info.get("cqz")
                    continent   = callsign_info.get("cont")
                    entity_wkb4 = message.get('entity_wkb4')
                    lotw        = callsign_info.get("lotw")

                elif callsign_info is None:
                    entity      = "Where?"

                message['lotw'] = lotw                    

                if entity_wkb4:
                    if wkb4_year is None:
                        wkb4_year = '⋆'
                 
                self.update_model_data(
                    wanted,
                    excluded,
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
                    lotw,
                    cq_zone,
                    continent,
                    message.get('grid'),
                    message_type,
                    message_color,
                    message.get('message_uid'),                  
                )   

                self.message_buffer.append(message)         

                if not self.process_timer:
                    self.process_timer = True
                    self.process_timer_timeout.start(10_000)
                    QtCore.QTimer.singleShot(300, lambda: self.process_message_buffer())            
        else:
            pass

    def apply_instance_settings(self, instance_settings):
        band = instance_settings.get('band')
        if band:
            """
                Check if need to play sound if
            """
            play_sound = False
            master_wanted_callsigns     = instance_settings.get('wanted_callsigns')
            master_wanted_cq_zones      = instance_settings.get('wanted_cq_zones')
            master_excluded_callsigns   = instance_settings.get('excluded_callsigns')
            master_excluded_cq_zones    = instance_settings.get('excluded_cq_zones')
            master_enable_sending_reply = instance_settings.get('enable_sending_reply')
            if(
                self.global_sound_toggle.isChecked() and
                (
                    has_significant_change(
                        self.wanted_callsigns_vars[band].text(),
                        ",".join(master_wanted_callsigns)
                    ) or
                    has_significant_change(
                        self.wanted_cq_zones_vars[band].text(),
                        ",".join(str(zone) for zone in master_wanted_cq_zones)
                    ) or
                    has_significant_change(
                        self.excluded_callsigns_vars[band].text(),
                        ",".join(master_excluded_callsigns)
                    ) or
                    has_significant_change(
                        self.excluded_cq_zones_vars[band].text(),
                        ",".join(str(zone) for zone in master_excluded_cq_zones)
                    )
                )
            ):                                    
                play_sound = True

            """
                Restore band and save wanted_callsigns_vars per band
            """
            self._synch_signal = False
            self.worker_signal_timer.stop()  # Stop any pending worker signal updates
            self.restore_settings()
            for amateur_band in AMATEUR_BANDS.keys():                
                self.before_synch_wanted_callsigns[amateur_band]    = self.wanted_callsigns_vars[amateur_band].text()   
                self.before_synch_wanted_cq_zones[amateur_band]     = self.wanted_cq_zones_vars[amateur_band].text()
                self.before_synch_excluded_callsigns[amateur_band]  = self.excluded_callsigns_vars[amateur_band].text()   
                self.before_synch_excluded_cq_zones[amateur_band]   = self.excluded_cq_zones_vars[amateur_band].text()   

            # To block signal 
            if not master_wanted_callsigns:
                self.wanted_callsigns_vars[band].clear()
            else:
                self.wanted_callsigns_vars[band].setText(", ".join(master_wanted_callsigns))

            if not master_wanted_cq_zones:
                self.wanted_cq_zones_vars[band].clear()
            else:  
                self.wanted_cq_zones_vars[band].setText(", ".join(str(zone) for zone in master_wanted_cq_zones))

            if not master_excluded_callsigns:
                self.excluded_callsigns_vars[band].clear()
            else:
                self.excluded_callsigns_vars[band].setText(", ".join(master_excluded_callsigns))

            if not master_excluded_cq_zones:
                self.excluded_cq_zones_vars[band].clear()
            else:  
                self.excluded_cq_zones_vars[band].setText(", ".join(str(zone) for zone in master_excluded_cq_zones))

            # Unblock signal
            self._synch_signal = True

            if master_enable_sending_reply is not None:
                self.enable_sending_reply = master_enable_sending_reply
                self.reply_toggle.setChecked(master_enable_sending_reply)

            # Update worker with new settings without triggering synch back to master
            if self.worker is not None:
                self.worker.update_listener_settings_signal.emit()

            if play_sound:
                self.play_sound("updated_settings")     

    def restore_settings(self):
        if self._instance == SLAVE:            
            frame = inspect.currentframe()
            try:
                caller = frame.f_back
                co_name = caller.f_code.co_name        
                log.warning(f"Restore settings: {co_name} from {caller}")
            finally:
                del frame
            
            for amateur_band in AMATEUR_BANDS.keys():                
                if self.before_synch_wanted_callsigns.get(amateur_band):
                    before_synch_wanted_callsigns_band = self.before_synch_wanted_callsigns[amateur_band]                    

                    if not before_synch_wanted_callsigns_band:
                        self.wanted_callsigns_vars[amateur_band].clear()
                    else:
                        self.wanted_callsigns_vars[amateur_band].setText(before_synch_wanted_callsigns_band)

                if self.before_synch_wanted_cq_zones.get(amateur_band): 
                    before_synch_wanted_cq_zones_band = self.before_synch_wanted_cq_zones[amateur_band]                    

                    if not before_synch_wanted_cq_zones_band:
                        self.wanted_cq_zones_vars[amateur_band].clear()
                    else:
                        self.wanted_cq_zones_vars[amateur_band].setText(before_synch_wanted_cq_zones_band)

                if self.before_synch_excluded_callsigns.get(amateur_band):
                    before_synch_excluded_callsigns_band = self.before_synch_excluded_callsigns[amateur_band]                    

                    if not before_synch_excluded_callsigns_band:
                        self.excluded_callsigns_vars[amateur_band].clear()
                    else:
                        self.excluded_callsigns_vars[amateur_band].setText(before_synch_excluded_callsigns_band)

                if self.before_synch_excluded_cq_zones.get(amateur_band): 
                    before_synch_excluded_cq_zones_band = self.before_synch_excluded_cq_zones[amateur_band]                    

                    if not before_synch_excluded_cq_zones_band:
                        self.excluded_cq_zones_vars[amateur_band].clear()
                    else:
                        self.excluded_cq_zones_vars[amateur_band].setText(before_synch_excluded_cq_zones_band)
        
    def process_message_buffer(self):     
        if self.enable_extra_gui_debug_output:
                log.info("Message buffer processing")
        if not self.message_buffer:
            if self.enable_extra_gui_debug_output:
                log.info("Message buffer is empty")
            return None
        else:
            """
                Get the latest message from last 5 seconds
            """
            max_decode_time = max(message['decode_time'] for message in self.message_buffer)            
            self.latest_messages = [
                message for message in self.message_buffer if message['decode_time'] >= (max_decode_time - timedelta(seconds=5))
            ]

            """
                For debug
            """
            if self.enable_extra_gui_debug_output:
                log_output = []
                for message in self.message_buffer:
                    callsign    = message.get('callsign') or "?"
                    priority    = message.get('priority') or 0
                    decode_time = message.get('decode_time') or "?"
                    log_output.append(f"process_message_buffer: [{priority}]{callsign:<13}@{decode_time}")
                log.info(f"\n\t".join(log_output))            

            """
                Select the latest message with the highest priority
            """
            selected_message = max(
                self.latest_messages,
                key=lambda message: message.get('priority', 0), default=None
            )

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
                if message_type == 'wanted_callsign_first_time_decoded' and self.enable_sound_wanted_callsigns:
                    play_sound = True 
                if message_type == 'wanted_callsign_decoded' and self.enable_sound_wanted_callsigns:
                    play_sound = True
                elif message_type == 'wanted_callsign_being_called' and self.enable_sound_wanted_callsigns:
                    play_sound = True                    
                elif message_type == 'directed_to_my_call' and self.enable_sound_directed_my_callsign:
                    if not selected_message.get('excluded'):
                        play_sound = True
                elif message_type == 'ready_to_log' and self.enable_sound_directed_my_callsign:
                    play_sound = True
                elif message_type == 'error_occurred':
                    play_sound = True
                elif (
                    message_type == 'monitored_callsign_decoded' 
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

            if message_type and message_type not in ['lost_targeted_callsign', 'callsign_excluded']:
                self.set_message_to_focus_value_label(selected_message)

        """
            Update map with new grid squares
        """
        self.update_grid_monitor_with_grids(self.latest_messages)
        
        """
            Clear buffer
        """
        if selected_message:
            selected_time = selected_message['decode_time']
            filtered_messages = []
            
            for message in self.message_buffer:
                message_time = message['decode_time']
                time_diff = abs((message_time - selected_time).total_seconds())

                if time_diff > 43200:
                    if message_time > selected_time:
                        alt_time_diff = abs((message_time - timedelta(days=1) - selected_time).total_seconds())
                    else:
                        alt_time_diff = abs((message_time + timedelta(days=1) - selected_time).total_seconds())
                    
                    time_diff = min(time_diff, alt_time_diff)
                
                if time_diff <= 120:
                    filtered_messages.append(message)
            
            self.message_buffer = deque(filtered_messages)  

        """
            Reset timer
        """
        self.process_timer = False
        self.process_timer_timeout.stop()  # Stop timeout timer when processing completes
        self.update_activity_bar()  

    def on_table_row_clicked(self, table, row, column):
        position = table.visualRect(table.model().index(row, column)).center()
        self.on_table_context_menu(table, position)        

    def on_table_context_menu(self, table, position):
        """
            Handle context menu for tables using ContextMenuHandler
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

        self.context_menu_handler.show_context_menu(table, position, data, "table")

    def open_qrz_com(self, callsign):
        if callsign:
            qrz_url = f"https://www.qrz.com/db/{callsign}"
            webbrowser.open(qrz_url)
        else:
            log.warning("No callsign provided to open QRZ.com")

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

        self.message_buffer = deque(maxlen=500)

    def add_callsign_to_exclusion_list(self, callsign, exclusion_minutes = 10):
        if not self.gui_selected_band:
            return

        if self.gui_selected_band not in self.temp_excluded_callsigns:
            self.temp_excluded_callsigns[self.gui_selected_band] = {}

        current_time = datetime.now()
        expiration_time = current_time + timedelta(minutes=exclusion_minutes)
        self.temp_excluded_callsigns[self.gui_selected_band][callsign.upper()] = expiration_time

        # Also add to the permanent excluded list
        self.update_var(self.excluded_callsigns_vars[self.gui_selected_band], callsign, "add")

        # Save to file
        self.save_temp_excluded_callsigns()

    def cleanup_expired_exclusions(self):
        current_time = datetime.now()
        changes_made = False
        
        for band in list(self.temp_excluded_callsigns.keys()):
            callsigns_to_remove = []
            
            for callsign, expiration_time in self.temp_excluded_callsigns[band].items():
                if current_time >= expiration_time:
                    callsigns_to_remove.append(callsign)
            
            # Remove expired callsigns from both temp and permanent exclusion lists
            for callsign in callsigns_to_remove:
                del self.temp_excluded_callsigns[band][callsign]
                if band in self.excluded_callsigns_vars:
                    self.update_var(self.excluded_callsigns_vars[band], callsign, "remove")
                changes_made = True
            
            # Clean up empty band dictionaries
            if not self.temp_excluded_callsigns[band]:
                del self.temp_excluded_callsigns[band]
        
        # Save to file if any changes were made
        if changes_made:
            self.save_temp_excluded_callsigns()

    def show_exclusion_time_dialog(self, callsign):
        dialog = ExclusionDialog(callsign, self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            selected_minutes = dialog.get_selected_minutes()
            self.add_callsign_to_exclusion_list(callsign, selected_minutes)

    def update_window_title(self):     
            window_title = GUI_LABEL_VERSION
            if self.my_wsjtx_id:
                window_title = f"{self.my_wsjtx_id} ➞ {GUI_LABEL_VERSION}"
            if self.my_call and self.frequency:
                window_title += f" ➞ {self.my_call} on {get_amateur_band(self.frequency)}"                
            if self.my_grid:
                sunrise, sunset = calculate_sunrise_sunset(self.my_grid)
                if sunrise and sunset:
                    window_title += f" [ {self.my_grid} - SR {sunrise}z SS {sunset}z ]"
                else:
                    window_title += f" [ {self.my_grid} ]"
            if self._instance and self._instance == SLAVE:
                window_title+= f" - Running as {self._instance}"

            if self.window_title != window_title:                 
                self.setWindowTitle(window_title)
                self.window_title = window_title

            if hasattr(self, 'grid_monitor') and self.grid_monitor:
                self.grid_monitor.update_window_title(f"{window_title} ➞ Grid Monitoring")

    def reset_window_title(self):
        self.window_title = None
        self.update_window_title()

    def init_activity_bar(self):
        self.activity_bar.setValue(ACTIVITY_BAR_MAX_VALUE)

    def update_activity_bar(self):
        time_delta_in_seconds = get_mode_interval(self.mode)
        """
            We need to double time_delta_to_be_used the time transmitting == 1 
            otherwise we are loosing accuracy of activity bar
        """
        if not self.transmitting:
            cutoff_time = datetime.now() - timedelta(seconds=time_delta_in_seconds)
            while self.message_times and self.message_times[0] < cutoff_time:
                self.message_times.popleft()

        self.activity_bar.setValue(len(self.message_times))                                     

    def start_blinking_status_button(self):
        if self.is_status_button_label_blinking is False:
            self.is_status_button_label_blinking = True
            self.blink_timer.start(500)

    def stop_blinking_status_button(self):    
        if self.is_status_button_label_blinking is True:
            self.is_status_button_label_blinking = False
            self.blink_timer.stop()            
            effect = QGraphicsOpacityEffect(self.status_button)
            effect.setOpacity(1)
            self.status_button.setGraphicsEffect(effect)
            self.is_status_button_label_visible = True

    @QtCore.pyqtSlot()
    def toggle_label_visibility(self):
        if self.is_status_button_label_visible:
            effect = QGraphicsOpacityEffect(self.status_button)
            effect.setOpacity(0)
            self.status_button.setGraphicsEffect(effect)
            self.is_status_button_label_visible = False
        else:
            effect = QGraphicsOpacityEffect(self.status_button)
            effect.setOpacity(1)
            self.status_button.setGraphicsEffect(effect)
            self.is_status_button_label_visible = True

    def update_status_bar_style(self, background_color, text_color):
        style = f"""
            QStatusBar::item {{
                border: none;
            }}           
            QStatusBar {{
                background-color: {background_color};                
                border: none;
            }}
            QStatusBar QLabel {{
                color: {text_color};
            }}
        """

        self.status_bar.setStyleSheet(style)
        
        if self.grid_monitor:
            self.grid_monitor.update_status_bar_color(style)

    def start_processing_animation(self):
        if not self.processing_active:
            self.processing_active = True
            self.processing_spinner_index = 0
            text = "Logbook Analysis: Starting..."
            self.status_bar_label_mode.setText(text)

            if self.grid_monitor:
                self.grid_monitor.status_bar_label_processing.setText(text)
    
    def stop_processing_animation(self):
        if self.processing_active:
            self.processing_active = False
            self.check_connection_status()

            if self.grid_monitor:
                self.grid_monitor.status_bar_label_processing.clear()

    def update_processing_progress(self, processed, total, file_path=""):
        if total > 0 and self.processing_active and file_path:
            filename = os.path.basename(file_path)

            # text_processing_progress = f"Logbook Analysis [ <i>{filename}</i> ]: {processed:,}/{total:,}"  
            percentage = (processed / total * 100) if total > 0 else 0
            text_processing_progress = f"Parsing <u>{filename}</u>: {percentage:.1f}%"  
            self.status_bar_label_mode.setText(text_processing_progress)
            if self.grid_monitor:
                self.grid_monitor.status_bar_label_processing.setText(text_processing_progress)

    def set_notice_to_focus_value_label(
            self,
            notice_message,
            fg_color_hex=FG_COLOR_BLACK_ON_WHITE,
            bg_color_hex=STATUS_TRX_COLOR
        ):           
        self.message_buffer = deque(maxlen=500)                 
        self.update_status_menu_message(notice_message, bg_color_hex, fg_color_hex)
        self.output_table.scrollToBottom()
        self.last_focus_value_message_uid = None

    def set_message_to_focus_value_label(self, message):  
        contains_my_call = message.get('directed') == message.get('my_call') and message.get('directed') is not None
        contains_alert   = message.get('type') == 'gui_alert'
        
        if contains_alert:
            bg_color_hex = FG_COLOR_FOCUS_MY_CALL
            fg_color_hex = FG_COLOR_BLACK_ON_WHITE
        elif contains_my_call:
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

        formatted_message = message.get('formatted_message').strip()
        priority_type     = message.get('priority_type', None)
        if priority_type:
            focus_message = None 
            if priority_type == 'wanted':
                if message.get('exactly_matched', None):
                    focus_message = "Wanted"
                else:
                    focus_message = "Wildcard"
            elif priority_type == 'wanted_grid':
                focus_message = "Grid"
            elif priority_type == 'marathon':
                focus_message = "Marathon"  
            elif priority_type == 'polite_reply':
                focus_message = "Politeness"  
            elif priority_type == 'wanted_cq_zone':
                focus_message = "Zone"

            if focus_message:    
                formatted_message+= f" / {focus_message.upper()}"
            
        self.focus_value_label.setText(formatted_message)

        self.update_status_menu_message(message.get('message', ''), bg_color_hex, fg_color_hex)

    @QtCore.pyqtSlot(object)
    def play_sound(self, sound_name):
        try:
            if sound_name in self.sound_files:
                log.debug(f"Queued sound: [{sound_name}]")
                self.sound_queue.put(sound_name)
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
            sound_name = self.sound_queue.get()
            
            # Recreate audio output to handle device changes on macOS
            if sys.platform == 'darwin':
                self.audio_output = QAudioOutput()
                self.media_player.setAudioOutput(self.audio_output)
            
            # Set source and play
            sound_file = self.sound_files[sound_name]
            self.media_player.setSource(QtCore.QUrl.fromLocalFile(sound_file))
            self.media_player.play()
            
            # Use fixed duration since QMediaPlayer duration isn't immediately available
            self.sound_timer.start(1000)
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
            if self._instance in (MASTER, None) and status == SLAVE:                
                self.before_synch_wanted_callsigns = {}
                self._synched_addr_port = addr_port 

            if self._instance == SLAVE and status == MASTER:
                self.restore_settings()
                self._synched_addr_port = None             

        self._instance          = status           
        self.update_tab_widget_labels_style()  
        self.update_window_title()          

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

        if not self.processing_active:
            if frequency is not None:
                operating_band = get_amateur_band(frequency)     
                if operating_band != 'Invalid' and self.operating_band != operating_band:
                    self.apply_band_change(operating_band)
            
            if self.mode is not None:
                current_mode = f"Mode: {self.mode}"
                self.status_bar_label_mode.setText(current_mode)
            else:
                self.status_bar_label_mode.setText(MainWindowStrings.WAITING_DATA_PACKETS())    

        if self.last_heartbeat_time:
            time_since_last_heartbeat = (current_time - self.last_heartbeat_time).total_seconds()
            if time_since_last_heartbeat > HEARTBEAT_TIMEOUT_THRESHOLD:
                heartbeat_str = MainWindowStrings.NO_HEARTBEAT_TIMEOUT(HEARTBEAT_TIMEOUT_THRESHOLD)
                connection_lost = True
            else:
                # Format with timezone-aware display
                formatted_time = self.last_heartbeat_time.astimezone().strftime('<u>%H:%M:%S</u>')
                heartbeat_str = MainWindowStrings.HEARTBEAT_TIME(formatted_time)
        else:
            heartbeat_str = MainWindowStrings.NO_HEARTBEAT_RECEIVED()

        self.status_bar_label_heartbeat.setText(heartbeat_str)

        if (
            self._instance and
            self._running and 
            not connection_lost and
            self._synched_addr_port is not None
        ):
            connection_str = f"{self._instance} ~ "
            connection_str+= MASTER if self._instance == SLAVE else SLAVE
            connection_str+= f" ({self._synched_addr_port[0]})"

            self.status_bar_label_connection.setText(connection_str)
        else:
            self.status_bar_label_connection.clear()

        if not self.processing_active:
            self.status_bar_label_packet.setText(MainWindowStrings.BUFFERED_PACKETS(
                self.output_model.rowCount(),
                self.get_size_of_output_model()
            ))

        if self.last_frequency and not self.processing_active:
            self.status_bar_label_freq.setText(f"Freq: <u>{display_frequency(self.last_frequency)}</u>")

        if self.last_targeted_call:
            # self.status_bar_label_reply.setText(f"Last reply: {self.last_targeted_call}")
            pass

        if self.last_decode_packet_time:
            time_since_last_decode = (current_time - self.last_decode_packet_time).total_seconds()
            network_check_status_interval = 5_000

            if time_since_last_decode > DECODE_PACKET_TIMEOUT_THRESHOLD:

                minutes_elapsed = time_since_last_decode / 60
                nothing_to_decode = True
                if minutes_elapsed > 90:
                    hours_elapsed = minutes_elapsed / 60
                    time_since_last_decode_text = f"{round(hours_elapsed)} hour{'s' if round(hours_elapsed) != 1 else ''}"
                else:
                    time_since_last_decode_text = f"{round(minutes_elapsed)} minutes"                
            else:      
                if time_since_last_decode < 3:
                    network_check_status_interval = 500
                    time_since_last_decode_text = f"{time_since_last_decode:.1f}s" 
                    self.update_status_button(MainWindowStrings.STATUS_DECODING(), STATUS_DECODING_COLOR)                                  
                else:
                    if time_since_last_decode < 15:
                        network_check_status_interval = 1_000
                    time_since_last_decode_text = f"{int(time_since_last_decode)}s"                  
                    self.update_status_button(MainWindowStrings.STATUS_MONITORING(), STATUS_MONITORING_COLOR) 

            self.status_bar_label_decode_packet.setText(f"Last decoded: {time_since_last_decode_text} ago")

            # Update new interval if necessary
            if network_check_status_interval != self.network_check_status_interval:
                self.network_check_status_interval = network_check_status_interval
                self.network_check_status.setInterval(self.network_check_status_interval)                               
        else:
            self.status_bar_label_decode_packet.setText(MainWindowStrings.WAITING_DATA_PACKETS())
        
        if connection_lost:            
            self.reset_window_title()
            self.update_status_bar_style("red", "white")
            if self._connected:
                if self.global_sound_toggle.isChecked():      
                    self.play_sound("error_occurred")
                self.on_lost_connection()
                self.update_tab_widget_labels_style()
        elif nothing_to_decode: 
            self.update_status_bar_style("white", "black")
        else:
            if not self._connected:  
                self.on_resume_connection()
            if self._instance == SLAVE:
                self.update_status_bar_style(BG_COLOR_WHITE_ON_BLUE_VIOLET, FG_COLOR_WHITE_ON_BLUE_VIOLET)
            else:
                if not self.last_decode_packet_time:
                    self.update_status_bar_style(BG_COLOR_BLACK_ON_YELLOW, "black")
                else:
                    self.update_status_bar_style(STATUS_MONITORING_COLOR, "white")                

        """
            Handle grid monitor status
        """
        if self.grid_monitor:
            self.grid_monitor.status_bar_label_last_decoded.setText(self.status_bar_label_decode_packet.text())

        """
            Handle change for status_button when transmitting
        """
        if self.transmitting and not connection_lost:            
            self.update_status_button(MainWindowStrings.STATUS_TRX(), STATUS_TRX_COLOR)
            self.last_transmit_time = datetime.now(timezone.utc)
            self.start_blinking_status_button()
            network_check_status_interval = 100            
        elif self.last_transmit_time:
            if self._running:
                self.update_status_button(MainWindowStrings.STATUS_MONITORING(), STATUS_MONITORING_COLOR) 
            self.last_transmit_time = None
            self.stop_blinking_status_button()   

    def on_lost_connection(self):
        log.warning("Lost connection")
        
        self._connected = False

        self.check_connection_status()
        
        self.stop_blinking_status_button()  
        self.activity_bar_timer.stop()
        self.blink_timer.stop()
        self.enforce_size_limit_timer.stop()

        if sys.platform == 'darwin':
            self.pobjc_timer.stop() 

        self.worker.reset_settings_signal.emit()
                    
    def on_resume_connection(self):
        log.warning("Resume connection")
        self._connected = True    
        self.activity_bar_timer.start(100)
        self.enforce_size_limit_timer.start(60_000) 
        if sys.platform == 'darwin':
            self.pobjc_timer.start(10) 
            
    def on_close(self, event):
        self.save_window_position()
        if self.grid_monitor:
            self.grid_monitor.close()
        if self.active_users_window:
            self.active_users_window.close()
        if self._running:
            self.stop_monitoring()
        event.accept()

    def show_active_users(self):
        try:
            if not hasattr(self, 'worker') or self.worker is None:
                log.error("Worker not initialized")
                return

            if not hasattr(self.worker, 'listener') or self.worker.listener is None:
                log.error("Listener not initialized")                
                return

            if not hasattr(self.worker.listener, 'telemetry_service') or self.worker.listener.telemetry_service is None:
                log.error("Telemetry service not initialized")                
                return

            if not hasattr(self, 'active_users_window') or self.active_users_window is None:
                log.info("Creating active users window")
                self.active_users_window = ActiveUsersWindow(
                    self.worker.listener.telemetry_service,
                    self.dark_mode,
                    self
                )

            self.active_users_window.show()
            self.active_users_window.raise_()
            self.active_users_window.activateWindow()
        except Exception as e:
            log.error(f"Error showing active users window: {e}")
            import traceback
            log.error(traceback.format_exc())            

    def open_settings(self):
        log.warning("Settings opened")

        self.last_targeted_call = None
        self.hide_focus_value_label(visible=False)

        dialog = SettingsDialog(self, self.local_params, self.dark_mode)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            new_params = dialog.get_result()
        
            previous_enable_pounce_log              = self.enable_pounce_log
            self.enable_pounce_log                  = new_params.get('enable_pounce_log', True)
            self.enable_extra_gui_debug_output      = new_params.get('enable_extra_gui_debug_output', False)

            self.local_params.update(new_params)
            self.save_params()

            self.enable_sound_wanted_callsigns      = self.local_params.get('enable_sound_wanted_callsigns', True)
            self.enable_sound_directed_my_callsign  = self.local_params.get('enable_sound_directed_my_callsign', True)
            self.enable_sound_monitored_callsigns   = self.local_params.get('enable_sound_monitored_callsigns', True)

            self.adif_file_path                     = self.local_params.get('adif_file_path', None)
            self.worked_before_preference           = convert_wkb4_reply_mode(self.local_params.get('worked_before_preference', WKB4_REPLY_MODE_ALWAYS))

            self.toggle_wkb4_column_visibility()

            if self.enable_pounce_log and not previous_enable_pounce_log:
                self.file_handler = add_timed_file_handler()
            elif not self.enable_pounce_log and previous_enable_pounce_log:
                remove_file_handler(self.file_handler)
                self.file_handler = None

            if self._running:
                self.refresh_monitoring()

    def quit_application(self):
        self.save_window_position()
        
        log.debug(f"Quit {GUI_LABEL_NAME}")
        
        # Set flag to indicate app is shutting down
        self.app_shutting_down = True
        
        # Close grid monitor without triggering toggle
        if self.grid_monitor:
            self.grid_monitor.close()
        
        QtWidgets.QApplication.quit()

    def change_language(self, language_code):
        """Change application language"""
        # Save language preference
        self.save_unique_param('language', language_code)

        # Load the new translation
        self.translation_manager.load_translation(language_code)

        # Show restart notification
        self.show_language_changed_dialog()

    def restart_application(self):
        if self._running:
                self.stop_monitoring()

        self.save_band_settings()
        self.save_worked_callsigns()

        log.debug(f"Restart {GUI_LABEL_NAME}")

        # Set flag to indicate app is shutting down
        self.app_shutting_down = True

        # Close grid monitor without triggering toggle
        if self.grid_monitor:
            self.grid_monitor.close()

        QtCore.QProcess.startDetached(sys.executable, sys.argv)
        QtWidgets.QApplication.quit()
        
    def apply_palette(self, dark_mode):
        self.dark_mode = dark_mode

        # Force macOS title bar appearance to match theme
        set_macos_window_appearance(self, dark_mode)

        if dark_mode:
            qt_bg_color = "#181818"
        else:
            qt_bg_color = "#E0E0E0"

        # Set global application palette
        app_palette = QtGui.QPalette()
        if dark_mode:
            app_palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#323232"))
            app_palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor("#FFFFFF"))
            app_palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(qt_bg_color))
            app_palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor("#353535"))
            app_palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtGui.QColor("#353535"))
            app_palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtGui.QColor("#FFFFFF"))
            app_palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor("#FFFFFF"))
            app_palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor("#353535"))
            app_palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor("#FFFFFF"))
            app_palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtGui.QColor("#FF0000"))
            app_palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor("#42A5F5"))
            app_palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor("#42A5F5"))
            app_palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor("#000000"))
            app_palette.setColor(QtGui.QPalette.ColorRole.Mid, QtGui.QColor(qt_bg_color))
        else:
            app_palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor("#F0F0F0"))
            app_palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor("#000000"))
            app_palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("#FFFFFF"))
            app_palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor("#F4F5F5"))
            app_palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtGui.QColor("#FFFFDC"))
            app_palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtGui.QColor("#000000"))
            app_palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor("#000000"))
            app_palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor("#F0F0F0"))
            app_palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor("#000000"))
            app_palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtGui.QColor("#FF0000"))
            app_palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor("#0000FF"))
            app_palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor("#308CC6"))
            app_palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor("#FFFFFF"))
            app_palette.setColor(QtGui.QPalette.ColorRole.Mid, QtGui.QColor("#B0B0B0"))

        QtWidgets.QApplication.instance().setPalette(app_palette)

        self.worked_history_widget.setStyleSheet(f"""
            #worked_history_widget {{
                border-left: 1px solid palette(Mid);
            }}
        """)

        self.filter_widget.setStyleSheet(f"""
            QWidget#FilterWidget {{
                background-color: {qt_bg_color};
                border-radius: 8px;
            }}
        """)

        # Set table colors directly in variables for easier control
        if dark_mode:        
            self.activity_bar.setColors("#3D3D3D", "#FFFFFF", "#101010")
        else:            
            self.activity_bar.setColors("#FFFFFF", "#000000", "#C6C6C6")

        self.output_table.setStyleSheet(get_main_table_qss(dark_mode))
        self.output_table.setShowGrid(False)
        self.wait_pounce_history_table.setStyleSheet(get_main_table_qss(dark_mode))
        self.wait_pounce_history_table.setShowGrid(False)

        # Update active users window theme if it exists
        if hasattr(self, 'active_users_window') and self.active_users_window is not None:
            self.active_users_window.apply_palette(dark_mode)

        # Update CustomQLabel instances with palette colors
        text_color = "#FFFFFF" if dark_mode else "#000000"
        custom_labels = [
            self.reply_label,
            self.all_label,
            self.filters_label,
            self.map_label,
            self.alternate_compact_view_label
        ]
        for label in custom_labels:
            if label:
                label.setStyleSheet(f"""
                    QLabel {{
                        font: {CUSTOM_FONT.pointSize()}pt '{CUSTOM_FONT.family()}';
                        color: {text_color};
                    }}
                """)

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
        self.local_params[key] = value
        self.save_params()

    def _prepare_params_for_json(self):
        """
            Convert any non-JSON serializable objects to JSON-compatible format
        """
        json_params = {}
        for key, value in self.local_params.items():
            try:
                json.dumps(value)
                json_params[key] = value
            except (TypeError, ValueError):
                if hasattr(value, '__dict__'):
                    json_params[key] = str(value)
                else:
                    json_params[key] = str(value)
                log.warning(f"Parameter '{key}' converted to string for JSON serialization")
        return json_params

    def save_params(self, updated_params=None):
        try:
            json_params = self._prepare_params_for_json()
            if updated_params:
                json_params.update(updated_params)
            with open(PARAMS_FILE, "w", encoding='utf-8') as f:
                json.dump(json_params, f, indent=2, ensure_ascii=False)
            log.info(f"Parameters saved to {PARAMS_FILE}")
        except Exception as e:
            log.error(f"Error saving parameters to JSON: {e}")
            # Fallback to pickle format
            try:
                with open(PARAMS_FILE_LEGACY, "wb") as f:
                    pickle.dump(self.local_params, f)
                log.warning(f"Parameters saved to legacy format {PARAMS_FILE_LEGACY}")
            except Exception as pickle_error:
                log.error(f"Error saving parameters to pickle: {pickle_error}")
                raise

    def load_params(self):
        # Try to load JSON format first (new format)
        if os.path.exists(PARAMS_FILE):
            try:
                with open(PARAMS_FILE, "r", encoding='utf-8') as f:
                    params = json.load(f)
                log.info(f"Parameters loaded from {PARAMS_FILE}")
                return params
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                log.error(f"Error loading JSON parameters from {PARAMS_FILE}: {e}")
                # Try to delete corrupted JSON file
                try:
                    os.remove(PARAMS_FILE)
                    log.warning(f"Corrupted JSON file {PARAMS_FILE} deleted")
                except OSError:
                    pass
        
        # Fallback to legacy pickle format for backward compatibility
        if os.path.exists(PARAMS_FILE_LEGACY):
            try:
                with open(PARAMS_FILE_LEGACY, "rb") as f:
                    params = pickle.load(f)
                log.info(f"Parameters loaded from legacy format {PARAMS_FILE_LEGACY}")
                
                # Migrate to JSON format and save
                try:
                    self.save_params()
                    log.info(f"Parameters migrated from legacy format to JSON")
                    # Optionally remove legacy file after successful migration
                    # os.remove(PARAMS_FILE_LEGACY)
                except Exception as e:
                    log.warning(f"Could not migrate parameters to JSON format: {e}")
                
                return params
            except (EOFError, pickle.UnpicklingError) as e:
                log.error(f"Error loading legacy parameters from {PARAMS_FILE_LEGACY}: {e}")
                try:
                    os.remove(PARAMS_FILE_LEGACY)
                    log.warning(f"Corrupted legacy file {PARAMS_FILE_LEGACY} deleted")
                except OSError:
                    pass
        
        log.info("No valid configuration file found, using default parameters")
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

    def save_temp_excluded_callsigns(self):
        try:
            with open(TEMP_EXCLUDED_CALLSIGNS_FILE, "wb") as f:
                pickle.dump(self.temp_excluded_callsigns, f)
        except Exception as e:
            log.error(f"Error saving temporary excluded callsigns: {e}")

    def load_temp_excluded_callsigns(self):
        if os.path.exists(TEMP_EXCLUDED_CALLSIGNS_FILE):
            try:
                if os.path.getsize(TEMP_EXCLUDED_CALLSIGNS_FILE) > 0:
                    with open(TEMP_EXCLUDED_CALLSIGNS_FILE, "rb") as f:
                        self.temp_excluded_callsigns = pickle.load(f)
                else:
                    self.temp_excluded_callsigns = {}
            except (EOFError, pickle.UnpicklingError) as e:
                log.error(f"Error loading temporary excluded callsigns: {e}")
                self.temp_excluded_callsigns = {}
        else:
            self.temp_excluded_callsigns = {}

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
        counter_text = MainWindowStrings.WORKED_CALLSIGNS_LABEL()
        counter_text+= f" ({len(self.worked_callsigns_history)}):"
        
        self.worked_callsign_label.setText(counter_text)
        header_item = self.wait_pounce_history_table.horizontalHeaderItem(1)
        if header_item and len(self.worked_callsigns_history) > 4:            
            header_item.setText(counter_text)

    def on_focus_value_label_clicked(self, event= None):
        message = self.focus_value_label.text()

        if message:
            self.blinking_grid()
            self.scroll_to_message_uid(self.last_focus_value_message_uid)
            self.copy_message_to_clipboard(message)

    def copy_message_to_clipboard(self, message):
        pyperclip.copy(message)
        log.warning(f"Copied to clipboard: {message}")

    def update_model_data(
            self,
            wanted,
            excluded,
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
            lotw,
            cq_zone,
            continent,
            grid,
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
            "message_uid"       : message_uid,            
            "message"           : message,
            "formatted_message" : formatted_message,
            "entity"            : entity,
            "lotw"              : lotw,            
            "cq_zone"           : cq_zone,
            "continent"         : continent,
            "grid"              : grid,
            "row_datetime"      : datetime.now(timezone.utc),
            "row_color"         : row_color,
            "message_type"      : message_type,
            "excluded"          : excluded
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

    def scroll_to_message_uid(self, uid):
        # Bring main window to forefront
        self.show()
        self.raise_()
        self.activateWindow()
        
        row = self.output_model.findRowByUid(uid)
        if row == -1:
            log.warning(f"Nothing found for this message_uid: {uid}")
            return  

        source_index = self.output_model.index(row, 0)
        if not source_index.isValid():
            return
        
        proxy_index = self.filter_proxy_model.mapFromSource(source_index)

        self.output_table.scrollTo(proxy_index, QtWidgets.QAbstractItemView.ScrollHint.PositionAtBottom)        
        self.output_table.setCurrentIndex(proxy_index)
        
        if self.grid_monitor and self.grid_monitor.isVisible():
            self.grid_monitor.show()
            self.grid_monitor.raise_()
            self.grid_monitor.activateWindow()

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
            self.save_worked_callsigns()  

        self.wait_pounce_history_table.scrollToBottom()    

    def apply_filters(self):
        callsign_filter   = self.callsign_input.text().strip().upper()
        country_filter    = self.country_input.text().strip().upper()
        continent_filter  = self.continent_combo.currentText()
        selected_color   = self.color_combo.currentData()
        selected_band    = self.band_combo.currentText()
        cq_filter         = self.cq_combo.currentText()

        # Get translated "All" for comparison
        translated_all = MainWindowStrings.FILTER_ALL()

        filters_map = [
            ('callsign',   callsign_filter,  ""),
            ('country',    country_filter,   ""),
            ('cq_zone',    cq_filter,        DEFAULT_FILTER_VALUE, translated_all),
            ('continent',  continent_filter, DEFAULT_FILTER_VALUE, translated_all),
            ('row_color',  selected_color,  None, None),
            ('band',       selected_band,   DEFAULT_FILTER_VALUE, translated_all),
        ]

        show_all_messages = False

        for filter_data in filters_map:
            key = filter_data[0]
            user_value = filter_data[1]
            default_value = filter_data[2]
            translated_default = filter_data[3] if len(filter_data) > 3 else None

            # Check both the identifier value AND translated display text
            if user_value and user_value != default_value and user_value != translated_default:
                self.filter_proxy_model.setFilter(key, user_value)
                show_all_messages = True
            else:
                self.filter_proxy_model.setFilter(key, default_value)
                self.output_table.scrollToBottom() 

        if show_all_messages:
            self.filter_proxy_model.showAllData()
            self.output_table.scrollToBottom() 

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

        self.apply_filters

        self.output_table.scrollToBottom()

    def on_country_column_resized(self, logical_index, old_size, new_size):
        if logical_index == 7:  # Country column
            self.save_window_position()

    def save_window_position(self):
        try:
            if self.enable_compact_view:
                if self.window_size:
                    width   = self.window_size.width()
                    height  = self.window_size.height()
                else:
                    width   = max(self.geometry().width(), 900)  
                    height  = max(self.geometry().height(), 700)
            else:
                width       = self.geometry().width()
                height      = self.geometry().height()
                
            position_data = {
                'x'                     : self.geometry().x(),
                'y'                     : self.geometry().y(),
                'width'                 : width,
                'height'                : height,
                'country_column_width'  : self.output_table.columnWidth(7)
            }

            position_data['grid_map_window'] = self.grid_monitor_geometry

            with open(POSITION_FILE, "wb") as f:
                pickle.dump(position_data, f)
                f.flush() 
                os.fsync(f.fileno()) 
        except Exception as e:
            self.log.error(f"Failed to save window position: {e}")

    def load_window_position(self):
        if os.path.exists(POSITION_FILE):
            with open(POSITION_FILE, "rb") as f:
                position_data = pickle.load(f)

                if (
                    'width' in position_data and 
                    'height' in position_data
                ):
                    self.setGeometry(
                        position_data['x'],
                        position_data['y'],
                        position_data['width'],
                        position_data['height']
                    )                                      
                else:
                    self.setGeometry(100, 100, 900, 700) 
                    os.remove(POSITION_FILE)

                self.grid_monitor_geometry = position_data.get('grid_map_window')

                # Restore country column width if saved
                country_column_width = position_data.get('country_column_width')
                if country_column_width:
                    self.output_table.setColumnWidth(7, country_column_width)

                QtCore.QTimer.singleShot(100, lambda: self.toggle_grid_monitor(self.enable_grid_monitor))
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

    def reset_process_timer(self):
        self.process_timer = False
        log.warning("Process timer reset due to timeout - processing may have been stuck")

    def update_status_button(
            self,        
            text = "",
            bg_color = "black",
            fg_color = "white",
        ):
            if (
                self.status_button.current_text     != text     or
                self.status_button.current_bg_color != bg_color or
                self.status_button.current_fg_color != fg_color
            ):      
                self.status_button.updateStyle(text, bg_color, fg_color)

    def update_tab_widget_labels_style(self):
        styles = [
            (BG_COLOR_BLACK_ON_YELLOW, FG_COLOR_BLACK_ON_YELLOW), # wanted    callsigns
            (BG_COLOR_BLACK_ON_PURPLE, FG_COLOR_BLACK_ON_PURPLE), # monitored callsigns
            (BG_COLOR_BLACK_ON_SAUMON, FG_COLOR_BLACK_ON_YELLOW), # wanted    CQ zones
            (BG_COLOR_BLACK_ON_CYAN, FG_COLOR_BLACK_ON_CYAN),     # monitored CQ zones
            ("transparent", "palette(text)"),                     # excluded  callsigns
            ("transparent", "palette(text)")                      # excluded  CQ zones
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

        for amateur_band in AMATEUR_BANDS.keys():
            content_widget = self.tab_widget.get_content_widget(amateur_band)
            layout = content_widget.layout()

            for idx, (bg_color, fg_color) in enumerate(styles, start=1):
                label_widget = layout.itemAtPosition(idx, 0).widget()
                input_widget = layout.itemAtPosition(idx, 1).widget()

                if amateur_band == self.operating_band and self._running:
                    label_widget.setStyleSheet(active_style_template.format(bg_color=bg_color, fg_color=fg_color))
                    if self._instance == SLAVE and (
                        idx == 1 or idx == 3 or idx == 5 or idx == 6
                    ):
                        input_widget.setEnabled(False)
                        input_widget.setStyleSheet(slave_style)
                    else:
                        input_widget.setEnabled(True)
                        input_widget.setStyleSheet("")
                else:
                    label_widget.setStyleSheet(default_style)
                    if idx == 1 or idx == 3 or idx == 5 or idx == 6:
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
            restart_action = QtGui.QAction(MainWindowStrings.RESTART_ACTION(), self)
            restart_action.setShortcut(QtGui.QKeySequence("Ctrl+R"))
            restart_action.triggered.connect(self.restart_application)
            main_menu.addAction(restart_action)

        main_menu.addSeparator()

        enable_sound_action = QtGui.QAction(MainWindowStrings.FILE_MENU(), self)  # Placeholder - needs proper string
        enable_sound_action.setShortcut(QtGui.QKeySequence("Ctrl+S"))
        enable_sound_action.triggered.connect(self.update_global_sound_preference)
        enable_sound_action.setCheckable(True)
        enable_sound_action.setChecked(self.enable_global_sound)
        main_menu.addAction(enable_sound_action)

        settings_action = QtGui.QAction(CommonStrings.SETTINGS() + "...", self)
        settings_action.setShortcut("Ctrl+,")  # Default shortcut for macOS
        settings_action.triggered.connect(self.open_settings)
        main_menu.addAction(settings_action)

        check_update_action = QtGui.QAction("Check for Updates...", self)  # No translation needed - technical term
        check_update_action.setShortcut("Ctrl+I")  
        check_update_action.triggered.connect(lambda: self.updater.check_expiration_or_update(True))
        main_menu.addAction(check_update_action)
        
        main_menu.addSeparator()
        donate_action = QtGui.QAction(f"⭐️ Support {GUI_LABEL_NAME}", self)
        donate_action.triggered.connect(lambda: webbrowser.open(DONATION_URL))
        main_menu.addAction(donate_action)

        # Add Online menu
        self.online_menu = self.menu_bar.addMenu(MainWindowStrings.TOOLS_MENU())

        load_clublog_action = QtGui.QAction("Update DXCC Info", self)  # Technical term - no translation
        load_clublog_action.triggered.connect(self.clublog_manager.load_clublog_info)

        load_lotw_action = QtGui.QAction("Update LoTW Info", self)  # Technical term - no translation
        load_lotw_action.triggered.connect(self.lotw_manager.load_lotw_info)

        load_country_file_action = QtGui.QAction("Update Country Files Info", self)  # Technical term - no translation
        load_country_file_action.triggered.connect(self.country_files_manager.load_country_file)
        
        self.online_menu.addAction(load_clublog_action)
        self.online_menu.addAction(load_lotw_action)
        self.online_menu.addAction(load_country_file_action)
        self.online_menu.addSeparator()

        show_active_users_action = QtGui.QAction("List of active users", self)
        show_active_users_action.triggered.connect(self.show_active_users)
        show_active_users_action.setShortcut(QtGui.QKeySequence("Ctrl+L"))
        self.addAction(show_active_users_action)  # Shortcut only, not in menu

        # Add Language menu
        self.language_menu = self.menu_bar.addMenu(MainWindowStrings.LANGUAGE_MENU())

        # Create language action group for radio button behavior
        self.language_action_group = QtGui.QActionGroup(self)
        self.language_action_group.setExclusive(True)

        # Get current language from params
        current_language = self.local_params.get('language', 'en')

        # English
        english_action = QtGui.QAction(MainWindowStrings.LANGUAGE_ENGLISH(), self)
        english_action.setCheckable(True)
        english_action.setChecked(current_language == 'en')
        english_action.triggered.connect(lambda: self.change_language('en'))
        self.language_action_group.addAction(english_action)
        self.language_menu.addAction(english_action)

        # Chinese
        chinese_action = QtGui.QAction(MainWindowStrings.LANGUAGE_CHINESE(), self)
        chinese_action.setCheckable(True)
        chinese_action.setChecked(current_language == 'zh')
        chinese_action.triggered.connect(lambda: self.change_language('zh'))
        self.language_action_group.addAction(chinese_action)
        self.language_menu.addAction(chinese_action)

        # Add Window menu
        self.window_menu = self.menu_bar.addMenu(MainWindowStrings.VIEW_MENU())

        self.compact_view_action = QtGui.QAction("Compact View", self)  # Keep as is for now
        self.compact_view_action.setShortcut(QtGui.QKeySequence("Ctrl+C"))
        self.compact_view_action.setCheckable(True)
        self.compact_view_action.setChecked(self.enable_compact_view)
        self.compact_view_action.triggered.connect(self.toggle_compact_view)

        self.window_menu.addAction(self.compact_view_action)

        self.alternate_compact_view_action = QtGui.QAction(MainWindowStrings.ALTERNATE_VIEW_LABEL(), self)        
        self.alternate_compact_view_action.setCheckable(self.enable_compact_view)
        self.alternate_compact_view_action.setChecked(self.enable_alternate_compact_view)
        self.alternate_compact_view_action.setEnabled(self.enable_compact_view)
        self.alternate_compact_view_action.triggered.connect(self.toggle_alternate_compact_view)

        self.window_menu.addAction(self.alternate_compact_view_action)

        self.window_menu.addSeparator()

        show_all_action = QtGui.QAction("Show All Messages", self)
        show_all_action.setShortcut(QtGui.QKeySequence("Ctrl+A"))
        show_all_action.setCheckable(True)  
        show_all_action.setChecked(self.enable_show_all_decoded)  
        show_all_action.triggered.connect(self.update_show_all_preference)

        self.show_all_action = show_all_action
        
        self.window_menu.addAction(show_all_action)
        
        filter_gui_action = QtGui.QAction("Show Filters", self)
        filter_gui_action.setShortcut(QtGui.QKeySequence("Ctrl+F"))
        filter_gui_action.setCheckable(True)  
        filter_gui_action.setChecked(self.enable_filter_gui)  
        filter_gui_action.triggered.connect(self.update_filter_gui_preference)

        self.filter_gui_action = filter_gui_action
        
        self.window_menu.addAction(filter_gui_action)

        grid_monitor_action = QtGui.QAction(MainWindowStrings.GRID_MONITORING_ACTION(), self)
        grid_monitor_action.setShortcut(QtGui.QKeySequence("Ctrl+G"))
        grid_monitor_action.setCheckable(True)
        grid_monitor_action.setChecked(self.enable_grid_monitor)
        grid_monitor_action.triggered.connect(self.update_grid_monitor_preference)

        self.grid_monitor_action = grid_monitor_action

        self.window_menu.addAction(grid_monitor_action)

        self.window_menu.addSeparator()
        
        clear_filters_action = QtGui.QAction("Clear Filters", self)
        clear_filters_action.setShortcut(QtGui.QKeySequence("Ctrl+W")) 
        clear_filters_action.triggered.connect(self.clear_filters)  
        self.window_menu.addAction(clear_filters_action)

        clear_output_action = QtGui.QAction("Clear rows from Table", self)
        clear_output_action.setShortcut(QtGui.QKeySequence("Ctrl+K")) 
        clear_output_action.triggered.connect(self.clear_output_and_filters)  
        self.window_menu.addAction(clear_output_action)
        
        format_time_menu = self.window_menu.addMenu(MainWindowStrings.FORMAT_TIME_MENU())

        self.age_column_action = QtGui.QAction(MainWindowStrings.SHOW_AGE_ACTION(), self)
        self.age_column_action.setCheckable(True)
        self.age_column_action.setChecked(self.datetime_column_setting == DATE_COLUMN_AGE)
        self.age_column_action.triggered.connect(self.enable_age_column)

        self.datetime_column_action = QtGui.QAction(MainWindowStrings.SHOW_TIME_ACTION(), self)
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

        theme_menu = self.window_menu.addMenu("Theme")

        self.light_theme_action = QtGui.QAction("Light", self)
        self.light_theme_action.setCheckable(True)
        self.light_theme_action.setChecked(self.theme_mode_setting == THEME_MODE_LIGHT)
        self.light_theme_action.triggered.connect(self.enable_light_theme)

        self.dark_theme_action = QtGui.QAction("Dark", self)
        self.dark_theme_action.setCheckable(True)
        self.dark_theme_action.setChecked(self.theme_mode_setting == THEME_MODE_DARK)
        self.dark_theme_action.triggered.connect(self.enable_dark_theme)

        self.system_theme_action = QtGui.QAction("System", self)
        self.system_theme_action.setCheckable(True)
        self.system_theme_action.setChecked(self.theme_mode_setting == THEME_MODE_SYSTEM)
        self.system_theme_action.triggered.connect(self.enable_system_theme)

        theme_menu.addAction(self.light_theme_action)
        theme_menu.addAction(self.dark_theme_action)
        theme_menu.addAction(self.system_theme_action)

        theme_action_group = QtGui.QActionGroup(self)
        theme_action_group.addAction(self.light_theme_action)
        theme_action_group.addAction(self.dark_theme_action)
        theme_action_group.addAction(self.system_theme_action)
        theme_action_group.setExclusive(True)

        self.window_menu.addSeparator()
        self.clear_worked_history_action = QtGui.QAction("Clear Worked Callsigns History", self)
        self.clear_worked_history_action.setEnabled(len(self.worked_callsigns_history) > 0)
        self.clear_worked_history_action.triggered.connect(self.clear_worked_callsigns)

        self.window_menu.addAction(self.clear_worked_history_action)

    def get_monitoring_action_text(self):
        return MainWindowStrings.STOP_BUTTON_LABEL() if self._running else MainWindowStrings.START_MONITORING_LABEL()

    def update_monitoring_action(self):
        try:
            self.monitoring_action.triggered.disconnect()
        except TypeError:
            pass

        if self._running:
            self.monitoring_action.setText(MainWindowStrings.STOP_BUTTON_LABEL())
            self.monitoring_action.triggered.connect(self.stop_monitoring)
        else:
            self.monitoring_action.setText(MainWindowStrings.START_MONITORING_LABEL())
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

        thanks_label = CustomQLabel("With special thanks to:")  # Keep as English
        thanks_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(thanks_label)

        thanks_names = CustomQLabel("Rick, DU6/PE1NSQ, Vincent F4BKV,<br />Juan TG9AJR, Neil G0JHC")  # Names - no translation
        thanks_names.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(thanks_names)

        layout.addStretch()

        second_separator = QtWidgets.QFrame()
        second_separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        second_separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        layout.addWidget(second_separator)

        donation_link = CustomQLabel(DONATION_SECTION)  # HTML link - keep as is
        donation_link.setOpenExternalLinks(True)
        donation_link.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(donation_link)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        ok_button = CustomButton(CommonStrings.OK())
        ok_button.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        dialog.exec()

    def show_language_changed_dialog(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(MainWindowStrings.LANGUAGE_CHANGED_TITLE())
        dialog.setFixedWidth(400)

        layout = QtWidgets.QVBoxLayout(dialog)

        icon_path = os.path.join(CURRENT_DIR, "pounce.png")
        icon_label = CustomQLabel()
        icon_pixmap = QtGui.QPixmap(icon_path)
        if not icon_pixmap.isNull():
            icon_pixmap = icon_pixmap.scaled(
                200,
                icon_pixmap.height(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )

        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        message_label = CustomQLabel(MainWindowStrings.LANGUAGE_CHANGED_MESSAGE())
        message_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        message_label.setStyleSheet("font-size: 13px;")
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        layout.addStretch()

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        ok_button = CustomButton(CommonStrings.OK())
        ok_button.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        dialog.exec()

    def save_band_settings(self):
        for amateur_band in AMATEUR_BANDS.keys():
            wanted_callsigns                    = self.wanted_callsigns_vars[amateur_band].text()
            monitored_callsigns                 = self.monitored_callsigns_vars[amateur_band].text()
            wanted_cq_zones                     = self.wanted_cq_zones_vars[amateur_band].text()
            monitored_cq_zones                  = self.monitored_cq_zones_vars[amateur_band].text()
            excluded_callsigns                  = self.excluded_callsigns_vars[amateur_band].text()
            excluded_cq_zones                   = self.excluded_cq_zones_vars[amateur_band].text()

            self.local_params.setdefault(amateur_band, {}).update({
                "monitored_callsigns"           : monitored_callsigns,
                "monitored_cq_zones"            : monitored_cq_zones,
                "excluded_callsigns"            : excluded_callsigns,
                "excluded_cq_zones"             : excluded_cq_zones,
                "wanted_callsigns"              : wanted_callsigns,
                "wanted_cq_zones"               : wanted_cq_zones,
            })
        self.save_params()               

    def start_monitoring(self):
        if self._running:
            return

        self._running = True   
        self.update_monitoring_action()   

        self.network_check_status.start(self.network_check_status_interval)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_mode_timer)
        self.timer.start(200)

        self.init_status_bar()

        self.is_status_button_label_visible = True
        self.is_status_button_label_blinking = False

        self.update_status_button(MainWindowStrings.STATUS_MONITORING(), STATUS_MONITORING_COLOR)
        self.stop_button.setEnabled(True)
        
        self.blink_timer = QtCore.QTimer()
        self.blink_timer.timeout.connect(self.toggle_label_visibility)

        self.stop_event.clear()
        self.hide_focus_value_label(visible=False)  

        # self.apply_band_change(self.gui_selected_band)
        
        self.local_params = self.load_params()
        # Create a QThread and a Worker object with default parameters
        self.thread = QThread()
        self.worker = Worker(
            self.monitoring_settings,
            self.stop_event
        )
        
        # Update worker with all current parameters
        self.set_worker_settings()
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

        self.worker.message.connect(self.handle_message_received)

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

        self.status_bar_label_mode.setText(MainWindowStrings.WAITING_DATA_PACKETS())    
        self.update_status_bar_style(STATUS_MONITORING_COLOR, "white")

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

    def refresh_monitoring(self):
        if not self._running or not self.worker:
            return
            
        self.local_params = self.load_params()
        self.set_worker_settings()
        
        # Signal the worker to update its listener settings
        self.worker.update_listener_settings_signal.emit()
        self.worker.show_listener_settings_signal.emit()

    def set_worker_settings(self):
        local_ip_address = get_local_ip_address()

        self.worker.primary_udp_server_address      = self.local_params.get('primary_udp_server_address') or local_ip_address
        self.worker.primary_udp_server_port         = int(self.local_params.get('primary_udp_server_port') or DEFAULT_UDP_PORT)
        self.worker.secondary_udp_server_address    = self.local_params.get('secondary_udp_server_address') or local_ip_address
        self.worker.secondary_udp_server_port       = int(self.local_params.get('secondary_udp_server_port') or DEFAULT_UDP_PORT)
        self.worker.enable_secondary_udp_server     = self.local_params.get('enable_secondary_udp_server', DEFAULT_SECONDARY_UDP_SERVER)
        self.worker.logging_udp_server_address      = self.local_params.get('logging_udp_server_address') or local_ip_address
        self.worker.logging_udp_server_port         = int(self.local_params.get('logging_udp_server_port') or DEFAULT_UDP_PORT)
        self.worker.enable_logging_udp_server       = self.local_params.get('enable_logging_udp_server', DEFAULT_SECONDARY_UDP_SERVER)
        self.worker.enable_sending_reply            = self.local_params.get('enable_sending_reply', DEFAULT_SENDING_REPLY)
        self.worker.enable_polite_reply             = self.local_params.get('enable_polite_reply', DEFAULT_POLITE_REPLY)

        self.worker.max_reply_attempts_to_callsign  = self.local_params.get('max_reply_attempts_to_callsign', DEFAULT_REPLY_ATTEMPTS)
        self.worker.max_working_delay               = self.local_params.get('max_working_delay', DEFAULT_MAX_WAITING_DELAY)

        self.worker.enable_log_all_valid_contact    = self.local_params.get('enable_log_all_valid_contact', DEFAULT_LOG_ALL_VALID_CONTACT)
        self.worker.enable_reply_to_valid_callsign  = self.local_params.get('enable_reply_to_valid_callsign', DEFAULT_LOG_ALL_VALID_CONTACT)
        self.worker.enable_reply_to_valid_direction = self.local_params.get('enable_reply_to_valid_direction', DEFAULT_LOG_ALL_VALID_CONTACT)
        self.worker.enable_reply_to_lotw_only       = self.local_params.get('enable_reply_to_lotw_only', False)
        self.worker.enable_gap_finder               = self.local_params.get('enable_gap_finder', DEFAULT_GAP_FINDER)
        self.worker.enable_watchdog_bypass          = self.local_params.get('enable_watchdog_bypass', DEFAULT_WATCHDOG_BYPASS)
        self.worker.enable_debug_output             = self.local_params.get('enable_debug_output', DEFAULT_DEBUG_OUTPUT)
        self.worker.enable_pounce_log               = self.local_params.get('enable_pounce_log', DEFAULT_POUNCE_LOG)
        self.worker.enable_log_packet_data          = self.local_params.get('enable_log_packet_data', DEFAULT_LOG_PACKET_DATA)

        self.worker.adif_file_paths                 = self.local_params.get('adif_file_paths', None)
        self.worker.adif_worked_backup_file_path    = self.local_params.get('adif_worked_backup_file_path', None)
        self.worker.worked_before_preference        = convert_wkb4_reply_mode(self.local_params.get('worked_before_preference', WKB4_REPLY_MODE_ALWAYS))
        self.worker.marathon_preference             = self.local_params.get('marathon_preference', {})
        self.worker.grid_tracker_preference         = self.local_params.get('grid_tracker_preference', {})
        self.worker.enable_grid_reply_new_grid      = self.local_params.get('enable_grid_reply_new_grid', False)
        self.worker.enable_grid_reply_unconfirmed   = self.local_params.get('enable_grid_reply_unconfirmed', False)
        self.worker.minimum_report_for_reply        = self.local_params.get('minimum_report_for_reply', DEFAULT_MINIMUM_REPORT)
        self.worker.priority_order                  = self.local_params.get('priority_order', list(PRIORITY_LIST.values()))

        self.worker.enable_club_log_synch           = self.local_params.get('enable_club_log_synch', False)
        self.worker.club_log_email                  = self.local_params.get('club_log_email', '')
        self.worker.club_log_password               = self.local_params.get('club_log_password', '')
        self.worker.club_log_callsign               = self.local_params.get('club_log_callsign', '')

        self.worker.min_freq                        = self.local_params.get('min_freq', FREQ_MINIMUM)
        self.worker.max_freq                        = self.local_params.get('max_freq', FREQ_MAXIMUM)

    def stop_monitoring(self):
        self.network_check_status.stop()        
        self.activity_bar.setValue(0) 
        self.hide_status_menu()

        if self.worker:
            self.worker.stop()  
            try:
                self.worker.finished.disconnect()
                self.worker.error.disconnect()
                self.worker.message.disconnect()
            except RuntimeError:
                pass
            self.worker = None

        if self.thread:
            try:
                self.thread.started.disconnect()
                self.thread.finished.disconnect()
            except RuntimeError:
                pass
        
        if self.timer: 
            self.timer.stop()
            self.timer_value_label.setText(DEFAULT_MODE_TIMER_VALUE)        

        if self._running:
            self.status_button.setEnabled(True)
            self.stop_button.setEnabled(False)

            self.stop_event.set()

            self._running            = False       

            self.update_tab_widget_labels_style()
            self.restore_settings()

            self._instance               = None
            self._synched_addr_port      = None
            self.operating_band          = None
            self.last_targeted_call      = None
            self.last_decode_packet_time = None
            self.transmitting            = False
                        
            self.stop_tray_icon()
            self.stop_blinking_status_button()            

            self.tab_widget.set_selected_tab(self.band_indices.get(self.operating_band))
            self.tab_widget.set_operating_tab(None)

            self.check_connection_status()

            self.update_status_bar_style("#E0E0E0", "#000000")
            self.update_status_button(MainWindowStrings.START_MONITORING_LABEL(), STATUS_TRX_COLOR)

            self.status_button.resetStyle()
            self.restore_settings()

            # Update Windows menu            
            self.update_monitoring_action()   
            self.reset_window_title()

            log.warning(f"Running: {self._running}")

            if hasattr(self, 'thread') and self.thread is not None:
                try:
                    if self.thread.isRunning():
                        self.thread.quit()
                        # Wait with timeout to prevent indefinite hanging
                        if not self.thread.wait(5000):  # 5-second timeout
                            log.warning("Thread did not stop gracefully within timeout")
                            self.thread.terminate()
                except RuntimeError as e:
                    log.error(f"RuntimeError when stopping thread: {e}")                        
                finally:
                    self.thread = None                        

    def log_exception_to_file(self, filename, message):
        timestamp = datetime.now(timezone.utc).strftime("%y%m%d_%H%M%S")
        with open(filename, "a") as log_file:
            log_file.write(f"{timestamp} {message}\n")
    
    def status_menu_agent_cleaner(self):
        if sys.platform == 'darwin':
            self.status_menu_agent.hide_status_menu_agent()
            self.status_menu_agent.deleteLater()       

def on_about_to_quit(window):
    log.info("Application is about to quit. Cleaning up...")
    
    if window.grid_monitor:
        window.app_shutting_down = True
        window.grid_monitor.close()

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

    window.updater  = UpdateManager()
    window.updater.check_expiration_or_update()
    
    cleanup_old_logs()
    cleanup_timer   = QtCore.QTimer()
    cleanup_timer.timeout.connect(cleanup_old_logs)
    cleanup_timer.start(60 * 60 * 1_000)

    window.show()
    window.update_window_title()       
    window.update_status_menu_message((f'{GUI_LABEL_VERSION}').upper(), BG_COLOR_REGULAR_FOCUS, FG_COLOR_REGULAR_FOCUS)   
   
    if is_first_launch_or_new_version(CURRENT_VERSION_NUMBER):
        window.show_about_dialog() 
        save_current_version(CURRENT_VERSION_NUMBER)

    app.aboutToQuit.connect(lambda: on_about_to_quit(window))

    exit_code = app.exec()

    log.info("Application event loop finished with exit code %s", exit_code)
    sys.exit(exit_code)

if __name__ == '__main__':
    # Fix for Windows multiprocessing - prevent infinite loop
    import multiprocessing
    if hasattr(multiprocessing, 'freeze_support'):
        multiprocessing.freeze_support()
    main()
