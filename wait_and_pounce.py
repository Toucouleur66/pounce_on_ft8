import pywsjtx.extra.simple_server
import threading
import sys
import signal
import time
import datetime

from wsjtx_listener import Listener

class MockQueue:
    def __init__(self):
        self.defered = False

    def addAdifFile(self, filepath, flag):
        pass

    def loadLotw(self, username, password):
        pass

    def needDataByBandAndCall(self, band, call, grid):
        return {}

    def addQso(self, qso):
        pass

class MockConfig:
    def get(self, section, option):
        default_values = {
            ('ADIF_FILES', 'paths'): '',
            ('OPTS', 'load_adif_files_on_start'): False,
            ('LOTW', 'enable'): False,
            ('LOTW', 'username'): '',
            ('LOTW', 'password'): '',
            ('WEBHOOKS', 'events'): '',
            ('WEBHOOKS', 'hooks'): '',
        }
        return default_values.get((section, option), '')

import logging

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

def signal_handler(sig, frame):
    print("\nArrêt manuel du script.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

class MyListener(Listener):
    def __init__(
            self,
            q,
            config,
            ip_address,
            port,
            wanted_callsigns,
            message_callback=None
        ):
        super().__init__(
            q,
            config,
            ip_address,
            port,
            wanted_callsigns,
            message_callback=message_callback
        )
        self.message_callback = message_callback

    def handle_packet(self):
        if isinstance(self.the_packet, pywsjtx.HeartBeatPacket):
            super().handle_packet()
            message = f"{self.the_packet}"
            log.info(message)
            if self.message_callback:
                self.message_callback(message)
        elif isinstance(self.the_packet, pywsjtx.StatusPacket):
            super().handle_packet()
            message = f"{self.the_packet}"
            log.info(message)
            if self.message_callback:
                self.message_callback(message)
        elif isinstance(self.the_packet, pywsjtx.DecodePacket):
            super().handle_packet()
            # print(f"Attributes of DecodePacket: {dir(self.the_packet)}")
            decode_time = self.the_packet.time
            decode_time_str = decode_time.strftime('%Y-%m-%d %H:%M:%S')

            message_text = self.the_packet.message
            snr = self.the_packet.snr
            delta_time = self.the_packet.delta_t  
            delta_frequency = self.the_packet.delta_f
            mode = self.the_packet.mode

            display_message = f"Decode at {decode_time_str} SNR {snr} dB {delta_time:+.1f}s {delta_frequency}Hz {mode}: [white_on_blue]{message_text}[/white_on_blue]"
            log.info(display_message)
            if self.message_callback:
                self.message_callback(display_message)
        else:
            super().handle_packet()

def main(
        frequency,
        time_hopping,
        wanted_callsigns,
        mode,
        stop_event,
        message_callback=None
    ):

    ip_address = '192.168.1.30'
    port = 2237

    q = MockQueue()
    config = MockConfig()

    if isinstance(wanted_callsigns, str):
        wanted_callsigns = [callsign.strip() for callsign in wanted_callsigns.split(',')]

    listener = MyListener(
        q,
        config,
        ip_address,
        port,
        wanted_callsigns=wanted_callsigns,
        message_callback=message_callback
    )
    listener.listen()

    try:
        while not stop_event.is_set():
            time.sleep(0.1)  
    except KeyboardInterrupt:
        print("\nArrêt du script.")
    finally:
        listener.stop()
        listener.t.join()
