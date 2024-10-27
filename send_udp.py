import struct
import datetime
import math
import socket
import argparse

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
    def datetime_to_julian_day(cls, dt):
        a = (14 - dt.month) // 12
        y = dt.year + 4800 - a
        m = dt.month + 12 * a - 3
        jd = dt.day + ((153 * m + 2) // 5) + 365 * y + y // 4 - y // 100 + y // 400 - 32045
        return jd    

    @classmethod
    def JDToDateMeeus(cls, jDNum):
        F = 0.0

        jDNum += 0.5
        Z = jDNum
        F = jDNum - Z
        if(Z < 2299161):
            A = Z
        else:
            alpha = math.floor((Z - 1867216.25) / 36524.25)
            A = Z + 1 + alpha - math.floor(alpha / 4.0)
        B = A + 1524
        C = math.floor((B - 122.1) /365.25)
        D = math.floor(365.25 * C)
        E = math.floor((B - D) /30.6001)
        day = int(B - D - math.floor(30.6001 * E) + F)
        if(E < 14):
            month = E - 1
        else:
            month = E - 13
        if(month > 2):
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

    def write_QDateTime(self, datetime_obj, spec=1, offset_seconds=0):
        jd = PacketUtil.datetime_to_julian_day(datetime_obj)
        self.write_QInt64(jd)
        midnight = datetime.datetime.combine(datetime_obj.date(), datetime.time(0, 0, 0))
        millis_since_midnight = int((datetime_obj - midnight).total_seconds() * 1000)
        self.write_QInt32(millis_since_midnight)
        self.write_QInt8(spec)
        if spec == 2:
            self.write_QInt32(offset_seconds)        

    def write_QColor(self, color_val):
        # Supposons que color_val a les attributs spec, alpha, red, green, blue
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
        (str_bytes,) = struct.unpack('{}s'.format(str_len), self.packet[self.ptr_pos:self.ptr_pos + str_len])
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

class DecodePacket(GenericWSJTXPacket):
    TYPE_VALUE = 2

    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        super().__init__(addr_port, magic, schema, pkt_type, id, pkt)
        # Traitement spécifique du paquet
        ps = PacketReader(pkt)
        the_type = ps.QInt32()
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
        str_repr = f'DecodePacket: from {self.addr_port[0]}:{self.addr_port[1]}\n\twsjtx id:{self.wsjtx_id}\tmessage:{self.message}\n'
        str_repr += f'\tdelta_f:{self.delta_f}\tnew:{self.new_decode}\ttime:{self.time}\tsnr:{self.snr}\tdelta_f:{self.delta_f}\tmode:{self.mode}'
        return str_repr

def send_decode_packet(
        wsjtx_id="WSJT-X",
        snr=0,
        delta_t=0.0,
        delta_f=0,
        mode="FT8",
        message="CQ DX",
        ip_address="127.0.0.1"  ,
        udp_port=2237
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

    print("Hex value for Packet:")
    print(PacketUtil.hexdump(packet_data))

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(packet_data, (UDP_IP, UDP_PORT))
        print(f"Packet sent to {UDP_IP}:{UDP_PORT}")

def send_heartbeat_packet(
        wsjtx_id="WSJT-X",
        max_schema=3,
        version=2,
        revision=0,
        ip_address="127.0.0.1",
        udp_port=2237
    ):
    UDP_IP = ip_address
    UDP_PORT = udp_port

    pkt_writer = PacketWriter()

    pkt_writer.write_QInt32(0)
    pkt_writer.write_QString(wsjtx_id)
    pkt_writer.write_QInt32(max_schema)
    pkt_writer.write_QInt32(version)
    pkt_writer.write_QInt32(revision)

    packet_data = pkt_writer.packet

    print("Hex value for HeartBeat Packet:")
    print(PacketUtil.hexdump(packet_data))

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(packet_data, (UDP_IP, UDP_PORT))
        print(f"HeartBeat Packet sent to {UDP_IP}:{UDP_PORT}")      

def send_qso_logged_packet(
        wsjtx_id="WSJT-X",
        datetime_off=None,
        call="CALLSIGN",
        grid="GRID",
        frequency=0,
        mode="FT8",
        report_sent="00",
        report_recv="00",
        tx_power="",
        comments="",
        name="",
        datetime_on=None,
        op_call="",
        my_call="MYCALL",
        my_grid="MYGRID",
        exchange_sent="",
        exchange_recv="",
        ip_address="127.0.0.1",
        udp_port=2237
    ):
    if datetime_off is None:
        datetime_off = datetime.datetime.utcnow()
    if datetime_on is None:
        datetime_on = datetime_off

    UDP_IP = ip_address
    UDP_PORT = udp_port

    pkt_writer = PacketWriter()

    pkt_writer.write_QInt32(5)
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

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(packet_data, (UDP_IP, UDP_PORT))
        print(f"QSOLogged Packet sent to {UDP_IP}:{UDP_PORT}")          

def parse_arguments():
    parser = argparse.ArgumentParser(description="Try to send to UDP server sample Packet.")

    parser.add_argument('--packet_type', type=str, default='decode', choices=['decode', 'heartbeat', 'qso_logged'],
                        help='Type of packet to send')

    parser.add_argument('--wsjtx_id', type=str, default="WSJT-X", help='ID for WSJT-X (default: WSJT-X).')
    parser.add_argument('--mode', type=str, default="FT8", help='Transmission Mode (default: FT8).')
    parser.add_argument('--ip_address', type=str, default="127.0.0.1",
                        help='IP address for UDP server (default: 127.0.0.1).')
    parser.add_argument('--udp_port', type=int, default=2237, help='UDP Server Port (default: 2237).')

    # DecodePacket
    parser.add_argument('--message', type=str, help='Message to handle (required for decode packet).')
    parser.add_argument('--snr', type=int, default=0, help='Signal-to-noise ratio (SNR).')
    parser.add_argument('--delta_t', type=float, default=0.1, help='Delta T.')
    parser.add_argument('--delta_f', type=int, default=350, help='Delta F.')

    # HeartBeatPacket
    parser.add_argument('--max_schema', type=int, default=3, help='Max schema version (default: 3).')
    parser.add_argument('--version', type=int, default=2, help='Version (default: 2).')
    parser.add_argument('--revision', type=int, default=0, help='Revision (default: 0).')

    # QSOLoggedPacket
    parser.add_argument('--call', type=str, default="CALLSIGN", help='Callsign.')
    parser.add_argument('--grid', type=str, default="GRID", help='Grid locator.')
    parser.add_argument('--frequency', type=int, default=0, help='Frequency in Hz.')
    parser.add_argument('--report_sent', type=str, default="-10", help='Report sent.')
    parser.add_argument('--report_recv', type=str, default="-05", help='Report received.')
    parser.add_argument('--tx_power', type=str, default="50", help='TX power.')
    parser.add_argument('--comments', type=str, default="", help='Comments.')
    parser.add_argument('--name', type=str, default="", help='Name.')
    parser.add_argument('--op_call', type=str, default="", help='Operator callsign.')
    parser.add_argument('--my_call', type=str, default="MYCALL", help='My callsign.')
    parser.add_argument('--my_grid', type=str, default="MYGRID", help='My grid locator.')
    parser.add_argument('--exchange_sent', type=str, default="", help='Exchange sent.')
    parser.add_argument('--exchange_recv', type=str, default="", help='Exchange received.')
    parser.add_argument('--datetime_on', type=str, help='Start datetime in ISO format (YYYY-MM-DDTHH:MM:SS).')
    parser.add_argument('--datetime_off', type=str, help='End datetime in ISO format (YYYY-MM-DDTHH:MM:SS).')


    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()

    if args.packet_type == 'decode':
        if not args.message:
            print("Message is required for decode packet.")
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
    elif args.packet_type == 'heartbeat':
        send_heartbeat_packet(
            wsjtx_id=args.wsjtx_id,
            max_schema=args.max_schema,
            version=args.version,
            revision=args.revision,
            ip_address=args.ip_address,
            udp_port=args.udp_port
        )
    elif args.packet_type == 'qso_logged':
        datetime_on = None
        datetime_off = None
        datetime_format = "%Y-%m-%dT%H:%M:%S"

        if args.datetime_on:
            try:
                datetime_on = datetime.datetime.strptime(args.datetime_on, datetime_format)
            except ValueError:
                print(f"Invalid datetime_on format. Expected format is {datetime_format}")
                exit(1)

        if args.datetime_off:
            try:
                datetime_off = datetime.datetime.strptime(args.datetime_off, datetime_format)
            except ValueError:
                print(f"Invalid datetime_off format. Expected format is {datetime_format}")
                exit(1)

        send_qso_logged_packet(
            wsjtx_id=args.wsjtx_id,
            datetime_off=datetime_off,
            call=args.call,
            grid=args.grid,
            frequency=args.frequency,
            mode=args.mode,
            report_sent=args.report_sent,
            report_recv=args.report_recv,
            tx_power=args.tx_power,
            comments=args.comments,
            name=args.name,
            datetime_on=datetime_on,
            op_call=args.op_call,
            my_call=args.my_call,
            my_grid=args.my_grid,
            exchange_sent=args.exchange_sent,
            exchange_recv=args.exchange_recv,
            ip_address=args.ip_address,
            udp_port=args.udp_port
        )
    else:
        print("Unknown packet type.")
