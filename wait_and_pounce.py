# wait_and_pounce.py

import pywsjtx.extra.simple_server
import threading
import signal
import time
import logging

from logger import get_logger, get_gui_logger
from wsjtx_listener import Listener
from utils import is_in_wanted

# logging.basicConfig(level=logging.DEBUG)
log = get_logger(__name__)
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
            enable_debug_output,
            enable_pounce_log,
            enable_log_packet_data, 
            enable_show_all_decoded,
            wanted_callsigns,
            message_callback=None
        ):
        super().__init__(
            primary_udp_server_address,
            primary_udp_server_port,
            secondary_udp_server_address,
            secondary_udp_server_port,
            enable_secondary_udp_server,
            enable_sending_reply,
            enable_debug_output,
            enable_pounce_log,
            enable_log_packet_data, 
            enable_show_all_decoded,
            wanted_callsigns,
            message_callback=message_callback
        )
        self.message_callback = message_callback

    def handle_packet(self):
        try:
            super().handle_packet()

            if isinstance(self.the_packet, (pywsjtx.HeartBeatPacket, pywsjtx.StatusPacket)):
                
                # Needed to handle GUI window title
                wsjtx_id = self.the_packet.wsjtx_id  
                wsjtx_id_message = f"wsjtx_id:{wsjtx_id}"
                self.message_callback(wsjtx_id_message)

                if self.enable_debug_output:
                    message = f"{self.the_packet}"
                    log.info(message)
                    if self.message_callback:
                        self.message_callback(message)

            elif isinstance(self.the_packet, pywsjtx.DecodePacket):
                is_from_wanted          = False
                decode_time             = self.the_packet.time
                decode_time_str         = decode_time.strftime('%Y-%m-%d %H:%M:%S')

                message_text            = self.the_packet.message
                snr                     = self.the_packet.snr
                delta_time              = self.the_packet.delta_t
                delta_frequency         = self.the_packet.delta_f

                message_color_text      = "white_on_blue"
                if is_in_wanted(message_text, self.wanted_callsigns):
                    is_from_wanted = True
                    message_color_text  = "black_on_yellow"

                display_message = (
                    f"{decode_time_str} "
                    f"{snr:+3d} dB "
                    f"{delta_time:+5.1f}s "
                    f"{delta_frequency:+6d}Hz ~ "
                    f"[{message_color_text}]{message_text:<21.21}[/{message_color_text}]"
                )

                if self.enable_debug_output:
                    message = f"{self.the_packet.message}"
                    log.info(message)

                if self.enable_show_all_decoded or is_from_wanted:
                    gui_log.info(display_message, extra={'to_gui': True})
                        
        except Exception as e:
            log.error(f"Error handling packet: {e}", exc_info=True)
            if self.message_callback:
                self.message_callback(f"Error handling packet: {e}")

def main(
        frequency,
        time_hopping,
        wanted_callsigns,
        mode,
        stop_event,
        primary_udp_server_address,
        primary_udp_server_port,
        secondary_udp_server_address,
        secondary_udp_server_port,
        enable_secondary_udp_server,
        enable_sending_reply,
        enable_debug_output,
        enable_pounce_log,
        enable_log_packet_data,
        enable_show_all_decoded,
        message_callback=None
    ):

    if isinstance(wanted_callsigns, str):
        wanted_callsigns = [callsign.strip() for callsign in wanted_callsigns.split(',')]

    listener = MyListener(
        primary_udp_server_address,
        primary_udp_server_port,
        secondary_udp_server_address,
        secondary_udp_server_port,
        enable_secondary_udp_server,
        enable_sending_reply,
        enable_debug_output,
        enable_pounce_log,
        enable_log_packet_data,
        enable_show_all_decoded,
        wanted_callsigns=wanted_callsigns,
        message_callback=message_callback
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
