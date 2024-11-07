# wait_and_pounce.py

import pywsjtx.extra.simple_server

import threading
import signal
import time

from logger import get_logger, get_gui_logger
from wsjtx_listener import Listener
from utils import parse_wsjtx_message

log     = get_logger(__name__)
gui_log = get_gui_logger()

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
            important_callsigns,
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
            important_callsigns,
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
                                            self.important_callsigns,
                                        )
                directed                = parsed_data['directed']
                wanted                  = parsed_data['wanted']
                important               = parsed_data['important']                
            
                if directed == self.my_call:
                    msg_color_text      = "bright_for_my_call"
                elif wanted is True:
                    msg_color_text      = "black_on_yellow"
                elif important is True:
                    msg_color_text      = "black_on_brown"                    
                elif directed in self.wanted_callsigns:  
                    msg_color_text      = "white_on_blue"
                else:
                    msg_color_text      = None

                if msg_color_text:
                    formatted_msg = f"[{msg_color_text}]{msg:<21.21}[/{msg_color_text}]"
                else:
                    formatted_msg = f"{msg:<21.21}"                    
                    
                display_message = (
                    f"{decode_time_str} "
                    f"{snr:+3d} dB "
                    f"{delta_time:+5.1f}s "
                    f"{delta_frequencies:+6d}Hz ~ "
                    f"{formatted_msg}"
                )

                if self.enable_show_all_decoded or msg_color_text:
                    gui_log.info(display_message, extra={'to_gui': True})
                        
        except Exception as e:
            log.error(f"Error handling packet: {e}", exc_info=True)
            if self.message_callback:
                self.message_callback(f"Error handling packet: {e}")

def main(
        important_callsigns,
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

    if isinstance(important_callsigns, str):
        important_callsigns = [callsign.strip() for callsign in important_callsigns.split(',')]                

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
        important_callsigns             = important_callsigns,
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
