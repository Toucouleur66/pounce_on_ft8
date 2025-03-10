# utils.py

import socket
import datetime
import time
import re
import json
import os
import sys
import fnmatch
import locale

from PyQt6.QtWidgets import QTextEdit, QLineEdit
from PyQt6.QtCore import QCoreApplication, QStandardPaths
from PyQt6.QtGui import QTextCursor

from collections import defaultdict
from datetime import datetime, timezone

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

ADIF_FIELD_RE = re.compile(r"<(\w+):\d+(?::\w+)?>([^<]+)", re.IGNORECASE)

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
    today = datetime.now().strftime("%y%m%d")

    return os.path.join(get_app_data_dir(), f"{today}_pounce.log")

def parse_wsjtx_message(
        message,
        lookup              = None,
        wanted_callsigns    = set(),
        worked_callsigns    = set(),
        excluded_callsigns  = set(),
        monitored_callsigns = set(),
        monitored_cq_zones  = set(),
        excluded_cq_zones   = set(),
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
    excluded                = False
    monitored               = False
    monitored_cq_zone       = False

    # 1) Handle <...> message
    match = re.match(
        r"^<\.\.\.>\s+([A-Z0-9/]*\d[A-Z0-9/]*)\s+([A-Z0-9+\-]+)?",
        message
    )
    if match:
        callsign = match.group(1)
        msg      = match.group(2)
    else:
        # 2) Handle CQ + directed CQ
        #
        #    Example : "CQ SEAS F4XXX JN12"
        #    - directed = F8ABC
        #    - callsign = F4XXX
        #    - grid     = JN12
        #
        match = re.match(
            r"^CQ\s+(?:(\w{2,4})\s+)([A-Z0-9/]*\d[A-Z0-9/]*)(?:\s+([A-Z]{2}\d{2}))",
            message
        )
        if match:
            cqing    = True
            directed = match.group(1)
            callsign = match.group(2)
            grid     = match.group(3)

        else:
            # 3) Handle CQ + callsign (+ optional grid)
            #
            #    Example : "CQ F4XXX JN12"
            #    - callsign = F4XXX
            #    - grid     = JN12 (optional)
            #
            match = re.match(
                r"^CQ\s+([A-Z0-9/]*\d[A-Z0-9/]*)(?:\s+([A-Z]{2}\d{2}))?",
                message
            )
            if match:
                cqing    = True
                callsign = match.group(1)
                grid     = match.group(2)

            else:
                # 4) Handle "directed" <callsign> 
                #
                #    Example : "F5UKW <VP2V/F4BKV> RR73"
                #      - directed = "F5UKW"
                #      - callsign = "VP2V/F4BKV"
                #      - msg      = "RR73"
                #
                #    Example : "F5UKW <VP2V/F4BKV>"
                #      - directed = "F5UKW"
                #      - callsign = "VP2V/F4BKV"
                #      - msg      = None
                #
                match = re.match(
                    r"^(?:([A-Z0-9/]*\d[A-Z0-9/]*)\s+<([A-Z0-9/]*\d[A-Z0-9/]*)>|<([A-Z0-9/]*\d[A-Z0-9/]*)>\s+([A-Z0-9/]*\d[A-Z0-9/]*))\s*(\S+)?$",
                    message
                )
                if match:
                    if match.group(1):
                        directed = match.group(1)
                        callsign = match.group(2)
                        msg      = match.group(5)
                    else:
                        # Branche B
                        directed = match.group(3)
                        callsign = match.group(4)
                        msg      = match.group(5)
                else:
                    # 5) Handle directed calls and standard messages
                    #
                    #    Example : "F5UKW F4XXX RR73"
                    #      - directed = "F5UKW"
                    #      - callsign = "F4XXX"
                    #      - msg      = "RR73"
                    #
                    match = re.match(
                        r"^([A-Z0-9/]*\d[A-Z0-9/]*)\s+([A-Z0-9/]*\d[A-Z0-9/]*)\s+([A-Z0-9+\-]+)",
                        message
                    )
                    if match:
                        directed = match.group(1)
                        callsign = match.group(2)
                        msg      = match.group(3)                        
                    else:
                        pass

    if msg:
        # RRR / RR73 / 73
        if re.match(r"^(RRR|RR73|73)$", msg):
            pass
        # Grids 2 letters + 2 numbers (ex: JN12)
        elif re.match(r"^[A-Z]{2}\d{2}$", msg):
            grid = msg
        # Report : R+NN, +NN, R-NN, -NN
        elif re.match(r"^(?:R[+\-]|[+\-])\d{2}$", msg):
            report = msg
        else:
            pass

    if callsign and lookup:    
        if cqing and not grid:
            pass
        else:     
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

        if cq_zone and cq_zone in excluded_cq_zones:
            is_excluded = True            

        wanted            = is_wanted and not is_excluded and not is_worked
        monitored         = is_monitored and not is_excluded
        monitored_cq_zone = is_monitored_cq_zone and not is_excluded
        excluded          = is_excluded

    return {
        'directed'           : directed,
        'callsign'           : callsign,
        'callsign_info'      : callsign_info,
        'grid'               : grid,
        'report'             : report,
        'msg'                : msg,
        'cqing'              : cqing,
        'wanted'             : wanted,
        'excluded'           : excluded,
        'monitored'          : monitored,
        'monitored_cq_zone'  : monitored_cq_zone
    }

def matches_any(patterns, callsign):
    return any(fnmatch.fnmatch(callsign, pattern) for pattern in patterns)

def int_to_array(pattern):
    array = []
    if re.fullmatch(r'[0-9,\s]*', pattern):
        array = sorted([int(number) for number in re.findall(r'\d+', pattern)])
    return array
        
def text_to_array(pattern):
    array = []
    if not re.fullmatch(r'[0-9,\s]*', pattern):
        array = sorted([text.strip().upper() for text in pattern.split(',') if text.strip()])
    return array        

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

def compute_time_ago(dt_value):
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)

    now     = datetime.now(timezone.utc)
    delta   = now - dt_value
    seconds = int(delta.total_seconds())

    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3_600:
        return f"{seconds // 60}m"
    elif seconds < 86_400:
        return f"{seconds // 3600}h"
    elif seconds <= 1_209_600:  # 2 weeks
        return f"{seconds // 86400}d"
    else:
        weeks = seconds // (86400 * 7)
        return f"{weeks}w"            

def parse_adif_record(record, lookup):    
    fields = {field.upper(): value.strip() for field, value in ADIF_FIELD_RE.findall(record)}
    
    call        = fields.get('CALL')
    band        = fields.get('BAND')
    qso_date    = fields.get('QSO_DATE')
    time_on     = fields.get('TIME_ON')
    
    qso_datetime = None
    if qso_date and len(qso_date) >= 8:
        year_str = qso_date[0:4]
        month    = qso_date[4:6]
        day      = qso_date[6:8]
        hour     = "00"
        minute   = "00"
        second   = "00"

        if time_on and len(time_on) >= 6:
            hour = time_on[0:2]
            minute = time_on[2:4]
            second = time_on[4:6]
        full_dt_str = f"{year_str}-{month}-{day} {hour}:{minute}:{second}"
        try:
            qso_datetime = datetime.datetime.strptime(full_dt_str, "%Y-%m-%d %H:%M:%S")
            qso_datetime = qso_datetime.replace(tzinfo=datetime.timezone.utc)
        except Exception as e:
            qso_datetime = None

    call = call.upper() if call else None
    band = band.lower() if band else None
    year = qso_date[0:4] if qso_date and len(qso_date) >= 4 else None

    info = {}
    if lookup and call:
        if qso_datetime:
            info = lookup.lookup_callsign(call, date=qso_datetime, enable_cache=False)
        else:
            info = lookup.lookup_callsign(call)

    return year, band, call, info

def parse_adif(file_path, lookup=None):
    start_time = time.time()

    parsed_wkb4_data    = defaultdict(lambda: defaultdict(set))
    parsed_entity_data  = defaultdict(lambda: defaultdict(set)) if lookup else None

    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    records = re.split(r"<EOR>", content, flags=re.IGNORECASE)

    for record in records:
        record = record.strip()
        if record:
            record = " ".join(record.split())
            year, band, call, info = parse_adif_record(record, lookup)

            if lookup and year and band and info and info.get('entity'):
                parsed_entity_data[year][band].add(info.get('entity'))
            if year and band and call:
                parsed_wkb4_data[year][band].add(call)

    processing_time = time.time() - start_time

    return processing_time, {
        'wkb4'  : parsed_wkb4_data,
        'entity': parsed_entity_data
    }

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

def get_clean_rst(rst):
    try:
        def repl(match):
            sign = match.group(1)       
            number = match.group(2).zfill(2)
            return f"{sign}{number}"
        
        pattern = r'^R?([+-]?)(\d+)$'
        cleaned_rst = re.sub(pattern, repl, rst)
        return cleaned_rst    
    except Exception as e:
        return None
        
"""
    Save marathon cache file
"""

def load_marathon_wanted_data(file):
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                marathon_data = json.load(f)
                return marathon_data
        except Exception as e:
            pass
    return {}

def save_marathon_wanted_data(file, marathon_data):
    try:
        with open(file, "w") as f:
            json.dump(marathon_data, f, indent=4)
    except Exception as e:
        pass

def log_format_message(message):
    decode_time = message.get('decode_time')
    if hasattr(decode_time, 'strftime'):
        decode_time_str = decode_time.strftime("%H:%M:%S")
    else:
        decode_time_str = str(decode_time)

    if message.get('directed') is not None:
        directed_or_grid = f"directed:{message.get('directed')}"
    else:
        directed_or_grid = f"grid:{message.get('grid')}" if message.get('grid') is not None else ''           

    msg = message.get('msg', None)
    if not msg and message.get('cqing'):
        msg = "CQ"

    return (            
        f"Message from packet_id #{message.get('packet_id'):<10}"
        f"\n\tpriority:{message.get('priority'):<10}"
        f"\tcallsign:{message.get('callsign'):<13}"
        f"\t{directed_or_grid}"                        
        f"\n\tdecode_time:{decode_time_str:<10}"                        
        f"\tcqing:{message.get('cqing'):<13}"
        f"\tmsg:{msg}"
    )        
