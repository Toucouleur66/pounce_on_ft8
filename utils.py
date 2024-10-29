# utils.py

import socket
import datetime

def get_local_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        local_ip_address = s.getsockname()[0]
    except Exception:
        local_ip_address = '127.0.0.1'
    finally:
        s.close()
    return local_ip_address

def get_log_filename():
    today = datetime.datetime.now().strftime("%y%m%d")
    return f"{today}_pounce.log"

def is_in_wanted(message, wanted_callsigns):
    for callsign in wanted_callsigns:
        if callsign in message:
            return True
    return False 
     