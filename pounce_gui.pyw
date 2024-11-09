# pounce_gui.pyw

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtMultimedia import QSound

import platform
import sys
import pickle
import os
import queue
import threading
import datetime
import re
import time
import pyperclip
import wait_and_pounce
import logging

from PIL import Image, ImageDraw
from utils import get_local_ip_address, get_log_filename, force_uppercase
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
    BG_COLOR_BLACK_ON_WHITE,
    FG_COLOR_BLACK_ON_WHITE,
    # Parameters
    PARAMS_FILE,
    POSITION_FILE,
    WANTED_CALLSIGNS_FILE,
    WANTED_CALLSIGNS_HISTORY_SIZE,
    # Labels
    GUI_LABEL_VERSION,
    RUNNING_TEXT_BUTTON,
    WAIT_POUNCE_LABEL,
    NOTHING_YET,
    WAITING_DATA_PACKETS_LABEL,
    WANTED_CALLSIGNS_HISTORY_LABEL,
    CALLSIGN_NOTICE_LABEL,
    # Modes
    MODE_FOX_HOUND,
    MODE_NORMAL,
    MODE_SUPER_FOX,
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
    DEFAULT_DELAY_BETWEEN_SOUND
    )

if platform.system() == 'Windows':
    from pystray import Icon, MenuItem

stop_event = threading.Event()

tray_icon = None

gui_queue = queue.Queue()
inputs_enabled = True

# PyQt equivalent of fonts in tkinter
courier_font                = QtGui.QFont("Courier", 10)
courier_font_bold           = QtGui.QFont("Courier", 12, QtGui.QFont.Bold)

if platform.system() == 'Windows':
    custom_font             = QtGui.QFont("Consolas", 12)
    custom_font_lg          = QtGui.QFont("Consolas", 18)
    custom_font_bold        = QtGui.QFont("Consolas", 12, QtGui.QFont.Bold)
elif platform.system() == 'Darwin':
    custom_font             = QtGui.QFont("Menlo", 14)
    custom_font_lg          = QtGui.QFont("Menlo", 18)
    custom_font_bold        = QtGui.QFont("Menlo", 12, QtGui.QFont.Bold)

class Worker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    message = pyqtSignal(object)

    def __init__(
            self,
            monitored_callsigns,
            excluded_callsigns,
            wanted_callsigns,
            mode,
            stop_event,
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
            enable_log_packet_data,
            enable_show_all_decoded                        
        ):
        super(Worker, self).__init__()
        self.monitored_callsigns            = monitored_callsigns
        self.excluded_callsigns             = excluded_callsigns
        self.wanted_callsigns               = wanted_callsigns
        self.mode                           = mode
        self.stop_event                     = stop_event
        self.primary_udp_server_address     = primary_udp_server_address
        self.primary_udp_server_port        = primary_udp_server_port
        self.secondary_udp_server_address   = secondary_udp_server_address
        self.secondary_udp_server_port      = secondary_udp_server_port
        self.enable_secondary_udp_server    = enable_secondary_udp_server
        self.enable_sending_reply           = enable_sending_reply
        self.enable_gap_finder               = enable_gap_finder
        self.enable_watchdog_bypass         = enable_watchdog_bypass
        self.enable_debug_output            = enable_debug_output
        self.enable_pounce_log              = enable_pounce_log   
        self.enable_log_packet_data         = enable_log_packet_data
        self.enable_show_all_decoded        = enable_show_all_decoded     

    def run(self):
        try:
            wait_and_pounce.main(
                self.monitored_callsigns,
                self.excluded_callsigns,
                self.wanted_callsigns,
                self.mode,
                self.stop_event,
                primary_udp_server_address      = self.primary_udp_server_address,
                primary_udp_server_port         = self.primary_udp_server_port,
                secondary_udp_server_address    = self.secondary_udp_server_address,
                secondary_udp_server_port       = self.secondary_udp_server_port,
                enable_secondary_udp_server     = self.enable_secondary_udp_server,
                enable_sending_reply            = self.enable_sending_reply,
                enable_gap_finder                = self.enable_gap_finder,
                enable_watchdog_bypass          = self.enable_watchdog_bypass,
                enable_debug_output             = self.enable_debug_output,
                enable_pounce_log               = self.enable_pounce_log,    
                enable_log_packet_data          = self.enable_log_packet_data,
                enable_show_all_decoded         = self.enable_show_all_decoded,            
                message_callback                = self.message.emit
            )
        except Exception as e:
            error_message = f"Erreur lors de l'exécution du script : {e}"
            self.error.emit(error_message)
        finally:
            self.finished.emit()


class TrayIcon:
    def __init__(self):
        self.color1 = FG_COLOR_REGULAR_FOCUS
        self.color2 = BG_COLOR_REGULAR_FOCUS
        self.current_color = self.color1
        self.icon = None
        self.blink_thread = None
        self._running = False

    def create_icon(self, color, size=(64, 64)):
        img = Image.new('RGB', size, color)
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, size[0], size[1]], fill=color)
        return img

    def blink_icon(self):
        while self._running:
            self.icon.icon = self.create_icon(self.current_color)
            self.icon.update_menu()
            self.current_color = self.color2 if self.current_color == self.color1 else self.color1
            time.sleep(1)

    def quit_action(self, icon):
        self._running = False
        icon.stop()

    def start(self):
        self._running = True
        self.icon = Icon('Pounce Icon', self.create_icon(self.color1))

        self.blink_thread = threading.Thread(target=self.blink_icon, daemon=True)
        self.blink_thread.start()

        self.icon.run()

    def stop(self):
        self._running = False
        if self.icon:
            self.icon.stop()


class ToolTip(QtWidgets.QWidget):
    def __init__(self, widget, text=''):
        super().__init__()
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.installEventFilter(self)

        QtWidgets.QToolTip.setFont(custom_font)

    def eventFilter(self, obj, event):
        if obj == self.widget:
            if event.type() == QtCore.QEvent.Enter:
                self.show_tooltip()
            elif event.type() == QtCore.QEvent.Leave:
                self.hide_tooltip()
        return super().eventFilter(obj, event)

    def show_tooltip(self):
        self.text = self.widget.text().replace(",", "<br/>")
        if not self.text:
            return
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), self.text, self.widget)

    def hide_tooltip(self):
        QtWidgets.QToolTip.hideText()


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, params=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(750, 900)
        if platform.system() == 'Windows':
            self.setWindowIcon(QtGui.QIcon("pounce.ico"))

        self.params = params or {}

        layout = QtWidgets.QVBoxLayout(self)

        small_font = QtGui.QFont()
        small_font.setPointSize(11)  

        jtdx_notice_text = (
            "For JTDX users, you have to disable automatic logging of QSO (Make sure <u>Settings > Reporting > Logging > Enable automatic logging of QSO</u> is unchecked)<br /><br />You might also need to accept UDP Reply messages from any messages (<u>Misc Menu > Accept UDP Reply Messages > any messages</u>)."
        )
        jtdx_notice_label = QtWidgets.QLabel(jtdx_notice_text)
        jtdx_notice_label.setWordWrap(True)
        jtdx_notice_label.setFont(small_font)
        jtdx_notice_label.setStyleSheet("background-color: #f6f6f5; padding: 5px; font-size: 12px;")
        jtdx_notice_label.setTextFormat(QtCore.Qt.RichText)

        primary_group = QtWidgets.QGroupBox("Primary UDP Server")
        primary_layout = QtWidgets.QGridLayout()

        self.primary_udp_server_address = QtWidgets.QLineEdit()
        self.primary_udp_server_port = QtWidgets.QLineEdit()

        primary_layout.addWidget(QtWidgets.QLabel("UDP Server:"), 0, 0, QtCore.Qt.AlignLeft)
        primary_layout.addWidget(self.primary_udp_server_address, 0, 1)
        primary_layout.addWidget(QtWidgets.QLabel("UDP Server port number:"), 1, 0, QtCore.Qt.AlignLeft)
        primary_layout.addWidget(self.primary_udp_server_port, 1, 1)

        primary_group.setLayout(primary_layout)

        secondary_group = QtWidgets.QGroupBox("Second UDP Server (Send logged QSO ADIF data)")
        secondary_layout = QtWidgets.QGridLayout()

        self.secondary_udp_server_address = QtWidgets.QLineEdit()
        self.secondary_udp_server_port = QtWidgets.QLineEdit()

        self.enable_secondary_udp_server = QtWidgets.QCheckBox("Enable sending to secondary UDP server")
        self.enable_secondary_udp_server.setChecked(DEFAULT_SECONDARY_UDP_SERVER)

        secondary_layout.addWidget(QtWidgets.QLabel("UDP Server:"), 0, 0, QtCore.Qt.AlignLeft)
        secondary_layout.addWidget(self.secondary_udp_server_address, 0, 1)
        secondary_layout.addWidget(QtWidgets.QLabel("UDP Server port number:"), 1, 0, QtCore.Qt.AlignLeft)
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
        
        udp_settings_widget.setStyleSheet(f"background-color: {BG_COLOR_FOCUS_MY_CALL}; color: {FG_COLOR_FOCUS_MY_CALL};")
        udp_settings_group.setLayout(QtWidgets.QVBoxLayout())
        udp_settings_group.layout().setContentsMargins(0, 0, 0, 0)
        udp_settings_group.layout().addWidget(udp_settings_widget)

        sound_notice_text = (
            "You can enable or disable the sounds as per your requirement. You can even set a delay between each sound triggered by a message where a monitored callsign has been found. This mainly helps you to be notified when the band opens or when you have a callsign on the air that you want to monitor.<br /><br />Monitored callsigns will never get reply from this program. Only <u>Wanted callsigns will get a reply</u>."
        )
    
        sound_notice_label = QtWidgets.QLabel(sound_notice_text)
        sound_notice_label.setStyleSheet("background-color: #f6f6f5; padding: 5px; font-size: 12px;")
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

        sound_settings_layout.addWidget(QtWidgets.QLabel("Delay between each monitored callsigns detected:"), 4, 0, QtCore.Qt.AlignLeft)
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
        
        self.enable_show_all_decoded = QtWidgets.QCheckBox("Show all decoded messages, not only Wanted Callsigns")
        self.enable_show_all_decoded.setChecked(DEFAULT_SHOW_ALL_DECODED)
    
        log_settings_layout.addWidget(self.enable_pounce_log, 0, 0, 1, 2)
        log_settings_layout.addWidget(self.enable_log_packet_data, 1, 0, 1, 2)        
        log_settings_layout.addWidget(self.enable_debug_output, 2, 0, 1, 2)        
        log_settings_layout.addWidget(self.enable_show_all_decoded, 3, 0, 1, 2)

        log_settings_group.setLayout(log_settings_layout)

        self.load_params()

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
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
            self.params.get('primary_udp_server_address', local_ip_address)
        )
        self.primary_udp_server_port.setText(
            str(self.params.get('primary_udp_server_port', DEFAULT_UDP_PORT))
        )
        self.secondary_udp_server_address.setText(
            self.params.get('secondary_udp_server_address', local_ip_address)
        )
        self.secondary_udp_server_port.setText(
            str(self.params.get('secondary_udp_server_port', DEFAULT_UDP_PORT))
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

class EditWantedDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, initial_value="", title="Edit Wanted Callsigns"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(400, 200)

        layout = QtWidgets.QVBoxLayout(self)

        label = QtWidgets.QLabel("Wanted Callsign(s) (Comma separated list):")
        layout.addWidget(label)

        self.entry = QtWidgets.QTextEdit()
        self.entry.setAcceptRichText(False)
        self.entry.setText(initial_value)
        self.entry.textChanged.connect(lambda: force_uppercase(self.entry))
        layout.addWidget(self.entry)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    def get_result(self):
        text = self.entry.toPlainText().strip()
        callsigns = [call.strip() for call in text.split(",") if call.strip()]
        sorted_callsigns = sorted(callsigns)
        return ",".join(sorted_callsigns)

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

        self.stop_event = threading.Event()
        self.error_occurred.connect(self.show_error_message)
        self.message_received.connect(self.handle_message_received)
        self._running = False

        self.connection_check_timer = QtCore.QTimer()
        self.connection_check_timer.timeout.connect(self.check_connection_status)

        self.decode_packet_count                = 0
        self.last_decode_packet_time            = None
        self.last_heartbeat_time                = None
        self.last_sound_played_time             = datetime.datetime.min

        self.wanted_callsign_detected_sound     = QSound(f"{CURRENT_DIR}/sounds/495650__matrixxx__supershort-ping-or-short-notification.wav")
        self.directed_to_my_call_sound          = QSound(f"{CURRENT_DIR}/sounds/716445__scottyd0es__tone12_error.wav")
        self.ready_to_log_sound                 = QSound(f"{CURRENT_DIR}/sounds/709072__scottyd0es__aeroce-dualtone-5.wav")
        self.error_occurred_sound               = QSound(f"{CURRENT_DIR}/sounds/142608__autistic-lucario__error.wav")
        self.monitored_callsign_detected_sound  = QSound(f"{CURRENT_DIR}/sounds/716442__scottyd0es__tone12_alert_3.wav")

        self.setGeometry(100, 100, 900, 700)
        self.base_title = GUI_LABEL_VERSION
        self.setWindowTitle(self.base_title)
        
        # Main layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QGridLayout()
        central_widget.setLayout(main_layout)

        # Variables
        self.wanted_callsigns_var = QtWidgets.QLineEdit()
        self.monitored_callsigns_var = QtWidgets.QLineEdit()
        self.excluded_callsigns_var = QtWidgets.QLineEdit()

        # Mode buttons (radio buttons)
        self.special_mode_var = QtWidgets.QButtonGroup()

        radio_normal = QtWidgets.QRadioButton(MODE_NORMAL)
        radio_foxhound = QtWidgets.QRadioButton(MODE_FOX_HOUND)
        radio_superfox = QtWidgets.QRadioButton(MODE_SUPER_FOX)

        self.special_mode_var.addButton(radio_normal)
        self.special_mode_var.addButton(radio_foxhound)
        self.special_mode_var.addButton(radio_superfox)

        radio_normal.setChecked(True)
            
        self.text_formats = {
            'black_on_purple'   : QtGui.QTextCharFormat(),
            'black_on_white'    : QtGui.QTextCharFormat(),
            'black_on_yellow'   : QtGui.QTextCharFormat(),
            'white_on_blue'     : QtGui.QTextCharFormat(),
            'bright_for_my_call': QtGui.QTextCharFormat()      
        }

        self.text_formats['black_on_purple'].setForeground(QtGui.QBrush(QtGui.QColor(FG_COLOR_BLACK_ON_PURPLE)))
        self.text_formats['black_on_purple'].setBackground(QtGui.QBrush(QtGui.QColor(BG_COLOR_BLACK_ON_PURPLE)))

        self.text_formats['black_on_white'].setForeground(QtGui.QBrush(QtGui.QColor(FG_COLOR_BLACK_ON_WHITE)))
        self.text_formats['black_on_white'].setBackground(QtGui.QBrush(QtGui.QColor(BG_COLOR_BLACK_ON_WHITE)))

        self.text_formats['black_on_yellow'].setForeground(QtGui.QBrush(QtGui.QColor(FG_COLOR_BLACK_ON_YELLOW)))
        self.text_formats['black_on_yellow'].setBackground(QtGui.QBrush(QtGui.QColor(BG_COLOR_BLACK_ON_YELLOW)))

        self.text_formats['white_on_blue'].setForeground(QtGui.QBrush(QtGui.QColor(FG_COLOR_WHITE_ON_BLUE)))
        self.text_formats['white_on_blue'].setBackground(QtGui.QBrush(QtGui.QColor(BG_COLOR_WHITE_ON_BLUE)))

        self.text_formats['bright_for_my_call'].setForeground(QtGui.QBrush(QtGui.QColor(FG_COLOR_FOCUS_MY_CALL)))
        self.text_formats['bright_for_my_call'].setBackground(QtGui.QBrush(QtGui.QColor(BG_COLOR_FOCUS_MY_CALL)))

        params = self.load_params()

        self.wanted_callsigns_history = self.load_wanted_callsigns()

        self.monitored_callsigns_var.setText(params.get("monitored_callsigns", ""))
        self.excluded_callsigns_var.setText(params.get("excluded_callsigns", ""))
        self.wanted_callsigns_var.setText(params.get("wanted_callsigns", ""))

        special_mode = params.get("special_mode", "Normal")
        if special_mode == "Normal":
            radio_normal.setChecked(True)
        elif special_mode == "Fox/Hound":
            radio_foxhound.setChecked(True)
        elif special_mode == "SuperFox":
            radio_superfox.setChecked(True)

        # Signals
        self.wanted_callsigns_var.textChanged.connect(lambda: force_uppercase(self.wanted_callsigns_var))
        self.wanted_callsigns_var.textChanged.connect(self.check_fields)

        self.monitored_callsigns_var.textChanged.connect(lambda: force_uppercase(self.monitored_callsigns_var))
        self.monitored_callsigns_var.textChanged.connect(self.check_fields)

        self.excluded_callsigns_var.textChanged.connect(lambda: force_uppercase(self.excluded_callsigns_var))
        self.excluded_callsigns_var.textChanged.connect(self.check_fields)

        # Wanted callsigns label
        self.wanted_callsigns_label = QtWidgets.QLabel(WANTED_CALLSIGNS_HISTORY_LABEL % len(self.wanted_callsigns_history))

        # Listbox (wanted callsigns)
        self.listbox = QtWidgets.QListWidget()
        self.listbox.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.listbox.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.listbox.itemClicked.connect(self.on_listbox_select)

        # Context menu for listbox
        self.listbox.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.listbox.customContextMenuRequested.connect(self.on_right_click)

        main_layout.addWidget(self.wanted_callsigns_label, 1, 2, 1, 2)
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
        self.focus_value_label.setFont(custom_font_lg)
        self.focus_value_label.setStyleSheet("padding: 10px;")
        self.focus_frame_layout.addWidget(self.focus_value_label)
        self.focus_frame.hide()
        self.focus_value_label.mousePressEvent = self.copy_to_clipboard

        # Timer value
        self.timer_value_label = QtWidgets.QLabel("00:00:00")
        self.timer_value_label.setFont(custom_font_lg)
        self.timer_value_label.setStyleSheet("background-color: #9dfffe; color: #555bc2; padding: 10px;")

        # Log analysis label and value
        self.counter_value_label = QtWidgets.QLabel(NOTHING_YET)
        self.counter_value_label.setFont(custom_font)
        self.counter_value_label.setIndent(5)
        self.counter_value_label.setStyleSheet("background-color: #D3D3D3;")

        # Log and clear button
        self.output_text = QtWidgets.QTextEdit(self)
        self.output_text.setFont(custom_font)
        self.output_text.setStyleSheet("background-color: #FFFFFF; ")
        self.output_text.setReadOnly(True)

        self.clear_button = QtWidgets.QPushButton("Clear Log")
        self.clear_button.setEnabled(False)
        self.clear_button.clicked.connect(self.clear_output_text)

        self.settings = QtWidgets.QPushButton("Settings")
        self.settings.clicked.connect(self.open_settings)

        self.disable_alert_checkbox = QtWidgets.QCheckBox("Disable all Sounds")
        self.disable_alert_checkbox.setChecked(False)
        self.disable_alert_checkbox.stateChanged.connect(self.update_alert_label_style)

        self.quit_button = QtWidgets.QPushButton("Quit")
        self.quit_button.clicked.connect(self.quit_application)

        if platform.system() == 'Darwin':
            self.restart_button = QtWidgets.QPushButton("Restart")
            self.restart_button.clicked.connect(self.restart_application)

        # Timer and start/stop buttons
        self.run_button = QtWidgets.QPushButton(WAIT_POUNCE_LABEL)
        self.run_button.clicked.connect(self.start_monitoring)
        self.stop_button = QtWidgets.QPushButton("Stop all")
        self.stop_button.clicked.connect(self.stop_monitoring)

        # Organize UI components
        main_layout.addWidget(self.focus_frame, 0, 0, 1, 4)

        self.callsign_notice = QtWidgets.QLabel(CALLSIGN_NOTICE_LABEL)
        self.callsign_notice.setStyleSheet("background-color: #9dfffe; color: #555bc2;")
    
        main_layout.addWidget(self.callsign_notice, 1, 1)

        self.wanted_label = QtWidgets.QLabel("Wanted Callsign(s):")
        self.monitored_label = QtWidgets.QLabel("Monitored Callsign(s):")
        self.excluded_label = QtWidgets.QLabel("Excluded Callsign(s):")

        main_layout.addWidget(self.wanted_label, 2, 0)
        main_layout.addWidget(self.wanted_callsigns_var, 2, 1)
        main_layout.addWidget(self.monitored_label, 3, 0)
        main_layout.addWidget(self.monitored_callsigns_var, 3, 1)
        main_layout.addWidget(self.excluded_label, 4, 0)
        main_layout.addWidget(self.excluded_callsigns_var, 4, 1)

        # Mode section
        mode_layout = QtWidgets.QHBoxLayout()
        mode_layout.addWidget(radio_normal)
        mode_layout.addWidget(radio_foxhound)
        mode_layout.addWidget(radio_superfox)
        main_layout.addLayout(mode_layout, 5, 1)

        # Timer label and log analysis
        main_layout.addWidget(self.timer_value_label, 0, 3)
        main_layout.addWidget(QtWidgets.QLabel("Status:"), 7, 0)
        main_layout.addWidget(self.counter_value_label, 7, 1)

        main_layout.addWidget(self.run_button, 7, 2)
        main_layout.addWidget(self.stop_button, 7, 3)

        # Add output text and buttons
        main_layout.addWidget(self.output_text, 8, 0, 1, 4)

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

        main_layout.addLayout(bottom_layout, 9, 0, 1, 4)

        # Timer to update time every second
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_timer_with_ft8_sequence)
        self.timer.start(200)

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

        self.check_fields()
        self.load_window_position()

        # Close event to save position
        self.closeEvent = self.on_close

    @QtCore.pyqtSlot(str)
    def show_error_message(self, message):
        self.append_output_text(f"[red_on_grey]{message}[/red_on_grey]\n")

    @QtCore.pyqtSlot(object)
    def handle_message_received(self, message):
        if isinstance(message, dict):
            message_type = message.get('type')
            if message_type == 'update_status':
                self.check_connection_status(
                    message.get('decode_packet_count', 0),
                    message.get('last_decode_packet_time'),
                    message.get('last_heartbeat_time')
                )
            else:
                formatted_message = message.get('formatted_message')
                if formatted_message is not None:                    
                    contains_my_call = message.get('contains_my_call')                        
                    self.update_focus_frame(formatted_message, contains_my_call)                            
                
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
                    elif message_type == 'monitored_callsign_detected' and self.enable_sound_monitored_callsigns:
                        current_time = datetime.datetime.now()
                        delay = 600                   
                        if (current_time - self.last_sound_played_time).total_seconds() > delay:                                                 
                            play_sound = True
                            self.last_sound_played_time = current_time               
                
                if play_sound:
                    self.play_sound(message_type)
    
        else:
            # Use this to handle window title update
            if isinstance(message, str) and message.startswith("wsjtx_id:"):
                wsjtx_id = message.split("wsjtx_id:")[1].strip()
                self.update_window_title(wsjtx_id)
            else:
                self.append_output_text(str(message) + "\n")

    def update_window_title(self, wsjtx_id):
            new_title = f"{self.base_title} - Connected to {wsjtx_id}"
            self.setWindowTitle(new_title)

    def reset_window_title(self):
        self.setWindowTitle(self.base_title)               

    def play_sound(self, sound_name):
        # Todo: add delay to settings
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

    def update_focus_frame(self, formatted_message, contains_my_call):
        self.focus_value_label.setText(formatted_message)
        if contains_my_call:
            bg_color_hex = BG_COLOR_FOCUS_MY_CALL
            fg_color_hex = FG_COLOR_FOCUS_MY_CALL
        else:
            bg_color_hex = BG_COLOR_REGULAR_FOCUS
            fg_color_hex = FG_COLOR_REGULAR_FOCUS
            
        self.focus_value_label.setStyleSheet(f"background-color: {bg_color_hex}; color: {fg_color_hex}; padding: 10px;")
        self.focus_frame.show()

    def check_connection_status(
        self,
        decode_packet_count=None,
        last_decode_packet_time=None,
        last_heartbeat_time=None
    ):
        if decode_packet_count is not None:
            self.decode_packet_count = decode_packet_count
        if last_decode_packet_time is not None:
            self.last_decode_packet_time = last_decode_packet_time
        if last_heartbeat_time is not None:
            self.last_heartbeat_time = last_heartbeat_time

        now = datetime.datetime.now()
        connection_lost = False

        status_text_array = []
        status_text_array.append(f"DecodePackets: #{self.decode_packet_count}")

        HEARTBEAT_TIMEOUT_THRESHOLD = 30  # secondes
        DECODE_PACKET_TIMEOUT_THRESHOLD = 60  # secondes

        if self.last_decode_packet_time:
            time_since_last_decode = (now - self.last_decode_packet_time).total_seconds()
            if time_since_last_decode > DECODE_PACKET_TIMEOUT_THRESHOLD:
                status_text_array.append(f"No DecodePacket for more than {DECODE_PACKET_TIMEOUT_THRESHOLD} seconds.")
                connection_lost = True
            else:
                status_text_array.append(f"Last DecodePacket {int(time_since_last_decode)} seconds ago.")
        else:
            status_text_array.append("No DecodePacket received yet.")

        if self.last_heartbeat_time:
            time_since_last_heartbeat = (now - self.last_heartbeat_time).total_seconds()
            if time_since_last_heartbeat > HEARTBEAT_TIMEOUT_THRESHOLD:
                status_text_array.append(f"No HeartBeat for more than {HEARTBEAT_TIMEOUT_THRESHOLD} seconds.")
                connection_lost = True
            else:
                last_heartbeat_str = self.last_heartbeat_time.strftime('%Y-%m-%d %H:%M:%S')
                status_text_array.append(f"Last HeartBeat @ {last_heartbeat_str}")
        else:
            status_text_array.append("No HeartBeat received yet.")

        self.counter_value_label.setText('\n'.join(status_text_array))

        if connection_lost:
            self.counter_value_label.setStyleSheet("background-color: red; color: white;")
            if not self.connection_lost_shown:
                self.connection_lost_shown = True
        else:
            self.connection_lost_shown = False
            self.counter_value_label.setStyleSheet("background-color: yellow; color: black;")              

    def on_close(self, event):
        self.save_window_position()
        if self._running:
            self.stop_monitoring()
        event.accept()

    def open_settings(self):
        params = self.load_params()

        dialog = SettingsDialog(self, params)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_params = dialog.get_result()
        
            previous_enable_pounce_log = self.enable_pounce_log
            self.enable_pounce_log = new_params.get('enable_pounce_log', True)

            params.update(new_params)
            self.save_params(params)

            log_filename = get_log_filename()

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

    def check_fields(self):
        if self.wanted_callsigns_var.text():
            self.run_button.setEnabled(True)
        else:
            self.run_button.setEnabled(False)

    def update_alert_label_style(self):
        if self.disable_alert_checkbox.isChecked():
            self.disable_alert_checkbox.setStyleSheet("background-color: #ff8888;")
        else:
            self.disable_alert_checkbox.setStyleSheet("")

    def disable_inputs(self):
        global inputs_enabled
        inputs_enabled = False
        self.monitored_callsigns_var.setEnabled(False)
        self.excluded_callsigns_var.setEnabled(False)
        self.wanted_callsigns_var.setEnabled(False)

    def enable_inputs(self):
        global inputs_enabled
        inputs_enabled = True
        self.monitored_callsigns_var.setEnabled(True)
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
        self.wanted_callsigns_label.setText(WANTED_CALLSIGNS_HISTORY_LABEL % len(self.wanted_callsigns_history))

    def on_listbox_select(self):
        if not inputs_enabled:
            return
        selected_item = self.listbox.currentItem()
        if selected_item:
            selected_callsign = selected_item.text()
            self.wanted_callsigns_var.setText(selected_callsign)

    def on_right_click(self, position):
        menu = QtWidgets.QMenu()
        remove_action = menu.addAction("Remove")
        edit_action = menu.addAction("Edit")

        action = menu.exec_(self.listbox.mapToGlobal(position))
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
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
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

    def append_output_text(self, text):
        cursor = self.output_text.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)

        pattern = re.compile(r'\[(\/?[a-zA-Z_]+)\]')
        lines = text.split('\n')

        for index, line in enumerate(lines):
            if index > 0:
                cursor.insertBlock()

            block_format = cursor.blockFormat()
            block_format.setTopMargin(0)
            block_format.setBottomMargin(0)
            cursor.setBlockFormat(block_format)

            pos = 0
            current_format = QtGui.QTextCharFormat()

            while True:
                match = pattern.search(line, pos)
                if not match:
                    text_to_insert = line[pos:]
                    cursor.insertText(text_to_insert, current_format)
                    break
                else:
                    start, end = match.span()
                    tag = match.group(1)
                    cursor.insertText(line[pos:start], current_format)
                    pos = end  

                    if tag.startswith('/'):
                        current_format = QtGui.QTextCharFormat()
                    else:
                        format = self.text_formats.get(tag)
                        if format:
                            current_format = format
                            current_format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
                        else:                    
                            pass

        cursor.movePosition(QtGui.QTextCursor.End)
        self.output_text.setTextCursor(cursor)
        self.output_text.ensureCursorVisible()
        self.clear_button.setEnabled(True)

    def clear_output_text(self):
        self.output_text.clear()
        self.clear_button.setEnabled(False)

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

    def update_timer_with_ft8_sequence(self):
        current_time = datetime.datetime.utcnow()
        utc_time = current_time.strftime("%H:%M:%S")

        if (current_time.second // 15) % 2 == 0:
            background_color = EVEN_COLOR
        else:
            background_color = ODD_COLOR

        self.timer_value_label.setText(utc_time)
        self.timer_value_label.setStyleSheet(f"background-color: {background_color}; color: #3d25fb; padding: 10px;")

    def start_monitoring(self):
        global tray_icon

        self.connection_check_timer.start(5_000)

        # self.output_text.clear()
        self.run_button.setEnabled(False)
        self.run_button.setText(RUNNING_TEXT_BUTTON)
        self.run_button.setStyleSheet("background-color: red; color: #ffffff")
        self.disable_inputs()
        self.stop_event.clear()
        self.focus_frame.hide()
        self.callsign_notice.hide()

        # For decorative purpose only and to match with color being used on output_text 
        self.wanted_label.setStyleSheet(f"background-color: {BG_COLOR_BLACK_ON_YELLOW}; color: {FG_COLOR_BLACK_ON_YELLOW};")
        self.monitored_label.setStyleSheet(f"background-color: {BG_COLOR_BLACK_ON_PURPLE}; color: {FG_COLOR_BLACK_ON_PURPLE};")

        if platform.system() == 'Windows':
            tray_icon = TrayIcon()
            tray_icon_thread = threading.Thread(target=tray_icon.start, daemon=True)
            tray_icon_thread.start()

        monitored_callsigns                 = self.monitored_callsigns_var.text()
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
        enable_show_all_decoded             = params.get('enable_show_all_decoded', DEFAULT_SHOW_ALL_DECODED)

        self.update_wanted_callsigns_history(wanted_callsigns)

        params.update({
            "monitored_callsigns"           : monitored_callsigns,
            "excluded_callsigns"            : excluded_callsigns,
            "wanted_callsigns"              : wanted_callsigns,
            "special_mode"                  : special_mode
        })
        self.save_params(params)

        self.counter_value_label.setText(WAITING_DATA_PACKETS_LABEL)    
        self.counter_value_label.setStyleSheet("background-color: yellow; color: black;")

        # Create a QThread and a Worker object
        self.thread = QThread()
        self.worker = Worker(
            monitored_callsigns,
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
            enable_log_packet_data,
            enable_show_all_decoded            
        )
        self.worker.moveToThread(self.thread)

        # Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # Connect worker's signals to the GUI slots
        # self.worker.finished.connect(self.stop_monitoring)
        self.worker.error.connect(self.show_error_message)
        self.worker.message.connect(self.handle_message_received)

        self.thread.start()
        self._running = True


    def stop_monitoring(self):
        global tray_icon

        self.connection_check_timer.stop()

        if tray_icon:
            tray_icon.stop()
            tray_icon = None

        if self._running:
            self.stop_event.set()

            if hasattr(self, 'thread') and self.thread.isRunning():
                self.thread.quit()
                self.thread.wait()
                self.thread = None

            self.worker = None
            self._running = False

            self.run_button.setEnabled(True)
            self.run_button.setText(WAIT_POUNCE_LABEL)
            self.run_button.setStyleSheet("")

            self.wanted_label.setStyleSheet("")
            self.monitored_label.setStyleSheet("")

            self.callsign_notice.show()

            self.counter_value_label.setStyleSheet("background-color: #D3D3D3;")
            self.enable_inputs()
            self.reset_window_title()

    def log_exception_to_file(self, filename, message):
        timestamp = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
        with open(filename, "a") as log_file:
            log_file.write(f"{timestamp} {message}\n")

def check_expiration():
    current_date = datetime.datetime.now()
    if current_date > EXPIRATION_DATE:
        app = QtWidgets.QApplication(sys.argv)
        
        expiration_date_str = EXPIRATION_DATE.strftime('%B %d, %Y')

        msg_box = QtWidgets.QMessageBox()
        msg_box.setWindowTitle("Program Expired")

        label = QtWidgets.QLabel(f"{GUI_LABEL_VERSION} expired on <u>{expiration_date_str}</u>. Please contact author.")
        small_font = QtGui.QFont()
        small_font.setPointSize(12)  
        label.setFont(small_font)
        label.setTextFormat(QtCore.Qt.RichText)
        
        msg_box.setText("")
        msg_box.layout().addWidget(label, 0, 1)
        
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg_box.resize(450, 650)
        msg_box.exec_()
        sys.exit()

def main():
    check_expiration()

    app = QtWidgets.QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
