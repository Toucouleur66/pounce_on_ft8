# constants.py
version_number          = 2.0

EVEN                            = 'EVEN'
ODD                             = 'ODD'

EVEN_COLOR                      = "#9dfffe"
ODD_COLOR                       = "#fffe9f"

BG_COLOR_FOCUS_MY_CALL          = "#80d0d0"
FG_COLOR_FOCUS_MY_CALL          = "#000000"

BG_COLOR_REGULAR_FOCUS          = "#000000"
FG_COLOR_REGULAR_FOCUS          = "#01ffff"

PARAMS_FILE                     = "params.pkl"
POSITION_FILE                   = "window_position.pkl"
WANTED_CALLSIGNS_FILE           = "wanted_callsigns.pkl"
WANTED_CALLSIGNS_HISTORY_SIZE   = 50

GUI_LABEL_VERSION               = f"Wait and Pounce v{version_number} by F5UKW"
RUNNING_TEXT_BUTTON             = "Running..."
WAIT_POUNCE_LABEL               = "Listen UDP Packets & Pounce"
NOTHING_YET                     = "Nothing yet"
WAITING_DATA_PACKETS_LABEL      = "Waiting for UDP Packets"
WANTED_CALLSIGNS_HISTORY_LABEL  = "Wanted Callsigns History (%d):"

MODE_NORMAL                     = "Normal"
MODE_FOX_HOUND                  = "Fox/Hound"
MODE_SUPER_FOX                  = "SuperFox"

FREQ_MINIMUM                    = 200
FREQ_MAXIMUM                    = 2900
FREQ_MINIMUM_FOX_HOUND          = 1050

DEFAULT_UDP_PORT                = 2237