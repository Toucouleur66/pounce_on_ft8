# constants.py
import os

from datetime import datetime
from utils import get_app_data_dir

version_number                  = "2.0.8.2"
EXPIRATION_DATE                 = datetime(2024, 11, 30)

EVEN                            = "EVEN"
ODD                             = "ODD"

EVEN_COLOR                      = "#9DFFFE"
ODD_COLOR                       = "#FFFE9F"

BG_COLOR_FOCUS_MY_CALL          = "#80D0D0"
FG_COLOR_FOCUS_MY_CALL          = "red"

BG_COLOR_REGULAR_FOCUS          = "#000000"
FG_COLOR_REGULAR_FOCUS          = "#01FFFF"

BG_COLOR_BLACK_ON_YELLOW        = "yellow"
FG_COLOR_BLACK_ON_YELLOW        = "#000000"

BG_COLOR_WHITE_ON_BLUE          = "#AEB4FF"
FG_COLOR_WHITE_ON_BLUE          = "000000"

BG_COLOR_BLACK_ON_PURPLE        = "#FFBDFF"
FG_COLOR_BLACK_ON_PURPLE        = "#000000"

BG_COLOR_BLACK_ON_WHITE         = "#000000"
FG_COLOR_BLACK_ON_WHITE         = "white"

BG_COLOR_BLACK_ON_CYAN          = "#C8F0C9"
FG_COLOR_BLACK_ON_CYAN          = "#000000"

STATUS_MONITORING_COLOR         = "#0D81FF"
STATUS_DECODING_COLOR           = "#2BBE7E"
STATUS_TRX_COLOR                = "#FF5600"

PARAMS_FILE                     = os.path.join(get_app_data_dir(), "params.pkl")
POSITION_FILE                   = os.path.join(get_app_data_dir(), "window_position.pkl")
WANTED_CALLSIGNS_FILE           = os.path.join(get_app_data_dir(), "wanted_callsigns.pkl")
WANTED_CALLSIGNS_HISTORY_SIZE   = 50

GUI_LABEL_VERSION               = f"Wait and Pounce v{version_number} by F5UKW"

STATUS_BUTTON_LABEL_MONITORING  = "Monitoring..."
STATUS_BUTTON_LABEL_DECODING    = "Decoding..."
STATUS_BUTTON_LABEL_TRX         = "Transmitting..."
STATUS_BUTTON_LABEL_START       = "Start Monitoring"
STATUS_BUTTON_LABEL_NOTHING_YET = "Nothing yet"

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

ACTIVITY_BAR_MAX_VALUE          = 50

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

CONTEXT_MENU_DARWIN_STYLE       = """
            QMenu {
                background-color: rgba(255, 255, 255, 0.95);                
                border-radius: 6px;
                padding: 6px;
            }
            QMenu::item {
                padding: 4px 12px;
                font-size: 12px;
                color: black;
            }
            QMenu::item:selected {
                background-color: #499eff;
                border-radius: 4px;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background: #CCCCCC;
                margin: 4px 0;
            }
        """