# utils.py

import socket
import difflib
import datetime
import time
import re
import json
import os
import sys
import fnmatch
import locale

from PyQt6.QtCore import QCoreApplication, QStandardPaths
from PyQt6.QtGui import QColor

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
        '4m'    : (69_950_000, 70_500_000),
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
    return os.path.join(get_app_data_dir(), f"pounce.log")

def parse_single_wsjtx_message(
        message,
        lookup              = None,
        wanted_callsigns    = set(),
        worked_callsigns    = set(),
        excluded_callsigns  = set(),
        monitored_callsigns = set(),
        wanted_cq_zones     = set(),
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
    wanted_cq_zone          = False
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
                        # 6) Handle two callsigns without message (e.g., "F5UKW DU6/PE1NSQ")
                        match = re.match(
                            r"^([A-Z0-9/]*\d[A-Z0-9/]*)\s+([A-Z0-9/]*\d[A-Z0-9/]*)\s*$",
                            message
                        )
                        if match:
                            directed = match.group(1)
                            callsign = match.group(2)
                            msg = None

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
            callsign = None
            msg      = None

    if callsign and lookup:            
        # Also check if exact match
        if cqing and not grid and callsign not in wanted_callsigns:
            pass
        else:     
            callsign_info = lookup.lookup_callsign(callsign, grid)    

        if callsign_info:            
            cq_zone = callsign_info["cqz"]

    if callsign:
        """
            Check if the callsign matches
        """
        is_wanted    = matches_any(wanted_callsigns, callsign)
        is_excluded  = matches_any(excluded_callsigns, callsign)
        is_worked    = matches_any(worked_callsigns, callsign)
        is_monitored = matches_any(monitored_callsigns, callsign)

        """
            Check if no grid is provided
        """
        if (
            not grid and 
            callsign_info and
            callsign_info.get('lat') and
            callsign_info.get('long')
        ):
            grid = latlon_to_grid(callsign_info.get('lat'), callsign_info.get('long'))[:4]    
        
        """
            Check if CQ Zone matches
        """
        is_wanted_cq_zone        = False
        is_monitored_cq_zone     = False
        if cq_zone and cq_zone in wanted_cq_zones:
            is_wanted_cq_zone    = True

        if cq_zone and cq_zone in monitored_cq_zones:
            is_monitored_cq_zone = True

        if cq_zone and cq_zone in excluded_cq_zones and callsign not in wanted_callsigns:
            is_excluded = True            

        wanted            = is_wanted and not is_excluded and not is_worked
        monitored         = is_monitored
        wanted_cq_zone    = is_wanted_cq_zone and not is_excluded and not is_worked
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
        'wanted_cq_zone'     : wanted_cq_zone,
        'excluded'           : excluded,
        'monitored'          : monitored,
        'monitored_cq_zone'  : monitored_cq_zone
    }

def parse_wsjtx_message(
    message,
    lookup              = None,
    wanted_callsigns    = set(),
    worked_callsigns    = set(),
    excluded_callsigns  = set(),
    monitored_callsigns = set(),
    wanted_cq_zones     = set(),
    monitored_cq_zones  = set(),
    excluded_cq_zones   = set(),
):
    multi = parse_combined_wsjtx_message(message)
    if multi is not None:
        results = []
        for sub_msg in multi:
            parsed = parse_single_wsjtx_message(
                sub_msg,
                lookup              = lookup,
                wanted_callsigns    = wanted_callsigns,
                worked_callsigns    = worked_callsigns,
                excluded_callsigns  = excluded_callsigns,
                monitored_callsigns = monitored_callsigns,
                wanted_cq_zones     = wanted_cq_zones,
                monitored_cq_zones  = monitored_cq_zones,
                excluded_cq_zones   = excluded_cq_zones
            )
            results.append(parsed)
        return results

    single_result = parse_single_wsjtx_message(
        message,
        lookup              = lookup,
        wanted_callsigns    = wanted_callsigns,
        worked_callsigns    = worked_callsigns,
        excluded_callsigns  = excluded_callsigns,
        monitored_callsigns = monitored_callsigns,
        wanted_cq_zones     = wanted_cq_zones,
        monitored_cq_zones  = monitored_cq_zones,
        excluded_cq_zones   = excluded_cq_zones
    )
    return [single_result]

def parse_combined_wsjtx_message(message):
    """
    Handle this combined message
      "DG3NAB RR73; R3PJ <3B9DJ> -06"

    then convert to
      1) "DG3NAB 3B9DJ RR73"
      2) "R3PJ 3B9DJ -06"

    """
    pattern = re.compile(
        r"^"
        r"([A-Z0-9/]*\d[A-Z0-9/]*)\s+([A-Z0-9+\-]+)"  # group(1)=directed1, group(2)=msg1
        r"\s*;\s*"
        r"([A-Z0-9/]*\d[A-Z0-9/]*)\s+<([A-Z0-9/]*\d[A-Z0-9/]*)>\s+([A-Z0-9+\-]+)"  # (3)=directed2, (4)=callsign, (5)=msg2
        r"$"
    )
    m = pattern.match(message)
    if not m:
        return None

    directed_1 = m.group(1)
    msg_1      = m.group(2)
    directed_2 = m.group(3)
    callsign   = m.group(4)  # common part
    msg_2      = m.group(5)

    line_1 = f"{directed_1} {callsign} {msg_1}"
    line_2 = f"{directed_2} {callsign} {msg_2}"

    return [line_1, line_2]

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
    for amateur_band, (lower_bound, upper_bound) in AMATEUR_BANDS.items():
        if lower_bound <= frequency <= upper_bound:
            return amateur_band
    
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

def get_period_for_datetime(dt_value, mode):
    from constants import EVEN, ODD
    
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    
    period_index = int(dt_value.timestamp() // get_mode_interval(mode))
    return "(1)" if period_index % 2 == 0 else "(2)"            

def has_significant_change(first_str, second_str):
    if first_str.count(',') != second_str.count(','):
        return True
    
    diff = list(difflib.ndiff(first_str, second_str))
    
    changes = sum(1 for d in diff if d.startswith(('+', '-')))
    
    if changes < 3:
        return False
    
    return True

def parse_adif_record(record, lookup):    
    fields = {field.upper(): value.strip() for field, value in ADIF_FIELD_RE.findall(record)}
    
    call        = fields.get('CALL')
    band        = fields.get('BAND')
    qso_date    = fields.get('QSO_DATE')
    time_on     = fields.get('TIME_ON')
    grid        = fields.get('GRIDSQUARE') 
    
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
    grid = grid.upper()[:4] if grid else None
    band = band.lower() if band else None
    year = qso_date[0:4] if qso_date and len(qso_date) >= 4 else None

    info = {}
    if lookup and call:
        if qso_datetime:
            info = lookup.lookup_callsign(call, date=qso_datetime, enable_cache=False)
        else:
            info = lookup.lookup_callsign(call)

    return year, band, grid, call, info

def parse_adif(file_path, lookup=None):
    start_time = time.time()

    parsed_wkb4_data    = defaultdict(lambda: defaultdict(set))
    parsed_grid_data    = defaultdict(lambda: defaultdict(set))
    parsed_entity_data  = defaultdict(lambda: defaultdict(set)) if lookup else None

    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    records = re.split(r"<EOR>", content, flags=re.IGNORECASE)

    for record in records:
        record = record.strip()
        if record:
            record = " ".join(record.split())
            year, band, grid, call, info = parse_adif_record(record, lookup)

            if lookup and year and band and info and info.get('entity'):
                parsed_entity_data[year][band].add(info.get('entity'))
            if year and band and call:
                parsed_wkb4_data[year][band].add(call)
            if band and grid and call:
                parsed_grid_data[band][grid].add(call)

    processing_time = time.time() - start_time

    return processing_time, {
        'wkb4'  : parsed_wkb4_data,
        'entity': parsed_entity_data,
        'grid'  : parsed_grid_data
    }

def is_worked_b4_year_band(data, callsign, year, band):
    if callsign in data.get(year, {}).get(band, set()):
        return True
    else:
        return False
    
def is_entity_worked_b4(data, entity_code, year):
    bands = data.get('entity', {}).get(year, {})
    for band, entities in bands.items():
        if entity_code in entities:
            return True
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

def get_grid_square_polygon(grid):
    try:
        top_left     = grid_to_latlon(grid + 'AA')  
        bottom_right = grid_to_latlon(grid + 'RR')  

        top = top_left[0]
        left = top_left[1]
        bottom = bottom_right[0]
        right = bottom_right[1]

        return [
            [top, left],
            [top, right],
            [bottom, right],
            [bottom, left]
        ]
    except Exception as e:
        return None

def grid_to_latlon(grid):
    grid = grid.upper()
    if len(grid) < 2:
        raise ValueError("Grid square invalid.")

    lon = (ord(grid[0]) - ord('A')) * 20 - 180
    lat = (ord(grid[1]) - ord('A')) * 10 - 90

    if len(grid) >= 4:
        lon += int(grid[2]) * 2
        lat += int(grid[3]) * 1

    if len(grid) >= 6:
        lon += (ord(grid[4]) - ord('A')) * 5 / 60
        lat += (ord(grid[5]) - ord('A')) * 2.5 / 60

    if len(grid) == 2:
        lon += 10
        lat += 5
    elif len(grid) == 4:
        lon += 1
        lat += 0.5
    elif len(grid) == 6:
        lon += 2.5 / 60
        lat += 1.25 / 60

    return (lat, lon)

def latlon_to_grid(lat, lon, precision=4):    
    if not (-90 <= lat <= 90):
        raise 
    if not (-180 <= lon <= 180):
        raise 
    if precision not in [2, 4, 6]:
        raise 
    
    adj_lat = lat + 90
    adj_lon = lon + 180
    
    grid = ""
    
    field_lon = int(adj_lon / 20)
    field_lat = int(adj_lat / 10)
    grid += chr(ord('A') + field_lon)
    grid += chr(ord('A') + field_lat)
    
    if precision == 2:
        return grid
    
    square_lon = int((adj_lon % 20) / 2)
    square_lat = int((adj_lat % 10) / 1)
    grid += str(square_lon)
    grid += str(square_lat)
    
    if precision == 4:
        return grid
    
    subsquare_lon = int(((adj_lon % 20) % 2) / (5/60))
    subsquare_lat = int(((adj_lat % 10) % 1) / (2.5/60))
    grid += chr(ord('A') + subsquare_lon)
    grid += chr(ord('A') + subsquare_lat)
    
    return grid

def darken_color(color, factor):
    r = int(color.red() * (1.0 - factor))
    g = int(color.green() * (1.0 - factor))
    b = int(color.blue() * (1.0 - factor))

    return QColor(r, g, b)

def lighten_color(color, factor):
    r = int(color.red() + (255 - color.red()) * factor)
    g = int(color.green() + (255 - color.green()) * factor)
    b = int(color.blue() + (255 - color.blue()) * factor)
    
    return QColor(r, g, b, color.alpha())
    
def complementary_color(color):
    h, s, v, a = color.getHsv()
    
    complementary_h = (h + 180) % 360
    
    return QColor.fromHsv(complementary_h, s, v, a)