# wait_and_pounce.py

import pywsjtx.extra.simple_server

import threading
import signal
import time

from logger import get_logger
from wsjtx_listener import Listener
from utils import parse_wsjtx_message
from callsign_lookup import CallsignLookup

log         = get_logger(__name__)
lookup      = CallsignLookup()

stop_event = threading.Event()

def signal_handler(sig, frame):
    log.info("Manual stop.")
    stop_event.set()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

class MyListener(Listener):
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
            enable_show_all_decoded,
            monitored_callsigns,
            excluded_callsigns,
            wanted_callsigns,
            special_mode,
            message_callback = None
        ):
        super().__init__(
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
            enable_show_all_decoded,
            monitored_callsigns,
            excluded_callsigns,
            wanted_callsigns,
            special_mode,
            message_callback=message_callback
        )
        self.message_callback = message_callback

    def handle_packet(self):
        try:
            super().handle_packet()

            if isinstance(self.the_packet, (
                pywsjtx.HeartBeatPacket,
                pywsjtx.StatusPacket
            )):
                
                # Needed to handle GUI window title
                wsjtx_id = self.the_packet.wsjtx_id  
                wsjtx_id_message = f"wsjtx_id:{wsjtx_id}"
                self.message_callback(wsjtx_id_message)

                if self.enable_pounce_log:
                    message = f"{self.the_packet}"
                    log.info(message)
                    if self.message_callback and self.enable_debug_output:
                        self.message_callback(message)

            elif isinstance(self.the_packet, pywsjtx.DecodePacket):
                decode_time             = self.the_packet.time
                decode_time_str         = decode_time.strftime('%Y-%m-%d %H:%M:%S')
               
                snr                     = self.the_packet.snr
                delta_time              = self.the_packet.delta_t
                delta_frequencies       = self.the_packet.delta_f
                msg                     = self.the_packet.message                

                parsed_data             = parse_wsjtx_message(
                                            msg,
                                            self.wanted_callsigns,
                                            self.excluded_callsigns,
                                            self.monitored_callsigns,
                                        )
                directed                = parsed_data['directed']
                wanted                  = parsed_data['wanted']
                monitored               = parsed_data['monitored']  
                callsign                = parsed_data['callsign']
                
                if callsign is None:
                    entity = "Where ?"
                else:
                    callsign_info = lookup.lookup_callsign(callsign)
                    if callsign_info:
                        entity = callsign_info["entity"].title()
                    else:
                        entity = ""
            
                if directed == self.my_call and self.my_call is not None:
                    msg_color_text      = "bright_for_my_call"
                elif wanted is True:
                    msg_color_text      = "black_on_yellow"
                elif monitored is True:
                    msg_color_text      = "black_on_purple"                    
                elif directed in self.wanted_callsigns:  
                    msg_color_text      = "white_on_blue"
                else:
                    msg_color_text      = None

                formatted_msg = f"{msg:<21.21}"                                        
                    
                display_message = (
                    f"{decode_time_str} "
                    f"{snr:+3d} dB "
                    f"{delta_time:+5.1f}s "
                    f"{delta_frequencies:+6d}Hz ~ "
                    f"{formatted_msg}"
                    "\t\t"
                    f"{entity}"
                )

                if self.enable_show_all_decoded or msg_color_text:
                    if self.message_callback:
                        self.message_callback({                        
                        'decode_time_str'   : decode_time_str,
                        'callsign'          : callsign,
                        'snr'               : snr,
                        'delta_time'        : delta_time,
                        'delta_freq'        : delta_frequencies,
                        'formatted_msg'     : formatted_msg.strip(),
                        'entity'            : entity,
                        'msg_color_text'    : msg_color_text,
                        'display_message'   : display_message
                    })
                        
        except Exception as e:
            log.error(f"Error handling packet: {e}", exc_info=True)
            if self.message_callback:
                self.message_callback(f"Error handling packet: {e}")

def main(
        monitored_callsigns,
        excluded_callsigns,
        wanted_callsigns,
        special_mode,
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
        enable_show_all_decoded,
        message_callback = None
    ):

    if isinstance(wanted_callsigns, str):
        wanted_callsigns = [callsign.strip() for callsign in wanted_callsigns.split(',')]

    if isinstance(excluded_callsigns, str):
        excluded_callsigns = [callsign.strip() for callsign in excluded_callsigns.split(',')]        

    if isinstance(monitored_callsigns, str):
        monitored_callsigns = [callsign.strip() for callsign in monitored_callsigns.split(',')]                

    listener = MyListener(
        primary_udp_server_address      = primary_udp_server_address,
        primary_udp_server_port         = primary_udp_server_port,
        secondary_udp_server_address    = secondary_udp_server_address,
        secondary_udp_server_port       = secondary_udp_server_port,
        enable_secondary_udp_server     = enable_secondary_udp_server,
        enable_sending_reply            = enable_sending_reply,
        enable_gap_finder                = enable_gap_finder,
        enable_watchdog_bypass          = enable_watchdog_bypass,
        enable_debug_output             = enable_debug_output,
        enable_pounce_log               = enable_pounce_log,
        enable_log_packet_data          = enable_log_packet_data,
        enable_show_all_decoded         = enable_show_all_decoded,
        monitored_callsigns             = monitored_callsigns,
        excluded_callsigns              = excluded_callsigns,
        wanted_callsigns                = wanted_callsigns,
        special_mode                    = special_mode,
        message_callback                = message_callback
    )
    listener.listen()

    try:
        while not stop_event.is_set():
            time.sleep(0.1)
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        listener.stop()
        listener.t.join()
