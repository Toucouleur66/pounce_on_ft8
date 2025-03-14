import socket
import struct
import pywsjtx
import ipaddress
import select
import traceback

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
                print(f"Starting with non-multicast: {self.ip_address}")
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                self.sock.bind((self.ip_address, int(self.udp_port)))
            else:
                self.multicast_setup(self.ip_address, self.udp_port)

            if self.timeout is not None:
                self.sock.settimeout(self.timeout)
        except socket.error as e:
            print(f"Error creating UDP socket: {e}")
            self.sock = None

    def close_socket(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def multicast_setup(self, group, port):
        print(f"Starting with multicast setup")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', port))
        mreq = struct.pack("4sl", socket.inet_aton(group), socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    def rx_packet(self):
        try:
            readable, _, _ = select.select([self.sock], [], [], 1.0)  # Timeout set to 1 second
            if readable:
                pkt, addr_port = self.sock.recvfrom(self.MAX_BUFFER_SIZE)
                return pkt, addr_port
        except socket.timeout:
            print("rx_packet: socket.timeout")
        except OSError as e:
            if e.errno == 10038:
                print("Invalid socket so try to create_socket")
                self.create_socket()
            else:
                print(f"Exception in rx_packet: {e}\n{traceback.format_exc()}")
        return None, None

    def send_packet(self, addr_port, pkt):
        try:
            if self.sock:
                self.sock.sendto(pkt, addr_port)
        except OSError as e:
            print(f"Exception in send_packet: {e}\n{traceback.format_exc()}")