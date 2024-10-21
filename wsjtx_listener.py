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
    def __init__(self,q,config,ip_address,port,timeout=2.0):
        log.debug('new listener: '+str(q))
        self.config = config
        self.call = None
        self.band = None
        self.lastReport = datetime.now()
        self.lastScan = None
        self.q = q
        self.unseen = []
        self.stopped = False
        self.ip_address = ip_address
        self.port = port

        self.initAdif()
        self.s = pywsjtx.extra.simple_server.SimpleServer(ip_address, port)

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
        log.debug("stopping wsjtx listener")
        self.stopped = True

    def doListen(self):
        while True:
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
            self.call = self.the_packet.de_call
            self.band = str(freqinfo)+'Khz'
        except Exception as e:
            pass

    def update_log(self):
        log.debug("update log".format(self.the_packet))
        nd = self.q.needDataByBandAndCall(self.band,self.the_packet.call,self.the_packet.grid)
        log.debug("update_log call {} grid {} needData {}".format(self.the_packet.call,self.the_packet.grid,nd))
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
            self.heartbeat()
        elif type(self.the_packet) == pywsjtx.StatusPacket:
            self.update_status()
        elif type(self.the_packet) == pywsjtx.QSOLoggedPacket:
            self.update_log()
        elif self.band != None:
            if type(self.the_packet) == pywsjtx.DecodePacket:
                self.parse_packet()
        else:
            log.debug('unknown packet type {}; {}'.format(type(self.the_packet),self.the_packet))