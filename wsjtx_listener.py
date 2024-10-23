import pywsjtx.extra.simple_server
import threading
import traceback
import socket
import requests
import re
import random
from datetime import datetime,timedelta
import pandas
from termcolor import colored
from logger import LOGGER as log

class Listener:
    def __init__(
            self,
            q,
            config,
            ip_address,
            port,
            your_callsign,
            wanted_callsigns,
            message_callback=None
        ):
        log.debug('New Listener: ' + str(q))
        self.config = config
        self.my_call = None
        self.band = None
        self.dx_call = None

        self.your_callsign = your_callsign
        self.wanted_callsigns = set(wanted_callsigns)
        self.message_callback = message_callback

        self.decode_packet_count = 0
        self.last_decode_packet_time = None
        self.last_heartbeat_time = None

        self.lastReport = datetime.now()
        self.lastScan = None
        self.q = q
        self.unseen = []
        self.unseen_lock = threading.Lock()

        self.stopped = False
        self.ip_address = ip_address
        self.port = port

        self._running = True

        self.s = pywsjtx.extra.simple_server.SimpleServer(ip_address, port)
        self.s.sock.settimeout(1.0)

        self.initAdif()

    def initAdif(self):
        filePaths = self.config.get('ADIF_FILES','paths').splitlines()
        if self.config.get('OPTS','load_adif_files_on_start'):
            for filepath in filePaths:
                self.q.addAdifFile(filepath,True)
            self.loadLotw()

    def loadLotw(self):
        if self.config.get('LOTW','enable'):
            username = self.config.get('LOTW','username')
            password = self.config.get('LOTW','password')
            if username and password:
                self.q.loadLotw(username,password)

    def webhook_event(self,event):
        events = self.config.get('WEBHOOKS','events').split(',')
        for webhook in self.config.get('WEBHOOKS','hooks').splitlines():
            try:
                for sendEvent in events:
                    if event[sendEvent]:
                        requests.post(webhook, data=event)
                        break
            except Exception as e:
                log.warn('webhook {} failed: event {} error {}'.format(webhook,event,e))

    def print_line(self):
        now = datetime.now()
        newLastReport = datetime(now.year, now.month, now.day, now.hour, now.minute, 15*(now.second // 15),0)
        if (newLastReport-self.lastReport).total_seconds() >= 15:
            log.info("------- "+str(newLastReport)+" -------")
        self.lastReport = newLastReport

    def send_reply(self,data):
        packet = pywsjtx.ReplyPacket.Builder(data['packet'])
        self.s.send_packet(data['addr_port'], packet)

    def parse_packet(self):
        if self.q.defered:
            return
        
        print('decode packet ',self.the_packet)

    def stop(self):
        self._running = False
        self.s.sock.close() 

    def doListen(self):
        while self._running:
            try:
                self.pkt, self.addr_port = self.s.sock.recvfrom(8192)
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
        log.info("Listener started "+self.ip_address+":"+str(self.port))
        self.t.start()

    def heartbeat(self):
        max_schema = max(self.the_packet.max_schema, 3)
        reply_beat_packet = pywsjtx.HeartBeatPacket.Builder(self.the_packet.wsjtx_id,max_schema)
        self.s.send_packet(self.addr_port, reply_beat_packet)

    def update_status(self):
        log.debug('wsjt-x status {}'.format(self.the_packet))
        try:
            freqinfo = self.the_packet.dial_frequency/1000
            self.my_call = self.the_packet.de_call
            self.dx_call = self.the_packet.dx_call
            self.band = str(freqinfo)+'Khz'
        except Exception as e:
            pass

    def update_log(self):
        log.debug("update log".format(self.the_packet))
        nd = self.q.wanted_dataByBandAndCall(self.band,self.the_packet.call,self.the_packet.grid)
        log.debug("update_log call {} grid {} wanted_data {}".format(self.the_packet.call,self.the_packet.grid,nd))
        try:
            qso = { 
                'CALL': self.the_packet.call, 
                'BAND': self.band,
                'DXCC': nd.get('dx'),
                'STATE': nd.get('state'),
                'GRID': nd.get('grid')
            }
            self.q.addQso(qso)
        except Exception as e:
            log.error("Failed to update log for call {}, data {}: {}".format(self.the_packet.call,nd,e))
            pass

    def handle_packet(self):
        if type(self.the_packet) == pywsjtx.HeartBeatPacket:
            self.last_heartbeat_time = datetime.now()
            self.heartbeat()
            self.send_status_update()
        elif type(self.the_packet) == pywsjtx.StatusPacket:
            self.update_status()
        elif type(self.the_packet) == pywsjtx.QSOLoggedPacket:
            self.update_log()
        elif type(self.the_packet) == pywsjtx.DecodePacket:
            self.last_decode_packet_time = datetime.now()
            self.decode_packet_count += 1
            self.parse_packet()
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

    def parse_packet(self):
        wanted_data = None

        if wanted_data is not None:
            wanted_data['packet'] = self.the_packet
            wanted_data['addr_port'] = self.addr_port
            log.debug("listener wanted_data {}".format(wanted_data))
            with self.unseen_lock:
                self.unseen.append(wanted_data)        

        log.debug('{}'.format(self.the_packet))
        try:
            message = self.the_packet.message
            decode_time = self.the_packet.time
            snr = self.the_packet.snr
            delta_t = self.the_packet.delta_t
            delta_f = self.the_packet.delta_f         

            time_str = decode_time.strftime('%H%M%S')

            formatted_message = f"{time_str} {snr:+d} {delta_t:+.1f} {delta_f} ~ {message}"

            # Pattern for CQ calls
            match = re.match(r"^CQ\s(\w{2,3}\b)?\s?([A-Z0-9/]+)\s?([A-Z0-9/]+)?\s?([A-Z]{2}[0-9]{2})?", message)
            if match:
                directed = match.group(1)
                callsign = match.group(2)
                grid = match.group(4)

                if callsign in self.wanted_callsigns:
                    wanted_data = {
                        'cuarto': 15 * (datetime.now().second // 15),
                        'directed': directed,
                        'callsign': callsign,
                        'grid': grid,
                        'cq': True
                    }

            else:
                # Pattern for dual-call messages
                match = re.match(r"([A-Z0-9/]+) ([A-Z0-9/]+) ([A-Z0-9+-]+)", message)
                if match:
                    directed = match.group(1)
                    callsign = match.group(2)
                    msg = match.group(3)

                    if callsign in self.wanted_callsigns:
                        wanted_data = {
                            'cuarto': 15 * (datetime.now().second // 15),
                            'directed': directed,
                           'callsign': callsign,
                            'msg': msg
                        }

            if wanted_data is not None:
                wanted_data['packet'] = self.the_packet
                wanted_data['addr_port'] = self.addr_port
                log.debug("Listener wanted_data {}".format(wanted_data))
                self.unseen.append(wanted_data)

                contains_my_call = False
                if self.my_call in message:
                    contains_my_call = True

                if self.message_callback:
                    self.message_callback({
                        'type': 'wanted_callsign_detected',
                        'formatted_message': formatted_message,
                        'contains_my_call': contains_my_call
                    })                    

                # Start the webhook event in a new thread if needed
                threading.Thread(target=self.webhook_event, args=(wanted_data,), daemon=True).start()

                debug_message = f"Found Wanted Callsign: [black_on_yellow]{callsign}[/black_on_yellow]"
                log.info(debug_message)

                try:
                    bg = pywsjtx.QCOLOR.Red()
                    fg = pywsjtx.QCOLOR.White()

                    # color_pkt = pywsjtx.HighlightCallsignPacket.Builder(
                    #    self.the_packet.wsjtx_id, callsign, bg, fg, True
                    # )
                    # log.debug(f"Sending HighlightCallsignPacket: {color_pkt}")
                    # self.s.send_packet(self.addr_port, color_pkt)
                    # log.debug("HighlightCallsignPacket sent successfully.")

                    # Construction et envoi du paquet Reply
                    reply_pkt = pywsjtx.ReplyPacket.Builder(self.the_packet)
                    log.debug(f"Sending ReplyPacket: {reply_pkt}")
                    self.s.send_packet(self.addr_port, reply_pkt)
                    log.debug("ReplyPacket sent successfully.")

                except Exception as e:
                    log.error(f"Error sending packets: {e}\n{traceback.format_exc()}")

                # Use message_callback to communicate with the GUI
                if self.message_callback:
                    self.message_callback(debug_message)

        except TypeError as e:
            log.error("Caught a type error in parsing packet: {}; error {}".format(self.the_packet.message, e))
        except Exception as e:
            log.error("Caught an error parsing packet: {}; error {}".format(self.the_packet.message, e))
