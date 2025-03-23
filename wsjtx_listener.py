# wsjtx_listener.py

import pywsjtx.extra.simple_server
import queue
import traceback
import socket
import bisect
import json
import inspect
import threading

from datetime import datetime, timezone
from collections import deque

from receiver_worker import ReceiverWorker
from processor_worker import ProcessorWorker

from PyQt6.QtCore import QObject, QThread, QTimer

from logger import get_logger

from utils import get_local_ip_address, get_mode_interval, get_amateur_band, parse_wsjtx_message
from utils import get_wkb4_year, get_clean_rst
from utils import log_format_message
from utils import load_marathon_wanted_data, save_marathon_wanted_data

from callsign_lookup import CallsignLookup
from adif_monitor import AdifMonitor

log     = get_logger(__name__)
lookup  = CallsignLookup()

from constants import (
    CURRENT_VERSION_NUMBER,
    BAND_CHANGE_WAITING_DELAY,
    EVEN,
    ODD,
    MASTER,
    SLAVE,
    DELAY_REPLY_PROCESS,
    HEARTBEAT_TIMEOUT_THRESHOLD,
    MODE_FOX_HOUND,
    MODE_NORMAL,
    WKB4_REPLY_MODE_NEVER,
    WKB4_REPLY_MODE_CURRENT_YEAR,
    FREQ_MINIMUM,
    FREQ_MAXIMUM,
    FREQ_MINIMUM_FOX_HOUND,
    ADIF_WORKED_CALLSIGNS_FILE,
    MARATHON_FILE
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
            max_reply_attemps_to_callsign,
            max_working_delay,
            enable_log_all_valid_contact,
            enable_gap_finder,
            enable_watchdog_bypass,
            enable_debug_output,
            enable_pounce_log,        
            enable_log_packet_data, 
            monitoring_settings,
            freq_range_mode,
            enable_marathon,
            marathon_preference,
            adif_file_path,
            adif_worked_backup_file_path,
            worked_before_preference,
            message_callback=None
        ):
        super().__init__()

        self.my_call                    = None
        self.my_grid                    = None
        self.dx_call                    = None

        self.decode_packet_count        = 0
        self.last_decode_packet_time    = None
        self.last_status_packet_time    = None
        self.last_heartbeat_time        = None

        self.packet_store               = {}
        self.packet_counter             = 0        
        self.reply_message_buffer       = deque()

        self.last_selected_message      = None
        self.reply_to_packet_time       = None

        self.call_ready_to_log          = None
        self.last_logged_call           = None
        self.targeted_call              = None
        self.targeted_call_frequencies  = set()
        self.targeted_call_period       = None
        self.grid_being_called          = {}
        self.rst_rcvd_from_being_called = {}
        self.rst_rcvd                   = None        
        self.qso_time_on                = {}
        self.qso_time_off               = {}
        self.rst_sent                   = {}
        self.mode                       = None
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

        self.enable_sending_reply           = enable_sending_reply
        self.enable_log_all_valid_contact   = enable_log_all_valid_contact
        self.enable_gap_finder               = enable_gap_finder
        self.enable_watchdog_bypass         = enable_watchdog_bypass
        self.enable_debug_output            = enable_debug_output
        self.enable_pounce_log              = enable_pounce_log 
        self.enable_log_packet_data         = enable_log_packet_data
        self.enable_marathon                = enable_marathon

        self.max_reply_attemps_to_callsign  = max_reply_attemps_to_callsign

        self.origin_addr_port               = None
        self._instance                      = None
        self.synched_band                   = None
        self.synched_settings               = None       
        self.requester_addr_port            = None
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
        self.monitored_cq_zones             = None
        self.excluded_cq_zones              = None
        self.worked_callsigns               = {}

        self.wanted_callsigns_per_entity   = {}

        self.freq_range_mode                = freq_range_mode
        self.message_callback               = message_callback

        self.worked_before_preference       = worked_before_preference      
        self.marathon_preference            = marathon_preference

        self.adif_data                      = {}        

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

        """
            Check ADIF file to handle Worked B4 
        """
        if adif_file_path:            
            self.adif_monitor               = AdifMonitor(adif_file_path, ADIF_WORKED_CALLSIGNS_FILE)
            if (
                self.enable_marathon and 
                lookup
            ):
                self.wanted_callsigns_per_entity = load_marathon_wanted_data(MARATHON_FILE)
                # register_lookup allow us to get adif data per band, year and entity
                self.adif_monitor.register_lookup(lookup)
            self.adif_monitor.start()
            self.adif_monitor.register_callback(self.update_adif_data)
        
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

        try:
            self.s = pywsjtx.extra.simple_server.SimpleServer(
                self.primary_udp_server_address,
                self.primary_udp_server_port
            )
            self.s.sock.settimeout(1.0)
            log.info(f"Primary server running on {self.primary_udp_server_address}:{self.primary_udp_server_port}")

        except socket.error as e:
            log.error(f"Error binding primary server to {self.primary_udp_server_address}:{self.primary_udp_server_port} - {e}")
            if e.errno == 49:  
                custom_message = (
                    f"Can't create server - {self.primary_udp_server_address}:{self.primary_udp_server_port}.\n"
                    "Please check your network settings or Primary UDP Server address."
                )
                log.error(custom_message)
                if self.message_callback:
                    self.message_callback(custom_message)
            raise

    def receive_packets(self):
        while self._running:
            try:                
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
                    log.error(f'Set instance [ {_instance} ] with [ {type(pywsjtx.WSJTXPacketClassFactory.from_udp_packet(self.origin_addr_port, pkt)).__name__} ] from {self.origin_addr_port}')

                    self._instance = _instance                 
                    if self.message_callback:
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
                log.info(error_message)
                if self.message_callback:
                    self.message_callback(error_message)
                return None, None
        try:
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
                self.assign_packet()  
                if self.can_forward_packet():
                    self.forward_packet(packet)                          
            except Exception as e:
                error_message = f"Exception in process_packets: {e}\n{traceback.format_exc()}"
                log.info(error_message)
                if self.message_callback:
                    self.message_callback(error_message)
            finally:
                self.packet_queue.task_done()
        log.info("Processor thread stopped")

    def add_master_header(self, address=None, port=None):
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
                send_sock.sendto(self.add_master_header() + packet, (
                    self.secondary_udp_server_address,
                    self.secondary_udp_server_port
                ))
        except Exception as e:
            error_message = f"Can't forward packet: {e}"
            log.info(error_message)
            if self.message_callback:
                self.message_callback(error_message)    

    def update_listener_settings(self):
        self.wanted_callsigns       = self.monitoring_settings.get_wanted_callsigns()
        self.excluded_callsigns     = self.monitoring_settings.get_excluded_callsigns()
        self.monitored_callsigns    = self.monitoring_settings.get_monitored_callsigns()
        self.monitored_cq_zones     = self.monitoring_settings.get_monitored_cq_zones()
        self.excluded_cq_zones      = self.monitoring_settings.get_excluded_cq_zones()
        self.synched_band           = self.monitoring_settings.get_operating_band()

        self.synch_time             = datetime.now()
        
        log_output = []
        log_output.append(f"Updated settings (~{CURRENT_VERSION_NUMBER}):")
        log_output.append(f"Instance={self._instance}")
        log_output.append(f"MyCall={self.my_call}")
        log_output.append(f"EnableSendingReply={self.enable_sending_reply}")             
        log_output.append(f"Band={self.band}")   
        log_output.append(f"WantedCallsigns={self.wanted_callsigns}")
        log_output.append(f"MonitoredCallsigns={self.monitored_callsigns}")
        log_output.append(f"ExcludedCallsigns={self.excluded_callsigns}")
        log_output.append(f"MonitoredZones={self.monitored_cq_zones}")
        log_output.append(f"ExcludedZones={self.excluded_cq_zones}")
        
        if self.enable_marathon:
            log_output.append(f"Marathon={self.marathon_preference.get(self.band)}")

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

    def synch_settings(self, requester_addr_port=None):        
        """
            Save requester_addr_port for later synch
        """
        if requester_addr_port:
            self.requester_addr_port = requester_addr_port
        """
            We don't send any sending if addr_port is None
        """
        addr_port = None
        if (
                self._instance == MASTER and
                self.band and 
                self.enable_secondary_udp_server and 
                self.requester_addr_port is not None
        ):
            addr_port = self.requester_addr_port
        elif (
                self._instance == SLAVE and
                self.synched_settings is not None
            ):  
            addr_port = self.origin_addr_port

        if addr_port is not None:
            frame = inspect.currentframe()
            try:
                caller = frame.f_back
                co_name = caller.f_code.co_name        
                log.warning(f"Synch settings: {co_name} from {caller} ({requester_addr_port})")
            finally:
                del frame

            self.send_settings_packet({             
                'band'                  : self.band,
                'wanted_callsigns'      : self.wanted_callsigns,
                'excluded_callsigns'    : self.excluded_callsigns,
                'monitored_callsigns'   : self.monitored_callsigns,
                'monitored_cq_zones'    : self.monitored_cq_zones,
                'excluded_cq_zones'     : self.excluded_cq_zones,
            }, addr_port)
        
    def send_settings_packet(self, settings_dict, addr_port):
        try:
            settings_packet = pywsjtx.SettingPacket.Builder(
                to_wsjtx_id="WSJT-X",
                settings_dict=settings_dict,
                synch_time=self.synch_time.isoformat()
            )

            if self._instance == MASTER:
                settings_packet = self.add_master_header() + settings_packet
                if self.message_callback:
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
            self.s.sock.close()
        except Exception:
            pass
        
        self.receiver_worker.stop()
        self.processor_worker.stop()
        self.receiver_thread.quit()
        self.processor_thread.quit()

    def listen(self):
        self.receiver_thread.start()
        self.processor_thread.start()

        display_message = f"Listener started on {self.primary_udp_server_address}:{self.primary_udp_server_port} (mode: {self.freq_range_mode})"
        log.info(display_message)
        
        if self.enable_debug_output and self.message_callback:
            self.message_callback(display_message)

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
            self.my_call                = self.the_packet.de_call
            self.my_grid                = self.the_packet.de_grid
            self.dx_call                = self.the_packet.dx_call
            self.tx_df                  = self.the_packet.tx_df       
            self.rx_df                  = self.the_packet.rx_df  
            self.mode                   = self.the_packet.mode            
            self.frequency              = self.the_packet.dial_frequency     
            self.band                   = get_amateur_band(self.frequency)    
            self.transmitting           = int(self.the_packet.transmitting)  
            
            self.rst_sent[self.dx_call] = self.the_packet.report               

            error_found     = False
            
            # Updating mode
            if self.last_mode != self.mode:
                self.last_mode = self.mode
                if self.message_callback:
                    self.message_callback({
                        'type'      : 'update_mode',
                        'mode'      : self.mode
                    })

            # Updating frequency
            if self.last_frequency != self.frequency:
                self.last_frequency = self.frequency

                if self.last_band != self.band:
                    self.last_band = self.band
                    self.last_band_time_change = datetime.now()
                    self.reset_targeted_call()
                    self.synched_settings = None

                if self.message_callback:
                    self.message_callback({
                        'type'      : 'update_frequency',
                        'frequency' : self.frequency
                    })       

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
                    if self.enable_watchdog_bypass :
                        self.reset_targeted_call()            
                elif self.targeted_call == self.dx_call:  
                    self.time_off   = datetime.now(timezone.utc)
                elif (
                    status_had_time_to_update and   
                    self.dx_call is not None
                ):
                    error_found = True
                    log.error('We should call [ {} ] not [ {} ]'.format(self.targeted_call, self.dx_call))   

                if error_found and self.message_callback:
                    self.message_callback({
                        'type': 'error_occurred',                
                    })
                
        except Exception as e:
            log.error("Caught an error on status handler: error {}\n{}".format(e, traceback.format_exc()))   

    def assign_packet(self):
        status_update = True

        if isinstance(self.the_packet, pywsjtx.HeartBeatPacket):
            self.last_heartbeat_time = datetime.now(timezone.utc)
            self.send_heartbeat_packet()
        elif isinstance(self.the_packet, pywsjtx.StatusPacket):
            self.handle_status_packet()
        elif isinstance(self.the_packet, pywsjtx.QSOLoggedPacket):
            log.warning('QSOLoggedPacket should not be handle')   
        elif isinstance(self.the_packet, pywsjtx.DecodePacket):
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
            self.callback_stop_monitoring()
        elif isinstance(self.the_packet, pywsjtx.RequestSettingPacket):
            self.handle_request_setting_packet()                      
        elif isinstance(self.the_packet, pywsjtx.SettingPacket):
            self.handle_setting_packet()      
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
        if self.message_callback:
            self.message_callback({
                'type'                      : 'update_status',
                'frequency'                 : self.frequency,
                'decode_packet_count'       : self.decode_packet_count,
                'last_decode_packet_time'   : self.last_decode_packet_time,
                'last_heartbeat_time'       : self.last_heartbeat_time,
                'transmitting'              : self.transmitting
            })

    def handle_request_setting_packet(self):    
        log.debug(f"Received RequestSettingPacket method from {self.origin_addr_port}.")  
        if self.synch_time.isoformat() != datetime.fromisoformat(self.the_packet.synch_time):
            self.synch_settings(self.origin_addr_port)       
            
    def callback_stop_monitoring(self):
        log.debug("Received ClosePacket method")
        if self.message_callback:
            self.message_callback({
                'type'                      : 'stop_monitoring',
                'decode_packet_count'       : self.decode_packet_count,
                'last_decode_packet_time'   : self.last_decode_packet_time
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

        freq_min = FREQ_MINIMUM_FOX_HOUND if self.freq_range_mode == MODE_FOX_HOUND else FREQ_MINIMUM
        freq_max = FREQ_MAXIMUM

        frequency_range = [freq_min] + used_frequencies + [freq_max]

        gaps = []
        for i in range(len(frequency_range) - 1):
            gap_start = frequency_range[i]
            gap_end = frequency_range[i + 1]
            gap_size = gap_end - gap_start
            if gap_size > 50:
                gaps.append((gap_start, gap_end))

        if self.freq_range_mode == MODE_NORMAL and self.targeted_call_frequencies:
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

        return int(suggested_freq)
    
    def handle_setting_packet(self):
        if (
            self.band is not None and 
            self.synched_band == self.band
        ):
            try:         
                log.info(f"SettingPacket received from {self.origin_addr_port}")             
                synch_time = datetime.fromisoformat(self.the_packet.synch_time)
                if (
                    self.synched_settings is None or 
                    self.synch_time is None or 
                    self.synch_time < synch_time
                ):
                    self.synched_settings = json.loads(self.the_packet.settings_json)
                    wanted_callsigns = self.synched_settings.get('wanted_callsigns')
                    """
                        Make sure to set synch_time after we checked if wanted_callsigns is valid
                    """
                    if wanted_callsigns and isinstance(wanted_callsigns, (list, tuple)):
                        self.synch_time = synch_time
                        if self.message_callback:
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
        self.last_decode_packet_time = datetime.now(timezone.utc)
        self.decode_packet_count += 1
        
        if not self.my_call:
            log.error("No StatusPacket received yet, can\'t handle DecodePacket for now.") 
            return
        
        """
            We need a StatusPacket before handling the DecodePacket
            and we have to check last_band_time_change            
        """
        seconds_since_band_change = round(
            (datetime.now() - self.last_band_time_change).total_seconds()
        )
        if seconds_since_band_change < BAND_CHANGE_WAITING_DELAY:
            wait_before_decoding = BAND_CHANGE_WAITING_DELAY - seconds_since_band_change
            if wait_before_decoding != self.wait_before_decoding:
                self.wait_before_decoding = wait_before_decoding
                log.error(f"Can't handle DecodePacket yet. {wait_before_decoding} seconds to wait.")    
                """
                    Add callback to let GUI know we can't handle decode yet
                """
            return 

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
                Parse message, might need "lookup" to parse message
            """
            parsed_data = parse_wsjtx_message(
                message,
                lookup,
                self.wanted_callsigns,
                self.worked_callsigns.get(self.band, {}),
                self.excluded_callsigns,
                self.monitored_callsigns,
                self.monitored_cq_zones,
                self.excluded_cq_zones
            )
            directed          = parsed_data['directed']
            callsign          = parsed_data['callsign']
            callsign_info     = parsed_data['callsign_info']
            worked_b4         = False
            marathon          = False
            priority          = 0

            grid              = parsed_data['grid']
            report            = parsed_data['report']
            msg               = parsed_data['msg']
            cqing             = parsed_data['cqing']
            wanted            = parsed_data['wanted']
            excluded          = parsed_data['excluded']
            monitored         = parsed_data['monitored']
            monitored_cq_zone = parsed_data['monitored_cq_zone']
            """
                Might need to handle in priority callsign set rather than callsign
                automatically added
            """
            current_year      = str(datetime.now().year)

            wkb4_year         = None
            entity_code       = callsign_info.get('entity') if callsign_info else None

            """
                Check if wanted and is Worked b4
            """
            if self.adif_data.get('wkb4'):
                wkb4_year = get_wkb4_year(self.adif_data['wkb4'], callsign, self.band)
                if wanted:
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
                        wanted    = False
                        worked_b4 = True
            
            """
                Check if entity code is needed for marathon
            """
            if (
                self.enable_marathon and 
                self.marathon_preference.get(self.band) and
                self.adif_data.get('entity') and 
                wanted is False and
                not excluded and                
                not worked_b4 and
                entity_code
            ):
                """
                    Callsign already checked and wanted for
                """
                if (
                    callsign in self.wanted_callsigns_per_entity.get(self.band, {}).get(entity_code, {})
                ):                                    
                    marathon = True
                elif entity_code not in self.adif_data.get('entity', {}).get(current_year, {}).get(self.band, {}):
                    marathon = True

                    if not self.wanted_callsigns_per_entity.get(self.band):
                        self.wanted_callsigns_per_entity[self.band] = {}

                    if not self.wanted_callsigns_per_entity[self.band].get(entity_code):
                        self.wanted_callsigns_per_entity[self.band][entity_code] = []

                    if callsign not in self.wanted_callsigns_per_entity[self.band][entity_code]:
                        self.wanted_callsigns_per_entity[self.band][entity_code].append(callsign)
                        save_marathon_wanted_data(MARATHON_FILE, self.wanted_callsigns_per_entity)

                        log.info(f"Entity Code Wanted={entity_code} ({self.band}/{current_year})\n\tAdding Wanted Callsign={callsign}\n\tWorked ({self.band}/{current_year}):{self.adif_data.get('entity', {}).get(current_year, {}).get(self.band, {})}")

                    if callsign not in self.wanted_callsigns:
                        if self.message_callback:
                            self.message_callback({    
                            'type'          : 'update_wanted_callsign',
                            'callsign'      : callsign,
                            'action'        : 'add'
                        })    
                            
                if marathon:
                    wanted = True

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
                wanted is True and
                self.targeted_call is not None and
                callsign != self.targeted_call            
            ):
                if (
                    self.qso_time_on.get(self.targeted_call) and
                    (time_now - self.qso_time_on.get(self.targeted_call)).total_seconds() >= self.max_working_delay_seconds            
                ):
                    log.warning(f"Waiting for [ {self.targeted_call} ] but we are about to switch on [ {callsign} ]")
                    self.reset_targeted_call()
                
                if len(self.reply_attempts.get('self.targeted_call') or []) >= self.max_reply_attemps_to_callsign:
                    log.warning(f"{len(self.reply_attempts[self.targeted_call])} attempts for [ {self.targeted_call} ] but we are about to switch on [ {callsign} ]")
                    self.reset_targeted_call()

                if (
                    directed == self.my_call and
                    self.qso_time_on.get(self.targeted_call) is None
                ):
                    log.warning(f"No answer yet for [ {self.targeted_call} ] but we are about to switch on [ {callsign} ]")
                    self.reset_targeted_call()

            """
                How to handle the logic for the message 
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
                            entity_code and
                            self.enable_marathon and 
                            self.adif_data.get('entity') and
                            self.marathon_preference.get(self.band)
                        ):
                            self.clear_wanted_callsigns(entity_code)  
                    else:
                        message_type = 'directed_to_my_call'

                    """
                        Clean Wanted callsigns
                    """  
                    self.call_ready_to_log = None
                    if msg in {'RR73', 'RRR'}:
                        reply_to_packet = True
                    elif msg == '73':
                        self.reset_targeted_call()

                    if callsign in self.wanted_callsigns:
                        self.wanted_callsigns.remove(callsign)   
                    
                elif self.targeted_call is not None:
                    log.error(f"Received |{msg}| from [ {callsign} ] but ongoing callsign is [ {self.targeted_call} ]")
                    message_type = 'error_occurred'   
                
            elif directed == self.my_call:
                log.warning(f"Found message directed to my call [ {directed} ] from [ {callsign} ]")
                
                message_type = 'directed_to_my_call'
                
                self.rst_rcvd_from_being_called[callsign]   = report                                   
                self.qso_time_on[callsign]                  = decode_time
                if not self.grid_being_called.get(callsign):
                    self.grid_being_called[callsign]        = grid or '' 

                if wanted is True:    
                    focus_info = f"Report [ {report} ]" if report else f"Grid [ {grid} ]"
                    log.warning(f"Focus on callsign [ {callsign} ]\t{focus_info}")
                    # We can't use self.the_packet.mode as it returns "~"
                    # self.mode             = self.the_packet.mode
                    if self.enable_sending_reply:  
                        reply_to_packet = True
                        message_type = 'wanted_callsign_being_called'  
                # We need to end this 
                elif self.call_ready_to_log == callsign and self.rst_sent.get(self.call_ready_to_log):
                    reply_to_packet = True
            elif wanted is True: 
                reply_to_packet = True
                message_type = 'wanted_callsign_detected'

                if self.enable_gap_finder:
                    self.targeted_call_frequencies.add(delta_f)     
                             
                if cqing is True:
                    debug_message = "Found CQ message from callsign [ {} ]. Targeted callsign: [ {} ]".format(callsign, self.targeted_call)
                else:
                    debug_message = "Found message directed to [ {} ] from callsign [ {} ]. Message: {}".format(directed, callsign, msg)
                log.warning(debug_message)

                # Use message_callback to communicate with the GUI
                if self.message_callback and self.enable_debug_output:
                    self.message_callback(debug_message)

            elif monitored or monitored_cq_zone:
                message_type = 'monitored_callsign_detected'   
            elif self.targeted_call is not None:
                if (
                    self.reply_attempts.get(self.targeted_call) and
                    (decode_time - self.reply_attempts[self.targeted_call][-1]).total_seconds() >= self.max_working_delay_seconds            
                ):
                    message_type = 'lost_targeted_callsign'
                    log.warning(f"Lost focus for callsign [ {self.targeted_call} ]")        
                    self.targeted_call = None  
                    self.halt_packet()
            
            """
                Check priority
            """
            if reply_to_packet:
                priority = self.process_reply_packet_buffer({           
                    'packet_id'         : packet_id,                   
                    'decode_time'       : decode_time,
                    'callsign'          : callsign,
                    'directed'          : directed,
                    'marathon'          : marathon,
                    'wkb4_year'         : wkb4_year,
                    'grid'              : grid,
                    'cqing'             : cqing,
                    'msg'               : msg
                }) 
            elif message_type:
                priority = 1
            
            """
                Send message to GUI
            """                      
            if self.message_callback:                    
                self.message_callback({           
                'wsjtx_id'          : self.the_packet.wsjtx_id,
                'my_call'           : self.my_call,     
                'packet_id'         : packet_id,     
                'decode_time'       : decode_time,              
                'decode_time_str'   : decode_time_str,
                'callsign'          : callsign,
                'callsign_info'     : callsign_info,
                'directed'          : directed,
                'wanted'            : wanted,
                'monitored'         : monitored,
                'monitored_cq_zone' : monitored_cq_zone,
                'wkb4_year'         : wkb4_year,
                'delta_time'        : delta_t,
                'delta_freq'        : delta_f,
                'snr'               : snr,                
                'message'           : f"{message:<21.21}".strip(),
                'message_type'      : message_type,
                'priority'          : priority,
                'formatted_message' : formatted_message
            })        

        except TypeError as e:
            log.error("Caught a type error in parsing packet: {}; error {}\n{}".format(
            self.the_packet.message, e, traceback.format_exc()))
        except Exception as e:
            log.error("Caught an error parsing packet: {}; error {}\n{}".format(
                self.the_packet.message, e, traceback.format_exc()))   

    def process_reply_packet_buffer(self, message):         
        """
            Add this message to buffer
        """    
        self.reply_message_buffer.append(message)

        filtered_messages = [
            message_in_buffer for message_in_buffer in self.reply_message_buffer if message_in_buffer['decode_time'].strftime('%H%M%S') == message['decode_time'].strftime('%H%M%S')
        ]
        
        """
            Handle priority
        """        
        for filtered_message in filtered_messages:
            if filtered_message['directed'] == self.my_call:
                if filtered_message['callsign'] == self.targeted_call:
                    filtered_message['priority'] = 4
                else:
                    filtered_message['priority'] = 3
            else:
                if filtered_message.get('cqing'):
                    filtered_message['priority'] = 2
                else:
                    filtered_message['priority'] = 1

                if filtered_message['marathon']:
                    filtered_message['priority']-= 1

        """
            Selects the message with the highest priority
        """       

        sort_key = lambda message: (
            # First select highest priority
            message['priority'],
            # If wkb4_year is None, return inf, which ranks this message before those with a numerical year
            float('inf') if message.get('wkb4_year') is None else -message['wkb4_year'],
            # In case of a tie on the first two criteria, the message with the lowest packet_id (the first received) is selected
            -message['packet_id']
        )

        selected_message = max(filtered_messages, key=sort_key, default=None)
                
        """
            Clear buffer
        """
        self.reply_message_buffer = deque(
            [same_time_message for same_time_message in self.reply_message_buffer
                if abs((same_time_message['decode_time'] - message['decode_time']).total_seconds()) <= 120]
        )   

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
                DELAY_REPLY_PROCESS,
                self.process_pending_reply,
                args=[selected_message] 
            )
            self._reply_timer.start()

            # Log filtered messages
            log.info(f"FilteredMessages ({len(filtered_messages)}):\n\t{"\n\t".join([
                log_format_message(m) for m in sorted(filtered_messages, key=sort_key)
            ])}")

            # Return priority for GUI callback
            return selected_message['priority']
        else:
            return -1 
                
    def process_pending_reply(self, selected_message):    
        callsign        = selected_message.get('callsign')
        packet_id       = selected_message.get('packet_id')
        
        callsign_packet = self.packet_store[packet_id]

        if self.targeted_call is None:
            self.targeted_call = callsign

        if callsign not in self.reply_attempts:
            self.reply_attempts[callsign] = []

        if callsign_packet.time not in self.reply_attempts[callsign]:
            self.reply_attempts[callsign].append(callsign_packet.time)
            count_attempts = len(self.reply_attempts[callsign])
            if count_attempts >= (self.max_reply_attemps_to_callsign - 1):
                log.warning(f"{count_attempts} attempts for [ {callsign} ]") 

        self.reply_to_packet(callsign_packet) 
        self.last_selected_message = selected_message

    def halt_packet(self):
        if self._instance == SLAVE:
            return        
        
        try:
            halt_pkt = pywsjtx.HaltTxPacket.Builder(self.the_packet)             
            self.s.send_packet(self.origin_addr_port, halt_pkt)         
            log.debug(f"Sent HaltPacket: {halt_pkt}")         
        except Exception as e:
            log.error(f"Error sending packets: {e}\n{traceback.format_exc()}")

    def reply_to_packet(self, callsign_packet):
        if self._instance == SLAVE:
            return        
        
        try:            
            self.reply_to_packet_time    = datetime.now(timezone.utc)
            self.targeted_call_period    = self.odd_or_even_period()
            my_period                    = ODD if self.targeted_call_period == EVEN else EVEN

            if (
                self.enable_gap_finder and
                self.suggested_frequency is None                
            ):
                self.suggested_frequency = self.get_frequency_suggestion(my_period)
                if self.suggested_frequency is not None:
                    self.set_delta_f_packet(self.suggested_frequency)

            reply_pkt = pywsjtx.ReplyPacket.Builder(callsign_packet)
            self.s.send_packet(self.origin_addr_port, reply_pkt)         
            log.debug(f"Sent ReplyPacket: {reply_pkt}")            
        except Exception as e:
            log.error(f"Error sending packets: {e}\n{traceback.format_exc()}")

    def set_delta_f_packet(self, frequency):  
        if self._instance == SLAVE:
            return        
      
        try:
            delta_f_paquet = pywsjtx.SetTxDeltaFreqPacket.Builder(self.the_packet.wsjtx_id, frequency)
            log.warning(f"Sending SetTxDeltaFreqPacket (Df={frequency}): {delta_f_paquet}")
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
            if self.message_callback:
                self.message_callback({        
                'type'              : 'update_wanted_callsign',
                'callsign'          : callsign,
                'action'            : 'remove'
            })       
        
        if entity_code in self.wanted_callsigns_per_entity.get(self.band, {}):
            del self.wanted_callsigns_per_entity[self.band][entity_code]     
            save_marathon_wanted_data(MARATHON_FILE, self.wanted_callsigns_per_entity)           
            log.info(f"Wanted Callsigns per entity cleared ({self.band})={self.wanted_callsigns_per_entity}")         
                                
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

            with open(self.adif_worked_backup_file_path, "a") as adif_file:
                adif_file.write(adif_entry)
            log.warning("QSO Logged [ {} ]".format(self.call_ready_to_log))
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

    def update_adif_data(self, parsed_data):
        self.adif_data = parsed_data

    """
        if self.adif_data.get('entity') and self.band:
            log.info(sorted(self.adif_data.get('entity').get(str(datetime.now().year)).get(self.band)))
    """