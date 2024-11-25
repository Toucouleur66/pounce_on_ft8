# wsjtx_listener.py

import pywsjtx.extra.simple_server

import threading
import traceback
import socket
import re
import bisect

from wsjtx_packet_sender import WSJTXPacketSender
from datetime import datetime, timezone
from collections import deque

from logger import get_logger
from utils import get_local_ip_address, get_mode_interval, get_amateur_band, parse_wsjtx_message
from callsign_lookup import CallsignLookup

log     = get_logger(__name__)
lookup  = CallsignLookup()

from constants import (
    EVEN,
    ODD,
    MODE_FOX_HOUND,
    MODE_NORMAL,
    MODE_SUPER_FOX,
    FREQ_MINIMUM,
    FREQ_MAXIMUM,
    FREQ_MINIMUM_FOX_HOUND
)

class Listener:
    def __init__(
            self,
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
            monitoring_settings,
            monitored_callsigns,
            monitored_cq_zones,
            excluded_callsigns,
            wanted_callsigns,
            special_mode,
            message_callback=None
        ):

        self.my_call                    = None
        self.my_grid                    = None
        self.dx_call                    = None

        self.decode_packet_count        = 0
        self.last_decode_packet_time    = None
        self.last_heartbeat_time        = None
              
        self.packet_store               = {}
        self.packet_counter             = 0

        self.targeted_call              = None
        self.targeted_call_frequencies  = set()
        self.targeted_call_period       = None
        self.grid_being_called          = None
        self.rst_rcvd_from_being_called = None
        self.reply_to_packet_time       = None
        self.qso_time_on                = None
        self.qso_time_off               = None
        self.rst_rcvd                   = None
        self.rst_sent                   = None
        self.mode                       = None
        self.last_mode                  = None
        self.transmitting               = None        
        self.last_frequency             = None
        self.frequency                  = None
        self.suggested_frequency        = None
        self.rx_df                      = None
        self.tx_df                      = None

        self.primary_udp_server_address     = primary_udp_server_address or get_local_ip_address()
        self.primary_udp_server_port        = primary_udp_server_port or 2237

        self.secondary_udp_server_address   = secondary_udp_server_address or get_local_ip_address()
        self.secondary_udp_server_port      = secondary_udp_server_port or 2237

        self.enable_secondary_udp_server    = enable_secondary_udp_server or False

        self.enable_sending_reply           = enable_sending_reply
        self.enable_gap_finder               = enable_gap_finder
        self.enable_watchdog_bypass         = enable_watchdog_bypass
        self.enable_debug_output            = enable_debug_output
        self.enable_pounce_log              = enable_pounce_log 
        self.enable_log_packet_data         = enable_log_packet_data

        self.monitoring_settings            = monitoring_settings

        self.wanted_callsigns               = set(wanted_callsigns)
        self.excluded_callsigns             = set(excluded_callsigns)
        self.monitored_callsigns            = set(monitored_callsigns)
        self.monitored_cq_zones             = set(monitored_cq_zones)
        self.special_mode                   = special_mode
        self.message_callback               = message_callback

        self.update_settings()

        self._running                       = True

        # To check gap, we keep a list of used df
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
        except socket.error as e:
            if e.errno == 49:  # Can't assign requested address
                custom_message = (
                    f"Can't create server - {self.primary_udp_server_address}:{self.primary_udp_server_port}.\n"
                    "Please check your network settings or Primary UDP Server address."
                )
                log.error(custom_message)
                if self.message_callback:
                    self.message_callback(custom_message)
            else:
                error_message = f"Socket error de socket : {e}"
                log.error(error_message, exc_info=True)
                if self.message_callback:
                    self.message_callback(error_message)
            raise

        self.packet_sender = WSJTXPacketSender(
            self.secondary_udp_server_address,
            self.secondary_udp_server_port
        )        

    def update_settings(self):
        self.wanted_callsigns       = self.monitoring_settings.get_wanted_callsigns()
        self.excluded_callsigns     = self.monitoring_settings.get_excluded_callsigns()
        self.monitored_callsigns    = self.monitoring_settings.get_monitored_callsigns()
        self.monitored_cq_zones     = self.monitoring_settings.get_monitored_cq_zones()

        log.warning(f"Updated settings:\n\tWanted={self.wanted_callsigns}\n\tExcluded={self.excluded_callsigns}\n\tMonitored={self.monitored_callsigns}\n\tZones={self.monitored_cq_zones}")
        
    def stop(self):
        self._running = False
        self.s.sock.close() 

    def doListen(self):
        while self._running:
            try:
                self.pkt, self.addr_port = self.s.sock.recvfrom(8192)
                if self.enable_log_packet_data:
                    message = f"Received packet of length {len(self.pkt)} from {self.addr_port}"
                    message += f"\nPacket data: {self.pkt.hex()}"
                    log.info(message)
                self.the_packet = pywsjtx.WSJTXPacketClassFactory.from_udp_packet(self.addr_port, self.pkt)
                self.assign_packet()
            except socket.timeout:
                continue
            except OSError as e:
                if e.winerror == 10038:
                    break
                else:
                    error_message = f"Exception in doListen: {e}\n{traceback.format_exc()}"
                    log.info(error_message)
                    if self.message_callback:
                        self.message_callback(error_message)
            except Exception as e:
                error_message = f"Exception in doListen: {e}\n{traceback.format_exc()}"
                log.info(error_message)
                if self.message_callback:
                    self.message_callback(error_message)
        
        try:
            self.s.sock.close()
        except Exception:
            pass
        log.info("Listener stopped")                       

    def listen(self):
        self.t = threading.Thread(target=self.doListen, daemon=True)
        display_message = "Listener:{}:{} started (mode: {})".format(self.primary_udp_server_address, self.primary_udp_server_port, self.special_mode)
        log.info(display_message)
        if self.enable_debug_output and self.message_callback:
            self.message_callback(display_message)
        self.t.start()

    def send_heartbeat(self):
        max_schema = max(self.the_packet.max_schema, 3)
        reply_beat_packet = pywsjtx.HeartBeatPacket.Builder(self.the_packet.wsjtx_id,max_schema)
        self.s.send_packet(self.addr_port, reply_beat_packet)

    def handle_status_packet(self):
        if self.enable_log_packet_data:
            log.debug('WSJT-X {}'.format(self.the_packet))
        try:
            self.my_call        = self.the_packet.de_call
            self.my_grid        = self.the_packet.de_grid
            self.dx_call        = self.the_packet.dx_call
            self.tx_df          = self.the_packet.tx_df       
            self.rx_df          = self.the_packet.rx_df  
            self.mode           = self.the_packet.mode            
            self.frequency      = self.the_packet.dial_frequency         
            self.transmitting   = int(self.the_packet.transmitting)  

            error_found     = False
            
            # Updating mode
            if self.last_mode != self.mode:
                self.last_mode = self.mode
                if self.message_callback:
                    self.message_callback({
                        'type': 'update_mode',
                        'mode': self.mode
                    })

            # Updating frequency
            if self.last_frequency != self.frequency:
                self.last_frequency = self.frequency
                if self.message_callback:
                    self.message_callback({
                        'type'      : 'update_frequency',
                        'frequency' : self.frequency
                    })                    
            
            if self.targeted_call is not None:
                if self.enable_gap_finder:
                    log.warning('Used frequencies: {}\n\tSuggested frequency ({}): {}Hz'.format(
                        self.used_frequencies,
                        self.targeted_call_period,
                        self.get_frequency_suggestion(self.targeted_call_period)
                    ))

                status_had_time_to_update = (datetime.now(timezone.utc) - self.reply_to_packet_time).total_seconds() > 30

                if (
                    status_had_time_to_update and
                    self.the_packet.tx_enabled == 0 and 
                    self.the_packet.dx_call is not None and
                    self.reply_to_packet_time is not None                    
                ):
                    error_found = True
                    log.error('Tx disabled')   
                    self.reset_ongoing_contact()
                elif self.the_packet.tx_watchdog == 1:
                    error_found = True
                    log.error('Watchdog enabled')
                    if self.enable_watchdog_bypass :
                        self.reset_ongoing_contact()            
                elif self.targeted_call == self.dx_call:
                    self.rst_sent   = self.the_packet.report     
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
            self.send_heartbeat()
        elif isinstance(self.the_packet, pywsjtx.StatusPacket):
            self.handle_status_packet()
        elif isinstance(self.the_packet, pywsjtx.QSOLoggedPacket):
            log.error('QSOLoggedPacket should not be handle due to JTDX restrictions')   
        elif isinstance(self.the_packet, pywsjtx.DecodePacket):
            self.last_decode_packet_time = datetime.now(timezone.utc)
            self.decode_packet_count += 1
            if self.enable_gap_finder:
                self.collect_used_frequencies()     

            if self.my_call:
                self.decode_parse_packet()
            else:
                log.error('No StatusPacket received yet, can\'t handle DecodePacket for now.')    
        else:
            status_update = False
            log.debug('unknown packet type {}; {}'.format(type(self.the_packet),self.the_packet))

        if status_update:
            self.send_status_update()            

    def send_status_update(self):
        if self.message_callback:
            self.message_callback({
                'type'                      : 'update_status',
                'decode_packet_count'       : self.decode_packet_count,
                'last_decode_packet_time'   : self.last_decode_packet_time,
                'last_heartbeat_time'       : self.last_heartbeat_time,
                'transmitting'              : self.transmitting
            })

    def reset_ongoing_contact(self):
        self.targeted_call              = None
        self.targeted_call_period       = None
        self.targeted_call_frequencies  = set()
        self.grid_being_called          = None
        self.reply_to_packet_time       = None
        self.qso_time_on                = None
        self.qso_time_off               = None        
        self.rst_rcvd_from_being_called = None
        self.rst_rcvd                   = None
        self.rst_sent                   = None
        self.grid                       = None
        self.mode                       = None
        self.frequency                  = None
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
        if not self.the_packet or not self.the_packet.time:
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

        freq_min = FREQ_MINIMUM_FOX_HOUND if self.special_mode == MODE_FOX_HOUND else FREQ_MINIMUM
        freq_max = FREQ_MAXIMUM

        frequency_range = [freq_min] + used_frequencies + [freq_max]

        gaps = []
        for i in range(len(frequency_range) - 1):
            gap_start = frequency_range[i]
            gap_end = frequency_range[i + 1]
            gap_size = gap_end - gap_start
            if gap_size > 50:
                gaps.append((gap_start, gap_end))

        if self.special_mode == MODE_NORMAL and self.targeted_call_frequencies:
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

    def decode_parse_packet(self):
        if self.enable_log_packet_data:
            log.debug('{}'.format(self.the_packet))

        try:
            self.packet_counter         += 1
            packet_id                    = self.packet_counter
            self.packet_store[packet_id] = self.the_packet

            max_packets = 1_000
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

            # Pase message
            parsed_data = parse_wsjtx_message(
                message,
                lookup,
                self.wanted_callsigns,
                self.excluded_callsigns,
                self.monitored_callsigns,
                self.monitored_cq_zones
            )
            directed          = parsed_data['directed']
            callsign          = parsed_data['callsign']
            callsign_info     = parsed_data['callsign_info']
            grid              = parsed_data['grid']
            msg               = parsed_data['msg']
            cqing             = parsed_data['cqing']
            wanted            = parsed_data['wanted']
            monitored         = parsed_data['monitored']
            monitored_cq_zone = parsed_data['monitored_cq_zone']

            """
                How to handle message for GUI
            """                         

            if self.message_callback:
                self.message_callback({                
                'packet_id'         : packet_id,   
                'my_call'           : self.my_call,     
                'decode_time_str'   : decode_time_str,
                'callsign'          : callsign,
                'callsign_info'     : callsign_info,
                'directed'          : directed,
                'wanted'            : wanted,
                'monitored'         : monitored,
                'monitored_cq_zone' : monitored_cq_zone,
                'delta_time'        : delta_t,
                'delta_freq'        : delta_f,
                'snr'               : snr,                
                'message'           : f"{message:<21.21}".strip(),
                'formatted_message' : formatted_message
            })
                
            """
                Reset values to focus on another wanted callsign
            """
            if (
                self.qso_time_on is not None                              and
                self.targeted_call is not None                            and
                (time_now - self.qso_time_on).total_seconds() > 120 and
                callsign != self.targeted_call                            and            
                wanted is True
            ):
                log.warning("Waiting [ {} ] but we are about to switch on [ {} ]".format(self.targeted_call, callsign))
                self.reset_ongoing_contact()

            """
                How to handle the logic for the message 
            """
            if directed == self.my_call and msg in {"RR73", "73", "RRR"}:
                log.warning("Found message [ {} ] we should log a QSO for [ {} ]".format(msg, self.targeted_call))

                if self.targeted_call == callsign:
                    log.warning("Found message to log [ {} ]".format(self.targeted_call))
                    self.qso_time_off = decode_time
                    self.log_qso_to_adif()
                    if self.enable_secondary_udp_server:
                        self.log_qso_to_udp()
                    self.reset_ongoing_contact()
                    # Make sure to remove this callsign once QSO done
                    if callsign in self.wanted_callsigns:
                        self.wanted_callsigns.remove(callsign)
                    self.excluded_callsigns.add(callsign)
     
                elif self.targeted_call is not None:
                    log.error(f"Received |{msg}| from [ {callsign} ] but ongoing callsign is [ {self.targeted_call} ]")
                    if self.message_callback:
                        self.message_callback({
                            'type': 'error_occurred',                
                        })

                if self.message_callback:
                    self.message_callback({
                        'type': 'ready_to_log',
                        'formatted_message': formatted_message
                    })                           
                
            elif directed == self.my_call:
                log.warning("Found message directed to my call [ {} ] from [ {} ]".format(directed, callsign))

                if wanted is True:                                        
                    self.rst_rcvd_from_being_called = msg                 
                    self.grid                       = grid or ''                    
                    self.qso_time_on                = decode_time

                    log.warning("Start focus on callsign [ {} ]\treport:{}".format(callsign, self.rst_rcvd_from_being_called))
                    # We can't use self.the_packet.mode as it returns "~"
                    # self.mode             = self.the_packet.mode
                    self.reply_to_packet()  

                if self.message_callback:
                    self.message_callback({
                        'type': 'directed_to_my_call',
                        'formatted_message': formatted_message,
                        'contains_my_call': True
                    })                            

            elif wanted is True:
                log.debug("Listener wanted_callsign {}".format(callsign))  
                if self.enable_gap_finder:
                    self.targeted_call_frequencies.add(delta_f)     

                # Do not use callback message if wanted callsign already gave us a report
                if self.message_callback and self.rst_rcvd_from_being_called is None:
                    self.message_callback({
                        'type': 'wanted_callsign_detected',
                        'formatted_message': formatted_message,
                        'contains_my_call': directed == self.my_call
                    })                    

                if cqing is True:
                    debug_message = "Found CQ message from callsign [ {} ]".format(callsign)
                else:
                    debug_message = "Found message directed to [ {} ] from callsign [ {} ]. Message: {}".format(directed, callsign, msg)
                log.warning(debug_message)

                if (
                    self.enable_sending_reply and 
                    self.targeted_call is None
                ):
                    self.targeted_call = callsign   
                    self.reply_to_packet()                    

                # Use message_callback to communicate with the GUI
                if self.message_callback and self.enable_debug_output:
                    self.message_callback(debug_message)

            elif monitored or monitored_cq_zone:
                if self.message_callback:
                    self.message_callback({
                        'type': 'monitored_callsign_detected',
                        'formatted_message': formatted_message
                    })                                 

        except TypeError as e:
            log.error("Caught a type error in parsing packet: {}; error {}\n{}".format(
            self.the_packet.message, e, traceback.format_exc()))
        except Exception as e:
            log.error("Caught an error parsing packet: {}; error {}\n{}".format(
                self.the_packet.message, e, traceback.format_exc()))   

    def reply_to_packet(self):
        try:
            self.reply_to_packet_time   = datetime.now(timezone.utc)
            self.targeted_call_period   = self.odd_or_even_period()
            my_period                   = ODD if self.targeted_call_period == EVEN else EVEN

            if (
                self.enable_gap_finder and
                self.suggested_frequency is None                
            ):
                self.suggested_frequency = self.get_frequency_suggestion(my_period)
                if self.suggested_frequency is not None:
                    self.set_delta_f_packet(self.suggested_frequency)

            reply_pkt = pywsjtx.ReplyPacket.Builder(self.the_packet)
            log.warning(f"Sending ReplyPacket: {reply_pkt}")
            self.s.send_packet(self.addr_port, reply_pkt)
            log.debug("ReplyPacket sent successfully.")                
        except Exception as e:
            log.error(f"Error sending packets: {e}\n{traceback.format_exc()}")

    def set_delta_f_packet(self, frequency):        
        try:
            delta_f_paquet = pywsjtx.SetTxDeltaFreqPacket.Builder(self.the_packet.wsjtx_id, frequency)
            log.warning(f"Sending SetTxDeltaFreqPacket: {delta_f_paquet}")
            self.s.send_packet(self.addr_port, delta_f_paquet)
        except Exception as e:
            log.error(f"Error sending packets: {e}\n{traceback.format_exc()}")

    def configure_packet(self):
        configure_paquet = pywsjtx.ConfigurePacket.Builder(self.the_packet.wsjtx_id, "FT4")
        log.warning(f"Sending ConfigurePacket: {configure_paquet}")
        self.s.send_packet(self.addr_port, configure_paquet)        

    def log_qso_to_adif(self):
        required_fields = {
            'targeted_call'         : self.targeted_call,
            'mode'                  : self.mode,
            'rst_sent'              : self.rst_sent,
            'rst_rcvd'              : self.rst_rcvd_from_being_called,
            'frequency'             : self.frequency,
            'rx_df'                 : self.rx_df,
            'tx_df'                 : self.tx_df,
            'my_call'               : self.my_call,
            'qso_time_on'           : self.qso_time_on,
            'qso_time_off'          : self.qso_time_off
        }

        missing_fields = [name for name, value in required_fields.items() if not value]
        if missing_fields:
            log.error(f"Missing data: {', '.join(missing_fields)}")
            return

        # log.warning(required_fields)

        callsign        = self.targeted_call
        grid            = self.grid_being_called or ''
        mode            = self.mode
        rst_sent        = self.get_clean_rst(self.rst_sent)
        rst_rcvd        = self.get_clean_rst(self.rst_rcvd_from_being_called)
        freq_rx         = f"{round((self.frequency + self.rx_df) / 1_000_000, 6):.6f}"
        freq            = f"{round((self.frequency + self.tx_df) / 1_000_000, 6):.6f}"
        band            = get_amateur_band(self.frequency)
        my_call         = self.my_call
        qso_time_on     = self.qso_time_on.strftime('%H%M%S')
        qso_time_off    = self.qso_time_off.strftime('%H%M%S')
        qso_date        = self.qso_time_on.strftime('%Y%m%d')

        # Création de l'entrée ADIF avec une ligne par élément
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

        try:
            with open("wsjtx_log.adif", "a") as adif_file:
                adif_file.write(adif_entry)
            log.warning("QSOLogged [ {} ]".format(self.targeted_call))
        except Exception as e:
            log.error(f"Can't write ADIF file {e}")

    def log_qso_to_udp(self):
        try:
            # Todo remove Debug
            log.warning("self.rst_sent: {}\tself.rst_rcvd_from_being_called: {}\n\tawaited_rst_sent: {}\tawaited_rst_rcvd: {}".format(self.rst_sent, self.rst_rcvd_from_being_called,self.get_clean_rst(self.rst_sent), self.get_clean_rst(self.rst_rcvd_from_being_called)))

            awaited_rst_sent = self.get_clean_rst(self.rst_sent)
            awaited_rst_rcvd = self.get_clean_rst(self.rst_rcvd_from_being_called)

            self.packet_sender.send_qso_logged_packet(
                wsjtx_id        = self.the_packet.wsjtx_id,
                datetime_off    = self.qso_time_off,
                call            = self.targeted_call,
                grid            = self.grid_being_called or '',
                frequency       = self.frequency,
                mode            = self.mode,
                report_sent     = awaited_rst_sent,
                report_recv     = awaited_rst_rcvd,
                tx_power        = '', 
                comments        = '',
                name            = '',
                datetime_on     = self.qso_time_on,
                op_call         = '',
                my_call         = self.my_call,
                my_grid         = self.my_grid,
                exchange_sent   = awaited_rst_sent,
                exchange_recv   = awaited_rst_rcvd
            )
            log.warning("QSOLoggedPacket sent via UDP for [ {} ]".format(self.targeted_call))
        except Exception as e:
            log.error(f"Error sending QSOLoggedPacket via UDP: {e}")
            log.error("Caught an error while trying to send QSOLoggedPacket packet: error {}\n{}".format(e, traceback.format_exc()))

    def get_cuarto():
        return 15 * (datetime.now().second // 15)

    def get_clean_rst(self, rst):
        def repl(match):
            sign = match.group(1)       
            number = match.group(2).zfill(2)
            return f"{sign}{number}"
        
        pattern = r'^R?([+-]?)(\d+)$'
        cleaned_rst = re.sub(pattern, repl, rst)
        return cleaned_rst    