# constants.py
from PyQt6 import QtGui, QtWidgets

import os
import platform

from datetime import datetime
from utils import get_app_data_dir

CURRENT_VERSION_NUMBER          = "2.16"
EXPIRATION_DATE                 = datetime(2026, 12, 15)
UPDATE_JSON_INFO_URL            = "https://storage.de.cloud.ovh.net/v1/AUTH_31163bb499dc49eb819aacdfd32ae82c/wait.and.pounce/public/update_info.json"

README_URL                      = "https://storage.de.cloud.ovh.net/v1/AUTH_31163bb499dc49eb819aacdfd32ae82c/wait.and.pounce/public/readme.txt"

EVEN                            = "EVEN"
ODD                             = "ODD"

MASTER                          = "Master"
SLAVE                           = "Slave"

SAVED_VERSION_FILE              = os.path.join(get_app_data_dir(), "app_version.json")
MARATHON_FILE                   = os.path.join(get_app_data_dir(), "marathon.json")
PARAMS_FILE                     = os.path.join(get_app_data_dir(), "params.json")
PARAMS_FILE_LEGACY              = os.path.join(get_app_data_dir(), "params.pkl")
POSITION_FILE                   = os.path.join(get_app_data_dir(), "window_position.json")
WORKED_CALLSIGNS_FILE           = os.path.join(get_app_data_dir(), "worked_callsigns.pkl")
TEMP_EXCLUDED_CALLSIGNS_FILE    = os.path.join(get_app_data_dir(), "temp_excluded_callsigns.pkl")
ADIF_WORKED_CALLSIGNS_FILE      = os.path.join(get_app_data_dir(), "wait_pounce_log.adif")
CLUB_LOG_CACHE_FILE                    = os.path.join(get_app_data_dir(), "club_log_cache.json")

GUI_LABEL_NAME                  = "Wait and Pounce"
GUI_LABEL_VERSION               = f"{GUI_LABEL_NAME} build {CURRENT_VERSION_NUMBER}"

CLUB_LOG_API_KEY                = "efc2af7050308f03a22275cf51f3fd7749582d66"

STATUS_BUTTON_LABEL_MONITORING  = "Monitoring..."
STATUS_BUTTON_LABEL_DECODING    = "Decoding..."
STATUS_BUTTON_LABEL_TRX         = "Transmitting..."
STATUS_BUTTON_LABEL_START       = "Start Monitoring"
STATUS_BUTTON_LABEL_NOTHING_YET = "Nothing yet"

ACTION_RESTART                  = "Restart"

STOP_BUTTON_LABEL               = "Stop all"

DATE_COLUMN_DATETIME            = "Time"
DATE_COLUMN_AGE                 = "Age"

THEME_MODE_LIGHT                = "Light"
THEME_MODE_DARK                 = "Dark"
THEME_MODE_SYSTEM               = "System"

LOTW_SYMBOL                     = "•"
QSL_RCVD_SYMBOL                 = "✓"
WKB4_YEAR_SYMBOL                = "★"

WAITING_DATA_PACKETS_LABEL      = "Waiting for UDP Packets"
WORKED_CALLSIGNS_HISTORY_LABEL  = "Worked Callsigns"
CALLSIGN_NOTICE_LABEL           = "Comma-separated list of callsigns (or prefixes). Allows wildcards with *"
CQ_ZONE_NOTICE_LABEL            = "Comma separated list of CQ Zone"

MODE_NORMAL                     = "Regular"
MODE_FOX_HOUND                  = "Hound"
MODE_SUPER_FOX                  = "SuperFox"
MODE_CUSTOM                     = "Custom"

MARATHON_UNLIMITED              = "Unlimited"

WKB4_REPLY_MODE_ALWAYS          = "always"
WKB4_REPLY_MODE_CURRENT_YEAR    = "current_year"
WKB4_REPLY_MODE_NEVER           = "never"

def convert_wkb4_reply_mode(value):
    """
        Convert old integer WKB4 reply mode values to new string values for backward compatibility
    """
    if isinstance(value, int):
        if value == 1:
            return WKB4_REPLY_MODE_ALWAYS
        elif value == 2:
            return WKB4_REPLY_MODE_CURRENT_YEAR
        elif value == 3:
            return WKB4_REPLY_MODE_NEVER
        else:
            return WKB4_REPLY_MODE_ALWAYS  # fallback
    return value  # assume it's already a string

DEFAULT_MODE_TIMER_VALUE        = "--:--:--"

FREQ_MINIMUM                    = 200
FREQ_MAXIMUM                    = 2900
FREQ_MINIMUM_FOX_HOUND          = 1050
FREQ_MAXIMUM_SUPER_FOX          = 3200

DEFAULT_UDP_PORT                = 2237

ACTIVITY_BAR_MAX_VALUE          = 50

HEARTBEAT_TIMEOUT_THRESHOLD     = 30
DECODE_PACKET_TIMEOUT_THRESHOLD = 60
WAITING_TIME_BEFORE_REPLY       = 200 / 1_000 # = 200ms (0,2s)
MAXIMUM_ALLOWED_DT              = 1.9

CURRENT_DIR                     = os.path.dirname(os.path.realpath(__file__))
CTY_XML                         = 'cty.xml'
CTY_XML_URL                     = f'https://cdn.clublog.org/cty.php?api={CLUB_LOG_API_KEY}'
CTY_WT_MOD_URL                  = 'https://www.country-files.com/cty/cty_wt_mod.dat'     

DEFAULT_SECONDARY_UDP_SERVER    = False
DEFAULT_AUTO_START_MONITORING   = False
DEFAULT_SENDING_REPLY           = True
DEFAULT_POLITE_REPLY            = False
DEFAULT_GAP_FINDER              = True
DEFAULT_WATCHDOG_BYPASS         = False
DEFAULT_DEBUG_OUTPUT            = False
DEFAULT_POUNCE_LOG              = True
DEFAULT_LOG_PACKET_DATA         = False
DEFAULT_SHOW_ALL_DECODED        = False
DEFAULT_LOG_ALL_VALID_CONTACT   = True
DEFAULT_DELAY_BETWEEN_SOUND     = 120
DEFAULT_MAX_WAITING_DELAY       = 2 # minutes
DEFAULT_REPLY_ATTEMPTS          = 10
DEFAULT_MINIMUM_REPORT          = -25
BAND_CHANGE_WAITING_DELAY       = 10

DEFAULT_SELECTED_BAND           = "6m"
DEFAULT_FILTER_VALUE            = "All"

PRIORITY_LIST                   = {
    "Wanted Callsign(s)"        : "wanted",
    "Wanted CQ Zone(s)"         : "wanted_cq_zone",
    "Marathon"                  : "marathon",
    "New Grid"                  : "wanted_grid",        
    "Politeness reply"          : "polite_reply",
}

DISCORD_SECTION                 = '<a href="https://discord.gg/fqCu24naCM">Support available on Discord</a>'
DONATION_URL                    = "https://www.paypal.com/donate/?cmd=_s-xclick&hosted_button_id=R4HK9ZTUPYHSL&ssrt=1732865689562"
DONATION_SECTION                = f'<a href="{DONATION_URL}">Donations are welcome</a>'

if platform.system() == 'Windows':
    app = QtWidgets.QApplication([])

    screen                      = app.primaryScreen()
    dpi_scaling                 = screen.logicalDotsPerInch() / 96
    base_size                   = int(10 * dpi_scaling)
    small_size                  = int(9 * dpi_scaling)

    system_default_font         = QtWidgets.QApplication.font()
    CUSTOM_FONT                 = system_default_font
    CUSTOM_FONT_SMALL           = QtGui.QFont(CUSTOM_FONT)
    
    CUSTOM_FONT.setPointSize(base_size)
    CUSTOM_FONT_SMALL.setPointSize(small_size)

    CUSTOM_FONT_MONO            = QtGui.QFont("Consolas", 10)
    CUSTOM_FONT_MONO_LG         = QtGui.QFont("Consolas", 16)
    CUSTOM_FONT_BOLD            = QtGui.QFont("Consolas", 13, QtGui.QFont.Weight.Bold)

    CUSTOM_FONT_README          = QtGui.QFont("Consolas", 11)

    MENU_FONT                   = QtGui.QFont("Segoe UI")
elif platform.system() == 'Darwin':
    CUSTOM_FONT                 = QtGui.QFont(".AppleSystemUIFont", 13)
    CUSTOM_FONT_SMALL           = QtGui.QFont(".AppleSystemUIFont", 11)
    CUSTOM_FONT_MONO            = QtGui.QFont("Monaco", 12)
    CUSTOM_FONT_MONO_LG         = QtGui.QFont("Monaco", 18)
    CUSTOM_FONT_BOLD            = QtGui.QFont("Monaco", 12, QtGui.QFont.Weight.Bold)

    CUSTOM_FONT_README          = QtGui.QFont("Menlo", 13)

    MENU_FONT                   = QtGui.QFont(".AppleSystemUIFont")