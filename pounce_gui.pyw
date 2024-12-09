# pounce_gui.pyw

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem
from PyQt6.QtCore import QThread
from PyQt6.QtMultimedia import QSoundEffect

import platform
import re
import sys
import pickle
import os
import threading
import pyperclip

from datetime import datetime, timezone, timedelta
from collections import deque
from packaging import version
from functools import partial

# Custom classes 
from custom_tab_widget import CustomTabWidget
from custom_button import CustomButton
from tray_icon import TrayIcon
from activity_bar import ActivityBar
from tooltip import ToolTip
from worker import Worker
from monitoring_setting import MonitoringSettings
from updater import Updater
from theme_manager import ThemeManager
from clublog import ClubLogManager
from setting_dialog import SettingsDialog

from utils import get_local_ip_address, get_log_filename, matches_any
from utils import get_mode_interval, get_amateur_band
from utils import force_input, text_to_array

from version import is_first_launch_or_new_version, save_current_version

from logger import get_logger, add_file_handler, remove_file_handler

from utils import(
    AMATEUR_BANDS
)

from constants import (
    CURRENT_VERSION_NUMBER,
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
    STATUS_COLOR_LABEL_SELECTED,
    # Parameters
    PARAMS_FILE,
    POSITION_FILE,
    WANTED_CALLSIGNS_FILE,
    WANTED_CALLSIGNS_HISTORY_SIZE,
    # Labels
    GUI_LABEL_NAME,
    GUI_LABEL_VERSION,
    STATUS_BUTTON_LABEL_MONITORING,
    STATUS_BUTTON_LABEL_DECODING,
    STATUS_BUTTON_LABEL_START,
    STATUS_BUTTON_LABEL_TRX,
    STATUS_BUTTON_LABEL_NOTHING_YET,
    STATUS_COLOR_LABEL_OFF,
    WAITING_DATA_PACKETS_LABEL,
    WANTED_CALLSIGNS_HISTORY_LABEL,
    CALLSIGN_NOTICE_LABEL,
    # Timer
    DEFAULT_MODE_TIMER_VALUE,
    # Band,
    DEFAULT_SELECTED_BAND,
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
    ACTIVITY_BAR_MAX_VALUE,
    # Style
    CONTEXT_MENU_DARWIN_QSS,
    # Fonts
    CUSTOM_FONT,
    CUSTOM_FONT_MONO,
    CUSTOM_FONT_MONO_LG,
    CUSTOM_FONT_SMALL,
    MENU_FONT,
    # URL
    DISCORD_SECTION,
    DONATION_SECTION
)

log         = get_logger(__name__)
stop_event  = threading.Event()

class UpdateWantedDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, selected_callsign=""):
        super().__init__(parent)

        self.theme_manager = ThemeManager()
        self.selected_callsign = selected_callsign

        if self.theme_manager:
            self.theme_manager.theme_changed.connect(self.apply_theme)

        self.init_ui()
        self.apply_theme(self.theme_manager.dark_mode)

    def init_ui(self):
        self.setWindowTitle("Update Wanted Callsigns")
        self.resize(450, 100)

        layout = QtWidgets.QVBoxLayout(self)
        
        message_label = QtWidgets.QLabel('Do you want to update Wanted Callsign(s) with:')
        layout.addWidget(message_label)
        
        self.entry = QtWidgets.QLabel(self.selected_callsign)
        self.entry.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.entry.setWordWrap(True)
        self.entry.setFont(CUSTOM_FONT_MONO)

        self.entry.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.entry)
        
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Yes | QtWidgets.QDialogButtonBox.StandardButton.No
        )
        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        self.adjust_dialog_size()

    def apply_theme(self, dark_mode):        
        if dark_mode:
            self.entry.setStyleSheet(f"background-color: {BG_COLOR_BLACK_ON_YELLOW}; color: {FG_COLOR_BLACK_ON_YELLOW};")
        else:
            self.entry.setStyleSheet(f"background-color: {FG_COLOR_REGULAR_FOCUS}; color: {BG_COLOR_REGULAR_FOCUS};")

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
        self.entry.setFont(CUSTOM_FONT_MONO)
        self.entry.textChanged.connect(lambda: force_input(self.entry, mode="uppercase"))
        layout.addWidget(self.entry)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    def get_result(self):
        return ",".join(text_to_array(self.entry.toPlainText().strip()))

class MainApp(QtWidgets.QMainWindow):
    error_occurred = QtCore.pyqtSignal(str)    
    message_received = QtCore.pyqtSignal(object)

    def __init__(self):
        super(MainApp, self).__init__()

        self.worker              = None
        self.timer               = None
        self.tray_icon           = None
        self.monitoring_settings = MonitoringSettings()       
        self.clublog_manager     = ClubLogManager(self) 

        self.setGeometry(100, 100, 1_000, 700)
        self.setMinimumSize(1_000, 600)
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

        self.theme_manager = ThemeManager()
        self.theme_manager.theme_changed.connect(self.apply_theme_to_all)

        self.theme_timer = QtCore.QTimer(self)
        self.theme_timer.timeout.connect(self.theme_manager.check_theme_change)
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
        self.gui_selected_band                  = None
        self.operating_band                     = None
        self.enable_show_all_decoded            = None

        self.wanted_callsign_detected_sound     = QSoundEffect()
        self.directed_to_my_call_sound          = QSoundEffect()
        self.ready_to_log_sound                 = QSoundEffect()
        self.error_occurred_sound               = QSoundEffect()
        self.band_change_sound                  = QSoundEffect()
        self.monitored_callsign_detected_sound  = QSoundEffect()

        self.wanted_callsign_detected_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/495650__matrixxx__supershort-ping-or-short-notification.wav"))
        self.directed_to_my_call_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/716445__scottyd0es__tone12_error.wav"))
        self.ready_to_log_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/709072__scottyd0es__aeroce-dualtone-5.wav"))
        self.error_occurred_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/142608__autistic-lucario__error.wav"))
        self.monitored_callsign_detected_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/716442__scottyd0es__tone12_alert_3.wav"))
        self.band_change_sound.setSource(QtCore.QUrl.fromLocalFile(f"{CURRENT_DIR}/sounds/342759__rhodesmas__score-counter-01.wav"))
        
        self.menu_bar                           = self.menuBar()    

        self.load_clublog_action = QtGui.QAction("Update DXCC Info", self)
        self.load_clublog_action.triggered.connect(self.clublog_manager.load_clublog_info)

        self.create_main_menu()

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        outer_layout = QtWidgets.QHBoxLayout()
        central_widget.setLayout(outer_layout)

        main_layout = QtWidgets.QGridLayout()
        outer_layout.addLayout(main_layout)

        params = self.load_params()

        self.wanted_callsigns_history = self.load_wanted_callsigns()

        # Wanted callsigns label
        self.wanted_callsigns_history_label = QtWidgets.QLabel(WANTED_CALLSIGNS_HISTORY_LABEL % len(self.wanted_callsigns_history))

        # Listbox (wanted callsigns)
        self.listbox = QtWidgets.QListWidget()
        self.listbox.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.listbox.setFont(CUSTOM_FONT)
        self.listbox.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.listbox.itemDoubleClicked.connect(self.on_listbox_double_click)

        # Context menu for listbox
        self.listbox.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.listbox.customContextMenuRequested.connect(self.on_right_click)        

        self.update_listbox()

        # Focus value (sequence)
        self.focus_frame = QtWidgets.QFrame()
        self.focus_frame_layout = QtWidgets.QHBoxLayout()
        self.focus_frame.setLayout(self.focus_frame_layout)
        self.focus_value_label = QtWidgets.QLabel("")
        self.focus_value_label.setFont(CUSTOM_FONT_MONO_LG)
        self.focus_value_label.setStyleSheet("padding: 10px;")
        self.focus_frame_layout.addWidget(self.focus_value_label)
        self.focus_frame.hide()
        self.focus_value_label.mousePressEvent = self.copy_to_clipboard

        # Timer value
        self.timer_value_label = QtWidgets.QLabel(DEFAULT_MODE_TIMER_VALUE)
        self.timer_value_label.setFont(CUSTOM_FONT_MONO_LG)
        self.timer_value_label.setStyleSheet("background-color: #9dfffe; color: #555bc2; padding: 10px;")

        self.callsign_notice = QtWidgets.QLabel(CALLSIGN_NOTICE_LABEL)
        self.callsign_notice.setStyleSheet("background-color: #9dfffe; color: #555bc2;")
    
        """
            Widget Tab
        """
        self.tab_widget = CustomTabWidget()

        self.tab_widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        
        self.wanted_callsigns_vars              = {}
        self.monitored_callsigns_vars           = {}
        self.excluded_callsigns_vars            = {}
        self.monitored_cq_zones_vars            = {}

        self.tooltip_wanted_vars                = {}
        self.tooltip_monitored_vars             = {}
        self.tooltip_excluded_vars              = {}
        self.tooltip_monitored_cq_zones_vars    = {}

        self.band_indices                       = {}
        self.band_content_widgets               = {}

        fixed_label_width                        = 150

        vars_dict = {
            'wanted_callsigns'      : self.wanted_callsigns_vars,
            'monitored_callsigns'   : self.monitored_callsigns_vars,            
            'monitored_cq_zones'    : self.monitored_cq_zones_vars,
            'excluded_callsigns'    : self.excluded_callsigns_vars,            
        }

        tooltip_vars_dict = {
            'wanted_callsigns'      : self.tooltip_wanted_vars,
            'monitored_callsigns'   : self.tooltip_monitored_vars,
            'monitored_cq_zones'    : self.tooltip_monitored_cq_zones_vars,
            'excluded_callsigns'    : self.tooltip_excluded_vars,
        }

        sought_variables = [
            {
                'name'             : 'wanted_callsigns',
                'label'            : 'Wanted Callsigns(s):',
                'function'         : partial(force_input, mode="uppercase"),
                'on_changed_method': self.on_wanted_callsigns_changed,
            },
            {
                'name'             : 'monitored_callsigns',
                'label'            : 'Monitored Callsign(s):',
                'function'         : partial(force_input, mode="uppercase"),
                'on_changed_method': self.on_monitored_callsigns_changed,
            },
            {
                'name'             : 'monitored_cq_zones',
                'label'            : 'Monitored CQ Zone(s):',
                'function'         : partial(force_input, mode="numbers"),
                'on_changed_method': self.on_monitored_cq_zones_changed,
            },
            {
                'name'             : 'excluded_callsigns',
                'label'            : 'Excluded Callsign(s):',
                'function'         : partial(force_input, mode="uppercase"),
                'on_changed_method': self.on_excluded_callsigns_changed,
            }
        ]

        for band in AMATEUR_BANDS.keys():
            tab_content = QtWidgets.QWidget()
            layout = QtWidgets.QGridLayout(tab_content)

            band_params = params.get(band, {})

            for idx, var_info in enumerate(sought_variables):
                var_name          = var_info['name']
                label_text        = var_info['label']
                function          = var_info['function']
                on_changed_method = var_info['on_changed_method']

                line_edit = QtWidgets.QLineEdit()
                line_edit.setFont(CUSTOM_FONT)

                vars_dict[var_name][band] = line_edit

                tooltip_vars_dict[var_name][band] = ToolTip(line_edit)

                line_edit.setText(band_params.get(var_name, ""))

                line_label = QtWidgets.QLabel(label_text)
                line_label.setStyleSheet("border-radius: 6px; padding: 3px;")
                line_label.setMinimumWidth(fixed_label_width)

                layout.addWidget(line_label, idx+1, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
                layout.addWidget(line_edit, idx+1, 1)

                line_edit.textChanged.connect(partial(function, line_edit))
                line_edit.textChanged.connect(on_changed_method)

            tab_content.setLayout(layout)
            self.band_content_widgets[band] = tab_content
            self.tab_widget.addTab(tab_content, band)

        self.tab_widget.tabClicked.connect(self.on_tab_clicked) 

        # Status layout
        status_layout = QtWidgets.QGridLayout()

        status_static_label = QtWidgets.QLabel("Status:")
        status_static_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
        status_static_label.setStyleSheet("padding-right: 30px;")
        status_static_label.setMinimumWidth(fixed_label_width)

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
        
        self.output_table.setFont(CUSTOM_FONT)
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
        self.output_table.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        """
            Bottom and Button layout
        """
        bottom_layout = QtWidgets.QHBoxLayout()
        button_layout = QtWidgets.QHBoxLayout()

        self.clear_button = CustomButton("Clear History")
        self.clear_button.setEnabled(False)
        self.clear_button.clicked.connect(self.clear_output_table)

        self.settings = CustomButton("Settings")
        self.settings.clicked.connect(self.open_settings)

        self.disable_alert_checkbox = QtWidgets.QCheckBox("Disable all Sounds")
        self.disable_alert_checkbox.setChecked(False)
        self.disable_alert_checkbox.stateChanged.connect(self.update_alert_label_style)

        self.quit_button = CustomButton("Quit")
        self.quit_button.clicked.connect(self.quit_application)

        self.inputs_enabled = True

        if platform.system() == 'Darwin':
            self.restart_button = CustomButton("Restart")
            self.restart_button.clicked.connect(self.restart_application)

        # Timer and start/stop buttons
        self.status_button = CustomButton(STATUS_BUTTON_LABEL_START)
        self.status_button.clicked.connect(self.start_monitoring)
        self.status_button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)

        self.status_button.setAttribute(QtCore.Qt.WidgetAttribute.WA_Hover, True)
        self.status_button.setMouseTracking(True)
        
        self.stop_button = CustomButton("Stop all")
        self.stop_button.setEnabled(False)        
        self.stop_button.clicked.connect(self.stop_monitoring)        
        self.stop_button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)

        self.stop_button.setAttribute(QtCore.Qt.WidgetAttribute.WA_Hover, True)
        self.stop_button.setMouseTracking(True)
        # Timer label and log analysis
        
        button_layout.addWidget(self.settings)
        button_layout.addWidget(self.clear_button)

        if platform.system() == 'Darwin':
            button_layout.addWidget(self.restart_button)

        button_layout.addWidget(self.quit_button)

        bottom_layout.addWidget(self.disable_alert_checkbox)
        bottom_layout.addStretch()  
        bottom_layout.addLayout(button_layout)

        self.activity_bar = ActivityBar(max_value=ACTIVITY_BAR_MAX_VALUE)
        self.activity_bar.setFixedWidth(30)

        outer_layout.addWidget(self.activity_bar)

        self.enable_pounce_log = params.get('enable_pounce_log', True)
        
        # Get sound configuration
        self.enable_sound_wanted_callsigns = params.get('enable_sound_wanted_callsigns', True)
        self.enable_sound_directed_my_callsign = params.get('enable_sound_directed_my_callsign', True)
        self.enable_sound_monitored_callsigns = params.get('enable_sound_monitored_callsigns', True)
       
        spacer = QtWidgets.QSpacerItem(0, 10, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)        

        main_layout.addWidget(self.focus_frame, 0, 0, 1, 4)
        main_layout.addWidget(self.timer_value_label, 0, 4)
            
        main_layout.addWidget(self.wanted_callsigns_history_label, 1, 3, 1, 2)
        main_layout.addWidget(self.tab_widget, 2, 0, 4, 3)                
        main_layout.addWidget(self.listbox, 2, 3, 5, 2)
        main_layout.addLayout(status_layout, 8, 1, 1, 1)
        main_layout.addWidget(self.status_button, 8, 3)
        main_layout.addWidget(self.stop_button, 8, 4)
        main_layout.addItem(spacer, 9, 0, 1, 5)
        main_layout.addWidget(self.output_table, 10, 0, 1, 5)
        main_layout.addLayout(bottom_layout, 11, 0, 1, 5)
        
        self.file_handler = None
        if self.enable_pounce_log:
            self.file_handler = add_file_handler(get_log_filename())

        """
            self.operating_band might be overided as soon as check_connection_status is used
        """
        self.gui_selected_band = params.get('last_band_used', DEFAULT_SELECTED_BAND)
        self.tab_widget.set_selected_tab(self.gui_selected_band)
        
        self.apply_theme_to_all(self.theme_manager.dark_mode)
        self.load_window_position()
        QtCore.QTimer.singleShot(1_000, lambda: self.init_activity_bar())          

        # Close event to save position
        self.closeEvent = self.on_close

    def apply_theme_to_all(self, dark_mode):
        self.apply_palette(dark_mode)

    def on_tab_clicked(self, tab_band):
        self.gui_selected_band = tab_band
        # log.debug(f"Selected_band: {self.gui_selected_band}")            

        self.tab_widget.set_selected_tab(self.gui_selected_band)

        if self.gui_selected_band != self.operating_band and self._running:
            self.tab_widget.set_operating_tab(self.operating_band)

        self.save_last_used_tab(self.gui_selected_band)
        
    def apply_band_change(self, band):
        if band != self.operating_band and band != 'Invalid':            
            self.operating_band = band
            self.monitoring_settings.set_wanted_callsigns(self.wanted_callsigns_vars[self.operating_band].text())
            self.monitoring_settings.set_monitored_callsigns(self.monitored_callsigns_vars[self.operating_band].text())
            self.monitoring_settings.set_excluded_callsigns(self.excluded_callsigns_vars[self.operating_band].text())
            self.monitoring_settings.set_monitored_cq_zones(self.monitored_cq_zones_vars[self.operating_band].text())
            
            self.update_tab_widget_labels_style()
            
            if self.worker is not None:
                self.worker.update_settings_signal.emit()

                if not self.disable_alert_checkbox.isChecked():      
                    self.play_sound("band_change")

        if self._running:
            # Make sure to reset last_sound_played_time if we switch band
            self.last_sound_played_time = datetime.min
            self.focus_frame.hide()
            self.tab_widget.set_operating_tab(self.operating_band)

    def save_last_used_tab(self, band):
        params = self.load_params()
        params['last_band_used'] = band
        self.save_params(params)                       

    """
        Used for MonitoringSetting
    """
    def on_wanted_callsigns_changed(self):
        if self.gui_selected_band == self.operating_band:
            self.monitoring_settings.set_wanted_callsigns(self.wanted_callsigns_vars[self.operating_band].text())
            if self.worker is not None:
                self.worker.update_settings_signal.emit()

    def on_monitored_callsigns_changed(self):
        if self.gui_selected_band == self.operating_band:
            self.monitoring_settings.set_monitored_callsigns(self.monitored_callsigns_vars[self.operating_band].text())
            if self.worker is not None:
                self.worker.update_settings_signal.emit()

    def on_excluded_callsigns_changed(self):
        if self.gui_selected_band == self.operating_band:
            self.monitoring_settings.set_excluded_callsigns(self.excluded_callsigns_vars[self.operating_band].text())
            if self.worker is not None:
                self.worker.update_settings_signal.emit()

    def on_monitored_cq_zones_changed(self):
        if self.gui_selected_band == self.operating_band:
            self.monitoring_settings.set_monitored_cq_zones(self.monitored_cq_zones_vars[self.operating_band].text())
            if self.worker is not None:
                self.worker.update_settings_signal.emit()

    def update_wanted_callsigns_history(self, new_callsigns):
        if new_callsigns:
            new_callsigns = ",".join(sorted([callsign.strip() for callsign in new_callsigns.split(",")]))
            if new_callsigns not in self.wanted_callsigns_history:
                self.wanted_callsigns_history.append(new_callsigns)
                if len(self.wanted_callsigns_history) > WANTED_CALLSIGNS_HISTORY_SIZE:
                    self.wanted_callsigns_history.pop(0)
                self.save_wanted_callsigns(self.wanted_callsigns_history)
                self.update_listbox()

    @QtCore.pyqtSlot(str)
    def add_message_to_table(self, message, fg_color='white', bg_color=STATUS_TRX_COLOR):
        self.clear_button.setEnabled(True)

        row_position = self.output_table.rowCount()
        self.output_table.insertRow(row_position)

        error_item = QTableWidgetItem(message)
        error_item.setForeground(QtGui.QBrush(QtGui.QColor(fg_color)))
        error_item.setBackground(QtGui.QBrush(QtGui.QColor(bg_color)))
        error_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        error_item.setFont(CUSTOM_FONT_MONO)

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
                    frequency = str(self.last_frequency / 1_000) + 'Khz'
                    band      = get_amateur_band(self.frequency)

                    if band != 'Invalid':
                        self.add_message_to_table(f"{frequency} ({band}) {self.mode}")                     
                        self.tab_widget.set_selected_tab(band)   
            elif message_type == 'stop_monitoring':
                self.stop_monitoring()     
            elif message_type == 'update_status':
                self.check_connection_status(
                    message.get('decode_packet_count', 0),
                    message.get('last_decode_packet_time'),
                    message.get('last_heartbeat_time'),
                    message.get('frequency'),
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
                    matches_any(text_to_array(self.wanted_callsigns_vars[self.operating_band].text()), directed)
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
                        self.operating_band,
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
        if self.operating_band:
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
            menu.setStyleSheet(CONTEXT_MENU_DARWIN_QSS)
            menu.setFont(MENU_FONT)
        """
        header_action = QtGui.QAction(f"Apply to {self.operating_band}")
        header_action.setEnabled(False)  
        menu.addAction(header_action)
        menu.addSeparator()
        """
        actions = {}

        """
            Wanted Callsigns
        """
        if callsign not in self.wanted_callsigns_vars[self.operating_band].text():
            actions['add_callsign_to_wanted'] = menu.addAction(f"Add {callsign} to Wanted Callsigns")
        else:
            actions['remove_callsign_from_wanted'] = menu.addAction(f"Remove {callsign} from Wanted Callsigns")

        if callsign != self.wanted_callsigns_vars[self.operating_band].text():
            actions['replace_wanted_with_callsign'] = menu.addAction(f"Make {callsign} your only Wanted Callsign")
        menu.addSeparator()

        """
            Monitored Callsigns
        """
        if callsign not in self.monitored_callsigns_vars[self.operating_band].text():
            actions['add_callsign_to_monitored'] = menu.addAction(f"Add {callsign} to Monitored Callsigns")
        else:
            actions['remove_callsign_from_monitored'] = menu.addAction(f"Remove {callsign} from Monitored Callsigns")
        menu.addSeparator()

        """
            Directed Callsigns
        """
        if directed:
            if directed not in self.wanted_callsigns_vars[self.operating_band].text():
                actions['add_directed_to_wanted'] = menu.addAction(f"Add {directed} to Wanted Callsigns")
            else:
                actions['remove_directed_from_wanted'] = menu.addAction(f"Remove {directed} from Wanted Callsigns")

            if directed != self.wanted_callsigns_vars[self.operating_band].text():
                actions['replace_wanted_with_directed'] = menu.addAction(f"Make {directed} your only Monitored Callsign")                

            if directed not in self.monitored_callsigns_vars[self.operating_band].text():
                actions['add_directed_to_monitored'] = menu.addAction(f"Add {directed} to Monitored Callsigns")
            else:
                actions['remove_directed_from_monitored'] = menu.addAction(f"Remove {directed} from Monitored Callsigns")
            menu.addSeparator()

        """
            Monitored CQ Zones
        """
        if cq_zone:
            try:
                if str(cq_zone) not in self.monitored_cq_zones_vars[self.operating_band].text():
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
                'add_callsign_to_wanted'         : lambda: self.update_var(self.wanted_callsigns_vars[self.operating_band], callsign),
                'remove_callsign_from_wanted'    : lambda: self.update_var(self.wanted_callsigns_vars[self.operating_band], callsign, "remove"),
                'replace_wanted_with_callsign'   : lambda: self.update_var(self.wanted_callsigns_vars[self.operating_band], callsign, "replace"),
                'add_callsign_to_monitored'      : lambda: self.update_var(self.monitored_callsigns_vars[self.operating_band], callsign),
                'remove_callsign_from_monitored' : lambda: self.update_var(self.monitored_callsigns_vars[self.operating_band], callsign, "remove"),
                'add_directed_to_wanted'         : lambda: self.update_var(self.wanted_callsigns_vars[self.operating_band], directed),
                'remove_directed_from_wanted'    : lambda: self.update_var(self.wanted_callsigns_vars[self.operating_band], directed, "remove"),
                'replace_wanted_with_directed'   : lambda: self.update_var(self.wanted_callsigns_vars[self.operating_band], directed, "replace"),
                'add_directed_to_monitored'      : lambda: self.update_var(self.monitored_callsigns_vars[self.operating_band], directed),
                'remove_directed_from_monitored' : lambda: self.update_var(self.monitored_callsigns_vars[self.operating_band], directed, "remove"),
                'add_to_cq_zone'                 : lambda: self.update_var(self.monitored_cq_zones_vars[self.operating_band], cq_zone),
                'remove_from_cq_zone'            : lambda: self.update_var(self.monitored_cq_zones_vars[self.operating_band], cq_zone, "remove"),
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
        if self.gui_selected_band:
            selected_callsign = item.text()
            dialog = UpdateWantedDialog(self, selected_callsign=selected_callsign)
            result = dialog.exec()
            if result == QtWidgets.QDialog.DialogCode.Accepted:            
                self.wanted_callsigns_vars[self.gui_selected_band].setText(selected_callsign)
                self.update_current_callsign_highlight()

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
        #self.status_button.hide()        

    def toggle_label_visibility(self):
        if self.is_status_button_label_visible:
            pass
            self.status_button.hide()
        else:
            pass
            self.status_button.show()

    def update_current_callsign_highlight(self):
        if self._running:
            for index in range(self.listbox.count()):
                item = self.listbox.item(index)
                if item.text() == self.wanted_callsigns_vars[self.operating_band].text() and self._running:
                    item.setBackground(QtGui.QBrush(QtGui.QColor('yellow')))
                    item.setForeground(QtGui.QBrush(QtGui.QColor('black')))
                else:
                    item.setBackground(QtGui.QBrush())
                    item.setForeground(QtGui.QBrush())   

    def update_status_label_style(self, background_color, text_color):
        style = f"""
            background-color: {background_color};
            color: {text_color};            
            border-radius: 5px;
            padding: 5px;
        """

        #if self.dark_mode:
            #style+= "border: 1px solid grey;"

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
            elif sound_name == 'band_change':
                self.band_change_sound.play()                
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
        frequency               = None,
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

        # Check band and control used tab
        if frequency is not None:
            operating_band = get_amateur_band(frequency)     
            if operating_band != 'Invalid' and self.operating_band != operating_band:
                self.apply_band_change(operating_band)
           
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

            self.enable_sound_wanted_callsigns      = params.get('enable_sound_wanted_callsigns', True)
            self.enable_sound_directed_my_callsign  = params.get('enable_sound_directed_my_callsign', True)
            self.enable_sound_monitored_callsigns   = params.get('enable_sound_monitored_callsigns', True)

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
        
    def check_theme_change(self):
        current_dark_mode = ThemeManager.is_dark_apperance()
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


        table_palette = QtGui.QPalette()          

        if dark_mode:
            table_palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor('#353535'))
            table_palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor('#454545'))
            table_palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor('#FFFFFF'))
        else:
            table_palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor('#FFFFFF'))
            table_palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor('#F4F5F5'))
            table_palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor('#000000'))
        
        self.output_table.setPalette(table_palette)

        gridline_color = '#D3D3D3' if not dark_mode else '#171717'
        background_color = '#FFFFFF' if not dark_mode else '#353535'
        self.output_table.setStyleSheet(f"""
            QTableWidget {{ 
                background-color: {background_color};
                gridline-color: {gridline_color}; 
            }}
        """)
        self.output_table.setPalette(table_palette)

        self.activity_bar.update()
        self.update_tab_widget_labels_style()

    def save_params(self, params):
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

    def save_wanted_callsigns(self, wanted_callsigns_history):
        with open(WANTED_CALLSIGNS_FILE, "wb") as f:
            pickle.dump(wanted_callsigns_history, f)

    def load_wanted_callsigns(self):
        if os.path.exists(WANTED_CALLSIGNS_FILE):
            with open(WANTED_CALLSIGNS_FILE, "rb") as f:
                return pickle.load(f)
        return []

    def update_listbox(self):
        self.listbox.clear()
        self.listbox.addItems(self.wanted_callsigns_history)
        self.update_wanted_callsigns_history_counter()

    def update_wanted_callsigns_history_counter(self):
        self.wanted_callsigns_history_label.setText(WANTED_CALLSIGNS_HISTORY_LABEL % len(self.wanted_callsigns_history))

    def update_alert_label_style(self):
        if self.disable_alert_checkbox.isChecked():
            self.disable_alert_checkbox.setStyleSheet(f"background-color: {BG_COLOR_BLACK_ON_YELLOW};")
        else:
            self.disable_alert_checkbox.setStyleSheet("")

    def on_right_click(self, position):
        menu = QtWidgets.QMenu()
        if sys.platform == 'darwin':
            menu.setStyleSheet(CONTEXT_MENU_DARWIN_QSS)
            menu.setFont(MENU_FONT)
        
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
        item_band.setFont(CUSTOM_FONT_SMALL)
        self.output_table.setItem(row_position, 1, item_band)
            
        item_snr = QTableWidgetItem(f"{snr:+3d} dB")
        item_snr.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        item_snr.setFont(CUSTOM_FONT_SMALL)
        self.output_table.setItem(row_position, 2, item_snr)
        
        item_dt = QTableWidgetItem(f"{delta_time:+5.1f}s")
        item_dt.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        item_dt.setFont(CUSTOM_FONT_SMALL)
        self.output_table.setItem(row_position, 3, item_dt)
        
        item_freq = QTableWidgetItem(f"{delta_freq:+6d}Hz")
        item_freq.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        item_freq.setFont(CUSTOM_FONT_SMALL)
        self.output_table.setItem(row_position, 4, item_freq)
        
        item_msg = QTableWidgetItem(f" {message}")
        item_msg.setFont(CUSTOM_FONT)
        self.output_table.setItem(row_position, 5, item_msg)
        
        item_country = QTableWidgetItem(entity)
        item_country.setFont(CUSTOM_FONT)
        self.output_table.setItem(row_position, 6, item_country)

        item_cq_zone = QTableWidgetItem(f"{cq_zone}")
        item_cq_zone.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        item_cq_zone.setFont(CUSTOM_FONT_SMALL)
        self.output_table.setItem(row_position, 7, item_cq_zone)

        item_continent = QTableWidgetItem(continent)
        item_continent.setFont(CUSTOM_FONT_SMALL)
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

    def update_status_button(
            self,        
            text = "",
            bg_color = "black",
            fg_color = "white",
        ):
        self.status_button.setText(text)
        self.status_button.setStyleSheet(f"""
            background-color: {bg_color}; 
            color: {fg_color};
            border: 2px solid {bg_color};
            border-radius: 8px;
            padding: 5px 10px;
        """)    
        
    def update_tab_widget_labels_style(self):
        styles = [
            (
                BG_COLOR_BLACK_ON_YELLOW,
                FG_COLOR_BLACK_ON_YELLOW
            ),
            (
                BG_COLOR_BLACK_ON_PURPLE,
                FG_COLOR_BLACK_ON_PURPLE
            ),
            (
                BG_COLOR_BLACK_ON_CYAN,
                FG_COLOR_BLACK_ON_CYAN
            ),
            (
                "transparent",
                "palette(text)"
            )
        ]

        for band in AMATEUR_BANDS.keys():    
            content_widget = self.tab_widget.get_content_widget(band)
            layout = content_widget.layout()

            for idx, (bg_color, fg_color) in enumerate(styles, start=1):
                label_widget = layout.itemAtPosition(idx, 0).widget()
                if band == self.operating_band and self._running:
                    label_widget.setStyleSheet(
                        f"""
                            background-color: {bg_color};
                            color: {fg_color}; 
                            border-radius: 6px;
                            padding: 3px;
                        """
                    )
                else:
                    label_widget.setStyleSheet("""
                        border-radius: 6px;
                        color: palette(text);                        
                        padding: 3px;
                    """)

    def create_main_menu(self):
        main_menu = self.menu_bar.addMenu(GUI_LABEL_NAME)

        about_action = QtGui.QAction(f"About {GUI_LABEL_NAME}", self)
        about_action.triggered.connect(self.show_about_dialog)
        main_menu.addAction(about_action)

        # Add separator
        main_menu.addSeparator()

        # "Settings..." action
        settings_action = QtGui.QAction("Settings...", self)
        settings_action.setShortcut("Ctrl+,")  # Default shortcut for macOS
        settings_action.triggered.connect(self.open_settings)
        main_menu.addAction(settings_action)

        # Add "Online" menu
        self.online_menu = self.menu_bar.addMenu("Online")
        self.online_menu.addAction(self.load_clublog_action)

    def show_about_dialog(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(f"About {GUI_LABEL_NAME}")
        dialog.setFixedWidth(400)

        layout = QtWidgets.QVBoxLayout(dialog)

        icon_path = os.path.join(CURRENT_DIR, "pounce.png")
        icon_label = QtWidgets.QLabel()
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

        program_name = QtWidgets.QLabel(f"<b>{GUI_LABEL_NAME}</b>")
        program_name.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        program_name.setStyleSheet("font-size: 14px;")
        layout.addWidget(program_name)

        version_label = QtWidgets.QLabel(f"Version: {CURRENT_VERSION_NUMBER}")
        version_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(version_label)

        first_separator = QtWidgets.QFrame()
        first_separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        first_separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        layout.addWidget(first_separator)

        discord_section = QtWidgets.QLabel(DISCORD_SECTION)
        discord_section.setOpenExternalLinks(True)
        discord_section.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(discord_section)

        layout.addStretch()

        thanks_label = QtWidgets.QLabel("With special thanks to:")
        thanks_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(thanks_label)

        thanks_names = QtWidgets.QLabel("Rick, DU6/PE1NSQ, Vincent F4BKV, Juan TG9AJR")
        thanks_names.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(thanks_names)

        current_year = datetime.now().year
        copyright_label = QtWidgets.QLabel(f'Copyright {current_year} Cédric Morelle <a href="https://qrz.com/db/f5ukw">F5UKW</a>')
        copyright_label.setOpenExternalLinks(True)
        copyright_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(copyright_label)

        layout.addStretch()

        second_separator = QtWidgets.QFrame()
        second_separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        second_separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        layout.addWidget(second_separator)

        donation_link = QtWidgets.QLabel(DONATION_SECTION)
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
            
            params.setdefault(band, {}).update({
                "monitored_callsigns"           : monitored_callsigns,
                "monitored_cq_zones"            : monitored_cq_zones,
                "excluded_callsigns"            : excluded_callsigns,
                "wanted_callsigns"              : wanted_callsigns
            })
        self.save_params(params)               

    def start_monitoring(self):
        self.status_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        self._running = True   

        self.network_check_status.start(self.network_check_status_interval)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_mode_timer)
        self.timer.start(200)

        self.update_status_button(STATUS_BUTTON_LABEL_MONITORING, STATUS_MONITORING_COLOR)

        self.blink_timer = QtCore.QTimer()
        self.blink_timer.timeout.connect(self.toggle_label_visibility)

        self.is_status_button_label_visible = True
        self.is_status_button_label_blinking = False

        self.stop_event.clear()
        self.focus_frame.hide()
        self.callsign_notice.hide()        

        self.apply_band_change(self.gui_selected_band)
        # Todo: We might need to move update_wanted_callsigns_history in apply_band_change
        self.update_wanted_callsigns_history(self.wanted_callsigns_vars[self.operating_band].text())
        self.update_current_callsign_highlight()
        
        params                              = self.load_params()
        local_ip_address                    = get_local_ip_address()

        freq_range_mode                     = params.get('freq_range_mode')
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

        params['freq_range_mode']           = freq_range_mode
        self.save_params(params)        

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
            enable_sending_reply,
            enable_gap_finder,
            enable_watchdog_bypass,
            enable_debug_output,
            enable_pounce_log,
            enable_log_packet_data          
        )
        self.worker.moveToThread(self.thread)

        if self.worker:
            self.worker.listener_started.connect(self.on_listener_started)

        # Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.error.connect(self.add_message_to_table)
        self.worker.error.connect(self.handle_worker_error)

        self.worker.message.connect(self.handle_message_received)

        self.thread.start()    

    def handle_worker_error(self, error_message):
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
        if self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()

    def stop_tray_icon(self):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None

    def stop_monitoring(self):
        self.network_check_status.stop()
        self.activity_bar.setValue(0) 
        
        if self.timer: 
            self.timer.stop()
            self.timer_value_label.setText(DEFAULT_MODE_TIMER_VALUE)        

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

            self.worker             = None
            self._running           = False
            self.operating_band     = None
            self.transmitting       = False
            
            self.stop_tray_icon()

            self.update_status_button(STATUS_BUTTON_LABEL_START, STATUS_COLOR_LABEL_OFF)
            self.status_button.resetStyle()
            self.status_button.setEnabled(True)
            self.stop_button.setEnabled(False)

            self.stop_blinking_status_button()
            self.update_tab_widget_labels_style()
            
            # self.callsign_notice.show()

            self.tab_widget.set_selected_tab(self.band_indices.get(self.operating_band))
            self.tab_widget.set_operating_tab(None)

            self.update_status_label_style(STATUS_COLOR_LABEL_SELECTED, "white")
            
            self.reset_window_title()

    def log_exception_to_file(self, filename, message):
        timestamp = datetime.now(timezone.utc).strftime("%y%m%d_%H%M%S")
        with open(filename, "a") as log_file:
            log_file.write(f"{timestamp} {message}\n")

def main():
    app             = QtWidgets.QApplication(sys.argv)
    updater         = Updater()
    update_timer    = QtCore.QTimer()

    update_timer.timeout.connect(updater.check_for_expiration_or_update)

    update_timer.setInterval(60 * 60 * 1_000)  
    update_timer.start()
    update_timer.timeout.emit()
    
    window          = MainApp()
    window.show()

    if is_first_launch_or_new_version(CURRENT_VERSION_NUMBER):
        window.show_about_dialog() 
        save_current_version(CURRENT_VERSION_NUMBER)

    app.aboutToQuit.connect(window.save_band_settings)        

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
