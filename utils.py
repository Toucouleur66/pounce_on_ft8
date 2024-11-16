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

def get_mode_interval(mode):
    if mode == "FT4":
        return 7.5
    else:
        return 15
    
def get_amateur_band(frequency):
    bands = {
        '160m'  : (1_800_000, 2_000_000),
        '80m'   : (3_500_000, 4_000_000),
        '60m'   : (5_351_500, 5_366_500),  
        '40m'   : (7_000_000, 7_300_000),
        '30m'   : (10_100_000, 10_150_000),
        '20m'   : (14_000_000, 14_350_000),
        '17m'   : (18_068_000, 18_168_000),
        '15m'   : (21_000_000, 21_450_000),
        '12m'   : (24_890_000, 24_990_000),
        '10m'   : (28_000_000, 29_700_000),
        '6m'    : (50_000_000, 54_000_000),
        '2m'    : (144_000_000, 148_000_000),
        '70cm'  : (430_000_000, 440_000_000)
    }
    
    for band, (lower_bound, upper_bound) in bands.items():
        if lower_bound <= frequency <= upper_bound:
            return band
    
    return "Invalid"    
    
import re
from PyQt5.QtWidgets import QTextEdit, QLineEdit

def force_uppercase(widget):
    try:
        allowed_pattern = re.compile(r'[A-Z0-9,/*]+')

        if isinstance(widget, QTextEdit):
            cursor = widget.textCursor()
            current_pos = cursor.position()
            
            current_text = widget.toPlainText()
            uppercase_text = ''.join([char for char in current_text.upper() if allowed_pattern.fullmatch(char)])
            if current_text != uppercase_text:
                widget.blockSignals(True)
                widget.setPlainText(uppercase_text)
                widget.blockSignals(False)
                
                cursor = widget.textCursor()
                cursor.setPosition(current_pos)
                widget.setTextCursor(cursor)
        elif isinstance(widget, QLineEdit):
            current_text = widget.text()
            uppercase_text = ''.join([char for char in current_text.upper() if allowed_pattern.fullmatch(char)])
            if current_text != uppercase_text:
                widget.blockSignals(True)
                widget.setText(uppercase_text)
                widget.blockSignals(False)
                
                widget.setCursorPosition(len(uppercase_text))
    except Exception as e:        
        pass

def force_numbers_and_commas(widget):
    try:
        if isinstance(widget, QTextEdit):
            cursor = widget.textCursor()
            current_pos = cursor.position()
            
            # Obtenir le texte courant et filtrer pour n'autoriser que des chiffres et des virgules
            current_text = widget.toPlainText()
            filtered_text = ''.join(char for char in current_text if char.isdigit() or char == ',')
            if current_text != filtered_text:
                widget.blockSignals(True)
                widget.setPlainText(filtered_text)
                widget.blockSignals(False)
                
                cursor = widget.textCursor()
                cursor.setPosition(current_pos)
                widget.setTextCursor(cursor)
        
        elif isinstance(widget, QLineEdit):
            current_text = widget.text()
            filtered_text = ''.join(char for char in current_text if char.isdigit() or char == ',')
            if current_text != filtered_text:
                widget.blockSignals(True)
                widget.setText(filtered_text)
                widget.blockSignals(False)
                
                widget.setCursorPosition(len(filtered_text))
    except Exception as e:        
        pass
