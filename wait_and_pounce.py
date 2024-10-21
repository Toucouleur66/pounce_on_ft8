import pywsjtx.extra.simple_server
import threading
import sys
import signal
import time

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
    def __init__(self, q, config, ip_address, port, message_callback=None):
        super().__init__(q, config, ip_address, port)
        self.message_callback = message_callback

    def handle_packet(self):
        if isinstance(self.the_packet, pywsjtx.HeartBeatPacket):
            super().handle_packet()
            message = f"Heartbeat: {self.addr_port}: {self.the_packet}"
            log.info(message)
            if self.message_callback:
                self.message_callback(message)
        elif isinstance(self.the_packet, pywsjtx.StatusPacket):
            super().handle_packet()
            message = f"Status update: {self.addr_port}: {self.the_packet}"
            log.info(message)
            if self.message_callback:
                self.message_callback(message)
        else:
            super().handle_packet()

def main(
        instance_type,
        frequency,
        time_hopping,
        your_callsign,
        wanted_callsigns,
        mode,
        control_log_analysis_tracking,
        stop_event,
        message_callback=None
    ):

    ip_address = '192.168.1.30'
    port = 2237

    q = MockQueue()
    config = MockConfig()

    listener = MyListener(q, config, ip_address, port, message_callback=message_callback)

    listener.listen()

    # Garder le script en cours d'exécution jusqu'à ce que stop_event soit défini
    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nArrêt du script.")
    finally:
        listener.stop()
