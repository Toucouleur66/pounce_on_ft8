# worker.py

import traceback

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from wsjtx_listener import Listener

class Worker(QObject):
    finished                         = pyqtSignal()
    error                           = pyqtSignal(str)
    listener_started                = pyqtSignal()
    message                         = pyqtSignal(object)
    update_listener_settings_signal = pyqtSignal()
    synch_settings_signal           = pyqtSignal()
    reset_settings_signal           = pyqtSignal()

    def __init__(
            self,
            monitoring_settings, 
            mode, 
            stop_event,
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
            adif_file_path, 
            adif_worked_backup_file_path, 
            worked_before_preference,
            enable_marathon,
            marathon_preference
        ):
        
        super().__init__()

        self.update_listener_settings_signal.connect(self.update_listener_settings)
        self.synch_settings_signal.connect(self.synch_settings)
        self.reset_settings_signal.connect(self.reset_synched_settings)

        self.listener = None
        self.stop_event = stop_event

        self.mode = mode
        self.monitoring_settings = monitoring_settings

        self.primary_udp_server_address = primary_udp_server_address
        self.primary_udp_server_port = primary_udp_server_port

        self.secondary_udp_server_address = secondary_udp_server_address
        self.secondary_udp_server_port = secondary_udp_server_port
        self.enable_secondary_udp_server = enable_secondary_udp_server

        self.logging_udp_server_address = logging_udp_server_address
        self.logging_udp_server_port = logging_udp_server_port
        self.enable_logging_udp_server = enable_logging_udp_server

        self.enable_sending_reply = enable_sending_reply
        self.max_reply_attemps_to_callsign = max_reply_attemps_to_callsign
        self.max_working_delay = max_working_delay
        self.enable_log_all_valid_contact = enable_log_all_valid_contact
        self.enable_gap_finder = enable_gap_finder
        self.enable_watchdog_bypass = enable_watchdog_bypass
        self.enable_debug_output = enable_debug_output
        self.enable_pounce_log = enable_pounce_log
        self.enable_log_packet_data = enable_log_packet_data

        self.adif_file_path = adif_file_path
        self.adif_worked_backup_file_path = adif_worked_backup_file_path
        self.worked_before_preference = worked_before_preference
        self.enable_marathon = enable_marathon
        self.marathon_preference = marathon_preference

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
                
                max_reply_attemps_to_callsign   = self.max_reply_attemps_to_callsign,
                max_working_delay               = self.max_working_delay,
                
                enable_log_all_valid_contact    = self.enable_log_all_valid_contact,
                enable_gap_finder                = self.enable_gap_finder,
                enable_watchdog_bypass          = self.enable_watchdog_bypass,
                enable_debug_output             = self.enable_debug_output,
                enable_pounce_log               = self.enable_pounce_log,
                enable_log_packet_data          = self.enable_log_packet_data,

                monitoring_settings             = self.monitoring_settings,
                
                freq_range_mode                 = self.mode,
                
                enable_marathon                 = self.enable_marathon,                
                marathon_preference             = self.marathon_preference,
                
                adif_file_path                   = self.adif_file_path,
                adif_worked_backup_file_path     = self.adif_worked_backup_file_path,                
                worked_before_preference        = self.worked_before_preference,
                
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
        self.stop_event.set()  
        self.check_stop_event()

    def update_listener_settings(self):
        if self.listener is not None:
                self.listener.update_listener_settings()

    def synch_settings(self):
        if self.listener is not None:
            self.listener.synch_settings()

    def reset_synched_settings(self):
        if self.listener is not None:
            self.listener.reset_synched_settings()