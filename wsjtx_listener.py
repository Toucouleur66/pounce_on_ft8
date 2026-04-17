# wsjtx_listener.py

import pywsjtx.extra.simple_server
import queue
import traceback
import socket
import bisect
import json
import inspect
import uuid
import threading

from datetime import datetime, timezone, timedelta
from collections import deque

from receiver_worker import ReceiverWorker
from processor_worker import ProcessorWorker

from PyQt6.QtCore import QObject, QThread, QTimer

from logger import get_logger

from utils import get_local_ip_address, get_mode_interval, get_amateur_band, parse_wsjtx_message
from utils import get_wkb4_year, get_clean_rst
from utils import is_valid_continent, is_valid_grid, is_grid_needed
from utils import load_marathon_wanted_data, save_marathon_wanted_data

from callsign_lookup import CallsignLookup
from adif_monitor import AdifMonitor
from telemetry_service import TelemetryService
from clublog import ClubLogUploader
from lotw_uploader import LoTWClient

log     = get_logger(__name__)

from constants import (
    CURRENT_VERSION_NUMBER,
    BAND_CHANGE_WAITING_DELAY,
    DEFAULT_REPLY_ATTEMPTS,
    MAXIMUM_ALLOWED_DT,
    EVEN,
    ODD,
    MASTER,
    SLAVE,
    MARATHON_UNLIMITED,
    WAITING_TIME_BEFORE_REPLY,
    HEARTBEAT_TIMEOUT_THRESHOLD,
    WKB4_REPLY_MODE_NEVER,
    WKB4_REPLY_MODE_CURRENT_YEAR,
    ADIF_WORKED_CALLSIGNS_FILE,
    MARATHON_FILE,
    PRIORITY_LIST,
    CLUB_LOG_API_KEY
)

class Listener(QObject):
    def __init__(
            self,
            primary_udp_server_address,
            primary_udp_server_port,
            secondary_udp_server_address,
            secondary_udp_server_port,
            enable_secondary_udp_server,
            logging_udp_server_address,
            logging_udp_server_port,
            enable_logging_udp_server,            
            enable_sending_reply,
            enable_polite_reply,
            max_reply_attempts_to_callsign,
            max_working_delay,
            enable_log_all_valid_contact,
            enable_reply_to_valid_callsign,
            enable_reply_to_valid_direction,
            enable_reply_to_lotw_only,
            enable_gap_finder,
            enable_watchdog,
            watchdog_number_of_attempts,
            watchdog_retry_time,
            enable_debug_output,
            enable_pounce_log,        
            enable_log_packet_data, 
            monitoring_settings,
            min_freq,
            max_freq,
            marathon_preference,
            grid_tracker_preference,
            enable_grid_reply_new_grid,
            enable_grid_reply_unconfirmed,
            adif_file_paths,
            adif_worked_backup_file_path,
            worked_before_preference,
            minimum_report_for_reply,
            priority_order,
            enable_club_log_synch,
            club_log_email,
            club_log_password,
            club_log_callsign,
            enable_lotw_upload,
            lotw_username,
            lotw_password,
            lotw_location,
            lotw_signing_password,
            tqsl_path,
            tqsl_dir,
            message_callback
        ):
        super().__init__()

        self.my_call                    = None
        self.my_cont                    = None
        self.my_grid                    = None
        self.dx_call                    = None

        self.decode_packet_count        = 0
        self.last_decode_packet_time    = None
        self.last_status_packet_time    = None
        self.last_heartbeat_time        = None

        self.the_packet                 = None
        self.packet_store               = {}
        self.packet_counter             = 0        
        self.reply_message_buffer       = deque()

        self.last_selected_message      = None
        self.reply_to_packet_time       = None

        self.call_ready_to_log          = None
        self.last_logged_call           = None
        self.targeted_call              = None
        self.targeted_call_frequencies  = set()
        self.first_time_decoded          = deque([set()], maxlen=10)
        self.targeted_call_period       = None
        self.grid_being_called          = {}
        self.rst_rcvd_from_being_called = {}
        self.rst_rcvd                   = None        
        self.qso_time_on                = {}
        self.qso_time_off               = {}
        self.rst_sent                   = {}
        self.mode                       = None
        self.special_op_mode            = None
        self.last_mode                  = None
        self.transmitting               = None

        self.frequency                  = None
        self.last_frequency             = None        
        
        self.band                       = None
        self.last_band                  = None
        self.last_band_time_change      = datetime.now()   
        self.wait_before_decoding       = None   
        
        self.suggested_frequency        = None
        self.rx_df                      = None
        self.tx_df                      = None

        self.reply_attempts             = {}
        self.watchdog_exclusions        = {}

        self.enable_sending_reply               = enable_sending_reply
        self.enable_polite_reply                = enable_polite_reply
        self.enable_log_all_valid_contact       = enable_log_all_valid_contact
        self.enable_reply_to_valid_callsign     = enable_reply_to_valid_callsign
        self.enable_reply_to_valid_direction    = enable_reply_to_valid_direction
        self.enable_reply_to_lotw_only          = enable_reply_to_lotw_only
        self.enable_gap_finder                  = enable_gap_finder
        self.enable_watchdog                    = enable_watchdog
        self.watchdog_number_of_attempts        = watchdog_number_of_attempts
        self.watchdog_retry_time                = watchdog_retry_time
        self.enable_debug_output                = enable_debug_output
        self.enable_pounce_log                  = enable_pounce_log 
        self.enable_log_packet_data             = enable_log_packet_data

        self.enable_marathon                    = None
        self.enable_grid_tracker                = None

        self.marathon_preference                = marathon_preference
        self.grid_tracker_preference            = grid_tracker_preference
        self.enable_grid_reply_new_grid         = enable_grid_reply_new_grid
        self.enable_grid_reply_unconfirmed      = enable_grid_reply_unconfirmed

        self.max_reply_attempts_to_callsign     = max_reply_attempts_to_callsign

        # Convert display names to property keys if needed
        if priority_order is not None:
            self.priority_order = [PRIORITY_LIST.get(name, name) for name in priority_order]
        else:
            self.priority_order = list(PRIORITY_LIST.values())

        self.origin_addr_port               = None
        self._instance                      = None
        self.synched_band                   = None
        self.synched_settings               = None       
        self.synch_time                     = datetime.now()   

        self.primary_udp_server_address     = primary_udp_server_address or get_local_ip_address()
        self.primary_udp_server_port        = primary_udp_server_port or 2237

        self.secondary_udp_server_address   = secondary_udp_server_address or get_local_ip_address()
        self.secondary_udp_server_port      = secondary_udp_server_port or 2237

        self.enable_secondary_udp_server    = enable_secondary_udp_server or False

        self.logging_udp_server_address     = logging_udp_server_address or get_local_ip_address()
        self.logging_udp_server_port        = logging_udp_server_port or 2237

        self.enable_logging_udp_server      = enable_logging_udp_server or False

        """
            Convert minutes to seconds from max_working_delay
        """
        self.max_working_delay_seconds      = max_working_delay * 60
        self.monitoring_settings            = monitoring_settings

        self.wanted_callsigns               = None
        self.excluded_callsigns             = None
        self.monitored_callsigns            = None
        self.wanted_cq_zones                = None
        self.monitored_cq_zones             = None
        self.excluded_cq_zones              = None
        self.wanted_callsigns_direction     = {}
        self.worked_callsigns               = {}
        self.worked_grids                   = {}

        self.wanted_callsigns_per_entity   = {}

        self.min_freq                       = min_freq
        self.max_freq                       = max_freq
        self.message_callback               = message_callback

        self.worked_before_preference       = worked_before_preference      

        self.minimum_report_for_reply       = minimum_report_for_reply

        self.enable_club_log_synch          = enable_club_log_synch
        self.club_log_email                 = club_log_email
        self.club_log_password              = club_log_password
        self.club_log_callsign              = club_log_callsign
        self.club_log_uploader              = None

        self.enable_lotw_upload             = enable_lotw_upload
        self.lotw_username                  = lotw_username
        self.lotw_password                  = lotw_password
        self.lotw_location                  = lotw_location
        self.lotw_signing_password          = lotw_signing_password
        self.tqsl_path                      = tqsl_path
        self.tqsl_dir                       = tqsl_dir
        self.lotw_uploader                  = None

        self.adif_data                      = {}
        self.adif_monitor                   = None
        self.adif_file_paths                 = adif_file_paths or []      

        self._running                       = True     
        
        self.packet_queue                   = queue.Queue(maxsize=1000)
        self.receiver_thread                = QThread()
        self.processor_thread               = QThread()

        self.receiver_worker                = ReceiverWorker(self.receive_packets)
        self.processor_worker               = ProcessorWorker(self.process_packets)

        self.receiver_worker.moveToThread(self.receiver_thread)
        self.processor_worker.moveToThread(self.processor_thread)

        self.receiver_thread.started.connect(self.receiver_worker.run)
        self.processor_thread.started.connect(self.processor_worker.run)

        self.lookup  = CallsignLookup()

        log.warning("Initialized CallsignLookup instance in listener process")

        """
            Check ADIF file to handle Worked B4 
        """          
        self.adif_monitor = AdifMonitor(adif_file_paths, ADIF_WORKED_CALLSIGNS_FILE)
        self.wanted_callsigns_per_entity = load_marathon_wanted_data(MARATHON_FILE)
    
        self.adif_monitor.register_lookup(self.lookup)
        self.adif_monitor.start()
        self.adif_monitor.register_callback(self.update_adif_data)
        self.adif_monitor.register_processing_callback(self.update_adif_processing_status)

        """
            Initialize telemetry service
        """
        self.telemetry_service = TelemetryService()

        """
            Initialize Club Log uploader
        """
        if self.enable_club_log_synch and self.club_log_email and self.club_log_password:
            self.club_log_uploader = ClubLogUploader(
                self.club_log_email,
                self.club_log_password,
                CLUB_LOG_API_KEY,
                self.club_log_callsign or ''
            )

        """
            Initialize LoTW uploader
        """
        if self.enable_lotw_upload and self.lotw_username:
            self.lotw_uploader = LoTWClient(
                self.lotw_username,
                self.lotw_password,
                self.tqsl_path or None,
                self.tqsl_dir or None,
                self.lotw_location or None,
                self.lotw_signing_password or None
            )

        """
            Use ADIF file to log
        """
        self.adif_worked_backup_file_path           = adif_worked_backup_file_path

        """
            Check what period to use
        """
        self.last_period_index              = None
        self.used_frequencies               = {
            EVEN                            : deque([set()], maxlen=2),
            ODD                             : deque([set()], maxlen=2)
        }

        """
            Start UDP server
        """
        try:
            success = self.start_udp_server()
            if not success:
                self.stop()
        except Exception:        
            raise

    def receive_packets(self):
        while self._running:
            try:
                # Check if socket is available before attempting to receive
                if not self.s or not self.s.sock:
                    log.error("Socket not available, stopping packet reception")
                    break
                    
                pkt, addr_port = self.s.sock.recvfrom(8192)
                _instance = None
                header_end = pkt.find(b'|')
                if header_end != -1:
                    try:
                        header = pkt[:header_end].decode('utf-8')

                        origin_ip, origin_port_str = header.split(':')

                        origin_port = int(origin_port_str)
                        origin_addr_port = (origin_ip, origin_port)
                        actual_pkt  = pkt[header_end+1:]                   

                        _instance = SLAVE        
                    except (UnicodeDecodeError, ValueError):                        
                        origin_addr_port = addr_port
                        actual_pkt  = pkt
                else:                    
                    origin_addr_port = addr_port
                    actual_pkt  = pkt

                    _instance = MASTER    

                """
                    self.origin_addr_port can be used to store
                    the UDP address and port from WSJT-X/JTDX
                    or a Slave instance
                """
                self.origin_addr_port = origin_addr_port

                if _instance and _instance != self._instance:
                    log.debug(f'Set instance [ {_instance} ] with [ {type(pywsjtx.WSJTXPacketClassFactory.from_udp_packet(self.origin_addr_port, pkt)).__name__} ] from {self.origin_addr_port}')

                    self._instance = _instance                 
                    self.message_callback({
                        'type'      : 'instance_status',
                        'status'    : self._instance,
                        'addr_port' : addr_port
                    })

                if self.enable_log_packet_data:
                    message = f"Received packet of length {len(pkt)} from {addr_port}\nPacket data: {pkt.hex()}"
                    log.info(message)
                self.packet_queue.put((actual_pkt, origin_addr_port))
            except socket.timeout:
                continue
            except OSError as e:
                if hasattr(e, 'winerror') and e.winerror == 10038:
                    return None, None
                error_message = f"Exception in receive_packets: {e}\n{traceback.format_exc()}"
                log.error(error_message)
                self.message_callback({
                    'type': 'error',
                    'message': error_message
                })
                return None, None
        try:
            if self.s and self.s.sock:
                self.s.sock.close()
        except Exception:
            pass
        log.info("Receiver thread stopped")

    def process_packets(self):
        while self._running or not self.packet_queue.empty():
            try:
                packet, addr_port = self.packet_queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                self.the_packet = pywsjtx.WSJTXPacketClassFactory.from_udp_packet(addr_port, packet)
                self.assign_packet(addr_port)  
                if self.can_forward_packet():
                    self.forward_packet(packet)                          
            except Exception as e:
                error_message = f"Exception in process_packets: {e}\n{traceback.format_exc()}"
                log.error(error_message)
                self.message_callback({
                    'type': 'error',
                    'message': error_message
                })
            finally:
                self.packet_queue.task_done()
        log.info("Processor thread stopped")

    def add_packet_header(self, address=None, port=None):
        if address is None:
            address = self.primary_udp_server_address
        if port is None:
            port = self.primary_udp_server_port
        """
            Add header "IP:port" to the packet and
            make sure to add "|" to the end of the header
        """
        return f"{address}:{port}|".encode('utf-8') 

    def forward_packet(self, packet):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as send_sock:
                # log.debug(f"Forwarding packet to secondary UDP server at {self.secondary_udp_server_address}:{self.secondary_udp_server_port}")
                send_sock.sendto(self.add_packet_header() + packet, (
                    self.secondary_udp_server_address,
                    self.secondary_udp_server_port
                ))
        except Exception as e:
            error_message = f"Can't forward packet: {e}"
            log.error(error_message)
            self.message_callback({
                'type': 'error',
                'message': error_message
            })           

    def start_udp_server(
            self,
            new_address = None,
            new_port    = None
        ):
        """
            Start or restart the UDP server with address and port settings
        """
        try:
            # Close existing server socket if it exists
            if hasattr(self, 's') and self.s and self.s.sock:
                log.info(f"Closing existing UDP server at {self.primary_udp_server_address}:{self.primary_udp_server_port}")
                self.s.sock.close()
                self.s = None
            
            # Update the address and port if provided
            if new_address is not None:
                self.primary_udp_server_address = new_address
            if new_port is not None:
                self.primary_udp_server_port = new_port
            
            # Create new server with updated settings
            log.info(f"Starting UDP server at {self.primary_udp_server_address}:{self.primary_udp_server_port}")
            self.s = pywsjtx.extra.simple_server.SimpleServer(
                self.primary_udp_server_address,
                self.primary_udp_server_port
            )
            if self.s.sock is not None:
                self.s.sock.settimeout(1.0)
                log.info(f"UDP server successfully started at {self.primary_udp_server_address}:{self.primary_udp_server_port}")
            else:
                error_message = f"Can't open socket for {self.primary_udp_server_address} using port {self.primary_udp_server_port}"
                log.error(error_message)
                if hasattr(self, 'message_callback'):
                    self.message_callback({
                        'type'              : 'gui_alert',
                        'formatted_message' : error_message
                    })
                return False
                
        except socket.error as e:
            error_message = f"Error binding server to {self.primary_udp_server_address} using port {self.primary_udp_server_port}: {e}"
            log.error(error_message)
            if hasattr(self, 'message_callback'):
                self.message_callback({
                    'type'              : 'gui_alert',
                    'formatted_message' : error_message
                })
            if e.errno == 49:  
                pass
            raise
        except Exception as e:
            error_message = f"Unexpected error starting UDP server: {e}"
            log.error(error_message)
            if hasattr(self, 'message_callback'):
                self.message_callback({
                    'type'              : 'gui_alert',
                    'formatted_message' : error_message
                })
            return False            
        return True

    def update_listener_settings(self):
        # Log the caller
        """
        frame = inspect.currentframe().f_back
        caller_info = f"{frame.f_code.co_filename}:{frame.f_lineno} in {frame.f_code.co_name}"
        log.error(f"Listener/update_listener_settings called from: {caller_info}")
        """
        self.wanted_callsigns       = self.monitoring_settings.get_wanted_callsigns()
        self.excluded_callsigns     = self.monitoring_settings.get_excluded_callsigns()
        self.monitored_callsigns    = self.monitoring_settings.get_monitored_callsigns()
        self.wanted_cq_zones        = self.monitoring_settings.get_wanted_cq_zones()
        self.monitored_cq_zones     = self.monitoring_settings.get_monitored_cq_zones()
        self.excluded_cq_zones      = self.monitoring_settings.get_excluded_cq_zones()
        self.synched_band           = self.monitoring_settings.get_operating_band()
        self.enable_sending_reply   = self.monitoring_settings.get_sending_reply()

        if self.marathon_preference.get(self.band):
            self.enable_marathon    = True
        elif self.marathon_preference.get(MARATHON_UNLIMITED):
            self.enable_marathon    = True
        else:
            self.enable_marathon    = False
        
        if self.grid_tracker_preference.get(self.band):
            self.enable_grid_tracker = True
        elif self.enable_grid_reply_new_grid:
            self.enable_grid_tracker = True
        else:
            self.enable_grid_tracker = False

        if self.worked_callsigns:
            callsigns_to_remove = [
                callsign for callsign in self.worked_callsigns if callsign in self.wanted_callsigns
            ]
            for callsign in callsigns_to_remove:
                self.worked_callsigns.remove(callsign)           
            
        self.synch_time             = datetime.now()
        
        self.show_listener_settings()
        
    def show_listener_settings(self):
        log_output = []
        log_output.append(f"Updated settings (~{CURRENT_VERSION_NUMBER}):")
        log_output.append(f"Instance={self._instance}")
        log_output.append(f"AdifFiles={self.adif_file_paths}")
        log_output.append(f"MyCall={self.my_call}")
        log_output.append(f"EnableSendingReply={self.enable_sending_reply}")    
        log_output.append(f"EnableGapFinder={self.enable_gap_finder}")    
        log_output.append(f"Band={self.band}")   
        log_output.append(f"FrequencyRange={self.min_freq}-{self.max_freq}Hz")
        log_output.append(f"MinimumSignalReport={self.minimum_report_for_reply}db")        
        log_output.append(f"WantedCallsigns={self.wanted_callsigns}")
        log_output.append(f"MonitoredCallsigns={self.monitored_callsigns}")
        log_output.append(f"ExcludedCallsigns={self.excluded_callsigns}")
        log_output.append(f"WantedZones={self.wanted_cq_zones}")
        log_output.append(f"MonitoredZones={self.monitored_cq_zones}")
        log_output.append(f"ExcludedZones={self.excluded_cq_zones}")
        log_output.append(f"WorkedBeforePreference={self.worked_before_preference}")
        log_output.append(f"Marathon={self.enable_marathon}")
        log_output.append(f"GridTracker={self.enable_grid_tracker}")
        log_output.append(f"LoTWReplyOnly={self.enable_reply_to_lotw_only }") 
        log_output.append(f"PriorityOrder={self.priority_order}")      
        log_output.append(f"ClubLogSynch={self.enable_club_log_synch}")
        log_output.append(f"LoTWUpload={self.enable_lotw_upload}")
        log_output.append(f"Watchdog={self.enable_watchdog} (attempts={self.watchdog_number_of_attempts}, retry={self.watchdog_retry_time}min)")

        log.warning(f"\n\t".join(log_output))

    """
        Handle slave master relationship 
    """
    def send_request_setting_packet(self):
        if (
            self._instance == SLAVE and
            self.band 
        ):  
            try:
                request_setting_packet = pywsjtx.RequestSettingPacket.Builder(
                    self.the_packet.wsjtx_id,
                    self.synch_time.isoformat()                   
                )
                self.s.send_packet(
                    self.origin_addr_port,
                    request_setting_packet
                )
                log.info(f"RequestSettingPacket sent to {self.origin_addr_port}.")      
            except Exception as e:
                log.error(f"Failed to request Master settings: {e}\n{traceback.format_exc()}")

    def reset_synched_settings(self):
        self.synched_settings = None

    def synch_settings(self, addr_port=None):       
        try: 
            if addr_port is None:
                # Do not proceed for synch unless we set synched_settings
                if self._instance == SLAVE and self.synched_settings is not None:
                    addr_port = self.origin_addr_port
                elif self.enable_secondary_udp_server:
                    addr_port = (
                        self.secondary_udp_server_address,
                        self.secondary_udp_server_port
                    )
            
            if addr_port:
                frame = inspect.currentframe()
                try:
                    caller = frame.f_back
                    co_name = caller.f_code.co_name        
                    log.warning(f"Synch settings ({self._instance}): {co_name} from {caller} {addr_port}")
                finally:
                    del frame

                self.send_settings_packet({             
                    'band'                  : self.band,
                    'wanted_callsigns'      : self.wanted_callsigns,
                    'excluded_callsigns'    : self.excluded_callsigns,
                    'monitored_callsigns'   : self.monitored_callsigns,
                    'wanted_cq_zones'       : self.wanted_cq_zones,
                    'monitored_cq_zones'    : self.monitored_cq_zones,
                    'excluded_cq_zones'     : self.excluded_cq_zones,
                    'enable_sending_reply'  : self.enable_sending_reply
                }, addr_port)
        except Exception as e:
            log.error(f"Failed to synch settings: {e}\n{traceback.format_exc()}")
        
    def send_settings_packet(self, settings_dict, addr_port):
        try:
            settings_packet = pywsjtx.SettingPacket.Builder(
                to_wsjtx_id="WSJT-X",
                settings_dict=settings_dict,
                synch_time=self.synch_time.isoformat()
            )

            if self._instance == MASTER:
                settings_packet = self.add_packet_header() + settings_packet
                self.message_callback({
                    'type'      : 'instance_synched',
                    'addr_port' : addr_port
                })

            self.s.send_packet(
                addr_port,
                settings_packet
            )

            log.info(f"SettingPacket sent to {addr_port}.")        
        except Exception as e:
            log.error(f"Failed to send SettingPacket: {e}")    

    """
        Process to stop Listener properly
    """
    def stop(self):
        self._running = False
        self._instance = MASTER
        self.synched_settings = False

        try:
            if self.s and self.s.sock:
                self.s.sock.close()
        except Exception:
            pass
        
        self.receiver_worker.stop()
        self.processor_worker.stop()
        self.receiver_thread.quit()
        self.processor_thread.quit()

        if not self.receiver_thread.wait(2_000):
            log.warning("Receiver thread did not quit in time")
        if not self.processor_thread.wait(2_000):
            log.warning("Processor thread did not quit in time")

        # Stop ADIF monitor to prevent duplicate processing
        if self.adif_monitor:
            log.info("Stopping ADIF monitor")
            self.adif_monitor.stop()
            self.adif_monitor = None

        # Stop telemetry service
        if self.telemetry_service:
            log.info("Stopping telemetry service")
            self.telemetry_service.stop()

    def listen(self):
        self.receiver_thread.start()
        self.processor_thread.start()

        # Start telemetry service
        self.telemetry_service.start()

    def send_heartbeat_packet(self):
        if self._instance == SLAVE: 
            if self.last_heartbeat_time:        
                if (datetime.now(timezone.utc) - self.last_heartbeat_time).total_seconds() > HEARTBEAT_TIMEOUT_THRESHOLD:
                    self.synched_settings = False                
            return    
            
        max_schema = max(self.the_packet.max_schema, 3)
        reply_beat_packet = pywsjtx.HeartBeatPacket.Builder(self.the_packet.wsjtx_id,max_schema)
        self.s.send_packet(self.origin_addr_port, reply_beat_packet)

    def handle_status_packet(self):
        if self.enable_log_packet_data:
            log.debug(self.the_packet)
        try:
            if self.my_call != self.the_packet.de_call:
                log.error(f"Updating my call to [ {self.the_packet.de_call} ]")                

            self.my_call                = self.the_packet.de_call
            self.my_grid                = self.the_packet.de_grid
            self.dx_call                = self.the_packet.dx_call
            self.tx_df                  = self.the_packet.tx_df
            self.rx_df                  = self.the_packet.rx_df
            self.mode                   = self.the_packet.mode
            self.special_op_mode        = int(self.the_packet.special_op_mode)
            self.frequency              = self.the_packet.dial_frequency
            self.band                   = get_amateur_band(self.frequency)
            
            self.transmitting           = int(self.the_packet.transmitting)  
            
            self.rst_sent[self.dx_call] = self.the_packet.report               

            error_found                 = False
            telemetry_update_needed     = False

            self.my_cont                = self.lookup.lookup_callsign(self.my_call).get('cont', None)

            # Updating mode
            if self.last_mode != self.mode:
                telemetry_update_needed = True
                self.last_mode = self.mode
                self.message_callback({
                    'type'      : 'update_mode',
                    'mode'      : self.mode
                })

            # Updating frequency
            if self.last_frequency != self.frequency:
                telemetry_update_needed = True
                self.last_frequency = self.frequency

                if self.last_band != self.band:
                    self.last_band = self.band
                    self.last_band_time_change = datetime.now()
                    self.reset_targeted_call()
                    self.synched_settings = None

                    if self.enable_grid_tracker and self.adif_data.get('grid'):
                        self.worked_grids[self.band] = list(self.adif_data.get('grid', {}).get(self.band, {}).keys())
                        # log.info(f"Grids for {self.band} band: {self.worked_grids[self.band]}")

                self.message_callback({
                    'type'      : 'update_frequency',
                    'frequency' : self.frequency
                })       

            if telemetry_update_needed:
                # Update telemetry service with user data
                self.telemetry_service.update_user_data(
                    my_call=self.my_call,
                    my_grid=self.my_grid,
                    band=self.band
                )        

            """
                If we are running Listerner as a slave instance we have to request settings
            """
            if (
                (
                    self._instance == SLAVE and
                    not self.synched_settings
                ) or 
                (
                    self.synched_settings and 
                    self.last_status_packet_time is not None and 
                    (datetime.now() - self.last_status_packet_time).total_seconds() > 60
                )
            ):
                time_since_last_status_packet_time = str(round(
                    (
                        datetime.now() - self.last_status_packet_time
                    ).total_seconds()
                )) + " seconds" if self.last_status_packet_time else None

                last_status_packet_time = self.last_status_packet_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_status_packet_time else None
                
                log_output = []
                log_output.append(f"SettingPacket required.")
                log_output.append(f"Instance={self._instance}")         
                log_output.append(f"LastStatusPacketTime={last_status_packet_time}")   
                log_output.append(f"TimeSinceLasStatusPacketTime={time_since_last_status_packet_time}")
                log_output.append(f"SynchedSettings={self.synched_settings}")

                log.info(f"\n\t".join(log_output))

                self.send_request_setting_packet()   

            self.last_status_packet_time = datetime.now()

            if self.targeted_call is not None:
                status_had_time_to_update = (datetime.now(timezone.utc) - self.reply_to_packet_time).total_seconds() > 30 if self.reply_to_packet_time else None 
                if (
                    status_had_time_to_update and
                    self.the_packet.tx_enabled == 0 and 
                    self.the_packet.dx_call is not None and
                    self.reply_to_packet_time is not None                    
                ):
                    error_found = True
                    log.error('Tx disabled')   
                    self.reset_targeted_call()
                elif self.the_packet.tx_watchdog == 1:
                    error_found = True
                    log.error('Watchdog enabled')

                elif self.targeted_call == self.dx_call:  
                    self.time_off   = datetime.now(timezone.utc)
                elif (
                    status_had_time_to_update and   
                    self.dx_call is not None
                ):
                    error_found = True
                    log.error('We should call [ {} ] not [ {} ]'.format(self.targeted_call, self.dx_call))   

                if error_found:
                    self.message_callback({
                        'type': 'error_occurred',                
                    })
                
        except Exception as e:
            log.error("Caught an error on status handler: error {}\n{}".format(e, traceback.format_exc()))   

    def assign_packet(self, addr_port=None):
        status_update = True

        if isinstance(self.the_packet, pywsjtx.HeartBeatPacket):
            self.last_heartbeat_time = datetime.now(timezone.utc)
            self.send_heartbeat_packet()
        elif isinstance(self.the_packet, pywsjtx.StatusPacket):
            self.handle_status_packet()
        elif isinstance(self.the_packet, pywsjtx.QSOLoggedPacket):
            log.warning('QSOLoggedPacket should not be handle')   
        elif isinstance(self.the_packet, pywsjtx.DecodePacket):
            self.last_decode_packet_time = datetime.now(timezone.utc)
            self.decode_packet_count += 1
            
            if not self.my_call:
                log.error("No StatusPacket received yet, can\'t handle DecodePacket for now.") 
                return
            
            seconds_since_band_change = round(
                (datetime.now() - self.last_band_time_change).total_seconds()
            )
            if seconds_since_band_change < BAND_CHANGE_WAITING_DELAY:
                wait_before_decoding = BAND_CHANGE_WAITING_DELAY - seconds_since_band_change
                if wait_before_decoding != self.wait_before_decoding:
                    self.wait_before_decoding = wait_before_decoding
                    log.error(f"Can't handle DecodePacket yet. {wait_before_decoding} seconds to wait.")    
                    # Add callback to let GUI know we can't handle decode yet
                return             

            self.handle_decode_packet()
            if self.enable_gap_finder:
                self.collect_used_frequencies()                     
        elif isinstance(self.the_packet, pywsjtx.ClearPacket):
            log.debug("Received ClearPacket method")        
        elif isinstance(self.the_packet, pywsjtx.LoggedADIFPacket):
            log.warning("Received LoggedADIFPacket method")            
        elif isinstance(self.the_packet, pywsjtx.ReplyPacket):
            log.debug("Received ReplyPacket method")            
        elif isinstance(self.the_packet, pywsjtx.ClosePacket):
            pass 
            """
                self.callback_stop_monitoring()
            """
        elif isinstance(self.the_packet, pywsjtx.RequestSettingPacket):
            self.handle_request_setting_packet(addr_port)                      
        elif isinstance(self.the_packet, pywsjtx.SettingPacket):
            self.handle_setting_packet(addr_port)      
        else:
            status_update = False
            log.error('Unknown packet type {}; {}'.format(type(self.the_packet),self.the_packet))

        if status_update:
            self.callback_status_update()   

    def can_forward_packet(self):    
        if (
            not self.enable_secondary_udp_server or
            (
                self.secondary_udp_server_address == self.primary_udp_server_address and
                self.secondary_udp_server_port == self.primary_udp_server_port
            )
        ):                    
            return False
        elif isinstance(self.the_packet, pywsjtx.RequestSettingPacket):
            return False
        elif isinstance(self.the_packet, pywsjtx.SettingPacket):
            return False
        else:
            return True
               
    def callback_status_update(self):
        self.message_callback({
            'type'                      : 'update_status',
            'my_call'                   : self.my_call,
            'my_grid'                   : self.my_grid,
            'frequency'                 : self.frequency,
            'decode_packet_count'       : self.decode_packet_count,
            'last_decode_packet_time'   : self.last_decode_packet_time,
            'last_heartbeat_time'       : self.last_heartbeat_time,
            'transmitting'              : self.transmitting
        })

    def handle_request_setting_packet(self, addr_port):    
        log.debug(f"Received RequestSettingPacket method from {addr_port}.")  
        if self.synch_time.isoformat() != datetime.fromisoformat(self.the_packet.synch_time):
            self.synch_settings(addr_port)       
            
    def callback_stop_monitoring(self):
        log.debug("Received ClosePacket method")
        self.message_callback({
            'type'                      : 'stop_monitoring',
            'decode_packet_count'       : self.decode_packet_count,
            'last_decode_packet_time'   : self.last_decode_packet_time
        })

    def get_watchdog_attempts_limit(self):
        if self.enable_watchdog:
            return self.watchdog_number_of_attempts
        return self.max_reply_attempts_to_callsign

    def is_watchdog_excluded(self, callsign):
        until = self.watchdog_exclusions.get(callsign)
        if until is None:
            return False
        if datetime.now(timezone.utc) >= until:
            self.lift_watchdog_exclusion(callsign, reason='window elapsed')
            return False
        return True

    def add_watchdog_exclusion(self, callsign):
        until = datetime.now(timezone.utc) + timedelta(minutes=self.watchdog_retry_time)
        self.watchdog_exclusions[callsign] = until
        log.error(f"Watchdog: [ {callsign} ] temporarily excluded for {self.watchdog_retry_time} min (until {until.isoformat()})")
        self.message_callback({
            'type'             : 'temporarily_excluded',
            'callsign'         : callsign,
            'exclusion_minutes': self.watchdog_retry_time
        })

    def lift_watchdog_exclusion(self, callsign, reason=None):
        if callsign in self.watchdog_exclusions:
            self.watchdog_exclusions.pop(callsign, None)
            self.reply_attempts.pop(callsign, None)
            if reason:
                log.warning(f"Watchdog exclusion lifted for [ {callsign} ] ({reason})")
            else:
                log.warning(f"Watchdog exclusion lifted for [ {callsign} ]")
            self.message_callback({
                'type'    : 'watchdog_exclusion_lifted',
                'callsign': callsign
            })

    def reset_targeted_call(self):
        """
        self.grid_being_called          .pop(self.targeted_call, None)
        self.qso_time_on                .pop(self.targeted_call, None)
        self.qso_time_off               .pop(self.targeted_call, None)
        self.rst_rcvd_from_being_called .pop(self.targeted_call, None)
        self.rst_sent                   .pop(self.targeted_call, None)
        """
        self.targeted_call              = None
        self.targeted_call_period       = None
        self.targeted_call_frequencies  = set()
        self.reply_to_packet_time       = None    
        self.rst_rcvd                   = None
        self.grid                       = None
        self.suggested_frequency        = None

    def collect_used_frequencies(self):
        try:
            current_period = self.odd_or_even_period()
            current_period_index = self.get_period_index()
            if current_period is None or current_period_index is None:
                log.error("Cannot determine current period or period index.")
                return

            if current_period_index != self.last_period_index:
                self.used_frequencies[current_period].append([])
                self.last_period_index = current_period_index

            current_frequencies = self.used_frequencies[current_period][-1]
            bisect.insort(current_frequencies, self.the_packet.delta_f)
        except Exception as e:
            log.error(f"Error collecting frequency usage: {e}\n{traceback.format_exc()}")

    def get_period_index(self):
        if (
            not self.the_packet or 
            not hasattr(self.the_packet, 'time') or
            not self.the_packet.time
        ):
            log.error("Packet time is not available.")
            return None

        return int(self.the_packet.time.timestamp() // get_mode_interval(self.mode))

    def odd_or_even_period(self):
        period_index = self.get_period_index()
        if period_index is None:
            return None
        return EVEN if period_index % 2 == 0 else ODD

    def get_frequency_suggestion(self, period):
        # Suggests a frequency in the middle of the largest available segment
        used_frequencies_sets = self.used_frequencies.get(period, deque())
        used_frequencies = set()
        for freq_set in used_frequencies_sets:
            used_frequencies.update(freq_set)

        used_frequencies = sorted(used_frequencies)

        freq_min = self.min_freq
        freq_max = self.max_freq

        frequency_range = [freq_min] + used_frequencies + [freq_max]

        gaps = []
        for i in range(len(frequency_range) - 1):
            gap_start = frequency_range[i]
            gap_end = frequency_range[i + 1]
            gap_size = gap_end - gap_start
            if gap_size > 50:
                gaps.append((gap_start, gap_end))

        if self.targeted_call_frequencies:
            min_targeted = min(self.targeted_call_frequencies)
            max_targeted = max(self.targeted_call_frequencies)
            adjusted_gaps = []
            for gap_start, gap_end in gaps:
                if gap_start < min_targeted < gap_end:
                    adjusted_gaps.append((gap_start, min_targeted))
                if gap_start < max_targeted < gap_end:
                    adjusted_gaps.append((max_targeted, gap_end))
                if not (gap_start < min_targeted < gap_end or gap_start < max_targeted < gap_end):
                    adjusted_gaps.append((gap_start, gap_end))
            gaps = adjusted_gaps

        if not gaps:
            return None

        largest_gap = max(gaps, key=lambda x: x[1] - x[0])
        suggested_freq = (largest_gap[0] + largest_gap[1]) / 2
        suggested_freq = max(freq_min, min(freq_max, suggested_freq))

        return int(suggested_freq)
    
    def handle_setting_packet(self, addr_port):
        if (
            self.band is not None and 
            self.synched_band == self.band
        ):
            try:         
                log.info(f"SettingPacket received from {addr_port}")             
                synch_time = datetime.fromisoformat(self.the_packet.synch_time)
                if (
                    self.synched_settings is None or 
                    self.synch_time is None or 
                    self.synch_time < synch_time
                ):
                    self.synched_settings = json.loads(self.the_packet.settings_json)
                    wanted_callsigns    = self.synched_settings.get('wanted_callsigns')
                    wanted_cq_zones     = self.synched_settings.get('wanted_cq_zones')
                    excluded_callsigns  = self.synched_settings.get('excluded_callsigns')
                    excluded_cq_zones   = self.synched_settings.get('excluded_cq_zones')
                    enable_sending_reply = self.synched_settings.get('enable_sending_reply')
                    """
                        Make sure to set synch_time after we checked if wanted_callsigns is valid
                    """
                    if (
                        wanted_callsigns    and isinstance(wanted_callsigns, (list, tuple)) or
                        wanted_cq_zones     and isinstance(wanted_cq_zones, (list, tuple))  or
                        excluded_callsigns  and isinstance(excluded_callsigns, (list, tuple)) or
                        excluded_cq_zones   and isinstance(excluded_cq_zones, (list, tuple))
                    ):
                        self.synch_time = synch_time

                        # Update enable_sending_reply if provided
                        if enable_sending_reply is not None:
                            self.enable_sending_reply = enable_sending_reply
                            self.monitoring_settings.set_sending_reply(enable_sending_reply)

                        self.message_callback({
                            'type'     : 'instance_settings',
                            'settings' : self.synched_settings
                        })
                        log.info(f"SettingPacket has been processed")     
            except Exception as e:
                log.error(f"Error processing SettingPacket: {e}")          
        else:
            self.synched_settings = None
            log.error(f"Can't handle SettingPacket yet.")     

    def handle_decode_packet(self):
        if self.enable_log_packet_data:
                log.debug('{}'.format(self.the_packet))

        """
            Start to handle DecodePacket
        """
        try:
            message_type                 = None 

            reply_to_packet              = False
            self.packet_counter         += 1
            packet_id                    = self.packet_counter
            self.packet_store[packet_id] = self.the_packet

            max_packets                  = 1_000
            if len(self.packet_store) > max_packets:
                oldest_packet_id = min(self.packet_store.keys())
                del self.packet_store[oldest_packet_id]

            message         = self.the_packet.message
            snr             = self.the_packet.snr
            delta_t         = self.the_packet.delta_t
            delta_f         = self.the_packet.delta_f     

            decode_time     = self.the_packet.time
            decode_time_str = decode_time.strftime('%Y-%m-%d %H:%M:%S')            

            time_str        = decode_time.strftime('%H%M%S')
            time_now        = datetime.now(timezone.utc).replace(tzinfo=None)        

            formatted_message = f"{time_str} {snr:+d} {delta_t:+.1f} {delta_f} ~ {message}"

            log.debug("DecodePacket: {}".format(formatted_message))

            """
                Parse message
            """
            parsed_messages = parse_wsjtx_message(
                message,
                self.lookup, # need lookup to parse message
                self.wanted_callsigns,
                self.worked_callsigns.get(self.band, {}),
                self.excluded_callsigns,
                self.monitored_callsigns,
                self.wanted_cq_zones,
                self.monitored_cq_zones,
                self.excluded_cq_zones
            )

            for parsed_message in parsed_messages:
                cleaned_message   = parsed_message['cleaned_message']
                q_tag             = parsed_message['q_tag']

                directed          = parsed_message['directed']
                callsign          = parsed_message['callsign']
                callsign_info     = parsed_message['callsign_info']
                callsign_wkb4     = False
                marathon          = False
                priority          = 0
                priority_type     = None

                grid              = parsed_message['grid']
                grid_updated      = parsed_message['grid_updated']  
                report            = parsed_message['report']
                msg               = parsed_message['msg']
                cqing             = parsed_message['cqing']
                exactly_matched   = parsed_message['exactly_matched']
                wanted            = parsed_message['wanted']
                wanted_cq_zone    = parsed_message['wanted_cq_zone']
                excluded          = parsed_message['excluded']
                monitored         = parsed_message['monitored']
                monitored_cq_zone = parsed_message['monitored_cq_zone']

                current_year      = str(datetime.now().year)

                wkb4_year         = None
                entity_wkb4       = False
                wanted_grid       = False 

                if callsign_info:
                    entity_code   = callsign_info.get('entity_code') 
                    lotw          = callsign_info.get('lotw', None) 
                else:
                    entity_code   = None
                    lotw          = None       

                debug_message     = None
                                        
                """
                    Check if wanted and is Worked b4
                """
                if self.adif_data.get('wkb4'):
                    wkb4_year = get_wkb4_year(self.adif_data['wkb4'], callsign, self.band)                    
                    if (
                        (
                            wkb4_year is not None and 
                            self.worked_before_preference == WKB4_REPLY_MODE_NEVER
                        ) or 
                        (
                            wkb4_year == datetime.now().year and
                            self.worked_before_preference == WKB4_REPLY_MODE_CURRENT_YEAR
                        )
                    ):
                        wanted         = exactly_matched
                        wanted_cq_zone = False
                        callsign_wkb4  = True

                """
                    Check if entity code is already worked for marathon
                """
                if (
                    self.enable_marathon 
                    and self.adif_data.get('entity') 
                    and entity_code
                ):     
                    entity_wkb4 = self.is_entity_worked_b4(entity_code, current_year)

                """
                    Check if entity code is needed for marathon
                """
                if (
                    self.enable_marathon 
                    and self.adif_data.get('entity')
                    and not entity_wkb4
                    and entity_code 
                    and not wanted
                    and not wanted_cq_zone
                ):      
                    marathon = self.is_callsign_needed_for_marathon(
                        callsign,
                        callsign_wkb4,
                        wkb4_year,
                        entity_code,
                        current_year
                    )       
                    if marathon:
                        log.info(f"Focus on [ {callsign} ] for marathon on [ {self.band} ]")
                        reply_to_packet = True
                
                """
                    Check if grid is needed
                """
                # Single condition for grid tracking
                if (
                    self.enable_grid_tracker 
                    and self.adif_data.get('grid')
                    and not callsign_wkb4 
                    and is_valid_grid(grid, callsign_info)
                    and not wanted
                    and not wanted_cq_zone
                    and (
                        self.grid_tracker_preference.get(self.band) or
                        self.enable_grid_reply_new_grid
                    )
                    and not (
                        wkb4_year is not None 
                        and grid_updated is None
                        )
                ):
                    # Check if callsign already exists for this grid on this band
                    grid_qsos = self.adif_data.get('grid', {}).get(self.band, {}).get(grid, [])
                    callsign_already_worked_on_grid = any(
                        qso.get('call') == callsign for qso in grid_qsos
                    )

                    if (
                        not callsign_already_worked_on_grid and
                        is_grid_needed(
                            self.adif_data,
                            grid,
                            self.band,
                            self.grid_tracker_preference.get(self.band),
                            self.enable_grid_reply_unconfirmed,
                            self.enable_grid_reply_new_grid
                        ) 
                    ):
                        log.info(f"Focus on [ {callsign} ] for grid [ {grid} ] on [ {self.band} ]")
                        wanted_grid     = True
                        reply_to_packet = True                        

                """
                    Ignore if callsign is not valid
                """
                if (
                    self.enable_reply_to_valid_callsign 
                    and entity_code is None
                    and not exactly_matched
                    and (
                        wanted 
                        or wanted_cq_zone
                    )
                ):
                    log.warning(f"[ {callsign} ] not valid callsign, skipping")
                    wanted         = False
                    wanted_cq_zone = False
                    wanted_grid    = False

                if wanted:
                    log.info(f"Focus on [ {callsign} ] as wanted on [ {self.band} ]")  

                if wanted_cq_zone:
                    log.info(f"Focus on [ {callsign} ] as wanted CQ Zone on [ {self.band} ]")                      

                """
                    Handle directional QSO
                """                
                if (
                    self.enable_reply_to_valid_direction
                    and directed
                    and (
                        wanted
                        or wanted_grid
                        or wanted_cq_zone
                        or marathon
                    )
                    and not self.is_direction_match_my_cont(
                        cqing,
                        callsign,
                        directed
                    )
                ):                       
                    log.error(f"Skipping [ {callsign} ] as it is not calling for [ {self.my_cont} ]")
                    wanted          = False
                    wanted_cq_zone  = False
                    reply_to_packet = False
                    marathon        = False
                    wanted_grid     = False
                    monitored       = True if exactly_matched else False

                """
                    Ignore if callsign is not a LoTW user
                """
                if (
                    (
                        wanted
                        or wanted_cq_zone
                        or wanted_grid
                    )
                    and not exactly_matched 
                    and not lotw 
                    and not marathon
                    and self.enable_reply_to_lotw_only 
                ):
                    log.debug(f"Skipping [ {callsign} ] as it is not a LoTW user")
                    reply_to_packet = False
                    wanted          = False
                    wanted_cq_zone  = False
                    wanted_grid     = False

                """
                    Callsign already logged, we can move over new Wanted callsign
                """
                if (callsign == self.targeted_call and
                    directed != self.my_call and
                    callsign in self.worked_callsigns.get(self.band, {})
                ):
                    self.reset_targeted_call()
                
                """
                    Might reset values to focus on another wanted callsign
                """
                if (                    
                    self.targeted_call is not None 
                    and callsign != self.targeted_call 
                    and not (wanted and wanted_cq_zone)
                ):
                    if (
                        self.qso_time_on.get(self.targeted_call) and
                        (time_now - self.qso_time_on.get(self.targeted_call)).total_seconds() >= self.max_working_delay_seconds            
                    ):
                        log.warning(f"Waiting for [ {self.targeted_call} ] but we are about to switch on [ {callsign} ]")
                        self.reset_targeted_call()
                    
                    attempts_limit = self.get_watchdog_attempts_limit()
                    if len(self.reply_attempts.get(self.targeted_call) or []) >= attempts_limit:
                        log.warning(f"{len(self.reply_attempts[self.targeted_call])} attempts for [ {self.targeted_call} ] but we are about to switch on [ {callsign} ]")
                        if self.enable_watchdog:
                            self.add_watchdog_exclusion(self.targeted_call)
                        self.reset_targeted_call()

                    if (
                        directed == self.my_call 
                        and self.qso_time_on.get(self.targeted_call) is None
                    ):
                        log.warning(f"No answer yet for [ {self.targeted_call} ] but we are about to switch on [ {callsign} ]")
                        self.reset_targeted_call()

                """
                    How to handle RR73 / 73 / RRR messages
                """
                if directed == self.my_call and msg in {'RR73', '73', 'RRR'}:
                    if self.targeted_call is not None and callsign != self.targeted_call:
                        log.error(f"Received |{msg}| from [ {callsign} ] but ongoing callsign is [ {self.targeted_call} ]")
                        message_type = 'error_occurred'

                    if self.targeted_call == callsign or self.enable_log_all_valid_contact:
                        self.call_ready_to_log = callsign 
                        log.warning("Found message to log [ {} ]".format(self.call_ready_to_log))
                        self.qso_time_off[self.call_ready_to_log] = decode_time

                        if callsign not in self.worked_callsigns.get(self.band, {}):
                            message_type = 'ready_to_log'  
                            # Make sure to not log again this callsign once QSO done    
                            if not self.worked_callsigns.get(self.band):
                                self.worked_callsigns[self.band] = []                        
                            self.worked_callsigns[self.band].append(callsign)                   

                            self.log_qso_to_adif()
                            self.log_qso_to_udp()
                            """
                                Update marathon data and clear all related Wanted callsigns
                            """
                            if (
                                entity_code 
                                and self.enable_marathon 
                                and self.adif_data.get('entity') 
                                and self.marathon_preference.get(self.band)
                            ):
                                self.clear_wanted_callsigns(entity_code)  
                        else:
                            message_type = 'directed_to_my_call'

                        """
                            Clean Wanted callsigns
                        """  
                        self.call_ready_to_log = None
                        if msg in {'RR73', 'RRR'}:
                            # 7 = Hound mode
                            if self.special_op_mode == 7:
                                pass
                            else:
                                reply_to_packet = True
                        elif msg == '73':
                            self.reset_targeted_call()

                        if callsign in self.wanted_callsigns:
                            self.wanted_callsigns.remove(callsign)   
                        
                    elif self.targeted_call is not None:
                        log.error(f"Received |{msg}| from [ {callsign} ] but ongoing callsign is [ {self.targeted_call} ]")
                        message_type = 'error_occurred'   

                elif directed == self.my_call:
                    """
                        How to handle message directed to my call
                    """ 
                    log.warning(f"Found message directed to my call [ {directed} ] from [ {callsign} ]")
                    
                    message_type = 'directed_to_my_call'
                    
                    self.rst_rcvd_from_being_called[callsign]   = report                                   
                    self.qso_time_on[callsign]                  = decode_time
                    if not self.grid_being_called.get(callsign):
                        self.grid_being_called[callsign]        = grid or '' 

                    if wanted or wanted_cq_zone:    
                        focus_info = f"Report [ {report} ]" if report else f"Grid [ {grid} ]"
                        log.warning(f"Focus on callsign [ {callsign} ]\t{focus_info}")
                        # We can't use self.the_packet.mode as it returns "~"
                        # self.mode             = self.the_packet.mode
                        reply_to_packet = True
                        message_type = 'wanted_callsign_being_called'  
                    # We need to end this 
                    elif self.call_ready_to_log == callsign and self.rst_sent.get(self.call_ready_to_log):  
                        reply_to_packet = True
                    elif self.rst_sent.get(callsign):
                        count_attempts = len(self.reply_attempts.get(callsign, []))
                        log.warning(f"Found unexpected message from callsign [ {callsign} ]")
                        if count_attempts < DEFAULT_REPLY_ATTEMPTS:
                            reply_to_packet = True    
                    elif self.enable_polite_reply:
                        reply_to_packet = True
                elif wanted or wanted_cq_zone: 
                    reply_to_packet = True
                    
                    message_type = 'wanted_callsign_decoded'
                    if callsign not in self.first_time_decoded:
                        self.first_time_decoded.append(callsign)
                        message_type = 'wanted_callsign_first_time_decoded'

                    if self.enable_gap_finder:
                        self.targeted_call_frequencies.add(delta_f)     
                                
                    if cqing:
                        debug_message = f"Found CQ message from callsign [ {callsign} ]."                        
                    else:
                        debug_message = "Found message directed to [ {} ] from callsign [ {} ]. Message: {}".format(directed, callsign, msg)
                    
                    if debug_message:
                        log.warning(debug_message)

                    # Use message_callback to communicate with the GUI
                    if self.enable_debug_output:
                        self.message_callback({
                            'type': 'debug',
                            'message': debug_message
                        })

                elif monitored or monitored_cq_zone:
                    message_type = 'monitored_callsign_decoded'   
                elif self.targeted_call is not None:
                    if (
                        self.reply_attempts.get(self.targeted_call) and
                        (decode_time - self.reply_attempts[self.targeted_call][-1]).total_seconds() >= self.max_working_delay_seconds            
                    ):
                        message_type = 'lost_targeted_callsign'
                        log.warning(f"Lost focus for callsign [ {self.targeted_call} ]")        
                        self.targeted_call = None  
                        self.halt_packet()


                if (
                    reply_to_packet
                    and message_type != 'ready_to_log'
                ):
                    """
                        Exclude if needed
                    """
                    if (
                        not exactly_matched
                        and directed != self.my_call
                        and callsign not in self.excluded_callsigns
                        and len(self.reply_attempts.get(self.targeted_call) or []) >= self.get_watchdog_attempts_limit()
                    ):
                        if self.enable_watchdog and self.targeted_call:
                            self.add_watchdog_exclusion(self.targeted_call)
                        self.reply_attempts[callsign] = []
                        log.error(f"Add [ {callsign} ] to temporarily excluded")
                        self.message_callback({
                            'type': 'temporarily_excluded',
                            'callsign': callsign
                        })
                        reply_to_packet = False

                    """
                        Ignore if temporarily excluded by Watchdog,
                        unless the callsign is replying directly to us — in that
                        case drop the exclusion and let the QSO proceed.
                    """
                    if self.enable_watchdog and self.is_watchdog_excluded(callsign):
                        if directed == self.my_call:
                            self.lift_watchdog_exclusion(callsign, reason='direct reply received')
                        else:
                            log.debug(f"Skipping [ {callsign} ] — watchdog retry window active")
                            reply_to_packet = False
                            wanted          = False
                            wanted_grid     = False
                            wanted_cq_zone  = False
                            message_type    = 'callsign_excluded'

                    """
                        Ignore if excluded
                    """
                    if excluded:
                        log.debug(f"Skipping [ {callsign} ] as it is set as excluded [ {excluded} ]")
                        reply_to_packet = False
                        wanted          = False
                        wanted_grid     = False
                        wanted_cq_zone  = False
                        message_type    = 'callsign_excluded'

                    if self.is_ftx_mode() and directed != self.my_call:
                        """
                            Ignore if DT is above normal values
                        """
                        if abs(delta_t) > MAXIMUM_ALLOWED_DT and callsign != self.targeted_call:
                            log.error(f"DT is above normal for [ {callsign } ]. DT: [ {round(delta_t, 1)}s ]")
                            message_type    = 'dt_above_normal'
                            reply_to_packet = False          

                        """
                            Check SNR
                        """
                        if snr < self.minimum_report_for_reply:
                            log.error(f"SNR value is below than the expected minimum [ {self.minimum_report_for_reply}dB ] for [ {callsign } ]. SNR: [ {snr}dB ]")
                            message_type    = 'snr_below_minimum'
                            reply_to_packet = False                            
                    
                    if not reply_to_packet:
                        monitored = True if exactly_matched else False   

                """
                    Check priority
                """
                if reply_to_packet and self.enable_sending_reply:
                    priority, priority_type = self.process_reply_packet_buffer({           
                        'packet_id'         : packet_id,                   
                        'decode_time'       : decode_time,
                        'callsign'          : callsign,
                        'directed'          : directed,
                        'wanted'            : wanted,
                        'wanted_cq_zone'    : wanted_cq_zone,
                        'wanted_grid'       : wanted_grid,
                        'marathon'          : marathon,
                        'lotw'              : lotw,
                        'snr'               : snr,
                        'wkb4_year'         : wkb4_year,
                        'grid'              : grid,
                        'cqing'             : cqing,
                        'msg'               : msg
                    }) 

                    """
                        Add callsign to wanted callsigns if not already in it
                    if (
                        callsign not in self.wanted_callsigns
                        and (marathon or wanted_grid)
                    ):
                        self.message_callback({    
                            'type'          : 'update_wanted_callsign',
                            'callsign'      : callsign,
                            'action'        : 'add'
                        })   
                    """
                elif message_type:
                    priority = 1

                """
                    Send messages to GUI                    
                """
                if reply_to_packet and message_type is None:
                    message_type = 'wanted_callsign_decoded'

                # log.debug(f"Priority for: {formatted_message} for {callsign:<15}\nWorkedB4\t= {callsign_wkb4}\nCallsignInfo\t= {callsign_info}\nEntityCode\t= {entity_code}\nEntityWkB4\t= {entity_wkb4}\nWanted\t\t= {wanted}\nWantedCQZone\t= {wanted_cq_zone}\nMarathon\t= {marathon}\nExcluded\t= {excluded}\nMonitored\t= {monitored}")

                self.message_callback({           
                'wsjtx_id'          : self.the_packet.wsjtx_id,
                'my_call'           : self.my_call, 
                'packet_id'         : packet_id,     
                'decode_time'       : decode_time,              
                'decode_time_str'   : decode_time_str,
                'excluded'          : excluded,
                'callsign'          : callsign,
                'callsign_info'     : callsign_info,
                'grid'              : grid,
                'directed'          : directed,
                'wanted'            : wanted,
                'wanted_cq_zone'    : wanted_cq_zone,
                'wanted_grid'       : wanted_grid,
                'monitored'         : monitored,
                'monitored_cq_zone' : monitored_cq_zone,
                'exactly_matched'   : exactly_matched,
                'wkb4_year'         : wkb4_year,
                'entity_wkb4'       : entity_wkb4,
                'delta_time'        : delta_t,
                'delta_freq'        : delta_f,
                'snr'               : snr,                
                'message'           : cleaned_message,
                'message_uid'       : str(uuid.uuid4()), 
                'message_type'      : message_type,
                'priority'          : priority,
                'priority_type'     : priority_type,
                'formatted_message' : formatted_message
            })        

        except TypeError as e:
            log.error("Caught a type error in parsing packet: {}; error {}\n{}".format(
            self.the_packet.message, e, traceback.format_exc()))
        except Exception as e:
            log.error("Caught an error parsing packet: {}; error {}\n{}".format(
                self.the_packet.message, e, traceback.format_exc()))   
            
    def get_priority_bonus(self, filtered_message):
        priority_bonus = 0
        priority_type = None
        
        for i, property_name in enumerate(self.priority_order):
            if filtered_message.get(property_name, False):
                priority_bonus = len(self.priority_order) - i
                priority_type = property_name
                break
                
        return priority_bonus, priority_type
            
    def get_sorted_keys(self):
        return lambda message: (
            # First select highest priority
            message['priority'],
            # If wkb4_year is None, return inf, which ranks this message before those with a numerical year
            float('inf') if message.get('wkb4_year') is None else -message['wkb4_year'],
            # If LoTW is not None, return 1
            1 if message.get('lotw') else 0,
            message['snr'],
            # In case of a tie on the first two criteria, the message with the lowest packet_id (the first received) is selected
            -message['packet_id']
        )

    def process_reply_packet_buffer(self, message):         
        """
            Add this message to buffer
        """    
        self.reply_message_buffer.append(message)

        filtered_messages = [
            message_in_buffer for message_in_buffer in self.reply_message_buffer if message_in_buffer['decode_time'].strftime('%H%M%S') == message['decode_time'].strftime('%H%M%S')
        ]
        
        """
            Handle priority: Make sure to keep priority higher
            than the one being used, for monitored messages
        """        
        highest_priority = len(self.priority_order)

        for filtered_message in filtered_messages:
            if filtered_message['directed'] == self.my_call:
                if filtered_message['callsign'] == self.targeted_call:
                    filtered_message['priority'] = highest_priority + 1
                else:
                    filtered_message['priority'] = highest_priority
            else:
                if filtered_message.get('cqing'):
                    filtered_message['priority'] = 1
                else:
                    filtered_message['priority'] = 0                    

            priority_bonus, priority_type = self.get_priority_bonus(filtered_message)
            filtered_message['priority'] += priority_bonus
            filtered_message['priority_type'] = priority_type
        """
            Selects the message with the highest priority
        """      
        selected_message = max(filtered_messages, key=self.get_sorted_keys(), default=None)

        """
            Clear buffer
        """
        self.reply_message_buffer = deque(
            [same_time_message for same_time_message in self.reply_message_buffer
                if abs((same_time_message['decode_time'] - message['decode_time']).total_seconds()) <= 120]
        )   

        """
            Get priority of the current message
        """
        priority = -1
        for filtered_message in filtered_messages:
            if filtered_message['packet_id'] == message['packet_id']:
                priority = filtered_message['priority']
                priority_type = filtered_message['priority_type']
                break

        """
            Proceed with selected message
        """               
        if selected_message and (
            self.last_selected_message is None or
            selected_message['priority'] > self.last_selected_message['priority'] or
            selected_message['packet_id'] != self.last_selected_message['packet_id']
        ):
            # Handle a timer to avoid multiple call for self.process_pending_reply
            if hasattr(self, '_reply_timer') and self._reply_timer:
                self._reply_timer.cancel()

            self._reply_timer = threading.Timer(
                WAITING_TIME_BEFORE_REPLY,
                self.process_pending_reply,
                args=[selected_message, filtered_messages] 
            )
            self._reply_timer.start()
          
        return priority, priority_type
                
    def process_pending_reply(self, selected_message, filtered_messages):    
        if filtered_messages:
            log.info(f"Selected messages ({len(filtered_messages)}):\n\t{"\n\t".join([
                self.format_log_message(message) for message in sorted(filtered_messages, key=self.get_sorted_keys(), reverse=True)
            ])}")

        callsign        = selected_message.get('callsign')
        packet_id       = selected_message.get('packet_id')
        
        callsign_packet = self.packet_store[packet_id]

        self.targeted_call = callsign

        if callsign not in self.reply_attempts:
            self.reply_attempts[callsign] = []

        attempts_limit = self.get_watchdog_attempts_limit()
        if (
            self.enable_watchdog
            and len(self.reply_attempts[callsign]) >= attempts_limit
        ):
            log.warning(f"Watchdog limit ({attempts_limit}) reached for [ {callsign} ] — skipping reply")
            self.add_watchdog_exclusion(callsign)
            self.reset_targeted_call()
            self.last_selected_message = selected_message
            return

        if callsign_packet.time not in self.reply_attempts[callsign]:
            self.reply_attempts[callsign].append(callsign_packet.time)
            count_attempts = len(self.reply_attempts[callsign])
            if count_attempts >= (attempts_limit - 1):
                log.warning(f"{count_attempts}/{attempts_limit} attempts for [ {callsign} ]")
        """
            Update frequency if necessary
        """
        if (
            self.enable_gap_finder and
            self.suggested_frequency is None
        ):
            self.targeted_call_period   = self.odd_or_even_period()
            my_period                   = ODD if self.targeted_call_period == EVEN else EVEN
            self.suggested_frequency    = self.get_frequency_suggestion(my_period)
            if self.suggested_frequency is not None:
                self.set_delta_f_packet(self.suggested_frequency)

        self.reply_to_packet(callsign_packet)
        self.last_selected_message = selected_message

    def halt_packet(self):
        if self._instance == SLAVE:
            return        
        
        if self.the_packet:
            log.warning("Build HaltPacket")
            try:
                halt_pkt = pywsjtx.HaltTxPacket.Builder(self.the_packet.wsjtx_id)             
                self.s.send_packet(self.origin_addr_port, halt_pkt)         
                log.debug(f"Sent HaltPacket: {halt_pkt}")         
            except Exception as e:
                log.error(f"Error sending packets: {e}\n{traceback.format_exc()}")

    def reply_to_packet(self, callsign_packet):
        if self._instance == SLAVE:
            return        
        
        try:            
            self.reply_to_packet_time = datetime.now(timezone.utc)            
            reply_pkt = pywsjtx.ReplyPacket.Builder(callsign_packet)
            self.s.send_packet(self.origin_addr_port, reply_pkt)         
            log.debug(f"[ {callsign_packet.wsjtx_id} ] Sent ReplyPacket: {reply_pkt}")            
        except Exception as e:
            log.error(f"Error sending packets: {e}\n{traceback.format_exc()}")

    def set_delta_f_packet(self, frequency):  
        if self._instance == SLAVE:
            return        
      
        try:
            delta_f_paquet = pywsjtx.SetTxDeltaFreqPacket.Builder(self.the_packet.wsjtx_id, frequency)
            log.warning(f"Sending SetTxDeltaFreqPacket (Df={frequency}hz): {delta_f_paquet}")
            self.s.send_packet(self.origin_addr_port, delta_f_paquet)
        except Exception as e:
            log.error(f"Error sending packets: {e}\n{traceback.format_exc()}")

    def configure_packet(self):
        configure_paquet = pywsjtx.ConfigurePacket.Builder(self.the_packet.wsjtx_id, "FT4")
        log.warning(f"Sending ConfigurePacket: {configure_paquet}")
        self.s.send_packet(self.origin_addr_port, configure_paquet)        

    def clear_wanted_callsigns(self, entity_code):
        entity_callsigns = self.wanted_callsigns_per_entity.get(self.band, {}).get(entity_code, [])

        for callsign in entity_callsigns:
            self.message_callback({        
            'type'              : 'update_wanted_callsign',
            'callsign'          : callsign,
            'action'            : 'remove'
        })       
        
        if entity_code in self.wanted_callsigns_per_entity.get(self.band, {}):
            del self.wanted_callsigns_per_entity[self.band][entity_code]     
            # save_marathon_wanted_data(MARATHON_FILE, self.wanted_callsigns_per_entity)                
                                
    def log_qso_to_adif(self):
        if self.last_logged_call == self.call_ready_to_log:
            return

        callsign        = self.call_ready_to_log
        grid            = self.grid_being_called.get(self.call_ready_to_log, '')
        mode            = self.mode
        rst_sent        = get_clean_rst(self.rst_sent.get(self.call_ready_to_log, '?'))
        rst_rcvd        = get_clean_rst(self.rst_rcvd_from_being_called.get(self.call_ready_to_log, '?'))
        freq_rx         = f"{round((self.frequency + self.rx_df) / 1_000_000, 6):.6f}"
        freq            = f"{round((self.frequency + self.tx_df) / 1_000_000, 6):.6f}"
        band            = self.band
        my_call         = self.my_call

        try:
            if (
                self.qso_time_off.get(self.call_ready_to_log) and
                not self.qso_time_on.get(self.call_ready_to_log)
            ):
                self.qso_time_on[self.call_ready_to_log] = self.qso_time_off[self.call_ready_to_log]

            qso_date        = self.qso_time_on[self.call_ready_to_log].strftime('%Y%m%d')
            qso_time_on     = self.qso_time_on[self.call_ready_to_log].strftime('%H%M%S')
            qso_time_off    = self.qso_time_off[self.call_ready_to_log].strftime('%H%M%S')

            adif_entry = " ".join([
                f"<call:{len(callsign)}>{callsign}",
                f"<gridsquare:{len(grid)}>{grid}",
                f"<mode:{len(mode)}>{mode}",
                f"<rst_sent:{len(rst_sent)}>{rst_sent}",
                f"<rst_rcvd:{len(rst_rcvd)}>{rst_rcvd}",
                f"<qso_date:{len(qso_date)}>{qso_date}",
                f"<time_on:{len(qso_time_on)}>{qso_time_on}",
                f"<time_off:{len(qso_time_off)}>{qso_time_off}",
                f"<band:{len(str(band))}>{band}",
                f"<freq:{len(str(freq))}>{freq}",
                f"<freq_rx:{len(str(freq_rx))}>{freq_rx}",
                f"<station_callsign:{len(my_call)}>{my_call}",
                f"<my_gridsquare:{len(self.my_grid)}>{self.my_grid}",
                f"<eor>\n"
            ])

            # Store the ADIF entry for reuse by other functions
            self.last_adif_entry = adif_entry

            with open(self.adif_worked_backup_file_path, "a") as adif_file:
                adif_file.write(adif_entry)
            log.warning("QSO Logged [ {} ]".format(self.call_ready_to_log))

            # Upload to Club Log if enabled
            if self.club_log_uploader:
                try:
                    success, message = self.club_log_uploader.upload_qso(adif_entry)
                    if success:
                        self.club_log_uploader.update_cache(callsign, band)
                        log.info(f"Club Log upload successful for {callsign}: {message}")
                    else:
                        log.error(f"Club Log upload failed for {callsign}: {message}")
                        if "Authentication failed" in message:
                            self.club_log_uploader = None
                except Exception as club_log_error:
                    log.error(f"Club Log upload error for {callsign}: {club_log_error}")

            if self.enable_lotw_upload and self.lotw_uploader:
                self.log_qso_to_lotw()

        except Exception as e:
            log.error(f"Can't write ADIF file {e}\n{traceback.format_exc()}")

        # Keep this callsign to ensure we are not breaking auto-sequence 
        self.last_logged_call = callsign            

    def log_qso_to_udp(self):
        if not self.enable_logging_udp_server:
            return        
        try:
            awaited_rst_sent = get_clean_rst(self.rst_sent.get(self.call_ready_to_log, '?')) 
            awaited_rst_rcvd = get_clean_rst(self.rst_rcvd_from_being_called.get(self.call_ready_to_log, '?')) 

            empty_string = ''

            log_pkt = pywsjtx.QSOLoggedPacket.Builder(
                self.the_packet.wsjtx_id,
                self.qso_time_off.get(self.call_ready_to_log),
                self.call_ready_to_log,
                self.grid_being_called.get(self.call_ready_to_log),
                self.frequency,
                self.mode,
                awaited_rst_sent,
                awaited_rst_rcvd,
                empty_string, 
                empty_string,
                empty_string,
                self.qso_time_on.get(self.call_ready_to_log),
                empty_string,
                self.my_call,
                self.my_grid,
                awaited_rst_sent,
                awaited_rst_rcvd
            )

            pywsjtx.extra.simple_server.SimpleServer().send_packet((
                self.logging_udp_server_address,
                self.logging_udp_server_port
            ), log_pkt)    

            log.debug(f"QSOLoggedPacket sent via UDP for [ {self.call_ready_to_log} ] to {(
                self.logging_udp_server_address,
                self.logging_udp_server_port
            )}")
        except Exception as e:
            log.error(f"Error sending QSOLoggedPacket via UDP: {e}")
            log.error("Caught an error while trying to send QSOLoggedPacket packet: error {}\n{}".format(e, traceback.format_exc()))

    def log_qso_to_lotw(self):
        if not self.enable_lotw_upload or not self.lotw_uploader:
            return

        # Reuse the ADIF entry created by log_qso_to_adif
        if not hasattr(self, 'last_adif_entry') or not self.last_adif_entry:
            log.error("No ADIF entry available for LoTW upload")
            return

        try:
            callsign = self.call_ready_to_log
            band = self.band

            # Remove the trailing newline from the ADIF entry and add <eor> if needed
            adif_entry = self.last_adif_entry.strip()
            if not adif_entry.endswith('<eor>'):
                adif_entry += ' <eor>'

            # Prepend ADIF header
            adif_with_header = "ADIF Export\n<ADIF_VER:5>3.1.0\n<PROGRAMID:17>Wait and Pounce\n<EOH>\n" + adif_entry

            log.warning(f"Uploading QSO with {callsign} to LoTW")
            success, message = self.lotw_uploader.upload_qso(adif_with_header)

            if success:
                self.lotw_uploader.update_cache(callsign, band)
                log.info(f"LoTW upload successful for {callsign}: {message}")
            else:
                log.error(f"LoTW upload failed for {callsign}: {message}")
                if "TQSL executable not found" in message or "Authentication failed" in message:
                    self.lotw_uploader = None
                    self.enable_lotw_upload = False

        except Exception as lotw_error:
            log.error(f"LoTW upload error for {self.call_ready_to_log}: {lotw_error}")
            log.error(f"LoTW upload exception: {traceback.format_exc()}")

    def is_ftx_mode(self):
        return self.mode in ["FT8", "FT4"]

    def is_direction_match_my_cont(
            self,
            cqing,
            callsign,
            directed
        ):
        if cqing:
            self.wanted_callsigns_direction[callsign] = directed
            if is_valid_continent(directed) and directed != self.my_cont:                
                return False
            elif directed == "DX" and self.lookup.lookup_callsign(callsign).get('cont', None) == self.my_cont:
                return False
            else:
                return True
        elif (
            self.wanted_callsigns_direction.get(callsign) 
            and self.wanted_callsigns_direction.get(callsign) != self.my_cont
        ):
            if is_valid_continent(directed) and directed != self.my_cont: 
                return False
            elif self.lookup.lookup_callsign(directed).get('cont', None) != self.wanted_callsigns_direction.get(callsign):
                log.warning(f"Reset direction for [ {callsign} ]")
                self.wanted_callsigns_direction.pop(callsign)
                return True
        else:
            return True

    def is_entity_worked_b4(
            self,
            entity_code,
            current_year
        ):
        if entity_code in self.adif_data.get('entity', {}).get(current_year, {}).get(self.band, {}):
            return True
        else:
            return False

    def is_entity_worked_unlimited_marathon(
            self,
            entity_code,
            current_year
        ):
        year_data = self.adif_data.get('entity', {}).get(current_year, {})

        for band, entities in year_data.items():
            if entity_code in entities:
                return True

        return False

    def is_callsign_needed_for_marathon(
            self,
            callsign,
            callsign_wkb4,
            wkb4_year,
            entity_code,
            current_year
        ):        
        marathon = False

        # entity_wkb4 not worked before
        if callsign_wkb4 and self.worked_before_preference == WKB4_REPLY_MODE_NEVER:
            log.warning(f"Skipping [ {callsign} ] as it is wkb4 [ {wkb4_year}]")
        elif callsign in self.wanted_callsigns_per_entity.get(self.band, {}).get(entity_code, {}):
            marathon = True
        elif self.marathon_preference.get(MARATHON_UNLIMITED):
            if self.is_entity_worked_unlimited_marathon(
                entity_code,
                current_year
            ):
                log.debug(f"Skipping [ {callsign} ] as entity [ {entity_code} ] already worked in unlimited marathon")
            else:
                marathon = True
        elif entity_code not in self.adif_data.get('entity', {}).get(current_year, {}).get(self.band, {}):
            marathon = True
            
        if marathon:         
            if not self.wanted_callsigns_per_entity.get(self.band):
                self.wanted_callsigns_per_entity[self.band] = {}

            if not self.wanted_callsigns_per_entity[self.band].get(entity_code):
                self.wanted_callsigns_per_entity[self.band][entity_code] = []

            if callsign not in self.wanted_callsigns_per_entity[self.band][entity_code]:
                self.wanted_callsigns_per_entity[self.band][entity_code].append(callsign)
                # save_marathon_wanted_data(MARATHON_FILE, self.wanted_callsigns_per_entity)

            log.warning(f"Found [ {callsign} ] for marathon [ {entity_code} ]")                           

        return marathon

    def format_log_message(self, message):
        decode_time = message.get('decode_time')
        if hasattr(decode_time, 'strftime'):
            decode_time_str = decode_time.strftime("%H%M%S")
        else:
            decode_time_str = str(decode_time)

        if message.get('directed') is not None:
            directed_or_grid = message.get('directed')

            if message.get('directed') == self.my_call:
                directed_or_grid+= ""
        else:
            if message.get('cqing'):
                directed_or_grid = "CQ"
            else:
                directed_or_grid = message.get('grid') if message.get('grid') is not None else ''         

        if message.get('wkb4_year') is not None:
            wkb4_year = f"wkb4y:{message.get('wkb4_year')}"
        else:
            wkb4_year = ""
        
        lotw = "*" if message.get('lotw') else " "

        snr = f'+{message.get("snr")}' if message.get('snr') >= 0 else message.get('snr')

        return (            
            f"[ {message.get('priority')} ] {decode_time_str} "
            f"de:{message.get('callsign'):<10}{lotw}"
            f"\tdir:{directed_or_grid:<4}" 
            f"\tsnr:{snr:<6}"
            f"\tpid:{message.get('packet_id'):<6}"
            f"\t{wkb4_year}"                                           
        )        
    
    def update_adif_data(self, parsed_message):
        self.adif_data = parsed_message
        
        self.message_callback({
            'type': 'adif_data_updated',
            'adif_data': self.adif_data
        })
    
    def update_adif_processing_status(self, status_message):
        self.message_callback(status_message)        

    """
        if self.adif_data.get('entity') and self.band:
            log.info(sorted(self.adif_data.get('entity').get(str(datetime.now().year)).get(self.band)))
    """