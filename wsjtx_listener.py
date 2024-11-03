# wsjtx_listener.py

import pywsjtx.extra.simple_server

import threading
import traceback
import socket
import re
import bisect
import traceback

from wsjtx_packet_sender import WSJTXPacketSender
from datetime import datetime
from collections import deque

from logger import get_logger
from utils import get_local_ip_address, parse_wsjtx_message

log     = get_logger(__name__)

class Listener:
    def __init__(
            self,
            primary_udp_server_address,
            primary_udp_server_port,
            secondary_udp_server_address,
            secondary_udp_server_port,
            enable_secondary_udp_server,
            enable_sending_reply,
            enable_watchdog_bypass,
            enable_debug_output,
            enable_pounce_log,        
            enable_log_packet_data, 
            enable_show_all_decoded,
            wanted_callsigns,
            message_callback=None
        ):
      
        self.my_call    = None
        self.my_grid    = None
        self.band       = None
        self.dx_call    = None

        self.decode_packet_count        = 0
        self.last_decode_packet_time    = None
        self.last_heartbeat_time        = None

        self.dx_being_called            = None
        self.grid_being_called          = None
        self.rst_rcvd_from_being_called = None
        self.qso_time_on                = None
        self.qso_time_off               = None
        self.rst_rcvd                   = None
        self.rst_sent                   = None
        self.mode                       = None
        self.frequency                  = None
        self.rx_df                      = None
        self.tx_df                      = None

        self.unseen                     = []
        self.unseen_lock                = threading.Lock()

        self.primary_udp_server_address     = primary_udp_server_address or get_local_ip_address()
        self.primary_udp_server_port        = primary_udp_server_port or 2237

        self.secondary_udp_server_address   = secondary_udp_server_address or get_local_ip_address()
        self.secondary_udp_server_port      = secondary_udp_server_port or 2237

        self.enable_secondary_udp_server    = enable_secondary_udp_server or False

        self.enable_sending_reply           = enable_sending_reply
        self.enable_watchdog_bypass         = enable_watchdog_bypass
        self.enable_debug_output            = enable_debug_output
        self.enable_pounce_log              = enable_pounce_log 
        self.enable_log_packet_data         = enable_log_packet_data
        self.enable_show_all_decoded        = enable_show_all_decoded

        self.wanted_callsigns               = set(wanted_callsigns)
        self.message_callback               = message_callback

        self._running                       = True

        # To check gap, we keep a list of used df
        self.last_period_index              = None
        self.used_frequencies               = {
            'even'                          : deque([set()], maxlen=2),
            'odd'                           : deque([set()], maxlen=2)
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

    def get_local_ip_address(self):
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP                

    def send_reply(self,data):
        packet = pywsjtx.ReplyPacket.Builder(data['packet'])
        self.s.send_packet(data['addr_port'], packet)

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
                self.handle_packet()
            except socket.timeout:
                continue
            except Exception as e:
                error_message = f"Exception in doListen: {e}\n{traceback.format_exc()}"
                log.info(error_message)
                if self.message_callback:
                    self.message_callback(error_message)
        
        self.s.sock.close()
        log.info("Listener stopped")                       

    def listen(self):
        self.t = threading.Thread(target=self.doListen, daemon=True)
        display_message = "Listener:{}:{} started".format(self.primary_udp_server_address, self.primary_udp_server_port)
        log.info(display_message)
        if self.enable_debug_output and self.message_callback:
            self.message_callback(display_message)
        self.t.start()

    def heartbeat(self):
        max_schema = max(self.the_packet.max_schema, 3)
        reply_beat_packet = pywsjtx.HeartBeatPacket.Builder(self.the_packet.wsjtx_id,max_schema)
        self.s.send_packet(self.addr_port, reply_beat_packet)

    def update_status(self):
        if self.enable_log_packet_data:
            log.debug('WSJT-X {}'.format(self.the_packet))
        try:
            self.my_call    = self.the_packet.de_call
            self.my_grid    = self.the_packet.de_grid
            self.dx_call    = self.the_packet.dx_call
            self.tx_df      = self.the_packet.tx_df       
            self.rx_df      = self.the_packet.rx_df  
            self.mode       = self.the_packet.mode            
            self.band       = str(self.the_packet.dial_frequency / 1_000) + 'Khz'
            self.frequency  = self.the_packet.dial_frequency            

            error_found     = False

            log.warning('Used frequencies: {}'.format(self.used_frequencies))

            # Handle logic when we get watchdog or Tx disabled
            if self.dx_being_called is not None:
                if self.the_packet.tx_watchdog == 1:
                    error_found = True
                    log.error('Watchdog enabled')
                    if self.enable_watchdog_bypass :
                        self.reset_ongoing_contact()

                elif self.the_packet.tx_enabled == 0:
                    error_found = True
                    log.error('Tx disabled')   
                    self.reset_ongoing_contact()

                if error_found and self.message_callback:
                    self.message_callback({
                        'type': 'error_occurred',                
                    })

            if self.dx_being_called is not None and self.dx_being_called == self.dx_call:
                self.rst_sent   = self.the_packet.report     
                self.time_off   = datetime.now()  
            elif self.dx_being_called is not None and self.dx_call is not None:
                log.error('We should call [ {} ] not [ {} ]'.format(self.dx_being_called, self.dx_call))   
                if self.message_callback:
                    self.message_callback({
                        'type': 'error_occurred',                
                    })

        except Exception as e:
            pass 

    def handle_packet(self):
        if isinstance(self.the_packet, pywsjtx.HeartBeatPacket):
            self.last_heartbeat_time = datetime.now()
            self.heartbeat()
            self.send_status_update()
        elif isinstance(self.the_packet, pywsjtx.StatusPacket):
            self.update_status()
        elif isinstance(self.the_packet, pywsjtx.QSOLoggedPacket):
            log.error('QSOLoggedPacket should not be handle due to JTDX restrictions')   
        elif isinstance(self.the_packet, pywsjtx.DecodePacket):
            self.last_decode_packet_time = datetime.now()
            self.decode_packet_count += 1
            self.collect_used_frequencies()
            if self.my_call:
                self.decode_parse_packet()
            else:
                log.error('No StatusPacket received yet, can\'t handle DecodePacket for now.')    
            self.send_status_update()
        else:
            log.debug('unknown packet type {}; {}'.format(type(self.the_packet),self.the_packet))

    def send_status_update(self):
        if self.message_callback:
            self.message_callback({
                'type': 'update_status',
                'decode_packet_count': self.decode_packet_count,
                'last_decode_packet_time': self.last_decode_packet_time,
                'last_heartbeat_time': self.last_heartbeat_time
            })

    def reset_ongoing_contact(self):
        self.dx_being_called            = None
        self.grid_being_called          = None
        self.qso_time_on                = None
        self.qso_time_off               = None        
        self.rst_rcvd_from_being_called = None
        self.rst_rcvd                   = None
        self.rst_sent                   = None
        self.grid                       = None
        self.mode                       = None
        self.frequency                  = None

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
        
        if self.mode == "FT4" or (self.the_packet and self.the_packet.mode == "FT4"):
            duration = 7.5
        else:
            duration = 15

        return int(self.the_packet.time.timestamp() // duration)

    def odd_or_even_period(self):
        period_index = self.get_period_index()
        if period_index is None:
            return None
        return 'even' if period_index % 2 == 0 else 'odd'

    def find_free_frequency(self, period):
        used_frequencies_sets = self.used_frequencies.get(period, deque())
        used_frequencies = set()
        for freq_set in used_frequencies_sets:
            used_frequencies.update(freq_set)

        used_frequencies = sorted(used_frequencies)

        freq_min = 200
        freq_max = 3000

        frequency_range = [freq_min] + used_frequencies + [freq_max]

        gaps = []
        for i in range(len(frequency_range) - 1):
            gap_start = frequency_range[i]
            gap_end = frequency_range[i + 1]
            if gap_end - gap_start > 50:  
                gaps.append((gap_start, gap_end))

        if gaps:
            largest_gap = max(gaps, key=lambda x: x[1] - x[0])
            free_frequency = int((largest_gap[0] + largest_gap[1]) / 2)
            log.info(f"Found free frequency at {free_frequency} Hz on {period} cycle.")
            return free_frequency
        else:
            log.info(f"No free frequency found on {period} cycle.")
            return None

    def decode_parse_packet(self):
        if self.enable_log_packet_data:
            log.debug('{}'.format(self.the_packet))

        try:
            wanted_callsign = None
            directed        = None
            msg             = None
            callsign        = None
            grid            = None     

            message         = self.the_packet.message
            decode_time     = self.the_packet.time
            snr             = self.the_packet.snr
            delta_t         = self.the_packet.delta_t
            delta_f         = self.the_packet.delta_f     

            time_str = decode_time.strftime('%H%M%S')

            formatted_message = f"{time_str} {snr:+d} {delta_t:+.1f} {delta_f} ~ {message}"

            log.debug("DecodePacket: {}".format(formatted_message))

            # Pattern for CQ calls
            match = re.match(r"^CQ\s+(?:(\w{2,3})\s+)?([A-Z0-9/]+)(?:\s+([A-Z]{2}\d{2}))?", message)
            if match:
                directed    = match.group(1)
                callsign    = match.group(2)
                grid        = match.group(3)

                if callsign in self.wanted_callsigns:
                    wanted_callsign = {
                        'directed': directed,                    
                        'callsign': callsign,
                        'grid': grid,
                        'cq': True
                    }
                    self.grid_being_called = grid

            else:
                # Pattern for dual-call messages
                match = re.match(r"^([A-Z0-9/]+)\s+([A-Z0-9/]+)\s+([A-Z0-9+-]+)", message)

                # log.warning(match)
                if match:
                    directed = match.group(1)
                    callsign = match.group(2)
                    msg = match.group(3)

                    if callsign in self.wanted_callsigns:
                        wanted_callsign = {
                            'directed': directed,
                            'callsign': callsign,
                            'msg': msg
                        }                    
            
            if (
                self.qso_time_on is not None and
                (datetime.now() - self.qso_time_on).total_seconds() > 120 and
                callsign != self.dx_being_called and            
                wanted_callsign is not None
            ):
                log.warning("Waiting [ {} ] but we are about to switch on [ {} ]".format(self.dx_being_called, callsign))
                self.reset_ongoing_contact()

            # if msg is not None and "73" in msg:
            #    log.warning("dx_being_called:{}\tdirected:{}\tcallsign:{}\trst_rcvd_from_being_called:{}".format(self.dx_being_called, directed, callsign, self.rst_rcvd_from_being_called))

            if directed == self.my_call and msg in {"RR73", "73"}:
                if self.dx_being_called == callsign:
                    log.warning("Found message to log [ {} ]".format(self.dx_being_called))
                    self.qso_time_off = decode_time
                    self.log_qso_to_adif()
                    if self.enable_secondary_udp_server:
                        self.log_qso_to_udp()
                    self.reset_ongoing_contact()
                    # Make sure to remove this callsign once QSO done
                    self.wanted_callsigns.remove(callsign)

                    if self.message_callback:
                        self.message_callback({
                            'type': 'ready_to_log',
                            'formatted_message': formatted_message
                        })        
                elif self.dx_being_called is not None:
                    log.error(f"Received |{msg}| from [ {callsign} ] but ongoing callsign is [ {self.dx_being_called} ]")
                    if self.message_callback:
                        self.message_callback({
                            'type': 'error_occurred',                
                        })
                
            elif directed == self.my_call:
                log.warning("Found message directed to my call [ {} ] from [ {} ]".format(directed, callsign))

                if wanted_callsign is not None:                                        
                    self.rst_rcvd_from_being_called = msg                 
                    self.grid                       = grid or ''                    
                    self.qso_time_on                = decode_time

                    log.warning("Start focus on callsign [ {} ]\treport:{}".format(callsign, self.rst_rcvd_from_being_called))
                    # We can't use self.the_packet.mode as it returns "~"
                    # self.mode             = self.the_packet.mode
                    self.reply_to_message()  

                if self.message_callback:
                    self.message_callback({
                        'type': 'directed_to_my_call',
                        'formatted_message': formatted_message,
                        'contains_my_call': True
                    })                            

            elif wanted_callsign is not None:
                wanted_callsign['packet'] = self.the_packet
                wanted_callsign['addr_port'] = self.addr_port
                log.debug("Listener wanted_callsign {}".format(wanted_callsign))
                self.unseen.append(wanted_callsign)

                contains_my_call = False
                if self.my_call in message:
                    contains_my_call = True

                # Do not use callback message if wanted callsign allready gave us a report
                if self.message_callback and self.rst_rcvd_from_being_called is None:
                    self.message_callback({
                        'type': 'wanted_callsign_detected',
                        'formatted_message': formatted_message,
                        'contains_my_call': contains_my_call
                    })                    

                if wanted_callsign.get('cq'):
                    debug_message = "Found CQ message from callsign [ {} ]. Message: {}".format(callsign, msg)
                else:
                    debug_message = "Found message directed to [ {} ] from callsign [ {} ]. Message: {}".format(directed, callsign, msg)
                log.warning(debug_message)

                if self.enable_sending_reply and self.dx_being_called is None:
                    self.dx_being_called = callsign   
                    self.reply_to_message()                    

                # Use message_callback to communicate with the GUI
                if self.message_callback and self.enable_debug_output:
                    self.message_callback(debug_message)

        except TypeError as e:
            log.error("Caught a type error in parsing packet: {}; error {}\n{}".format(
            self.the_packet.message, e, traceback.format_exc()))
        except Exception as e:
            log.error("Caught an error parsing packet: {}; error {}\n{}".format(
                self.the_packet.message, e, traceback.format_exc()))   

    def reply_to_message(self):
        try:
            reply_pkt = pywsjtx.ReplyPacket.Builder(self.the_packet)
            log.warning(f"Sending ReplyPacket: {reply_pkt}")
            self.s.send_packet(self.addr_port, reply_pkt)
            log.debug("ReplyPacket sent successfully.")                
        except Exception as e:
            log.error(f"Error sending packets: {e}\n{traceback.format_exc()}")

    def log_qso_to_adif(self):
        required_fields = {
            'dx_being_called'       : self.dx_being_called,
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

        callsign        = self.dx_being_called
        grid            = self.grid_being_called or ''
        mode            = self.mode
        rst_sent        = self.get_clean_rst(self.rst_sent)
        rst_rcvd        = self.get_clean_rst(self.rst_rcvd_from_being_called)
        freq_rx         = f"{round((self.frequency + self.rx_df) / 1_000_000, 6):.6f}"
        freq            = f"{round((self.frequency + self.tx_df) / 1_000_000, 6):.6f}"
        band            = self.get_amateur_band(self.frequency)
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
            log.warning("QSOLogged [ {} ]".format(self.dx_being_called))
        except Exception as e:
            log.error(f"Can't write ADIF file {e}")

    def log_qso_to_udp(self):
        try:
            awaited_rst_sent = self.get_clean_rst(self.rst_sent)
            awaited_rst_rcvd = self.get_clean_rst(self.rst_rcvd_from_being_called)

            self.packet_sender.send_qso_logged_packet(
                wsjtx_id        = self.the_packet.wsjtx_id,
                datetime_off    = self.qso_time_off,
                call            = self.dx_being_called,
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
            log.warning("QSOLoggedPacket sent via UDP for [ {} ]".format(self.dx_being_called))
        except Exception as e:
            log.error(f"Error sending QSOLoggedPacket via UDP: {e}")
            log.error("Caught an error while trying to send QSOLoggedPacket packet: error {}\n{}".format(e, traceback.format_exc()))

    def get_cuarto(self):
        return 15 * (datetime.now().second // 15)

    def get_clean_rst(self, rst):
        def repl(match):
            sign = match.group(1)
            number = match.group(2).zfill(2)[:2]
            return f"{sign}{number}"
        pattern = r'^R?([+-]?)(\d+)$'
        cleaned_rst = re.sub(pattern, repl, rst)
        return cleaned_rst

    def get_amateur_band(self, frequency):
        bands = {
            '160m'  : (1_800_000, 2_000_000),
            '80m'   : (3_500_000, 4_000_000),
            '60m'   : (5_351_500, 5_366_500),  
            '40m'   : (7_000_000, 7_300_000),
            '30m'   : (10_100_000, 10_150_000),
            '20m'   : (14_000_000, 14_350_000),
            '17m'   : (18_068_000, 18_168_000),
            '15m'   : (21_000_000, 21_450_000),
            '12m'   : (24_890_000, 24_990_000),
            '10m'   : (28_000_000, 29_700_000),
            '6m'    : (50_000_000, 54_000_000),
            '2m'    : (144_000_000, 148_000_000),
            '70cm'  : (430_000_000, 440_000_000)
        }
        
        for band, (lower_bound, upper_bound) in bands.items():
            if lower_bound <= frequency <= upper_bound:
                return band
        
        return "Invalid"