# wait_and_pounce.py

import pywsjtx.extra.simple_server
import threading
import sys
import signal
import time
import datetime
import logging

from wsjtx_listener import Listener
from utils import is_in_wanted

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

# Gestion de l'événement d'arrêt global
stop_event = threading.Event()

# Gestionnaire de signaux pour arrêter proprement le programme
def signal_handler(sig, frame):
    print("Manual stop.")
    stop_event.set()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Classe personnalisée MyListener héritant de Listener
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
            wanted_callsigns,
            message_callback=message_callback
        )
        self.message_callback = message_callback

    def handle_packet(self):
        try:
            super().handle_packet()

            if isinstance(self.the_packet, (pywsjtx.HeartBeatPacket, pywsjtx.StatusPacket)) and self.enable_debug_output:
                message = f"{self.the_packet}"
                log.info(message)
                if self.message_callback:
                    self.message_callback(message)

            elif isinstance(self.the_packet, pywsjtx.DecodePacket):
                decode_time             = self.the_packet.time
                decode_time_str         = decode_time.strftime('%Y-%m-%d %H:%M:%S')

                message_text            = self.the_packet.message
                snr                     = self.the_packet.snr
                delta_time              = self.the_packet.delta_t
                delta_frequency         = self.the_packet.delta_f

                message_color_text      = "white_on_blue"
                if is_in_wanted(message_text, self.wanted_callsigns):
                    message_color_text  = "black_on_yellow"

                display_message = (
                    f"Decode at {decode_time_str} "
                    f"SNR {snr:+3d} dB "
                    f"{delta_time:+5.1f}s "
                    f"{delta_frequency:+6d}Hz ~ "
                    f"[{message_color_text}]{message_text:<21.21}[/{message_color_text}]"
                )
                log.info(display_message)
                if self.message_callback:
                    self.message_callback(display_message)
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
        wanted_callsigns=wanted_callsigns,
        message_callback=message_callback
    )

    listener.listen()

    try:
        while not stop_event.is_set():
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stop everything.")
        stop_event.set()
    finally:
        listener.stop()
        listener.t.join()
        log.info("Listener stopped.")
