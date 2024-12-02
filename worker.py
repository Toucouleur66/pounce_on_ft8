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
            enable_gap_finder,
            enable_watchdog_bypass,
            enable_debug_output,
            enable_pounce_log,
            enable_log_packet_data                      
        ):
        super(Worker, self).__init__()

        self.update_settings_signal.connect(self.update_settings)

        self.listener                       = None 

        self.stop_event                     = stop_event

        self.mode                           = mode
        self.monitoring_settings            = monitoring_settings                
        
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

    def run(self):
        try:
            self.listener = Listener(
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
                monitoring_settings             = self.monitoring_settings,
                freq_range_mode                 = self.mode,
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

    def update_settings(self):
        # print(f"update_settings called")
        if self.listener is not None:
            # print(f"Listener settings updated in thread")
            self.listener.update_settings()