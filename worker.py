# worker.py

import time
import traceback

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from wsjtx_listener import Listener

class Worker(QObject):
    finished                = pyqtSignal()
    error                  = pyqtSignal(str)
    listener_started       = pyqtSignal()
    message                = pyqtSignal(object)
    update_settings_signal = pyqtSignal()
    send_settings_signal   = pyqtSignal()

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
            worked_before_preference,
            enable_marathon,
            marathon_preference                          
        ):
        super(Worker, self).__init__()

        self.update_settings_signal.connect(self.update_settings)
        self.send_settings_signal.connect(self.send_settings_to_slave)

        self.listener                           = None 
        self.stop_event                         = stop_event

        self.mode                               = mode
        self.monitoring_settings                = monitoring_settings                
            
        self.primary_udp_server_address         = primary_udp_server_address
        self.primary_udp_server_port            = primary_udp_server_port

        self.secondary_udp_server_address       = secondary_udp_server_address
        self.secondary_udp_server_port          = secondary_udp_server_port

        self.enable_secondary_udp_server        = enable_secondary_udp_server                            
        self.enable_sending_reply               = enable_sending_reply
        self.max_reply_attemps_to_callsign      = max_reply_attemps_to_callsign
        self.max_working_delay                  = max_working_delay
        self.enable_log_all_valid_contact       = enable_log_all_valid_contact
        self.enable_gap_finder                   = enable_gap_finder
        self.enable_watchdog_bypass             = enable_watchdog_bypass
        self.enable_debug_output                = enable_debug_output
        self.enable_pounce_log                  = enable_pounce_log   
        self.enable_log_packet_data             = enable_log_packet_data
        
        self.adif_file_path                      = adif_file_path
        self.worked_before_preference           = worked_before_preference
        self.enable_marathon                    = enable_marathon
        self.marathon_preference                = marathon_preference

    def run(self):
        try:
            self.listener = Listener(
                primary_udp_server_address      = self.primary_udp_server_address,
                primary_udp_server_port         = self.primary_udp_server_port,
                secondary_udp_server_address    = self.secondary_udp_server_address,
                secondary_udp_server_port       = self.secondary_udp_server_port,
                enable_secondary_udp_server     = self.enable_secondary_udp_server,
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
                worked_before_preference        = self.worked_before_preference,
                message_callback                = self.message.emit
            )
            self.listener.listen()
            self.listener_started.emit()

            while not self.stop_event.is_set():
                time.sleep(0.1)
            self.listener.stop()
            self.listener.t.join()
        except Exception as e:
            error_message = f"{e}\n{traceback.format_exc()}"
            self.error.emit(error_message)
        finally:
            self.finished.emit()

    def stop(self):
        if self.listener is not None:
            self.listener.stop()            

    """
        Make sure we are using the latest settings
    """
    def update_settings(self):
        if self.listener is not None:
            self.listener.update_settings()

    def send_settings_to_slave(self):
        if self.listener is not None:
            self.listener.send_settings_to_slave()            