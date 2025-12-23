# translatable_strings.py
"""
Centralized translatable strings for DX Pounce on FT8
All strings are defined with QCoreApplication.translate() for Qt Linguist extraction
"""

from PyQt6.QtCore import QCoreApplication

def tr(context, text):
    """Helper function for translations"""
    return QCoreApplication.translate(context, text)


# =============================================================================
# COMMON / GENERAL
# =============================================================================

class CommonStrings:
    """Common strings used across the application"""
    CONTEXT = "Common"

    OK = lambda: tr("Common", "Ok")
    CANCEL = lambda: tr("Common", "Cancel")
    CLOSE = lambda: tr("Common", "Close")
    SAVE = lambda: tr("Common", "Save")
    APPLY = lambda: tr("Common", "Apply")
    CLEAR = lambda: tr("Common", "Clear")
    ERASE = lambda: tr("Common", "Erase")
    START = lambda: tr("Common", "Start")
    STOP = lambda: tr("Common", "Stop")
    SETTINGS = lambda: tr("Common", "Settings")
    REFRESH = lambda: tr("Common", "Refresh")
    REFRESH_NOW = lambda: tr("Common", "Refresh Now")
    SUMMARY = lambda: tr("Common", "Summary")
    YES = lambda: tr("Common", "Yes")
    NO = lambda: tr("Common", "No")


# =============================================================================
# MAIN WINDOW (pounce_gui.pyw)
# =============================================================================

class MainWindowStrings:
    """Strings for main application window"""
    CONTEXT = "MainWindow"

    # Menu items
    FILE_MENU = lambda: tr("MainWindow", "File")
    EDIT_MENU = lambda: tr("MainWindow", "Edit")
    VIEW_MENU = lambda: tr("MainWindow", "View")
    TOOLS_MENU = lambda: tr("MainWindow", "Tools")
    LANGUAGE_MENU = lambda: tr("MainWindow", "Language")
    HELP_MENU = lambda: tr("MainWindow", "Help")

    # Language names
    LANGUAGE_ENGLISH = lambda: tr("MainWindow", "English")
    LANGUAGE_FRENCH = lambda: tr("MainWindow", "Français")
    LANGUAGE_CHINESE = lambda: tr("MainWindow", "中文")

    # Language change notification
    LANGUAGE_CHANGED_TITLE = lambda: tr("MainWindow", "Language Changed")
    LANGUAGE_CHANGED_MESSAGE = lambda: tr("MainWindow", "Please restart the application for the language change to take effect.")

    # Toggle labels
    REPLY_LABEL = lambda: tr("MainWindow", "Reply")
    ALL_LABEL = lambda: tr("MainWindow", "All")
    FILTERS_LABEL = lambda: tr("MainWindow", "Filters")
    GRID_MONITOR_LABEL = lambda: tr("MainWindow", "Grid Monitor")
    ALTERNATE_VIEW_LABEL = lambda: tr("MainWindow", "Alternate View")

    # Status
    STATUS_MONITORING = lambda: tr("MainWindow", "Monitoring")
    STATUS_DECODING = lambda: tr("MainWindow", "Decoding")
    STATUS_TRX = lambda: tr("MainWindow", "TRX")

    # Buttons
    RESTART = lambda: tr("MainWindow", "Restart")

    # Tab widget labels
    WANTED_CALLSIGNS_LABEL = lambda: tr("MainWindow", "Wanted Callsign(s):")
    MONITORED_CALLSIGNS_LABEL = lambda: tr("MainWindow", "Monitored Callsign(s):")
    WANTED_CQ_ZONES_LABEL = lambda: tr("MainWindow", "Wanted CQ Zone(s):")
    MONITORED_CQ_ZONES_LABEL = lambda: tr("MainWindow", "Monitored CQ Zone(s):")
    EXCLUDED_CALLSIGNS_LABEL = lambda: tr("MainWindow", "Excluded Callsign(s):")
    EXCLUDED_CQ_ZONES_LABEL = lambda: tr("MainWindow", "Excluded CQ Zone(s):")

    # Placeholders
    CALLSIGN_PLACEHOLDER = lambda: tr("MainWindow", "Comma-separated list of callsigns")
    CQ_ZONE_PLACEHOLDER = lambda: tr("MainWindow", "Comma-separated list of CQ zones")

    # Table headers (output table)
    HEADER_DATETIME = lambda: tr("MainWindow", "DateTime")
    HEADER_AGE = lambda: tr("MainWindow", "Age")
    HEADER_SNR = lambda: tr("MainWindow", "SNR")
    HEADER_DT = lambda: tr("MainWindow", "DT")
    HEADER_DF = lambda: tr("MainWindow", "DF")
    HEADER_MESSAGE = lambda: tr("MainWindow", "Message")
    HEADER_COUNTRY = lambda: tr("MainWindow", "Country")
    HEADER_LOTW = lambda: tr("MainWindow", "LoTW")
    HEADER_CQ_ZONE = lambda: tr("MainWindow", "CQ")
    HEADER_CONT = lambda: tr("MainWindow", "Cont")
    HEADER_WKB4 = lambda: tr("MainWindow", "WkB4")

    # History table
    WORKED_CALLSIGNS_LABEL = lambda: tr("MainWindow", "Worked Callsigns")
    BAND_LABEL = lambda: tr("MainWindow", "Band")

    # Status messages
    WAITING_DATA_PACKETS = lambda: tr("MainWindow", "Waiting for UDP data packets...")
    NO_CONNECTION = lambda: tr("MainWindow", "No connection")
    CONNECTED = lambda: tr("MainWindow", "Connected")

    # Heartbeat messages
    NO_HEARTBEAT_TIMEOUT = lambda seconds: tr("MainWindow", f"No HeartBeat for more than {seconds} seconds.")
    HEARTBEAT_TIME = lambda time: tr("MainWindow", f"HeartBeat: {time}")
    NO_HEARTBEAT_RECEIVED = lambda: tr("MainWindow", "No HeartBeat received.")

    # Buffer status
    LABEL_BUFFERED = lambda: tr("MainWindow", "Buffered:")
    STATUS_BUFFERED = lambda count: tr("MainWindow", "Buffered:") + f" {count}"
    BUFFERED_PACKETS = lambda count, size: tr("MainWindow", "Buffered:") + f" {count} {size}"

    # Action labels
    GRID_MONITORING_ACTION = lambda: tr("MainWindow", "Grid Monitoring")
    STOP_BUTTON_LABEL = lambda: tr("MainWindow", "Stop all")
    START_MONITORING_LABEL = lambda: tr("MainWindow", "Start Monitoring")
    RESTART_ACTION = lambda: tr("MainWindow", "Restart")

    # Status button labels
    STATUS_MONITORING = lambda: tr("MainWindow", "Monitoring...")
    STATUS_DECODING = lambda: tr("MainWindow", "Decoding...")
    STATUS_TRX = lambda: tr("MainWindow", "Transmitting...")
    STATUS_NOTHING_YET = lambda: tr("MainWindow", "Nothing yet")


# =============================================================================
# SETTINGS DIALOG
# =============================================================================

class SettingsStrings:
    """Strings for Settings Dialog"""
    CONTEXT = "SettingsDialog"

    WINDOW_TITLE = lambda: tr("SettingsDialog", "Settings")

    # Menu items (left sidebar)
    MENU_SERVER = lambda: tr("SettingsDialog", "Server")
    MENU_GENERAL_SETTINGS = lambda: tr("SettingsDialog", "General Settings")
    MENU_OFFSET_UPDATER = lambda: tr("SettingsDialog", "Offset Updater")
    MENU_SOUND_ALERTS = lambda: tr("SettingsDialog", "Sound Alerts")
    MENU_LOTW = lambda: tr("SettingsDialog", "Logbook of The World")
    MENU_DX_MARATHON = lambda: tr("SettingsDialog", "DX Marathon")
    MENU_GRID_TRACKER = lambda: tr("SettingsDialog", "Grid Tracker")
    MENU_PRIORITY_MANAGER = lambda: tr("SettingsDialog", "Priority Manager")
    MENU_LOGBOOK_ANALYSIS = lambda: tr("SettingsDialog", "Logbook Analysis")
    MENU_WORKED_BEFORE = lambda: tr("SettingsDialog", "Worked before")
    MENU_CLUB_LOG = lambda: tr("SettingsDialog", "Club Log")
    MENU_LOGBOOK_BACKUP = lambda: tr("SettingsDialog", "Logbook Backup")
    MENU_DEBUGGING = lambda: tr("SettingsDialog", "Debugging")

    # Server page
    SERVER_NOTICE_JTDX = lambda: tr("SettingsDialog",
        "<p>For JTDX users, you have to disable automatic logging of QSO (Make sure <u>Settings > Reporting > Logging > Enable automatic logging of QSO</u> is unchecked).</p><p>You might also need to accept UDP Reply messages from any messages (<u>Misc Menu > Accept UDP Reply Messages > any messages</u>).</p>"
    )

    GROUP_PRIMARY_UDP = lambda: tr("SettingsDialog", "Main UDP instance (the one set as Primary UDP Server on JTDX)")
    GROUP_SECONDARY_UDP = lambda: tr("SettingsDialog", "Secondary UDP Server (used to forward UDP packets)")
    GROUP_LOGGING_UDP = lambda: tr("SettingsDialog", "UDP instance for external logging program (e.g. Logger32, RUMlogNG)")

    LABEL_UDP_SERVER = lambda: tr("SettingsDialog", "UDP Server:")
    LABEL_UDP_PORT = lambda: tr("SettingsDialog", "UDP Server port number:")

    CHECK_AUTO_START = lambda: tr("SettingsDialog", "Enable auto start monitoring when program launched")
    CHECK_ENABLE_SECONDARY = lambda: tr("SettingsDialog", "Enable forwarding to Secondary UDP Server")
    CHECK_ENABLE_LOGGING = lambda: tr("SettingsDialog", "Enable sending QSO data for logging program")

    # General Settings page
    GENERAL_NOTICE = lambda: tr("SettingsDialog",
        "<p>DX Pounce on FT8 won't trigger a reply unless you enable <u>Enable reply</u> or <u>Enable polite reply</u>.</p><p>If you disable these settings, DX Pounce on FT8 will still run as a monitoring tool with different visual or sound alerts depending on your preference.</p><p>If you enable them, this program will double-click on any of the lines of decoded text in the Band Activity window of your WSJT-X/JTDX instance which match with your preferences.</p>"
    )

    GROUP_GENERAL_SETTINGS = lambda: tr("SettingsDialog", "General DX Pounce on FT8 Settings")
    CHECK_ENABLE_REPLY = lambda: tr("SettingsDialog", "Enable reply")
    CHECK_ENABLE_POLITE_REPLY = lambda: tr("SettingsDialog", "Enable polite reply")
    CHECK_ENABLE_WATCHDOG_BYPASS = lambda: tr("SettingsDialog", "Enable watchdog bypass")
    CHECK_LOG_ALL_VALID = lambda: tr("SettingsDialog", "Log all valid contacts (not only from Wanted)")
    CHECK_IGNORE_INVALID_CALLSIGN = lambda: tr("SettingsDialog", "Ignore callsign if prefix is invalid")
    CHECK_IGNORE_WRONG_CONTINENT = lambda: tr("SettingsDialog", "Ignore callsign if it targets another continent")

    # Offset Updater page
    OFFSET_NOTICE = lambda: tr("SettingsDialog",
        "<p>The frequency offset updater helps to find a free frequency offset from nominal (DF).</p><p>Select one of the pre-defined operating modes from <u>Normal</u>, <u>Fox/Hound</u>, or <u>SuperFox</u>.</p><p>You can also set your own custom frequency range.</p>"
    )

    GROUP_OFFSET_SETTINGS = lambda: tr("SettingsDialog", "Frequency Offset Settings")
    CHECK_ENABLE_GAP_FINDER = lambda: tr("SettingsDialog", "Enable frequencies offset updater")

    GROUP_FREQ_RANGE = lambda: tr("SettingsDialog", "Select range of frequency being used for offset updater")
    LABEL_MIN_FREQUENCY = lambda: tr("SettingsDialog", "Min Frequency")
    LABEL_MAX_FREQUENCY = lambda: tr("SettingsDialog", "Max Frequency")
    LABEL_MODE = lambda: tr("SettingsDialog", "Mode")

    MODE_NORMAL = lambda: tr("SettingsDialog", "Normal")
    MODE_FOX_HOUND = lambda: tr("SettingsDialog", "Fox/Hound")
    MODE_SUPER_FOX = lambda: tr("SettingsDialog", "SuperFox")
    MODE_CUSTOM = lambda: tr("SettingsDialog", "Custom")

    GROUP_CUSTOM_RANGE = lambda: tr("SettingsDialog", "Custom frequency range")
    LABEL_MIN_FREQ = lambda: tr("SettingsDialog", "Min Freq (Hz):")
    LABEL_MAX_FREQ = lambda: tr("SettingsDialog", "Max Freq (Hz):")

    MINIMUM_REPORT_NOTICE = lambda: tr("SettingsDialog",
        "<p>DX Pounce on FT8 won't trigger reply unless decoded message reach a minimal signal report.</p>"
    )
    GROUP_MINIMUM_REPORT = lambda: tr("SettingsDialog", "Minimum dB signal for reply (FT8/FT4 Mode only)")
    LABEL_MINIMUM_REPORT = lambda: tr("SettingsDialog", "Minimum report")

    # Priority Manager
    GROUP_PRIORITY_MANAGER = lambda: tr("SettingsDialog", "Priority Manager")
    PRIORITY_NOTICE = lambda: tr("SettingsDialog",
        "<p>Set the priority order for reply decisions when decoding several potential callsigns for a same period.</p><p>Drag and drop blocks to reorder them. The first row has the highest priority, and the last row refers to the lowest priority.</p>"
    )

    SEQUENCING_NOTICE = lambda: tr("SettingsDialog",
        "<p>When several Wanted callsigns are detected during the same sequence and if program starts to reply to one specific callsign, it has a limited <u>number of attempts</u> before moving on to the next detected callsign.</p><p>The maximum <u>waiting delay</u> is used to halt TX and stop calling a station that the program has started to call but is no longer decoded. However, if another Wanted callsign is detected, this setting has no effect.</p>"
    )

    GROUP_SEQUENCING = lambda: tr("SettingsDialog", "Sequencing")
    LABEL_MAX_ATTEMPTS = lambda: tr("SettingsDialog", "Maximum number of attempts")
    LABEL_TIMES = lambda: tr("SettingsDialog", "times")
    LABEL_MAX_WAITING_DELAY = lambda: tr("SettingsDialog", "Maximum waiting delay")
    LABEL_MINUTES = lambda: tr("SettingsDialog", "minutes")

    HEADER_PRIORITY = lambda: tr("SettingsDialog", "Priority")
    HEADER_REPLY_TO = lambda: tr("SettingsDialog", "Reply to")

    # LoTW Settings
    LOTW_NOTICE = lambda: tr("SettingsDialog",
        "<p>LoTW (Logbook of The World®) is ARRL's online QSO confirmation system.</p><p>Enable it to limit sound alerts and only respond to callsigns who use LoTW especially <u>if you use a Wildcard in your Wanted callsigns</u>.</p><p>DX Pounce on FT8 will always respond to the callsign if it exactly matches a wanted callsign that is not LoTW.</p><p><u>This setting is ignored for Marathon</u> but is used for GridTracker and if you make use of Wildcard.</p>"
    )

    LOTW_CACHE_STATUS = lambda callsigns, last_update: tr("SettingsDialog",
        f"LoTW Cache Status: {callsigns} callsigns<br />Last updated: {last_update}"
    )
    LOTW_NO_DATA = lambda: tr("SettingsDialog", "No LoTW data available yet")

    GROUP_LOTW_SETTINGS = lambda: tr("SettingsDialog", "LoTW Settings")
    CHECK_LOTW_ONLY = lambda: tr("SettingsDialog", "Enable reply only for callsigns that use LoTW")

    # Sound Alerts
    SOUND_NOTICE = lambda: tr("SettingsDialog",
        "<p>You can enable or disable the sounds as per your requirement. You can even set a delay between each sound triggered by a message where a monitored callsign has been found. This mainly helps you to be notified when the band opens or when you have a callsign on the air that you want to monitor.</p><p>Monitored callsigns will never get reply from this program. Only <u>Wanted callsigns will get a reply</u>.</p>"
    )

    GROUP_SOUND_SETTINGS = lambda: tr("SettingsDialog", "Sound Alert Settings")
    LABEL_PLAY_SOUND_WHEN = lambda: tr("SettingsDialog", "Play Sounds when:")
    CHECK_SOUND_WANTED = lambda: tr("SettingsDialog", "Message from any Wanted Callsign")
    CHECK_SOUND_DIRECTED = lambda: tr("SettingsDialog", "Message directed to my Callsign")
    CHECK_SOUND_MONITORED = lambda: tr("SettingsDialog", "Message from any Monitored Callsign")
    LABEL_DELAY_BETWEEN = lambda: tr("SettingsDialog", "Delay between each monitored callsigns detected:")
    LABEL_SECONDS = lambda: tr("SettingsDialog", "seconds")

    # Logbook Analysis
    LOG_ANALYSIS_NOTICE = lambda: tr("SettingsDialog",
        "<p>While using DX Pounce on FT8, you can let this program analyze your working ADIF files from WSJT-x or JTDX.<p><p>DX Pounce on FT8 won't update your ADIF files. Still, it can read, parse and analyse them. You can set several ADIF files, for exemple your main WSJT-X ADIF and a full export of your log.</p>"
    )

    GROUP_FILE_SELECTION = lambda: tr("SettingsDialog", "ADIF Files for log analysis")
    BUTTON_SELECT_ADIF = lambda: tr("SettingsDialog", "Select new ADIF File for analysis")
    HEADER_ADIF_FILES = lambda: tr("SettingsDialog", "ADIF Files for analysis")

    # Worked Before
    WORKED_B4_NOTICE = lambda: tr("SettingsDialog",
        "<p>DX Pounce on FT8, will show the year of the Worked B4 stations you decode.<p><p>You can select from this panel, how the program will behave when it decodes some already worked callsign on the same band.</p>"
    )

    GROUP_WKB4_SETTINGS = lambda: tr("SettingsDialog", "What should we do with Worked B4?")
    RADIO_REPLY_ALWAYS = lambda: tr("SettingsDialog", "Reply to any Wanted Callsign even if Worked B4")
    RADIO_REPLY_CURRENT_YEAR = lambda year: tr("SettingsDialog", f"Reply to Wanted Callsign if not Worked B4 in current year ({year})")
    RADIO_REPLY_NEVER = lambda: tr("SettingsDialog", "Do not reply to any Callsign Worked B4")

    # Marathon
    MARATHON_NOTICE = lambda: tr("SettingsDialog",
        "<p>Marathon feature has to be used with caution.</p><p>DX Pounce on FT8 will analyze your log and check for any missing entities you haven't worked on selected band. If a missing entity is decoded, DX Pounce on FT8 will reply to this callsign.</p><p>Note that rules set for <u>Worked Before</u> will remain in effect.</p>"
    )

    GROUP_MARATHON_SETTINGS = lambda: tr("SettingsDialog", "DX Marathon Settings")
    CHECK_ENABLE_MARATHON = lambda: tr("SettingsDialog", "Enable Marathon mode")
    LABEL_SELECT_BANDS = lambda: tr("SettingsDialog", "Select bands for Marathon:")

    # Grid Tracker
    GRID_TRACKER_NOTICE = lambda: tr("SettingsDialog",
        "<p>Grid Tracker feature monitors for new grids (4 or 6 character Maidenhead) that haven't been worked yet.</p><p>When enabled, the program will reply to stations in grids you haven't worked on the selected bands.</p>"
    )

    GROUP_GRID_TRACKER_SETTINGS = lambda: tr("SettingsDialog", "Grid Tracker Settings")
    CHECK_ENABLE_GRID_TRACKER = lambda: tr("SettingsDialog", "Enable Grid Tracker mode")
    LABEL_SELECT_BANDS_GRID = lambda: tr("SettingsDialog", "Select bands for Grid Tracker:")

    # Club Log
    CLUB_LOG_NOTICE = lambda: tr("SettingsDialog",
        "<p>Club Log is a web service for amateur radio logging and statistics.</p><p>You can enable automatic upload of your QSO data to Club Log.</p>"
    )

    GROUP_CLUB_LOG_SETTINGS = lambda: tr("SettingsDialog", "Club Log Settings")
    CHECK_ENABLE_CLUB_LOG = lambda: tr("SettingsDialog", "Enable automatic upload to Club Log")
    LABEL_CALLSIGN = lambda: tr("SettingsDialog", "Callsign:")
    LABEL_API_KEY = lambda: tr("SettingsDialog", "API Key:")
    BUTTON_TEST_CONNECTION = lambda: tr("SettingsDialog", "Test Connection")

    # Debugging
    DEBUG_NOTICE = lambda: tr("SettingsDialog",
        "<p>Enable debugging options to help troubleshoot issues.</p><p>Warning: These options may generate large log files and affect performance.</p>"
    )

    GROUP_DEBUG_SETTINGS = lambda: tr("SettingsDialog", "Debugging Options")
    CHECK_ENABLE_POUNCE_LOG = lambda: tr("SettingsDialog", "Enable pounce log")
    CHECK_ENABLE_GUI_DEBUG = lambda: tr("SettingsDialog", "Enable extra GUI debug output")
    CHECK_LOG_PACKET_DATA = lambda: tr("SettingsDialog", "Log UDP packet data")


# =============================================================================
# GRID MAP VIEWER
# =============================================================================

class GridMapStrings:
    """Strings for Grid Map Viewer"""
    CONTEXT = "GridMapViewer"

    WINDOW_TITLE = lambda: tr("GridMapViewer", "Grid Monitor")
    WINDOW_TITLE_SUFFIX = lambda: tr("GridMapViewer", "Grid Monitoring")

    # Toggle labels
    TOGGLE_GRID_SQUARE = lambda: tr("GridMapViewer", "Grid square")
    TOGGLE_GRIDS = lambda: tr("GridMapViewer", "Grids")
    TOGGLE_HEATMAP = lambda: tr("GridMapViewer", "Heatmap")
    TOGGLE_WORKED = lambda: tr("GridMapViewer", "Worked")
    TOGGLE_ALL_BANDS = lambda: tr("GridMapViewer", "All bands")
    TOGGLE_GREYLINE = lambda: tr("GridMapViewer", "Greyline")
    TOGGLE_EXCLUDED = lambda: tr("GridMapViewer", "Excluded")

    # Heatmap controls
    LABEL_DENSITY = lambda: tr("GridMapViewer", "Density")
    LABEL_RADIUS = lambda: tr("GridMapViewer", "Radius")
    LABEL_WEIGHT = lambda: tr("GridMapViewer", "Weight")

    # Status bar messages
    STATUS_BAND = lambda band: tr("GridMapViewer", f"Band: <u>{band}</u>")
    STATUS_ALL_BANDS = lambda: tr("GridMapViewer", "All bands")
    STATUS_WORKED = lambda count: tr("GridMapViewer", f"Worked: {count}")
    STATUS_CONFIRMED = lambda count: tr("GridMapViewer", f"Confirmed: {count}")

    # Zoom controls
    ZOOM_IN = lambda: tr("GridMapViewer", "Zoom In")
    ZOOM_OUT = lambda: tr("GridMapViewer", "Zoom Out")
    RESET_VIEW = lambda: tr("GridMapViewer", "Reset View")

    # Keyboard shortcuts help
    SHORTCUTS_HELP = lambda: tr("GridMapViewer",
        "Keyboard Shortcuts:\nG - Toggle Grid\nH - Toggle Heatmap\nW - Toggle Worked\nL - Toggle Night/Day"
    )


# =============================================================================
# ADIF SUMMARY DIALOG
# =============================================================================

class AdifSummaryStrings:
    """Strings for ADIF Summary Dialog"""
    CONTEXT = "AdifSummaryDialog"

    WINDOW_TITLE = lambda: tr("AdifSummaryDialog", "ADIF File Analyzer")
    TITLE_SUCCESS = lambda: tr("AdifSummaryDialog", "ADIF File Parsed Successfully")

    LABEL_FILE_PATH = lambda path: tr("AdifSummaryDialog", f"File: {path}")
    LABEL_PROCESSING_TIME = lambda time: tr("AdifSummaryDialog", f"Total processing time: {time:.4f}s")
    LABEL_UNIQUE_CALLSIGNS = lambda: tr("AdifSummaryDialog", "Unique callsigns per Year and per Band:")

    TOGGLE_SHOW_ALL_BANDS = lambda: tr("AdifSummaryDialog", "Show all bands")

    # Table headers
    HEADER_YEAR = lambda: tr("AdifSummaryDialog", "Year")
    HEADER_TOTAL = lambda: tr("AdifSummaryDialog", "Total")
    LABEL_TOTAL = lambda: tr("AdifSummaryDialog", "Total")


# =============================================================================
# ACTIVE USERS WINDOW
# =============================================================================

class ActiveUsersStrings:
    """Strings for Active Users Window"""
    CONTEXT = "ActiveUsersWindow"

    WINDOW_TITLE = lambda: tr("ActiveUsersWindow", "Active Users")

    # Info labels
    INFO_LOADING = lambda: tr("ActiveUsersWindow", "Loading active users...")
    INFO_ACTIVE_USERS = lambda count: tr("ActiveUsersWindow", f"Active users: {count} (refreshing every 5 seconds)")
    INFO_FAILED = lambda: tr("ActiveUsersWindow", "Failed to fetch active users. Retrying...")
    INFO_ERROR = lambda error: tr("ActiveUsersWindow", f"Error: {error}")

    # Table headers
    HEADER_CALLSIGN = lambda: tr("ActiveUsersWindow", "Callsign")
    HEADER_LAST_HEARTBEAT = lambda: tr("ActiveUsersWindow", "Last Heartbeat")
    HEADER_GRID = lambda: tr("ActiveUsersWindow", "Grid")
    HEADER_BAND = lambda: tr("ActiveUsersWindow", "Band")
    HEADER_VERSION = lambda: tr("ActiveUsersWindow", "Version")
    HEADER_OS = lambda: tr("ActiveUsersWindow", "OS")


# =============================================================================
# CONTEXT MENU
# =============================================================================

class ContextMenuStrings:
    """Strings for context menus"""
    CONTEXT = "ContextMenu"

    COPY = lambda: tr("ContextMenu", "Copy")
    COPY_CALLSIGN = lambda: tr("ContextMenu", "Copy Callsign")
    COPY_GRID = lambda: tr("ContextMenu", "Copy Grid")
    COPY_MESSAGE = lambda: tr("ContextMenu", "Copy Message")

    ADD_TO_WANTED = lambda: tr("ContextMenu", "Add to Wanted")
    ADD_TO_MONITORED = lambda: tr("ContextMenu", "Add to Monitored")
    ADD_TO_EXCLUDED = lambda: tr("ContextMenu", "Add to Excluded")

    REMOVE_FROM_WANTED = lambda: tr("ContextMenu", "Remove from Wanted")
    REMOVE_FROM_MONITORED = lambda: tr("ContextMenu", "Remove from Monitored")
    REMOVE_FROM_EXCLUDED = lambda: tr("ContextMenu", "Remove from Excluded")

    LOOKUP_QRZ = lambda: tr("ContextMenu", "Lookup on QRZ.com")
    LOOKUP_QRZCQ = lambda: tr("ContextMenu", "Lookup on QRZCQ.com")
    LOOKUP_HAMQTH = lambda: tr("ContextMenu", "Lookup on HamQTH.com")


# =============================================================================
# ERROR MESSAGES
# =============================================================================

class ErrorStrings:
    """Error messages"""
    CONTEXT = "Errors"

    CONNECTION_FAILED = lambda: tr("Errors", "Connection failed")
    FILE_NOT_FOUND = lambda file: tr("Errors", f"File not found: {file}")
    INVALID_FORMAT = lambda: tr("Errors", "Invalid format")
    PARSE_ERROR = lambda: tr("Errors", "Parse error")
    NETWORK_ERROR = lambda: tr("Errors", "Network error")
    PERMISSION_DENIED = lambda: tr("Errors", "Permission denied")
    TIMEOUT = lambda: tr("Errors", "Operation timed out")


# =============================================================================
# TIME FORMATS
# =============================================================================

class TimeStrings:
    """Time-related strings"""
    CONTEXT = "Time"

    JUST_NOW = lambda: tr("Time", "just now")
    SECONDS_AGO = lambda n: tr("Time", f"{n}s ago")
    MINUTES_AGO = lambda n: tr("Time", f"{n}m ago")
    HOURS_AGO = lambda n: tr("Time", f"{n}h ago")
    DAYS_AGO = lambda n: tr("Time", f"{n}d ago")
