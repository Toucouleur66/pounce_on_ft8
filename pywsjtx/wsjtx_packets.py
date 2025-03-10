# wsjtx_packets.py

import struct
import datetime
import math
import json

class PacketUtil:
    @classmethod
    # this hexdump brought to you by Stack Overflow
    def hexdump(cls, src, length=16):
        FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or '.' for x in range(256)])
        lines = []
        for c in range(0, len(src), length):
            chars = src[c:c + length]
            hex = ' '.join(["%02x" % x for x in chars])
            printable = ''.join(["%s" % ((x <= 127 and FILTER[x]) or '.') for x in chars])
            lines.append("%04x  %-*s  %s\n" % (c, length * 3, hex, printable))
        return ''.join(lines)

    # timezone tomfoolery
    @classmethod
    def midnight_utc(cls):
        utcnow = datetime.datetime.utcnow()
        utcmidnight = datetime.datetime(utcnow.year, utcnow.month, utcnow.day, 0, 0)
        return utcmidnight

    #converts a Julian day to a calendar Date
    @classmethod
    def JDToDateMeeus(cls,jDNum):
        F=0.0

        jDNum += 0.5
        Z = jDNum  #Z == int so I = int part
        F = jDNum - Z  #F =  fractional part
        if(Z < 2299161):  #Julian?
            A = Z
        else:  #Gregorian
            alpha = math.floor((Z - 1867216.25) / 36524.25)
            A = Z + 1 + alpha - math.floor(alpha / 4.0)
        B = A + 1524
        C = math.floor((B - 122.1) /365.25)
        D = math.floor(365.25 * C)
        E = math.floor((B - D) /30.6001)
        day = int(B - D - math.floor(30.6001 * E) + F)
        if( E < 14):
            month = E - 1
        else:
            month = E - 13
        if(month > 2):
            year = C - 4716
        else:
            year = C - 4715
        return (year,month,day)
    
    @classmethod
    def datetime_to_julian_day(cls, dt):
        a = (14 - dt.month) // 12
        y = dt.year + 4800 - a
        m = dt.month + 12 * a - 3
        jd = dt.day + ((153 * m + 2) // 5) + 365 * y + y // 4 - y // 100 + y // 400 - 32045
        return jd    


class PacketWriter(object):
    def __init__(self ):
        self.ptr_pos = 0
        self.packet = bytearray()
        # self.max_ptr_pos
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
        self.packet.extend(struct.pack('>l',val))

    def write_QUInt32(self, val):
        self.packet.extend(struct.pack('>L', val))

    def write_QInt64(self, val):
        self.packet.extend(struct.pack('>q',val))

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
        # see Qt serialization for QColor format; unfortunately thes serialization is nothing like what's in that.
        #  It's not correct. Look instead at the wsjt-x configuration settings, where
        #  color values have been serialized.
        #
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

    def bytes_left(self):
        return self.max_ptr_pos - self.ptr_pos + 1        

    def at_eof(self):
        return self.ptr_pos > self.max_ptr_pos

    def skip_header(self):
        if self.max_ptr_pos < 8:
            raise Exception('Not enough data to skip header')
        self.ptr_pos = 8

    def check_ptr_bound(self,field_type, length):
        if self.ptr_pos + length > self.max_ptr_pos+1:
            raise Exception('Not enough data to extract {}'.format(field_type))

    ## grab data from the packet, incrementing the ptr_pos on the basis of the data we've gleaned
    def QInt32(self):
        self.check_ptr_bound('QInt32', 4)   # sure we could inspect that, but that is slow.
        (the_int32,) = struct.unpack('>l',self.packet[self.ptr_pos:self.ptr_pos+4])
        self.ptr_pos += 4
        return the_int32


    def QInt8(self):
        self.check_ptr_bound('QInt8', 1)
        (the_int8,) = struct.unpack('>b', self.packet[self.ptr_pos:self.ptr_pos+1])
        self.ptr_pos += 1
        return the_int8

    def QInt64(self):
        self.check_ptr_bound('QInt64', 8)
        (the_int64,) = struct.unpack('>q', self.packet[self.ptr_pos:self.ptr_pos+8])
        self.ptr_pos += 8
        return the_int64

    def QFloat(self):
        self.check_ptr_bound('QFloat', 8)
        (the_double,) = struct.unpack('>d', self.packet[self.ptr_pos:self.ptr_pos+8])
        self.ptr_pos += 8
        return the_double

    def QString(self):
        str_len = self.QInt32()
        if str_len == -1:
            return None
        self.check_ptr_bound('QString[{}]'.format(str_len),str_len)
        (str,) = struct.unpack('{}s'.format(str_len), self.packet[self.ptr_pos:self.ptr_pos + str_len])
        self.ptr_pos += str_len
        return str.decode('utf-8')

    def QDateTime(self):
        jdnum = self.QInt64()
        millis_since_midnight = self.QInt32()
        spec = self.QInt8()
        offset = 0
        if spec == 2:
            offset = self.QInt32()
        date = PacketUtil.JDToDateMeeus(jdnum)
        time = PacketUtil.midnight_utc() + datetime.timedelta(milliseconds=millis_since_midnight)
        return QDateTime(date,time,spec,offset)

class QDateTime(object):
    def __init__(self,date,time,spec,offset):
        self.date=date
        self.time=time
        self.spec=spec
        self.offset=offset

    def __repr__(self):
        return "date {}\n\ttime {}\n\tspec {}\n\toffset {}".format(self.date,self.time,self.spec,self.offset)

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
        self.id = id
        self.pkt = pkt

class InvalidPacket(GenericWSJTXPacket):
    TYPE_VALUE = -1
    def __init__(self, addr_port, packet,  message):
        self.packet = packet
        self.message = message
        self.addr_port = addr_port

    def __repr__(self):
        return 'Invalid Packet: %s from %s:%s\n%s' % (self.message, self.addr_port[0], self.addr_port[1], PacketUtil.hexdump(self.packet))

class HeartBeatPacket(GenericWSJTXPacket):
    TYPE_VALUE = 0

    def __init__(self, addr_port: object, magic: object, schema: object, pkt_type: object, id: object, pkt: object) -> object:
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)
        ps = PacketReader(pkt)
        the_type = ps.QInt32()
        self.wsjtx_id = ps.QString()
        self.max_schema = ps.QInt32()
        self.version = ps.QInt8()
        self.revision = ps.QInt8()

    def __repr__(self):
        return 'HeartBeatPacket: from {}:{}\n\twsjtx id:{}\tmax_schema:{}\tschema:{}\tversion:{}\trevision:{}' .format(self.addr_port[0], self.addr_port[1], self.wsjtx_id, self.max_schema, self.schema, self.version, self.revision)
    @classmethod
    # make a heartbeat packet (a byte array) we can send to a 'client'. This should be it's own class.
    def Builder(cls,wsjtx_id='pywsjtx', max_schema=2, version=1, revision=1):
        # build the packet to send
        pkt = PacketWriter()
        pkt.write_QInt32(HeartBeatPacket.TYPE_VALUE)
        pkt.write_QString(wsjtx_id)
        pkt.write_QInt32(max_schema)
        pkt.write_QInt32(version)
        pkt.write_QInt32(revision)
        return pkt.packet

class StatusPacket(GenericWSJTXPacket):
    TYPE_VALUE = 1
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)
        ps = PacketReader(pkt)
        
        the_type = ps.QInt32()
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

        # new in wsjtx-2.0.0
        self.special_op_mode = ps.QInt8()

    def __repr__(self):
        str =  'StatusPacket: from {}:{}\n\twsjtx id:{}\t\tde_call:{}\tde_grid:{}\tfrequency:{}\n'.format(
            self.addr_port[0],
            self.addr_port[1],
            self.wsjtx_id,
            self.de_call,
            self.de_grid,
            self.dial_frequency / 1_000            
        )

        str += "\trx_df:{}\ttx_df:{}\tdx_call:{}\tdx_grid:{}\treport:{}\n".format(
            self.rx_df,
            self.tx_df,
            self.dx_call,
            self.dx_grid,
            self.report
        )
        str += "\ttransmitting:{}\tdecoding:{}\ttx_enabled:{}\ttx_watchdog:{}\tmode:{}\n\tsub_mode:{}\tfast_mode:{}\tspecial_op_mode:{}".format(
            self.transmitting,
            self.decoding,
            self.tx_enabled,
            self.tx_watchdog,
            self.mode,
            self.sub_mode,
            self.fast_mode,
            self.special_op_mode
        )
        return str

class DecodePacket(GenericWSJTXPacket):
    TYPE_VALUE = 2
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)
        
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
        str = 'DecodePacket: from {}:{}\n\twsjtx id:{}\tmessage:{}\n'.format(
            self.addr_port[0],
            self.addr_port[1],
            self.wsjtx_id,
            self.message
        )
        str += "\tdelta_f:{}\tnew:{}\ttime:{}\tsnr:{}\tdelta_f:{}".format(
            self.delta_f,
            self.new_decode,
            self.time,
            self.snr,
            self.delta_f
        )
        return str

class ClearPacket(GenericWSJTXPacket):
    TYPE_VALUE = 3
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)

class ReplyPacket(GenericWSJTXPacket):
    TYPE_VALUE = 4
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)

    @classmethod
    def Builder(cls, decode_packet):
        # build the packet to send
        pkt = PacketWriter()
        pkt.write_QInt32(ReplyPacket.TYPE_VALUE)
        pkt.write_QString(decode_packet.wsjtx_id)
        pkt.write_QInt32(decode_packet.millis_since_midnight)
        pkt.write_QInt32(decode_packet.snr)
        pkt.write_QFloat(decode_packet.delta_t)
        pkt.write_QInt32(decode_packet.delta_f)
        pkt.write_QString(decode_packet.mode)
        pkt.write_QString(decode_packet.message)
        pkt.write_QInt8(decode_packet.low_confidence)
        pkt.write_QInt8(0)
        return pkt.packet

class QSOLoggedPacket(GenericWSJTXPacket):
    TYPE_VALUE = 5
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)
        ps = PacketReader(pkt)
        the_type = ps.QInt32()
        self.wsjtx_id = ps.QString()
        self.datetime_off = ps.QDateTime()
        self.call = ps.QString()
        self.grid = ps.QString()
        self.frequency = ps.QInt64()
        self.mode = ps.QString()
        self.report_sent = ps.QString()
        self.report_recv = ps.QString()
        self.tx_power = ps.QString()
        self.comments = ps.QString()
        self.name = ps.QString()
        self.datetime_on = ps.QDateTime()
        self.op_call = ps.QString()
        self.my_call = ps.QString()
        self.my_grid = ps.QString()
        
        if self.schema >= 3 and ps.bytes_left() >= 4:
            try:
                self.exchange_sent = ps.QString()
                self.exchange_recv = ps.QString()
            except Exception as e:
                self.exchange_sent = None
                self.exchange_recv = None
                print(f"Warning: can't read exchange report: {e}")
        else:
            self.exchange_sent = None
            self.exchange_recv = None

    def __repr__(self):
        str = 'QSOLoggedPacket: call {} @ {}\n\tdatetime:{}\tfreq:{}\n'.format(self.call,
                                                                             self.grid,
                                                                             self.datetime_off,
                                                                             self.frequency)
        str += "\tmode:{}\tsent:{}\trecv:{}".format(self.mode,
                                                    self.report_sent,
                                                    self.report_recv)
        return str

class ClosePacket(GenericWSJTXPacket):
    TYPE_VALUE = 6
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)

class ReplayPacket(GenericWSJTXPacket):
    TYPE_VALUE = 7
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)

class HaltTxPacket(GenericWSJTXPacket):
    TYPE_VALUE = 8
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)

    @classmethod
    def Builder(cls,to_wsjtx_id='WSJT-X', auto_tx_only=False):
        # build the packet to send
        pkt = PacketWriter()
        print('To_wsjtx_id ',to_wsjtx_id,' auto_tx_only ',auto_tx_only)
        pkt.write_QInt32(FreeTextPacket.TYPE_VALUE)
        pkt.write_QString(to_wsjtx_id)
        pkt.write_QInt8(auto_tx_only)
        return pkt.packet    

class FreeTextPacket(GenericWSJTXPacket):
    TYPE_VALUE = 9
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)

    @classmethod
    def Builder(cls,to_wsjtx_id='WSJT-X', text="", send=False):
        pkt = PacketWriter()
        print('To_wsjtx_id ',to_wsjtx_id,' text ',text, 'send ',send)
        pkt.write_QInt32(FreeTextPacket.TYPE_VALUE)
        pkt.write_QString(to_wsjtx_id)
        pkt.write_QString(text)
        pkt.write_QInt8(send)
        return pkt.packet

class WSPRDecodePacket(GenericWSJTXPacket):
    TYPE_VALUE = 10
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)

class LocationChangePacket(GenericWSJTXPacket):
    TYPE_VALUE = 11
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)

    @classmethod
    def Builder(cls, to_wsjtx_id='WSJT-X', new_grid=""):
        # build the packet to send
        pkt = PacketWriter()
        pkt.write_QInt32(LocationChangePacket.TYPE_VALUE)
        pkt.write_QString(to_wsjtx_id)
        pkt.write_QString(new_grid)
        return pkt.packet

class LoggedADIFPacket(GenericWSJTXPacket):
    TYPE_VALUE = 12
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)

    @classmethod
    def Builder(cls, to_wsjtx_id='WSJT-X', adif_text=""):
        # build the packet to send
        pkt = PacketWriter()
        pkt.write_QInt32(LoggedADIFPacket.TYPE_VALUE)
        pkt.write_QString(to_wsjtx_id)
        pkt.write_QString(adif_text)
        return pkt.packet
    
class SetTxDeltaFreqPacket(GenericWSJTXPacket):
    TYPE_VALUE = 50
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)

    @classmethod
    def Builder(cls,to_wsjtx_id='WSJT-X', delta_f=0):
        # build the packet to send
        pkt = PacketWriter()
        pkt.write_QInt32(SetTxDeltaFreqPacket.TYPE_VALUE)
        pkt.write_QString(to_wsjtx_id)
        pkt.write_QInt32(delta_f)
        return pkt.packet    

class HighlightCallsignPacket(GenericWSJTXPacket):
    TYPE_VALUE = 13
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)

    @classmethod
    def Builder(cls, to_wsjtx_id='WSJT-X', callsign="K1JT", background_color=None, foreground_color=None, highlight_last_only=True ):
        # build the packet to send
        pkt = PacketWriter()
        pkt.write_QInt32(HighlightCallsignPacket.TYPE_VALUE)
        pkt.write_QString(to_wsjtx_id)
        pkt.write_QString(callsign)
        pkt.write_QColor(background_color)
        pkt.write_QColor(foreground_color)
        pkt.write_QBool(highlight_last_only)
        return pkt.packet
    
class ConfigurePacket(GenericWSJTXPacket):
    TYPE_VALUE = 15
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)

    @classmethod
    def Builder(
        cls,
        to_wsjtx_id='WSJT-X',
        mode="",
        frequency_tolerance=0,
        sub_mode="",
        fast_mode="",
        tr_period=0,
        rx_df=600,
        dx_call="",
        dx_grid="",
        generate_messages=False
        ):
        # build the packet to send
        pkt = PacketWriter()
        pkt.write_QInt32(ConfigurePacket.TYPE_VALUE)
        pkt.write_QString(to_wsjtx_id)
        pkt.write_QString(mode)
        pkt.write_QInt32(frequency_tolerance)
        pkt.write_QString(sub_mode)
        pkt.write_QBool(fast_mode)
        pkt.write_QInt32(tr_period)
        pkt.write_QInt32(rx_df)
        pkt.write_QString(dx_call)
        pkt.write_QString(dx_grid)
        pkt.write_QBool(generate_messages)
        return pkt.packet

class SettingPacket(GenericWSJTXPacket):
    TYPE_VALUE = 33

    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)
        ps = PacketReader(pkt)
        the_type = ps.QInt32()
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

class RequestSettingPacket(GenericWSJTXPacket):
    TYPE_VALUE = 34
    
    def __init__(self, addr_port: object, magic: object, schema: object, pkt_type: object, id: object, pkt: object) -> object:
        GenericWSJTXPacket.__init__(self, addr_port, magic, schema, pkt_type, id, pkt)
        ps = PacketReader(pkt)
        the_type = ps.QInt32()
        self.wsjtx_id = ps.QString()
        self.max_schema = ps.QInt32()
        self.version = ps.QInt8()
        self.revision = ps.QInt8()

    def __repr__(self):
        return 'RequestSettingPacket: from {}:{}\n\twsjtx id:{}\tmax_schema:{}' .format(self.addr_port[0], self.addr_port[1], self.wsjtx_id, self.max_schema)    

    @classmethod
    def Builder(cls, to_wsjtx_id='WSJT-X'):
        pkt = PacketWriter()
        pkt.write_QInt32(RequestSettingPacket.TYPE_VALUE)
        pkt.write_QString(to_wsjtx_id)
        return pkt.packet

class WSJTXPacketClassFactory(GenericWSJTXPacket):
    PACKET_TYPE_TO_OBJ_MAP = {
        HeartBeatPacket.TYPE_VALUE: HeartBeatPacket,
        StatusPacket.TYPE_VALUE:    StatusPacket,
        DecodePacket.TYPE_VALUE:    DecodePacket,
        ClearPacket.TYPE_VALUE:     ClearPacket,
        ReplyPacket.TYPE_VALUE:    ReplyPacket,
        QSOLoggedPacket.TYPE_VALUE: QSOLoggedPacket,
        ClosePacket.TYPE_VALUE:     ClosePacket,
        ReplayPacket.TYPE_VALUE:    ReplayPacket,
        HaltTxPacket.TYPE_VALUE:    HaltTxPacket,
        FreeTextPacket.TYPE_VALUE:  FreeTextPacket,
        WSPRDecodePacket.TYPE_VALUE: WSPRDecodePacket,
        LoggedADIFPacket.TYPE_VALUE: LoggedADIFPacket,  
        SetTxDeltaFreqPacket.TYPE_VALUE: SetTxDeltaFreqPacket,
        HighlightCallsignPacket.TYPE_VALUE: HighlightCallsignPacket,
        ConfigurePacket.TYPE_VALUE: ConfigurePacket,
        SettingPacket.TYPE_VALUE: SettingPacket,
        RequestSettingPacket.TYPE_VALUE: RequestSettingPacket 
    }
    def __init__(self, addr_port, magic, schema, pkt_type, id, pkt):
        self.addr_port = addr_port
        self.magic = magic
        self.schema = schema
        self.pkt_type = pkt_type
        self.pkt_id = id
        self.pkt = pkt

    def __repr__(self):
        return 'WSJTXPacketFactory: from {}:{}\n{}' .format(self.addr_port[0], self.addr_port[1], PacketUtil.hexdump(self.pkt))

    # Factory-like method
    @classmethod
    def from_udp_packet(cls, addr_port, udp_packet):
        if len(udp_packet) < GenericWSJTXPacket.MINIMUM_NETWORK_MESSAGE_SIZE:
            return InvalidPacket( addr_port, udp_packet, "Packet too small")

        if len(udp_packet) > GenericWSJTXPacket.MAXIMUM_NETWORK_MESSAGE_SIZE:
            return InvalidPacket( addr_port, udp_packet, "Packet too large")

        (magic, schema, pkt_type, id_len) = struct.unpack('>LLLL', udp_packet[0:16])

        if magic != GenericWSJTXPacket.MAGIC_NUMBER:
            return InvalidPacket( addr_port, udp_packet, "Invalid Magic Value")

        if schema < GenericWSJTXPacket.MINIMUM_SCHEMA_SUPPORTED or schema > GenericWSJTXPacket.MAXIMUM_SCHEMA_SUPPORTED:
            return InvalidPacket( addr_port, udp_packet, "Unsupported schema value {}".format(schema))
        klass = WSJTXPacketClassFactory.PACKET_TYPE_TO_OBJ_MAP.get(pkt_type)

        if klass is None:
            return InvalidPacket( addr_port, udp_packet, "Unknown packet type {}".format(pkt_type))

        return klass(addr_port, magic, schema, pkt_type, id, udp_packet)