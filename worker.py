# worker.py

import traceback
import inspect

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from wsjtx_listener import Listener
from utils import get_local_ip_address
from logger import get_logger

log     = get_logger(__name__)

from constants import (
    DEFAULT_UDP_PORT,
    DEFAULT_SECONDARY_UDP_SERVER,
    DEFAULT_SENDING_REPLY,
    DEFAULT_POLITE_REPLY,
    DEFAULT_REPLY_ATTEMPTS,
    DEFAULT_MAX_WAITING_DELAY,
    DEFAULT_LOG_ALL_VALID_CONTACT,
    DEFAULT_GAP_FINDER,
    DEFAULT_WATCHDOG_BYPASS,
    DEFAULT_DEBUG_OUTPUT,
    DEFAULT_POUNCE_LOG,
    DEFAULT_LOG_PACKET_DATA,
    DEFAULT_MINIMUM_REPORT,
    DEFAULT_JTDX_CLICK_PROMPT_LOG_QSO,
    WKB4_REPLY_MODE_ALWAYS,
    FREQ_MINIMUM,
    FREQ_MAXIMUM
)

class Worker(QObject):
    finished                         = pyqtSignal()
    error                           = pyqtSignal(str)
    listener_started                = pyqtSignal()
    message                         = pyqtSignal(object)
    update_listener_settings_signal = pyqtSignal()
    show_listener_settings_signal   = pyqtSignal()
    synch_settings_signal           = pyqtSignal()
    reset_settings_signal           = pyqtSignal()

    def __init__(
            self,
            monitoring_settings,
            stop_event,
            min_freq                           = FREQ_MINIMUM,
            max_freq                           = FREQ_MAXIMUM,
            primary_udp_server_address         = None,
            primary_udp_server_port            = None,
            secondary_udp_server_address       = None,
            secondary_udp_server_port          = None,
            enable_secondary_udp_server        = DEFAULT_SECONDARY_UDP_SERVER,
            logging_udp_server_address         = None,
            logging_udp_server_port            = None,
            enable_logging_udp_server          = DEFAULT_SECONDARY_UDP_SERVER,
            enable_sending_reply               = DEFAULT_SENDING_REPLY,
            enable_polite_reply                = DEFAULT_POLITE_REPLY,
            max_reply_attempts_to_callsign     = DEFAULT_REPLY_ATTEMPTS,
            max_working_delay                  = DEFAULT_MAX_WAITING_DELAY,
            enable_log_all_valid_contact       = DEFAULT_LOG_ALL_VALID_CONTACT,
            enable_reply_to_valid_callsign     = DEFAULT_LOG_ALL_VALID_CONTACT,
            enable_reply_to_valid_direction    = DEFAULT_LOG_ALL_VALID_CONTACT,
            enable_reply_to_lotw_only          = False,
            enable_gap_finder                  = DEFAULT_GAP_FINDER,
            enable_watchdog_bypass             = DEFAULT_WATCHDOG_BYPASS,
            enable_jtdx_click_log_qso          = DEFAULT_JTDX_CLICK_PROMPT_LOG_QSO,
            enable_debug_output                = DEFAULT_DEBUG_OUTPUT,
            enable_pounce_log                  = DEFAULT_POUNCE_LOG,
            enable_log_packet_data             = DEFAULT_LOG_PACKET_DATA,
            adif_file_paths                    = None,
            adif_worked_backup_file_path       = None,
            worked_before_preference           = WKB4_REPLY_MODE_ALWAYS,
            marathon_preference                = None,
            grid_tracker_preference            = None,
            enable_grid_reply_new_grid         = False,
            enable_grid_reply_unconfirmed      = False,
            minimum_report_for_reply           = DEFAULT_MINIMUM_REPORT,
            priority_order                     = None,
            enable_club_log_synch              = False,
            club_log_email                     = '',
            club_log_password                  = '',
            club_log_callsign                  = '',
            enable_lotw_upload                 = False,
            lotw_username                      = '',
            lotw_password                      = '',
            lotw_location                      = '',
            lotw_signing_password              = '',
            tqsl_path                          = '',
            tqsl_dir                           = ''
        ):

        super().__init__()

        self.update_listener_settings_signal.connect(self.update_listener_settings)
        self.show_listener_settings_signal.connect(self.show_listener_settings)
        self.synch_settings_signal.connect(self.synch_settings)
        self.reset_settings_signal.connect(self.reset_synched_settings)

        local_ip                                = get_local_ip_address()

        self.listener                           = None
        self.stop_event                         = stop_event

        self.min_freq                           = min_freq
        self.max_freq                           = max_freq
        self.monitoring_settings                = monitoring_settings

        self.primary_udp_server_address         = primary_udp_server_address or local_ip
        self.primary_udp_server_port            = primary_udp_server_port or DEFAULT_UDP_PORT

        self.secondary_udp_server_address       = secondary_udp_server_address or local_ip
        self.secondary_udp_server_port          = secondary_udp_server_port or DEFAULT_UDP_PORT
        self.enable_secondary_udp_server        = enable_secondary_udp_server

        self.logging_udp_server_address         = logging_udp_server_address or local_ip
        self.logging_udp_server_port            = logging_udp_server_port or DEFAULT_UDP_PORT
        self.enable_logging_udp_server          = enable_logging_udp_server

        self.enable_sending_reply               = enable_sending_reply
        self.enable_polite_reply                = enable_polite_reply
        self.max_reply_attempts_to_callsign     = max_reply_attempts_to_callsign
        self.max_working_delay                  = max_working_delay
        self.enable_log_all_valid_contact       = enable_log_all_valid_contact
        self.enable_reply_to_valid_callsign     = enable_reply_to_valid_callsign
        self.enable_reply_to_valid_direction    = enable_reply_to_valid_direction
        self.enable_reply_to_lotw_only          = enable_reply_to_lotw_only
        self.enable_gap_finder                  = enable_gap_finder
        self.enable_watchdog_bypass             = enable_watchdog_bypass
        self.enable_jtdx_click_log_qso          = enable_jtdx_click_log_qso
        self.enable_debug_output                = enable_debug_output
        self.enable_pounce_log                  = enable_pounce_log
        self.enable_log_packet_data             = enable_log_packet_data

        self.adif_file_paths                    = adif_file_paths
        self.adif_worked_backup_file_path       = adif_worked_backup_file_path
        self.worked_before_preference           = worked_before_preference
        self.marathon_preference                = marathon_preference or {}
        self.grid_tracker_preference            = grid_tracker_preference or {}
        self.enable_grid_reply_new_grid         = enable_grid_reply_new_grid
        self.enable_grid_reply_unconfirmed      = enable_grid_reply_unconfirmed
        self.minimum_report_for_reply           = minimum_report_for_reply
        self.priority_order                     = priority_order

        self.enable_club_log_synch              = enable_club_log_synch
        self.club_log_email                     = club_log_email
        self.club_log_password                  = club_log_password
        self.club_log_callsign                  = club_log_callsign

        self.enable_lotw_upload                 = enable_lotw_upload
        self.lotw_username                      = lotw_username
        self.lotw_password                      = lotw_password
        self.lotw_location                      = lotw_location
        self.lotw_signing_password              = lotw_signing_password
        self.tqsl_path                          = tqsl_path
        self.tqsl_dir                           = tqsl_dir

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_stop_event)

    def run(self):
        try:
            self.listener = Listener(
                primary_udp_server_address      = self.primary_udp_server_address,
                primary_udp_server_port         = self.primary_udp_server_port,

                secondary_udp_server_address    = self.secondary_udp_server_address,
                secondary_udp_server_port       = self.secondary_udp_server_port,
                
                enable_secondary_udp_server     = self.enable_secondary_udp_server,
                
                logging_udp_server_address      = self.logging_udp_server_address,
                logging_udp_server_port         = self.logging_udp_server_port,
                
                enable_logging_udp_server       = self.enable_logging_udp_server,                
                
                enable_sending_reply            = self.enable_sending_reply,
                enable_polite_reply             = self.enable_polite_reply,

                max_reply_attempts_to_callsign  = self.max_reply_attempts_to_callsign,
                max_working_delay               = self.max_working_delay,
                
                enable_log_all_valid_contact    = self.enable_log_all_valid_contact,
                enable_reply_to_valid_callsign  = self.enable_reply_to_valid_callsign,
                enable_reply_to_valid_direction = self.enable_reply_to_valid_direction,
                enable_reply_to_lotw_only       = self.enable_reply_to_lotw_only,

                enable_gap_finder               = self.enable_gap_finder,
                enable_watchdog_bypass          = self.enable_watchdog_bypass,
                enable_debug_output             = self.enable_debug_output,
                enable_pounce_log               = self.enable_pounce_log,
                enable_log_packet_data          = self.enable_log_packet_data,

                monitoring_settings             = self.monitoring_settings,
                
                min_freq                        = self.min_freq,
                max_freq                        = self.max_freq,

                marathon_preference             = self.marathon_preference,
                grid_tracker_preference         = self.grid_tracker_preference,
                enable_grid_reply_new_grid      = self.enable_grid_reply_new_grid,
                enable_grid_reply_unconfirmed   = self.enable_grid_reply_unconfirmed,

                adif_file_paths                  = self.adif_file_paths,
                adif_worked_backup_file_path     = self.adif_worked_backup_file_path,
                worked_before_preference        = self.worked_before_preference,
                minimum_report_for_reply        = self.minimum_report_for_reply,
                priority_order                  = self.priority_order,

                enable_club_log_synch           = self.enable_club_log_synch,
                club_log_email                  = self.club_log_email,
                club_log_password               = self.club_log_password,
                club_log_callsign               = self.club_log_callsign,

                enable_lotw_upload              = self.enable_lotw_upload,
                lotw_username                   = self.lotw_username,
                lotw_password                   = self.lotw_password,
                lotw_location                   = self.lotw_location,
                lotw_signing_password           = self.lotw_signing_password,
                tqsl_path                       = self.tqsl_path,
                tqsl_dir                        = self.tqsl_dir,

                message_callback                = self.message.emit
            )
            self.listener.listen()
            self.listener_started.emit()
        
            QTimer.singleShot(100, self.check_stop_event)
            
        except Exception as e:
            error_message = f"{e}\n{traceback.format_exc()}"
            self.error.emit(error_message)
            self.stop()

    def check_stop_event(self):
        if self.stop_event.is_set():
            self.timer.stop()
            if self.listener is not None:
                self.listener.stop()
                if hasattr(self.listener, "t") and self.listener.t is not None:
                    self.listener.t.join()
            self.finished.emit()

    def stop(self):
        if self.listener is not None:
            self.listener.halt_packet()            
        self.stop_event.set()  
        self.check_stop_event()

    def update_listener_settings(self):
        """
        # Log the caller
        frame = inspect.currentframe().f_back
        caller_info = f"{frame.f_code.co_filename}:{frame.f_lineno} in {frame.f_code.co_name}"
        log.error(f"Worker/update_listener_settings called from: {caller_info}")
        """
        
        if self.listener is not None:
            # Check if UDP server settings have changed and restart if needed
            udp_server_changed = (
                self.listener.primary_udp_server_address != self.primary_udp_server_address or
                self.listener.primary_udp_server_port != self.primary_udp_server_port
            )
            
            if udp_server_changed:                
                self.listener.start_udp_server(self.primary_udp_server_address, self.primary_udp_server_port)
            else:
                # Update settings normally if UDP server hasn't changed
                self.listener.primary_udp_server_address        = self.primary_udp_server_address
                self.listener.primary_udp_server_port           = self.primary_udp_server_port
                
            self.listener.secondary_udp_server_address          = self.secondary_udp_server_address
            self.listener.secondary_udp_server_port             = self.secondary_udp_server_port
            self.listener.enable_secondary_udp_server           = self.enable_secondary_udp_server
            self.listener.logging_udp_server_address            = self.logging_udp_server_address
            self.listener.logging_udp_server_port               = self.logging_udp_server_port
            self.listener.enable_logging_udp_server             = self.enable_logging_udp_server
            self.listener.enable_sending_reply                  = self.enable_sending_reply
            self.listener.enable_polite_reply                   = self.enable_polite_reply
            self.listener.min_freq                              = self.min_freq
            self.listener.max_freq                              = self.max_freq
            self.listener.max_reply_attempts_to_callsign        = self.max_reply_attempts_to_callsign
            self.listener.max_working_delay_seconds             = self.max_working_delay * 60
            self.listener.enable_log_all_valid_contact          = self.enable_log_all_valid_contact
            self.listener.enable_reply_to_valid_callsign        = self.enable_reply_to_valid_callsign
            self.listener.enable_reply_to_valid_direction       = self.enable_reply_to_valid_direction
            self.listener.enable_reply_to_lotw_only             = self.enable_reply_to_lotw_only
            self.listener.enable_gap_finder                     = self.enable_gap_finder
            self.listener.enable_watchdog_bypass                = self.enable_watchdog_bypass
            self.listener.enable_debug_output                   = self.enable_debug_output
            self.listener.enable_pounce_log                     = self.enable_pounce_log
            self.listener.enable_log_packet_data                = self.enable_log_packet_data
            self.listener.marathon_preference                   = self.marathon_preference
            self.listener.grid_tracker_preference               = self.grid_tracker_preference
            self.listener.enable_grid_reply_new_grid            = self.enable_grid_reply_new_grid
            self.listener.enable_grid_reply_unconfirmed         = self.enable_grid_reply_unconfirmed
            self.listener.worked_before_preference              = self.worked_before_preference
            self.listener.minimum_report_for_reply              = self.minimum_report_for_reply
            if self.priority_order is not None:
                self.listener.priority_order                    = self.priority_order

            self.listener.enable_club_log_synch                 = self.enable_club_log_synch
            self.listener.club_log_email                        = self.club_log_email
            self.listener.club_log_password                     = self.club_log_password
            self.listener.club_log_callsign                     = self.club_log_callsign

            self.listener.enable_lotw_upload                    = self.enable_lotw_upload
            self.listener.lotw_username                         = self.lotw_username
            self.listener.lotw_password                         = self.lotw_password
            self.listener.lotw_location                         = self.lotw_location
            self.listener.lotw_signing_password                 = self.lotw_signing_password
            self.listener.tqsl_path                             = self.tqsl_path
            self.listener.tqsl_dir                              = self.tqsl_dir

            # Reinitialize Club Log uploader if settings changed
            if self.enable_club_log_synch and self.club_log_email and self.club_log_password:
                from clublog import ClubLogUploader
                from constants import CLUB_LOG_API_KEY
                self.listener.club_log_uploader = ClubLogUploader(
                    self.club_log_email,
                    self.club_log_password,
                    CLUB_LOG_API_KEY,
                    self.club_log_callsign or ''
                )
            else:
                self.listener.club_log_uploader = None

            # Reinitialize LoTW uploader if settings changed
            if self.enable_lotw_upload and self.lotw_username:
                from lotw_uploader import LoTWUploader
                self.listener.lotw_uploader = LoTWUploader(
                    self.lotw_username,
                    self.lotw_password,
                    self.tqsl_path or None,
                    self.tqsl_dir or None,
                    self.lotw_location or None,
                    self.lotw_signing_password or None
                )
            else:
                self.listener.lotw_uploader = None
            
            self.listener.update_listener_settings()

            # Handle ADIF file paths update
            if hasattr(self.listener, 'adif_file_paths'):
                current_file_paths = self.listener.adif_file_paths
                updated_file_paths = self.adif_file_paths
                if current_file_paths != updated_file_paths:
                    self.listener.adif_file_paths = updated_file_paths

                    if self.listener.adif_monitor:
                        self.listener.adif_monitor.update_file_paths(updated_file_paths)

    def synch_settings(self):
        if self.listener is not None:
            self.listener.synch_settings()

    def show_listener_settings(self):
        if self.listener is not None:
            self.listener.show_listener_settings()            

    def reset_synched_settings(self):
        if self.listener is not None:
            self.listener.reset_synched_settings()