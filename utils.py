# utils.py

import socket
import datetime

from PyQt5.QtWidgets import QTextEdit, QLineEdit
from PyQt5.QtGui import QTextCursor

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

def force_uppercase(widget):
    try:
        if isinstance(widget, QTextEdit):
            cursor = widget.textCursor()
            current_pos = cursor.position()
            
            current_text = widget.toPlainText()
            uppercase_text = current_text.upper()
            if current_text != uppercase_text:
                widget.blockSignals(True)
                widget.setPlainText(uppercase_text)
                widget.blockSignals(False)
                
                cursor = widget.textCursor()
                cursor.setPosition(current_pos)
                widget.setTextCursor(cursor)
        elif isinstance(widget, QLineEdit):
            current_text = widget.text()
            uppercase_text = current_text.upper()
            if current_text != uppercase_text:
                widget.blockSignals(True)
                widget.setText(uppercase_text)
                widget.blockSignals(False)
                                
                widget.setCursorPosition(len(uppercase_text))
    except Exception as e:        
        pass