# utils.py

import socket
import datetime
import re
import os
import sys
import fnmatch

from PyQt5.QtWidgets import QTextEdit, QLineEdit
from PyQt5.QtCore import QCoreApplication, QStandardPaths

QCoreApplication.setApplicationName("Wait and Pounce")

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

def get_app_data_dir():
    if getattr(sys, 'frozen', False):
        app_data_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    else:
        app_data_dir = os.path.abspath(".")

    if not os.path.exists(app_data_dir):
        os.makedirs(app_data_dir)

    return app_data_dir

def get_log_filename():
    today = datetime.datetime.now().strftime("%y%m%d")

    return os.path.join(get_app_data_dir(), f"{today}_pounce.log")

def parse_wsjtx_message(
        message,
        wanted_callsigns,
        excluded_callsigns = set(),
        monitored_callsigns = set()
    ):
    directed  = None
    callsign  = None
    grid      = None
    msg       = None
    cqing     = False
    wanted    = False
    monitored = False

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
        is_monitored = matches_any(monitored_callsigns, callsign)

        wanted    = is_wanted and not is_excluded
        monitored = is_monitored and not is_excluded

    return {
        'directed'  : directed,
        'callsign'  : callsign,
        'grid'      : grid,
        'msg'       : msg,
        'cqing'     : cqing,
        'wanted'    : wanted,
        'monitored' : monitored
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