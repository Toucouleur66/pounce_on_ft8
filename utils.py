# utils.py

import socket
import datetime
import re
import fnmatch

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

def parse_wsjtx_message(
        message,
        wanted_callsigns,
        excluded_callsigns = set(),
        important_callsigns = set()
    ):
    directed  = None
    callsign  = None
    grid      = None
    msg       = None
    cqing     = False
    wanted    = False
    important = False

    match = re.match(r"^CQ\s+(?:(\w{2,3})\s+)?([A-Z0-9/]+)(?:\s+([A-Z]{2}\d{2}))?", message)
    if match:
        cqing    = True
        directed = match.group(1)
        callsign = match.group(2)
        grid     = match.group(3)

    else:
        match = re.match(r"^([A-Z0-9/]+)\s+([A-Z0-9/]+)\s+([A-Z0-9+-]+)", message)
        if match:
            directed = match.group(1)
            callsign = match.group(2)
            msg      = match.group(3)

    if callsign:
        def matches_any(patterns, callsign):
            return any(fnmatch.fnmatch(callsign, pattern) for pattern in patterns)

        is_wanted    = matches_any(wanted_callsigns, callsign)
        is_excluded  = matches_any(excluded_callsigns, callsign)
        is_important = matches_any(important_callsigns, callsign)

        wanted    = is_wanted and not is_excluded
        important = is_important and not is_excluded

    return {
        'directed'  : directed,
        'callsign'  : callsign,
        'grid'      : grid,
        'msg'       : msg,
        'cqing'     : cqing,
        'wanted'    : wanted,
        'important' : important
    }

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