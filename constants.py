# constants.py
from PyQt6 import QtGui, QtWidgets

import os
import platform

from datetime import datetime
from utils import get_app_data_dir

CURRENT_VERSION_NUMBER          = "2.6.5.1"
EXPIRATION_DATE                 = datetime(2025, 4, 15)
UPDATE_JSON_INFO_URL            = "https://storage.de.cloud.ovh.net/v1/AUTH_31163bb499dc49eb819aacdfd32ae82c/wait.and.pounce/public/update_info.json"

README_URL                      = "https://storage.de.cloud.ovh.net/v1/AUTH_31163bb499dc49eb819aacdfd32ae82c/wait.and.pounce/public/readme.txt"

EVEN                            = "EVEN"
ODD                             = "ODD"

EVEN_COLOR                      = "#9DFFFE"
ODD_COLOR                       = "#FFFE9F"

"""
BG_COLOR_FOCUS_MY_CALL          = "#CCDEAA"
"""
BG_COLOR_FOCUS_MY_CALL          = ODD_COLOR
FG_COLOR_FOCUS_MY_CALL          = "#FF0000"

BG_COLOR_REGULAR_FOCUS          = "#000000"
FG_COLOR_REGULAR_FOCUS          = "#01FFFF"

BG_COLOR_BLACK_ON_YELLOW        = "#FFFF00"
FG_COLOR_BLACK_ON_YELLOW        = "#000000"

BG_COLOR_WHITE_ON_BLUE          = "#AEB4FF"
FG_COLOR_WHITE_ON_BLUE          = "000000"

BG_COLOR_BLACK_ON_PURPLE        = "#FFBDFF"
FG_COLOR_BLACK_ON_PURPLE        = "#000000"

BG_COLOR_BLACK_ON_WHITE         = "#000000"
FG_COLOR_BLACK_ON_WHITE         = "#FFFFFF"

BG_COLOR_BLACK_ON_CYAN          = "#C8F0C9"
FG_COLOR_BLACK_ON_CYAN          = "#000000"

STATUS_MONITORING_COLOR         = "#0D81FF"
STATUS_DECODING_COLOR           = "#2BBE7E"
STATUS_TRX_COLOR                = "#FF5600"

STATUS_COLOR_LABEL_OFF          = "#E5E5E5"
STATUS_COLOR_LABEL_SELECTED     = "#808080"

SAVED_VERSION_FILE              = os.path.join(get_app_data_dir(), "app_version.json")
PARAMS_FILE                     = os.path.join(get_app_data_dir(), "params.pkl")
POSITION_FILE                   = os.path.join(get_app_data_dir(), "window_position.pkl")
WORKED_CALLSIGNS_FILE           = os.path.join(get_app_data_dir(), "worked_callsigns.pkl")
ADIF_WORKED_CALLSIGNS_FILE      = os.path.join(get_app_data_dir(), "wait_pounce_log.adif")

GUI_LABEL_NAME                  = "Wait and Pounce"
GUI_LABEL_VERSION               = f"{GUI_LABEL_NAME} v{CURRENT_VERSION_NUMBER}"

STATUS_BUTTON_LABEL_MONITORING  = "Monitoring..."
STATUS_BUTTON_LABEL_DECODING    = "Decoding..."
STATUS_BUTTON_LABEL_TRX         = "Transmitting..."
STATUS_BUTTON_LABEL_START       = "Start Monitoring"
STATUS_BUTTON_LABEL_NOTHING_YET = "Nothing yet"

ACTION_RESTART                  = "Restart"

STOP_BUTTON_LABEL               = "Stop all"

DATE_COLUMN_DATETIME            = "Time"
DATE_COLUMN_AGE                 = "Age"

WAITING_DATA_PACKETS_LABEL      = "Waiting for UDP Packets"
WORKED_CALLSIGNS_HISTORY_LABEL  = "Worked Callsigns History (%d):"
CALLSIGN_NOTICE_LABEL           = "Comma-separated list of callsigns (or prefixes). Allows wildcards with *"
CQ_ZONE_NOTICE_LABEL            = "Comma separated list of CQ Zone"

MODE_NORMAL                     = "Regular"
MODE_FOX_HOUND                  = "Hound"
MODE_SUPER_FOX                  = "SuperFox"

WKB4_REPLY_MODE_ALWAYS          = 1
WKB4_REPLY_MODE_CURRENT_YEAR    = 2
WKB4_REPLY_MODE_NEVER           = 3

DEFAULT_MODE_TIMER_VALUE        = "--:--:--"

FREQ_MINIMUM                    = 200
FREQ_MAXIMUM                    = 2900
FREQ_MINIMUM_FOX_HOUND          = 1050
FREQ_MAXIMUM_SUPER_FOX          = 3200

DEFAULT_UDP_PORT                = 2237

ACTIVITY_BAR_MAX_VALUE          = 50

CURRENT_DIR                     = os.path.dirname(os.path.realpath(__file__))
CTY_XML                         = 'cty.xml'
CTY_XML_URL                     = 'https://cdn.clublog.org/cty.php?api=efc2af7050308f03a22275cf51f3fd7749582d66'

DEFAULT_SECONDARY_UDP_SERVER    = False
DEFAULT_SENDING_REPLY           = True
DEFAULT_GAP_FINDER              = True
DEFAULT_WATCHDOG_BYPASS         = False
DEFAULT_DEBUG_OUTPUT            = False
DEFAULT_POUNCE_LOG              = True
DEFAULT_LOG_PACKET_DATA         = False
DEFAULT_SHOW_ALL_DECODED        = False
DEFAULT_LOG_ALL_VALID_CONTACT   = True
DEFAULT_DELAY_BETWEEN_SOUND     = 120
DEFAULT_REPLY_ATTEMPTS          = 10

DEFAULT_SELECTED_BAND           = "6m"
DEFAULT_FILTER_VALUE            = "All"

MESSAGE_TYPE_PRIORITY           = {
                                    'ready_to_log'                    : 6,
                                    'wanted_callsign_being_called'    : 5,
                                    'directed_to_my_call'             : 4,                                    
                                    'wanted_callsign_detected'        : 3,
                                    'monitored_callsign_detected'     : 2,
                                    'lost_targeted_callsign'          : 1,
                                }

SETTING_QSS                     = f"""
                background-color: #9DFFFE; 
                color: #555BC2;
                padding: 5px;
                margin-bottom: 15px;
                font-size: 12px;
                border-radius: 6px;
        """

TOOLTIP_QSS                      = f"""
            QToolTip {{
                background-color: {STATUS_MONITORING_COLOR}; 
                color: white;
                padding: 3px;
                border-style: none;
            }}
        """

CONTEXT_MENU_DARWIN_QSS         = f"""
            QMenu {{
                background-color: rgba(255, 255, 255, 0.95);                
                border-radius: 6px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 4px 12px;
                font-size: 12px;
                color: black;
            }}
            QMenu::item:selected,
            QMenu::item:disabled {{
                background-color: #499EFF;
                border-radius: 4px;
                color: white;
            }}
            QMenu::item:disabled {{
                background-color: {STATUS_TRX_COLOR};      
            }}
            QMenu::separator {{
                height: 1px;
                background: #CCCCCC;
                margin: 4px 0;
            }}
        """

DISCORD_SECTION                 = '<a href="https://discord.gg/fqCu24naCM">Support available on Discord</a>'
DONATION_SECTION                = '<a href="https://www.paypal.com/donate/?cmd=_s-xclick&hosted_button_id=R4HK9ZTUPYHSL&ssrt=1732865689562">Donations are welcome</a>'

if platform.system() == 'Windows':
    system_default_font          = QtWidgets.QApplication.font()
    CUSTOM_FONT                  = system_default_font
    CUSTOM_FONT_SMALL            = QtGui.QFont(CUSTOM_FONT)
    
    CUSTOM_FONT.setPointSize(11)
    CUSTOM_FONT_SMALL.setPointSize(9)

    CUSTOM_FONT_MONO            = QtGui.QFont("Consolas", 11)
    CUSTOM_FONT_MONO_LG         = QtGui.QFont("Consolas", 18)
    CUSTOM_FONT_BOLD            = QtGui.QFont("Consolas", 13, QtGui.QFont.Weight.Bold)

    MENU_FONT                   = QtGui.QFont("Segoe UI")
elif platform.system() == 'Darwin':
    CUSTOM_FONT                 = QtGui.QFont(".AppleSystemUIFont", 13)
    CUSTOM_FONT_SMALL           = QtGui.QFont(".AppleSystemUIFont", 11)
    CUSTOM_FONT_MONO            = QtGui.QFont("Monaco", 12)
    CUSTOM_FONT_MONO_LG         = QtGui.QFont("Monaco", 18)
    CUSTOM_FONT_BOLD            = QtGui.QFont("Monaco", 12, QtGui.QFont.Weight.Bold)

    MENU_FONT                   = QtGui.QFont(".AppleSystemUIFont")