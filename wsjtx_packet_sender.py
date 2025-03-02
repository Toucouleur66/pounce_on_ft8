# wsjtx_packet_sender.py

import socket
from pywsjtx.wsjtx_packets import PacketWriter, QSOLoggedPacket, StatusPacket, DecodePacket, HeartBeatPacket, PacketUtil
import datetime

class WSJTXPacketSender:
    def __init__(self, ip_address='127.0.0.1', udp_port=2237):
        self.ip_address = ip_address
        self.udp_port = udp_port

    def send_packet(self, packet_data):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(packet_data, (self.ip_address, self.udp_port))
            print(f"Packet sent to {self.ip_address}:{self.udp_port}")

    def send_qso_logged_packet(
            self,
            wsjtx_id        = None,
            datetime_off    = None,
            call            = None,
            grid            = None,
            frequency       = None,
            mode            = None,
            report_sent     = None,
            report_recv     = None,
            tx_power        = None,
            comments        = None,
            name            = None,
            datetime_on     = None,
            op_call         = None,
            my_call         = None,
            my_grid         = None,
            exchange_sent   = None,
            exchange_recv   = None
        ):
        if datetime_off is None:
            datetime_off = datetime.datetime.now()
        if datetime_on is None:
            datetime_on = datetime_off

        pkt_writer = PacketWriter()

        pkt_writer.write_QInt32(QSOLoggedPacket.TYPE_VALUE)
        pkt_writer.write_QString(wsjtx_id)
        pkt_writer.write_QDateTime(datetime_off)
        pkt_writer.write_QString(call)
        pkt_writer.write_QString(grid)
        pkt_writer.write_QInt64(frequency)
        pkt_writer.write_QString(mode)
        pkt_writer.write_QString(report_sent)
        pkt_writer.write_QString(report_recv)
        pkt_writer.write_QString(tx_power)
        pkt_writer.write_QString(comments)
        pkt_writer.write_QString(name)
        pkt_writer.write_QDateTime(datetime_on)
        pkt_writer.write_QString(op_call)
        pkt_writer.write_QString(my_call)
        pkt_writer.write_QString(my_grid)
        pkt_writer.write_QString(exchange_sent)
        pkt_writer.write_QString(exchange_recv)

        packet_data = pkt_writer.packet

        print("Hex value for QSOLogged Packet:")
        print(PacketUtil.hexdump(packet_data))

        self.send_packet(packet_data)

    def send_heartbeat_packet(
            self,
            wsjtx_id    = "WSJT-X",
            max_schema  = 3,
            version     = 2,
            revision    = 0
        ):
        pkt_writer = PacketWriter()

        pkt_writer.write_QInt32(HeartBeatPacket.TYPE_VALUE)
        pkt_writer.write_QString(wsjtx_id)
        pkt_writer.write_QInt32(max_schema)
        pkt_writer.write_QInt32(version)
        pkt_writer.write_QInt32(revision)

        packet_data = pkt_writer.packet

        print("Hex value for HeartBeat Packet:")
        print(PacketUtil.hexdump(packet_data))

        self.send_packet(packet_data)

    def send_decode_packet(
            self,
            wsjtx_id="WSJT-X",
            snr=0,
            delta_t=0.0,
            delta_f=0,
            mode="FT8",
            message="CQ DX",
        ):
        pkt_writer = PacketWriter()

        pkt_writer.write_QInt32(DecodePacket.TYPE_VALUE)  
        pkt_writer.write_QString(wsjtx_id)                
        pkt_writer.write_QInt8(1)                         

        midnight = datetime.datetime.combine(datetime.datetime.utcnow().date(), datetime.time(0))
        millis_since_midnight = int((datetime.datetime.utcnow() - midnight).total_seconds() * 1000)
        pkt_writer.write_QInt32(millis_since_midnight)    

        pkt_writer.write_QInt32(snr)                      
        pkt_writer.write_QFloat(delta_t)                  
        pkt_writer.write_QInt32(delta_f)                  
        pkt_writer.write_QString(mode)                    
        pkt_writer.write_QString(message)                 
        pkt_writer.write_QInt8(0)                         
        pkt_writer.write_QInt8(0)                         

        packet_data = pkt_writer.packet

        print("Hex value for Packet:")
        print(PacketUtil.hexdump(packet_data))

        self.send_packet(packet_data)

    def send_status_packet(
            self,
            wsjtx_id="WSJT-X",
            dial_frequency=50313000, 
            mode="FT8",
            dx_call="CQ",
            report="-10",
            tx_mode="FT8",
            tx_enabled=False,
            transmitting=False,
            decoding=True,
            rx_df=1500,
            tx_df=1500,
            de_call="F5UKW",
            de_grid="JN12",
            dx_grid="FN31",
            tx_watchdog=True,
            sub_mode="",
            fast_mode=False,
            special_op_mode=False
        ):
        pkt_writer = PacketWriter()

        pkt_writer.write_QInt32(StatusPacket.TYPE_VALUE)
        pkt_writer.write_QString(wsjtx_id)
        pkt_writer.write_QInt64(dial_frequency)
        pkt_writer.write_QString(mode)
        pkt_writer.write_QString(dx_call)
        pkt_writer.write_QString(report)
        pkt_writer.write_QString(tx_mode)
        pkt_writer.write_QInt8(int(tx_enabled))
        pkt_writer.write_QInt8(int(transmitting))
        pkt_writer.write_QInt8(int(decoding))
        pkt_writer.write_QInt32(rx_df)
        pkt_writer.write_QInt32(tx_df)
        pkt_writer.write_QString(de_call)
        pkt_writer.write_QString(de_grid)
        pkt_writer.write_QString(dx_grid)
        pkt_writer.write_QInt8(int(tx_watchdog))
        pkt_writer.write_QString(sub_mode)
        pkt_writer.write_QInt8(int(fast_mode))
        pkt_writer.write_QInt8(int(special_op_mode))

        packet_data = pkt_writer.packet

        print("📡 Hex value for Status Packet:")
        print(PacketUtil.hexdump(packet_data))

        self.send_packet(packet_data)