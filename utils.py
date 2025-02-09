# utils.py

import socket
import datetime
import time
import re
import os
import sys
import fnmatch
import locale

from PyQt6.QtWidgets import QTextEdit, QLineEdit
from PyQt6.QtCore import QCoreApplication, QStandardPaths
from PyQt6.QtGui import QTextCursor

from collections import defaultdict

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
        lookup              = None,
        wanted_callsigns    = set(),
        worked_callsigns    = set(),
        excluded_callsigns  = set(),
        monitored_callsigns = set(),
        monitored_cq_zones  = set()
    ):
    directed                = None
    callsign                = None
    callsign_info           = None
    grid                    = None
    cq_zone                 = None
    msg                     = None
    report                  = None
    cqing                   = False
    wanted                  = False
    monitored               = False
    monitored_cq_zone       = False

    # Handle <...> message
    match = re.match(r"^<\.\.\.>\s+([A-Z0-9/]*\d[A-Z0-9/]*)\s+(\w{2,3}|RR73|\d{2}[A-Z]{2})?", message)
    if match:
        callsign = match.group(1)
        msg = match.group(2)
    else:      
        match = re.match(r"^CQ\s+(?:(\w{2,4})\s+)([A-Z0-9/]*\d[A-Z0-9/]*)(?:\s+([A-Z]{2}\d{2}))", message)        
        if match:
            # Handle CQ messages with directed CQ   
            cqing    = True
            directed = match.group(1)
            callsign = match.group(2)
            grid     = match.group(3)
        else:
            # 4) # Handle partial <...>
            match = re.match(
                r"^([A-Z0-9/]*\d[A-Z0-9/]*)\s+<([A-Z0-9/]*\d[A-Z0-9/]*)>\s*(\S+)?",
                message
            )
            if match:
                directed = match.group(1)
                callsign = match.group(2)
                msg      = match.group(3) 

                if msg:
                    if re.match(r"^(RRR|RR73|73)$", msg):
                        pass
                    elif re.match(r"^[A-Z]{2}\d{2}$", msg):
                        grid = msg
                    elif re.match(r"^(?:R[+\-]|[+\-])\d{2}$", msg):
                        report = msg
                    else:
                        pass
            else:
                # 5) Handle directed calls and standard messages
                match = re.match(
                    r"^([A-Z0-9/]*\d[A-Z0-9/]*)\s+([A-Z0-9/]*\d[A-Z0-9/]*)\s+([A-Z0-9+\-]+)",
                    message
                )
                if match:
                    directed = match.group(1)
                    callsign = match.group(2)
                    msg      = match.group(3)

                    if re.match(r"^(RRR|RR73|73)$", msg):
                        pass
                    elif re.match(r"^[A-Z]{2}\d{2}$", msg):
                        grid = msg
                    elif re.match(r"^(?:R[+\-]|[+\-])\d{2}$", msg):
                        report = msg
                else:
                    pass

    if callsign and lookup:         
        callsign_info = lookup.lookup_callsign(callsign, grid)    

        if callsign_info:            
            cq_zone = callsign_info["cqz"]

        """
            Check if the callsign matches
        """
        is_wanted    = matches_any(wanted_callsigns, callsign)
        is_excluded  = matches_any(excluded_callsigns, callsign)
        is_worked    = matches_any(worked_callsigns, callsign)
        is_monitored = matches_any(monitored_callsigns, callsign)
        """
            Check if CQ Zone matches
        """
        is_monitored_cq_zone = False
        if cq_zone and cq_zone in monitored_cq_zones:
            is_monitored_cq_zone = True

        wanted            = is_wanted and not is_excluded and not is_worked
        monitored         = is_monitored and not is_excluded
        monitored_cq_zone = is_monitored_cq_zone and not is_excluded

    return {
        'directed'           : directed,
        'callsign'           : callsign,
        'callsign_info'      : callsign_info,
        'grid'               : grid,
        'report'             : report,
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

def display_frequency(frequency):
    if not frequency:
        return ''
    
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, 'C')
      
    formatted       = locale.format_string("%.5f", frequency / 1_000_000, grouping=True)
    conv            = locale.localeconv()
    decimal_point   = conv['decimal_point']
    
    try:
        integer_part, decimal_part = formatted.split(decimal_point)
    except ValueError:
        integer_part, decimal_part = formatted, ''
    
    if len(decimal_part) > 3:
        decimal_part = decimal_part[:3] + decimal_part[3:].rstrip('0')
    else:
        decimal_part = decimal_part.rstrip('0')
    
    if decimal_part:
        return f"{integer_part}{decimal_point}{decimal_part}"
    else:
        return integer_part

def force_input(widget, mode="uppercase"):
    try:
        allowed_pattern = None

        if mode == "uppercase":
            allowed_pattern = re.compile(r'[A-Z0-9,/*]')
        elif mode == "numbers":
            allowed_pattern = re.compile(r'[0-9,]')

        old_cursor_pos = widget.cursorPosition()

        original_text = widget.text()
        current_text = original_text.upper() if mode == "uppercase" else original_text
        filtered_text = ''.join(char for char in current_text if allowed_pattern.fullmatch(char))

        filtered_text = re.sub(r',+', ',', filtered_text)  
        filtered_text = re.sub(r'^,', '', filtered_text)

        if original_text != filtered_text:
            widget.blockSignals(True)
            widget.setText(filtered_text)

            new_cursor_pos = min(old_cursor_pos, len(filtered_text))
            widget.setCursorPosition(new_cursor_pos)

            widget.blockSignals(False)

    except Exception as e:
        print(f"force_input: {e}")

def focus_out_event(widget, mode):
    original_focus_out = widget.focusOutEvent

    def custom_focus_out(event):
        try:
            if mode == "numbers":
                text = widget.text()
                parts = text.split(',')
                valid_parts = []
                for part in parts:
                    if part.isdigit():
                        number = int(part)
                        if 1 <= number <= 40:
                            valid_parts.append(number)

                valid_parts = sorted(set(valid_parts))
                widget.blockSignals(True)
                widget.setText(','.join(map(str, valid_parts)))
                widget.blockSignals(False)

            elif mode == "uppercase":
                text = widget.text()
                parts = text.split(',')
                unique_parts = []
                for part in parts:
                    if part and part not in unique_parts:
                        unique_parts.append(part)

                widget.blockSignals(True)
                widget.setText(','.join(unique_parts))
                widget.blockSignals(False)

        except Exception as e:
            print(f"focusOutEvent: {e}")

        original_focus_out(event)

    widget.focusOutEvent = custom_focus_out

def parse_adif_record(record):
    call_match = re.search(r"<CALL:\d+>([^ <]+)", record, re.IGNORECASE)
    band_match = re.search(r"<BAND:\d+>([^ <]+)", record, re.IGNORECASE)
    date_match = re.search(r"<QSO_DATE:\d+>(\d{4})", record, re.IGNORECASE)
    
    call = call_match.group(1).upper() if call_match else None
    band = band_match.group(1).lower() if band_match else None
    year = date_match.group(1) if date_match else None

    return year, band, call

def parse_adif(file_path):
    start_time = time.time()

    parsed_data = defaultdict(lambda: defaultdict(set))

    current_record_lines = []
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line:
                current_record_lines.append(line)
                if "<EOR>" in line.upper():
                    record = " ".join(current_record_lines)
                    year, band, call = parse_adif_record(record)
                    if year and band and call:
                        parsed_data[year][band].add(call)
                    current_record_lines = []

    end_time = time.time()
    processing_time = end_time - start_time

    return parsed_data, processing_time

def is_worked_b4_year_band(data, callsign, year, band):
    if callsign in data.get(year, {}).get(band, set()):
        return True
    else:
        return False

def get_wkb4_year(data, callsign, band):
    worked_years = []    
    for year, bands in data.items():
        if band in bands and callsign in bands[band]:
            worked_years.append(year)

    if worked_years:
        return int(max(worked_years))
    return None