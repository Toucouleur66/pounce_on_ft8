# utils.py

import socket
import datetime
import re
import os
import sys
import fnmatch

from PyQt6.QtWidgets import QTextEdit, QLineEdit
from PyQt6.QtCore import QCoreApplication, QStandardPaths
from PyQt6.QtGui import QTextCursor

QCoreApplication.setApplicationName("Wait and Pounce")

AMATEUR_BANDS = {
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
        app_data_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
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
        lookup,
        wanted_callsigns,
        excluded_callsigns  = set(),
        monitored_callsigns = set(),
        monitored_cq_zones  = set()
    ):
    directed          = None
    callsign          = None
    callsign_info     = None
    grid              = None
    cq_zone           = None
    msg               = None
    cqing             = False
    wanted            = False
    monitored         = False
    monitored_cq_zone = False

    match = re.match(r"^<\.\.\.>\s+([A-Z0-9/]+)\s+(\w{2,3}|RR73|\d{2}[A-Z]{2})?", message)
    if match:
        callsign = match.group(1)
        msg = match.group(2)
    else:      
        match = re.match(r"^CQ\s+(?:(\w{2,3})\s+)?([A-Z0-9/]+)(?:\s+([A-Z]{2}\d{2}))?", message)
        if match:
            # Handle CQ messages      
            cqing    = True
            directed = match.group(1)
            callsign = match.group(2)
            grid     = match.group(3)

        else:
            # Handle directed calls and standard messages
            match = re.match(r"^([A-Z0-9/]+)\s+([A-Z0-9/]+)\s+([A-Z0-9+-]+)", message)
            if match:
                directed = match.group(1)
                callsign = match.group(2)
                msg      = match.group(3)

    if callsign:         
        callsign_info = lookup.lookup_callsign(callsign)    

        if callsign_info:            
            cq_zone = callsign_info["cqz"]

        """
            Check if the callsign matches
        """
        is_wanted    = matches_any(wanted_callsigns, callsign)
        is_excluded  = matches_any(excluded_callsigns, callsign)
        is_monitored = matches_any(monitored_callsigns, callsign)
        """
            Check if CQ Zone matches
        """
        is_monitored_cq_zone = False
        if cq_zone and cq_zone in monitored_cq_zones:
            is_monitored_cq_zone = True

        wanted            = is_wanted and not is_excluded
        monitored         = is_monitored and not is_excluded
        monitored_cq_zone = is_monitored_cq_zone and not is_excluded

    return {
        'directed'           : directed,
        'callsign'           : callsign,
        'callsign_info'      : callsign_info,
        'grid'               : grid,
        'msg'                : msg,
        'cqing'              : cqing,
        'wanted'             : wanted,
        'monitored'          : monitored,
        'monitored_cq_zone'  : monitored_cq_zone
    }

def matches_any(patterns, callsign):
    return any(fnmatch.fnmatch(callsign, pattern) for pattern in patterns)

def text_to_array(pattern):
    if re.fullmatch(r'[0-9,\s]*', pattern):
        array = [int(number) for number in re.findall(r'\d+', pattern)]
    else:
        array = [text.strip().upper() for text in pattern.split(',') if text.strip()]
        
    return sorted(array)

def get_mode_interval(mode):
    if mode == "FT4":
        return 7.5
    else:
        return 15
    
def get_amateur_band(frequency):   
    for band, (lower_bound, upper_bound) in AMATEUR_BANDS.items():
        if lower_bound <= frequency <= upper_bound:
            return band
    
    return 'Invalid'       

def force_input(widget, mode="uppercase"):
    try:
        allowed_pattern = None
        max_number = None

        if mode == "uppercase":
            allowed_pattern = re.compile(r'[A-Z0-9,/*]')
        elif mode == "numbers":
            allowed_pattern = re.compile(r'[0-9,]')
            max_number = 40

        if isinstance(widget, QTextEdit):
            cursor = widget.textCursor()
            current_pos = cursor.position()

            original_text = widget.toPlainText()

            current_text = original_text.upper() if mode == "uppercase" else original_text
            filtered_text = ''.join(char for char in current_text if allowed_pattern.fullmatch(char))

            if mode == "numbers":
                filtered_text = re.sub(r',+', ',', filtered_text)
                filtered_text = re.sub(r'^,', '', filtered_text)
                parts = filtered_text.split(',')
                valid_parts = []
                for part in parts:
                    if part.isdigit():
                        number = int(part)
                        if 1 <= number <= max_number and str(number) not in valid_parts:
                            valid_parts.append(str(number))
                    elif part == '':
                        valid_parts.append('')
                cleaned_text = ','.join(valid_parts)
            elif mode == "uppercase":
                filtered_text = re.sub(r',+', ',', filtered_text)
                filtered_text = re.sub(r'^,', '', filtered_text)
                parts = filtered_text.split(',')
                unique_parts = []
                for part in parts:
                    if part and part not in unique_parts:
                        unique_parts.append(part)
                cleaned_text = ','.join(unique_parts)
                if filtered_text.endswith(','):
                    cleaned_text += ','

            if original_text != cleaned_text:
                widget.blockSignals(True)
                widget.setPlainText(cleaned_text)
                widget.blockSignals(False)

                new_pos = min(current_pos, len(cleaned_text))
                cursor.setPosition(new_pos, QTextCursor.MoveMode.MoveAnchor)
                widget.setTextCursor(cursor)

        elif isinstance(widget, QLineEdit):
            original_text = widget.text()
            current_text = original_text.upper() if mode == "uppercase" else original_text
            filtered_text = ''.join(char for char in current_text if allowed_pattern.fullmatch(char))

            if mode == "numbers":
                filtered_text = re.sub(r',+', ',', filtered_text)
                filtered_text = re.sub(r'^,', '', filtered_text)
                parts = filtered_text.split(',')
                valid_parts = []
                for part in parts:
                    if part.isdigit():
                        number = int(part)
                        if 1 <= number <= max_number and str(number) not in valid_parts:
                            valid_parts.append(str(number))
                    elif part == '':
                        valid_parts.append('')
                cleaned_text = ','.join(valid_parts)
            elif mode == "uppercase":
                filtered_text = re.sub(r',+', ',', filtered_text)
                filtered_text = re.sub(r'^,', '', filtered_text)
                parts = filtered_text.split(',')
                unique_parts = []
                for part in parts:
                    if part and part not in unique_parts:
                        unique_parts.append(part)
                cleaned_text = ','.join(unique_parts)
                if filtered_text.endswith(','):
                    cleaned_text += ','

            if original_text != cleaned_text:
                widget.blockSignals(True)
                widget.setText(cleaned_text)
                widget.blockSignals(False)

                new_pos = min(widget.cursorPosition(), len(cleaned_text))
                widget.setCursorPosition(new_pos)

    except Exception as e:
        print(f"force_input: {e}")
