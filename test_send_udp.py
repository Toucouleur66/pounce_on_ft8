import struct
import datetime
import math
import socket
import argparse
import time
import json

class PacketUtil:
    @classmethod
    def hexdump(cls, src, length=16):
        FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or '.' for x in range(256)])
        lines = []
        for c in range(0, len(src), length):
            chars = src[c:c + length]
            hex_str = ' '.join(["%02x" % x for x in chars])
            printable = ''.join(["%s" % ((x <= 127 and FILTER[x]) or '.') for x in chars])
            lines.append("%04x  %-*s  %s\n" % (c, length * 3, hex_str, printable))
        return ''.join(lines)

    @classmethod
    def midnight_utc(cls):
        utcnow = datetime.datetime.utcnow()
        utcmidnight = datetime.datetime(utcnow.year, utcnow.month, utcnow.day, 0, 0)
        return utcmidnight

    @classmethod
    def JDToDateMeeus(cls, jDNum):
        F = 0.0
        jDNum += 0.5
        Z = jDNum
        F = jDNum - Z
        if Z < 2299161:
            A = Z
        else:
            alpha = math.floor((Z - 1867216.25) / 36524.25)
            A = Z + 1 + alpha - math.floor(alpha / 4.0)
        B = A + 1524
        C = math.floor((B - 122.1) / 365.25)
        D = math.floor(365.25 * C)
        E = math.floor((B - D) / 30.6001)
        day = int(B - D - math.floor(30.6001 * E) + F)
        if E < 14:
            month = E - 1
        else:
            month = E - 13
        if month > 2:
            year = C - 4716
        else:
            year = C - 4715
        return (year, month, day)

class GenericWSJTXPacket(object):
    SCHEMA_VERSION = 3
    MINIMUM_SCHEMA_SUPPORTED = 2
    MAXIMUM_SCHEMA_SUPPORTED = 3
    MINIMUM_NETWORK_MESSAGE_SIZE = 8
    MAXIMUM_NETWORK_MESSAGE_SIZE = 2048
    MAGIC_NUMBER = 0xadbccbda

    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        self.addr_port = addr_port
        self.magic = magic
        self.schema = schema
        self.pkt_type = pkt_type
        self.pkt_id = id
        self.pkt = pkt

class PacketWriter(object):
    def __init__(self):
        self.ptr_pos = 0
        self.packet = bytearray()
        self.write_header()

    def write_header(self):
        self.write_QUInt32(GenericWSJTXPacket.MAGIC_NUMBER)
        self.write_QInt32(GenericWSJTXPacket.SCHEMA_VERSION)

    def write_QInt8(self, val):
        self.packet.extend(struct.pack('>b', val))

    def write_QUInt8(self, val):
        self.packet.extend(struct.pack('>B', val))

    def write_QBool(self, val):
        self.packet.extend(struct.pack('>?', val))

    def write_QInt16(self, val):
        self.packet.extend(struct.pack('>h', val))

    def write_QUInt16(self, val):
        self.packet.extend(struct.pack('>H', val))

    def write_QInt32(self, val):
        self.packet.extend(struct.pack('>l', val))

    def write_QUInt32(self, val):
        self.packet.extend(struct.pack('>L', val))

    def write_QInt64(self, val):
        self.packet.extend(struct.pack('>q', val))

    def write_QFloat(self, val):
        self.packet.extend(struct.pack('>d', val))

    def write_QString(self, str_val):
        b_values = str_val
        if type(str_val) != bytes:
            b_values = str_val.encode()
        length = len(b_values)
        self.write_QInt32(length)
        self.packet.extend(b_values)

    def write_QColor(self, color_val):
        self.write_QInt8(color_val.spec)
        self.write_QUInt8(color_val.alpha)
        self.write_QUInt8(color_val.alpha)
        self.write_QUInt8(color_val.red)
        self.write_QUInt8(color_val.red)
        self.write_QUInt8(color_val.green)
        self.write_QUInt8(color_val.green)
        self.write_QUInt8(color_val.blue)
        self.write_QUInt8(color_val.blue)
        self.write_QUInt16(0)

class PacketReader(object):
    def __init__(self, packet):
        self.ptr_pos = 0
        self.packet = packet
        self.max_ptr_pos = len(packet)-1
        self.skip_header()

    def at_eof(self):
        return self.ptr_pos > self.max_ptr_pos

    def skip_header(self):
        if self.max_ptr_pos < 8:
            raise Exception('Not enough data to skip header')
        self.ptr_pos = 8

    def check_ptr_bound(self, field_type, length):
        if self.ptr_pos + length > self.max_ptr_pos + 1:
            raise Exception('Not enough data to extract {}'.format(field_type))

    def QInt32(self):
        self.check_ptr_bound('QInt32', 4)
        (the_int32,) = struct.unpack('>l', self.packet[self.ptr_pos:self.ptr_pos+4])
        self.ptr_pos += 4
        return the_int32

    def QInt8(self):
        self.check_ptr_bound('QInt8', 1)
        (the_int8,) = struct.unpack('>b', self.packet[self.ptr_pos:self.ptr_pos+1])
        self.ptr_pos += 1
        return the_int8

    def QFloat(self):
        self.check_ptr_bound('QFloat', 8)
        (the_double,) = struct.unpack('>d', self.packet[self.ptr_pos:self.ptr_pos+8])
        self.ptr_pos += 8
        return the_double

    def QString(self):
        str_len = self.QInt32()
        if str_len == -1:
            return None
        self.check_ptr_bound('QString[{}]'.format(str_len), str_len)
        (str_bytes,) = struct.unpack('{}s'.format(str_len), self.packet[self.ptr_pos:self.ptr_pos+str_len])
        self.ptr_pos += str_len
        return str_bytes.decode('utf-8')

class QDateTime(object):
    def __init__(self, date, time, spec, offset):
        self.date = date
        self.time = time
        self.spec = spec
        self.offset = offset

    def __repr__(self):
        return "date {}\n\ttime {}\n\tspec {}\n\toffset {}".format(self.date, self.time, self.spec, self.offset)

class StatusPacket(GenericWSJTXPacket):
    TYPE_VALUE = 1
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)
        ps = PacketReader(pkt)
        _ = ps.QInt32()  # Type
        self.wsjtx_id = ps.QString()
        self.dial_frequency = ps.QInt64()
        self.mode = ps.QString()
        self.dx_call = ps.QString()
        self.report = ps.QString()
        self.tx_mode = ps.QString()
        self.tx_enabled = ps.QInt8()
        self.transmitting = ps.QInt8()
        self.decoding = ps.QInt8()
        self.rx_df = ps.QInt32()
        self.tx_df = ps.QInt32()
        self.de_call = ps.QString()
        self.de_grid = ps.QString()
        self.dx_grid = ps.QString()
        self.tx_watchdog = ps.QInt8()
        self.sub_mode = ps.QString()
        self.fast_mode = ps.QInt8()
        self.special_op_mode = ps.QInt8()

    def __repr__(self):
        return f"StatusPacket: from {self.addr_port[0]}:{self.addr_port[1]}, wsjtx_id: {self.wsjtx_id}, freq: {self.dial_frequency/1000} kHz"


class RequestSettingPacket(GenericWSJTXPacket):
    TYPE_VALUE = 34
    
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)
        ps = PacketReader(pkt)
        the_type = ps.QInt32()
        self.wsjtx_id = ps.QString()

    def __repr__(self):
        return 'RequestSettingPacket: from {}:{}\n\twsjtx id:{}' .format(self.addr_port[0], self.addr_port[1], self.wsjtx_id)

    @classmethod
    def Builder(cls, to_wsjtx_id='WSJT-X'):
        pkt = PacketWriter()
        pkt.write_QInt32(RequestSettingPacket.TYPE_VALUE)
        pkt.write_QString(to_wsjtx_id)
        return pkt.packet

class DecodePacket(GenericWSJTXPacket):
    TYPE_VALUE = 2
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)
        ps = PacketReader(pkt)
        _ = ps.QInt32()  # Type
        self.wsjtx_id = ps.QString()
        self.new_decode = ps.QInt8()
        self.millis_since_midnight = ps.QInt32()
        self.time = PacketUtil.midnight_utc() + datetime.timedelta(milliseconds=self.millis_since_midnight)
        self.snr = ps.QInt32()
        self.delta_t = ps.QFloat()
        self.delta_f = ps.QInt32()
        self.mode = ps.QString()
        self.message = ps.QString()
        self.low_confidence = ps.QInt8()
        self.off_air = ps.QInt8()

    def __repr__(self):
        return f"DecodePacket: from {self.addr_port[0]}:{self.addr_port[1]}, wsjtx_id: {self.wsjtx_id}, message: {self.message}"

class SettingPacket(GenericWSJTXPacket):
    TYPE_VALUE = 33

    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)
        ps = PacketReader(pkt)
        self.wsjtx_id = ps.QString()
        self.settings_json = ps.QString() 

    def __repr__(self):
        return f"SettingPacket: settings: {self.settings_json}"

    @classmethod
    def Builder(cls, to_wsjtx_id='WSJT-X', settings_dict=None):
        pkt = PacketWriter()
        pkt.write_QInt32(SettingPacket.TYPE_VALUE)
        pkt.write_QString(to_wsjtx_id)
        if settings_dict is None:
            settings_dict = {}
        settings_str = json.dumps(settings_dict)
        pkt.write_QString(settings_str)
        return pkt.packet

class WSJTXPacketClassFactory(GenericWSJTXPacket):
    PACKET_TYPE_TO_OBJ_MAP = {
        StatusPacket.TYPE_VALUE: StatusPacket,
        DecodePacket.TYPE_VALUE: DecodePacket,
        SettingPacket.TYPE_VALUE: SettingPacket
    }
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        self.addr_port = addr_port
        self.magic = magic
        self.schema = schema
        self.pkt_type = pkt_type
        self.pkt_id = id
        self.pkt = pkt

    def __repr__(self):
        return 'WSJTXPacketFactory: from {}:{}\n{}'.format(self.addr_port[0], self.addr_port[1], PacketUtil.hexdump(self.pkt))

    @classmethod
    def from_udp_packet(cls, addr_port, udp_packet):
        if len(udp_packet) < GenericWSJTXPacket.MINIMUM_NETWORK_MESSAGE_SIZE:
            return None  # Pour simplifier la simulation
        if len(udp_packet) > GenericWSJTXPacket.MAXIMUM_NETWORK_MESSAGE_SIZE:
            return None
        (magic, schema, pkt_type, id_len) = struct.unpack('>LLLL', udp_packet[0:16])
        if magic != GenericWSJTXPacket.MAGIC_NUMBER:
            return None
        if schema < GenericWSJTXPacket.MINIMUM_SCHEMA_SUPPORTED or schema > GenericWSJTXPacket.MAXIMUM_SCHEMA_SUPPORTED:
            return None
        klass = WSJTXPacketClassFactory.PACKET_TYPE_TO_OBJ_MAP.get(pkt_type)
        if klass is None:
            return None
        return klass(addr_port, magic, schema, pkt_type, id_len, udp_packet)

def send_status_packet(
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
        special_op_mode=False,
        ip_address="127.0.0.1",
        udp_port=2237,
        is_slave=False
    ):
    UDP_IP = ip_address
    UDP_PORT = udp_port        

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

    #if is_slave:
    #    header = f"{UDP_IP}:{UDP_PORT}|".encode('utf-8')
    #    packet_data = header + packet_data

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(packet_data, (UDP_IP, UDP_PORT))
        print(f"✅ Status Packet sent to {UDP_IP}:{UDP_PORT}")

def send_decode_packet(
        wsjtx_id="WSJT-X",
        snr=0,
        delta_t=0.0,
        delta_f=0,
        mode="FT8",
        message="CQ DX",
        ip_address="127.0.0.1",
        udp_port=2237,
        is_slave=False
    ):
    UDP_IP = ip_address
    UDP_PORT = udp_port        
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

    print("Hex value for Decode Packet:")
    print(PacketUtil.hexdump(packet_data))

    if is_slave:
        header = f"{UDP_IP}:{UDP_PORT}|".encode('utf-8')
        packet_data = header + packet_data

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(packet_data, (UDP_IP, UDP_PORT))
        print(f"Packet sent to {UDP_IP}:{UDP_PORT}")

def request_master_settings(
        wsjtx_id="WSJT-X",
        ip_address="127.0.0.1",
        udp_port=2237,
    ):
    UDP_IP = ip_address
    UDP_PORT = udp_port
    packet = RequestSettingPacket.Builder(to_wsjtx_id=wsjtx_id)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(packet, (UDP_IP, UDP_PORT))
        print(f"Settings Packet sent to {UDP_IP}:{UDP_PORT}")

def send_settings_packet(
        wsjtx_id="WSJT-X",
        settings_dict=None,
        ip_address="127.0.0.1",
        udp_port=2237,
        primary_addr="127.0.0.1",
        primary_port=2237
    ):
    UDP_IP = ip_address
    UDP_PORT = udp_port
    # Construire le paquet SettingPacket
    packet = SettingPacket.Builder(to_wsjtx_id=wsjtx_id, settings_dict=settings_dict)
    # Construire un header "primary_addr:primary_port|"
    header = f"{primary_addr}:{primary_port}|".encode('utf-8')
    packet_with_header = header + packet
    print("Hex value for Settings Packet with header:")
    print(PacketUtil.hexdump(packet_with_header))
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(packet_with_header, (UDP_IP, UDP_PORT))
        print(f"Settings Packet sent to {UDP_IP}:{UDP_PORT}")

def simulate(ip_address="127.0.0.1", udp_port=2237, is_slave=True):  

    print("Running as slave" if is_slave else "Running as master")

    messages_series = [[
        {"message": "BG4TDG 9A2AA +12", "snr": "+12", "delta_t": "+0.3", "delta_f": "450"},
        {"message": "F5BZB SV5DKL -13", "snr": "+12", "delta_t": "+0.3", "delta_f": "450"},
        {"message": "F2DX F4BKB -13", "snr": "+12", "delta_t": "+0.3", "delta_f": "450"},
        {"message": "CQ 3D2AG RJ11", "snr": "+13", "delta_t": "+0.2", "delta_f": "1400"},
    ],
    [
        {"message": "CQ VK9DX AA12", "snr": "+12", "delta_t": "+0.3", "delta_f": "450"},
        {"message": "F5UKW 3D2AG -12", "snr": "+13", "delta_t": "+0.2", "delta_f": "1400"},
    ],
    [
        {"message": "CQ VK9DX AA12", "snr": "+12", "delta_t": "+0.3", "delta_f": "450"},
        {"message": "F5UKW 3D2AG RR73", "snr": "+13", "delta_t": "+0.2", "delta_f": "1400"},
    ],
    [
        {"message": "F2DX F4BKB -13", "snr": "+12", "delta_t": "+0.3", "delta_f": "450"},
        {"message": "CQ 3D2AG RJ1112", "snr": "+13", "delta_t": "+0.2", "delta_f": "1400"},
    ]]
    
    send_status_packet(ip_address=ip_address, udp_port=udp_port, is_slave=is_slave)
    if is_slave:
        simulate_settings(ip_address=ip_address, udp_port=udp_port)
    time.sleep(15)

    for i, message_series in enumerate(messages_series):
        print(f"📡 Sending series {i + 1}...\n")
        for msg in message_series:
            print(f"📨 Sending: {msg['message']} (SNR: {msg['snr']}, ΔT: {msg['delta_t']}, ΔF: {msg['delta_f']})")
            send_decode_packet(
                message=msg["message"],
                snr=int(msg["snr"]),              
                delta_t=float(msg["delta_t"]),    
                delta_f=int(msg["delta_f"]),      
                ip_address=ip_address,
                udp_port=udp_port,
                is_slave=is_slave
            )
        print("⏳ Waiting 15 seconds before next series...\n")
        time.sleep(15)

def simulate_settings(ip_address="127.0.0.1", udp_port=2237):
    settings = {
        "band": "6m",
        "wanted_callsigns": ["VK9DX,SV1GA/A"],
        "excluded_callsigns": ["9M2DA"],
        "monitored_callsigns": ["F4BKV"],
        "monitored_cq_zones": ["31,32"],
        "excluded_cq_zones": ["14"]
    }
    send_settings_packet(wsjtx_id="WSJT-X Simulator", settings_dict=settings, ip_address=ip_address, udp_port=udp_port)

def request_settings(ip_address="127.0.0.1", udp_port=2237):
    request_master_settings(wsjtx_id="WSJT-X Simulator", ip_address=ip_address, udp_port=udp_port)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Simulate sending WSJT-X packets via UDP.")
    parser.add_argument('--message', type=str, help='Message to send (for decode packet)')
    parser.add_argument('--wsjtx_id', type=str, default="WSJT-X", help='ID for WSJT-X (default: WSJT-X)')
    parser.add_argument('--snr', type=int, default=0, help='Signal-to-noise ratio (SNR)')
    parser.add_argument('--delta_t', type=float, default=0.1, help='Delta T')
    parser.add_argument('--delta_f', type=int, default=350, help='Delta F')
    parser.add_argument('--mode', type=str, default="FT8", help='Transmission mode (default: FT8)')
    parser.add_argument('--ip_address', type=str, default="127.0.0.1", help='IP address for UDP server (default: 127.0.0.1)')
    parser.add_argument('--is_slave', action='store_true', help='Set is server behavior jas to be a slave')
    parser.add_argument('--udp_port', type=int, default=2237, help='UDP server port (default: 2237)')
    parser.add_argument('--simulate', action='store_true', help='Run simulation with decode/status packets')
    parser.add_argument('--request_settings', action='store_true', help='Run simulation and asking for settings')
    parser.add_argument('--simulate_settings', action='store_true', help='Simulate sending a Settings packet')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    if args.simulate_settings:
        simulate_settings(ip_address=args.ip_address, udp_port=args.udp_port)
    elif args.request_settings:
        request_settings(ip_address=args.ip_address, udp_port=args.udp_port)
    elif args.simulate:
        simulate(ip_address=args.ip_address, udp_port=args.udp_port, is_slave=args.is_slave)
    else:
        if not args.message:
            print("Error: You must provide a message with --message unless using --simulate or --simulate_settings")
            exit(1)
        send_decode_packet(
            wsjtx_id=args.wsjtx_id,
            snr=args.snr,
            delta_t=args.delta_t,
            delta_f=args.delta_f,
            mode=args.mode,
            message=args.message,
            ip_address=args.ip_address,
            udp_port=args.udp_port
        )