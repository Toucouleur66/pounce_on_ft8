# constants.py
import os

from datetime import datetime
from utils import get_app_data_dir

version_number                  = "2.0.4"
EXPIRATION_DATE                 = datetime(2024, 11, 30)

EVEN                            = "EVEN"
ODD                             = "ODD"

EVEN_COLOR                      = "#9DFFFE"
ODD_COLOR                       = "#FFFE9F"

BG_COLOR_FOCUS_MY_CALL          = "#80D0D0"
FG_COLOR_FOCUS_MY_CALL          = "#000000"

BG_COLOR_REGULAR_FOCUS          = "#000000"
FG_COLOR_REGULAR_FOCUS          = "#01FFFF"

BG_COLOR_BLACK_ON_YELLOW        = "yellow"
FG_COLOR_BLACK_ON_YELLOW        = "#000000"

BG_COLOR_WHITE_ON_BLUE          = "blue"
FG_COLOR_WHITE_ON_BLUE          = "white"

BG_COLOR_BLACK_ON_PURPLE        = "#D080D0"
FG_COLOR_BLACK_ON_PURPLE        = "#000000"

BG_COLOR_BLACK_ON_WHITE         = "#000000"
FG_COLOR_BLACK_ON_WHITE         = "white"

PARAMS_FILE                     = os.path.join(get_app_data_dir(), "params.pkl")
POSITION_FILE                   = os.path.join(get_app_data_dir(), "window_position.pkl")
WANTED_CALLSIGNS_FILE           = os.path.join(get_app_data_dir(), "wanted_callsigns.pkl")
WANTED_CALLSIGNS_HISTORY_SIZE   = 50

GUI_LABEL_VERSION               = f"Wait and Pounce v{version_number} by F5UKW"
MONITORING_RUN_BUTTON_LABEL     = "Monitoring..."
DECODING_RUN_BUTTON_LABEL       = "Decoding..."
WAIT_RUN_BUTTON_LABEL           = "Start Monitoring"
NOTHING_YET                     = "Nothing yet"
WAITING_DATA_PACKETS_LABEL      = "Waiting for UDP Packets"
WANTED_CALLSIGNS_HISTORY_LABEL  = "Wanted Callsigns History (%d):"
CALLSIGN_NOTICE_LABEL           = "Comma separated list of callsigns - Wildcard allowed (*)"

MODE_NORMAL                     = "Normal"
MODE_FOX_HOUND                  = "Fox/Hound"
MODE_SUPER_FOX                  = "SuperFox"

DEFAULT_MODE_TIMER_VALUE        = "--:--:--"

FREQ_MINIMUM                    = 200
FREQ_MAXIMUM                    = 2900
FREQ_MINIMUM_FOX_HOUND          = 1050

DEFAULT_UDP_PORT                = 2237

CURRENT_DIR                     = os.path.dirname(os.path.realpath(__file__))
CTY_XML                         = 'cty.xml'

DEFAULT_SECONDARY_UDP_SERVER    = False
DEFAULT_SENDING_REPLY           = True
DEFAULT_GAP_FINDER              = True
DEFAULT_WATCHDOG_BYPASS         = False
DEFAULT_DEBUG_OUTPUT            = False
DEFAULT_POUNCE_LOG              = True
DEFAULT_LOG_PACKET_DATA         = False
DEFAULT_SHOW_ALL_DECODED        = True
DEFAULT_DELAY_BETWEEN_SOUND     = 120