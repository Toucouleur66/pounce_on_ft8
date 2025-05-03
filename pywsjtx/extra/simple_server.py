import socket
import struct
import pywsjtx
import ipaddress
import select
import traceback

from logger import get_logger

log = get_logger(__name__)

class SimpleServer(object):
    MAX_BUFFER_SIZE = pywsjtx.GenericWSJTXPacket.MAXIMUM_NETWORK_MESSAGE_SIZE
    DEFAULT_UDP_PORT = 2237

    def __init__(self, ip_address='127.0.0.1', udp_port=DEFAULT_UDP_PORT, **kwargs):
        self.timeout = kwargs.get("timeout", None)

        self.ip_address = ip_address
        self.udp_port = udp_port

        self.sock = None
        self.create_socket()

    def create_socket(self):    
        try:
            self.close_socket() 

            the_address = ipaddress.ip_address(self.ip_address)
            if not the_address.is_multicast:
                log.info(f"Starting with non-multicast: {self.ip_address}:{self.udp_port}")
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                self.sock.bind((self.ip_address, int(self.udp_port)))
            else:
                self.multicast_setup(self.ip_address, self.udp_port)

            if self.timeout is not None:
                self.sock.settimeout(self.timeout)
        except socket.error as e:
            log.error(f"Error creating UDP socket: {e}")
            self.sock = None

    def close_socket(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def multicast_setup(self, group, port, interface_ip="0.0.0.0"):
        try:
            if not ipaddress.ip_address(group).is_multicast:
                raise ValueError(f"{group} is not a valid multicast address")
            log.debug(f"Starting with multicast setup on group {group}, port {port}, interface {interface_ip}")
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('', port))
            mreq = struct.pack("4s4s", socket.inet_aton(group), socket.inet_aton(interface_ip))
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2**16) 
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)  
        except (socket.error, ValueError) as e:
            log.error(f"Error during multicast setup: {e}")
            self.sock = None

    def rx_packet(self):
        try:
            readable, _, _ = select.select([self.sock], [], [], 1.0)  # Timeout set to 1 second
            if readable:
                pkt, addr_port = self.sock.recvfrom(self.MAX_BUFFER_SIZE)
                return pkt, addr_port
        except socket.timeout:
            log.warning("rx_packet: socket.timeout")
        except OSError as e:
            if e.errno == 10038:
                log.warning("Invalid socket so try to create_socket")
                self.create_socket()
            else:
                log.warning(f"Exception in rx_packet: {e}\n{traceback.format_exc()}")
        return None, None

    def send_packet(self, addr_port, pkt):
        try:
            if self.sock:
                self.sock.sendto(pkt, addr_port)
        except OSError as e:
            log.error(f"Exception in send_packet: {e}\n{traceback.format_exc()}")