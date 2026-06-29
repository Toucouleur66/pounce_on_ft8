from PyQt6.QtCore import QCoreApplication

def tr(context, text):
    """Helper function for translations"""
    return QCoreApplication.translate(context, text)

# COMMON / GENERAL
class CommonStrings:
    CONTEXT = "Common"
    OK = lambda: tr("Common", "Ok")
    CANCEL = lambda: tr("Common", "Cancel")
    CLOSE = lambda: tr("Common", "Close")
    QUIT = lambda: tr("Common", "Quit")
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


# MAIN WINDOW (pounce_gui.pyw)
class MainWindowStrings:
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
    LANGUAGE_JAPANESE = lambda: tr("MainWindow", "日本語")
    LANGUAGE_UKRAINIAN = lambda: tr("MainWindow", "Українська")
    # Language change notification
    LANGUAGE_CHANGED_TITLE = lambda: tr("MainWindow", "Language Changed")
    LANGUAGE_CHANGED_MESSAGE = lambda: tr("MainWindow", "You are about to change the language, application will restart to take effect.")
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
    CALLSIGN_PLACEHOLDER = lambda: tr("MainWindow", "Callsign list separated by uppercase commas")
    CQ_ZONE_PLACEHOLDER = lambda: tr("MainWindow", "CQ zones list separated by uppercase commas")
    # Table headers (output table)
    HEADER_DATETIME = lambda: tr("MainWindow", "DateTime")
    HEADER_TIME = lambda: tr("MainWindow", "Time") + " ⇥"
    HEADER_AGE = lambda: tr("MainWindow", "Age") + " ⇤"
    HEADER_TIME_TOGGLE_TOOLTIP = lambda: tr("MainWindow", "Click to toggle between Time and Age")
    # Time display mode labels
    SHOW_TIME_ACTION = lambda: tr("MainWindow", "Show Time")
    SHOW_AGE_ACTION = lambda: tr("MainWindow", "Show Age")
    FORMAT_TIME_MENU = lambda: tr("MainWindow", "Format Time")
    # Filter field labels
    FILTER_CALLSIGN = lambda: tr("MainWindow", "Callsign")
    FILTER_BAND = lambda: tr("MainWindow", "Band")
    FILTER_COLOR = lambda: tr("MainWindow", "Color")
    FILTER_ZONE = lambda: tr("MainWindow", "Zone")
    FILTER_CONTINENT = lambda: tr("MainWindow", "Continent")
    FILTER_COUNTRY = lambda: tr("MainWindow", "Country")
    FILTER_ALL = lambda: tr("MainWindow", "All")
    # Table headers (raw data table)
    HEADER_SNR = lambda: tr("MainWindow", "SNR")
    HEADER_DT = lambda: tr("MainWindow", "DT")
    HEADER_DF = lambda: tr("MainWindow", "DF")
    HEADER_FREQ = lambda: tr("MainWindow", "Freq")
    HEADER_REPORT = lambda: tr("MainWindow", "Report")
    HEADER_MESSAGE = lambda: tr("MainWindow", "Message")
    HEADER_COUNTRY = lambda: tr("MainWindow", "Country")
    HEADER_LOTW = lambda: tr("MainWindow", "LoTW")
    HEADER_CQ_ZONE = lambda: tr("MainWindow", "CQ Zone")
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
    LABEL_HEARTBEAT = lambda: tr("MainWindow", "HeartBeat:")
    NO_HEARTBEAT_TIMEOUT = lambda seconds: tr("MainWindow", f"No HeartBeat for more than {seconds} seconds.")
    HEARTBEAT_TIME = lambda time: tr("MainWindow", "HeartBeat:") + f" {time}"
    NO_HEARTBEAT_RECEIVED = lambda: tr("MainWindow", "No HeartBeat received.")
    # Buffer status
    LABEL_BUFFERED = lambda: tr("MainWindow", "Buffered:")
    STATUS_BUFFERED = lambda count: tr("MainWindow", "Buffered:") + f" {count}"
    BUFFERED_PACKETS = lambda count, size: tr("MainWindow", "Buffered:") + f" {count} {size}"

    # Status bar labels
    STATUS_MODE = lambda mode: tr("MainWindow", "Mode:") + f" {mode}"
    STATUS_FREQ = lambda freq: tr("MainWindow", "Freq:") + f" <u>{freq}</u>"
    STATUS_LAST_DECODED = lambda time: tr("MainWindow", "Last decoded: %s ago").replace("%s", str(time))
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

    # Menu actions
    CHECK_FOR_UPDATES = lambda: tr("MainWindow", "Check for Updates...")
    SUPPORT_APP = lambda: tr("MainWindow", "⭐️ Donate and support us")
    DISCORD_SERVER = lambda app_name: tr("MainWindow", "Discord Server for %1").replace("%1", str(app_name))
    UPDATE_DXCC_INFO = lambda: tr("MainWindow", "Update DXCC Info")
    UPDATE_LOTW_INFO = lambda: tr("MainWindow", "Update LoTW Info")
    SHOW_LOTW_QSLS = lambda: tr("MainWindow", "Show LoTW QSLs received")
    UPDATE_COUNTRY_FILES = lambda: tr("MainWindow", "Update country and region files")
    COMPACT_VIEW = lambda: tr("MainWindow", "Compact View")
    ALWAYS_ON_TOP = lambda: tr("MainWindow", "Always on Top")
    SHOW_ALL_MESSAGES = lambda: tr("MainWindow", "Show All Messages")
    SHOW_FILTERS = lambda: tr("MainWindow", "Show Filters")
    CLEAR_FILTERS = lambda: tr("MainWindow", "Clear Filters")
    CLEAR_ROWS_FROM_TABLE = lambda: tr("MainWindow", "Clear rows from Table")
    THEME_MENU = lambda: tr("MainWindow", "Theme")
    LIGHT_THEME = lambda: tr("MainWindow", "Light")
    DARK_THEME = lambda: tr("MainWindow", "Dark")
    SYSTEM_THEME = lambda: tr("MainWindow", "System")
    CLEAR_WORKED_HISTORY = lambda: tr("MainWindow", "Clear Worked Callsigns History")


# SETTINGS DIALOG
class SettingsStrings:
    CONTEXT = "SettingsDialog"
    WINDOW_TITLE = lambda: tr("SettingsDialog", "Settings")
    # Menu items (left sidebar)
    MENU_SERVER = lambda: tr("SettingsDialog", "Server")
    MENU_GENERAL_SETTINGS = lambda: tr("SettingsDialog", "General Settings")
    MENU_WATCHDOG_RETRY = lambda: tr("SettingsDialog", "Watchdog and retry")
    MENU_OFFSET_UPDATER = lambda: tr("SettingsDialog", "Offset Updater")
    MENU_SOUND_ALERTS = lambda: tr("SettingsDialog", "Sound Alerts")
    MENU_LOTW = lambda: tr("SettingsDialog", "Logbook of The World")
    MENU_DX_MARATHON = lambda: tr("SettingsDialog", "DX Marathon")
    MENU_DXCC_PROGRAM = lambda: tr("SettingsDialog", "DXCC Program")
    MENU_GRID_TRACKER = lambda: tr("SettingsDialog", "Grid Tracker")
    MENU_PRIORITY_MANAGER = lambda: tr("SettingsDialog", "Priority Manager")
    MENU_LOGBOOK_ANALYSIS = lambda: tr("SettingsDialog", "Logbook Analysis")
    MENU_WORKED_BEFORE = lambda: tr("SettingsDialog", "Worked before")
    MENU_CLUB_LOG = lambda: tr("SettingsDialog", "Club Log")
    MENU_LOGBOOK_BACKUP = lambda: tr("SettingsDialog", "Logbook Backup")
    MENU_AUTOMATE_TASKS = lambda: tr("SettingsDialog", "Automate tasks")
    MENU_PSTROTATOR = lambda: tr("SettingsDialog", "Antenna Rotator")
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
        "<p>Wait and Pounce won't trigger a reply unless you enable <u>Enable reply</u> or <u>Enable polite reply</u>.</p><p>If you disable these settings, Wait and Pounce will still run as a monitoring tool with different visual or sound alerts depending on your preference.</p><p>If you enable them, this program will double-click on any of the lines of decoded text in the Band Activity window of your WSJT-X/JTDX instance which match with your preferences.</p>"
    )
    GROUP_GENERAL_SETTINGS = lambda: tr("SettingsDialog", "General Wait and Pounce Settings")
    CHECK_ENABLE_REPLY = lambda: tr("SettingsDialog", "Enable reply")
    CHECK_ENABLE_POLITE_REPLY = lambda: tr("SettingsDialog", "Enable polite reply")
    CHECK_LOG_ALL_VALID = lambda: tr("SettingsDialog", "Log all valid contacts (not only from Wanted)")
    CHECK_IGNORE_INVALID_CALLSIGN = lambda: tr("SettingsDialog", "Ignore callsign if prefix is invalid")
    CHECK_IGNORE_WRONG_CONTINENT = lambda: tr("SettingsDialog", "Ignore callsign if it targets another continent")
    # Watchdog and retry page
    WATCHDOG_NOTICE = lambda: tr("SettingsDialog",
        "<p>Wait and Pounce can prevent you from calling indefinitely, unlike the Watchdog function of traditional tools. If you activate the Watchdog function, you can determine the number of times Wait and Pounce will reply to make QSO.</p><p>If it fails, Wait and Pounce will retry after a specified time.</p><p>If the wanted callsign reply within this interval, Wait and Pounce will complete the QSO, overiding watchdog timer set in your JTDX/WSJT-X instance.</p>"
    )
    GROUP_WATCHDOG_RETRY = lambda: tr("SettingsDialog", "Watchdog and retry Settings")
    CHECK_ENABLE_WATCHDOG = lambda: tr("SettingsDialog", "Enable Watchdog")
    LABEL_WATCHDOG_NUMBER_OF_ATTEMPTS = lambda: tr("SettingsDialog", "Number of attempts")
    LABEL_WATCHDOG_RETRY_TIME = lambda: tr("SettingsDialog", "Wait time")
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
        "<p>Wait and Pounce won't trigger reply unless decoded message reach a minimal signal report.</p>"
    )
    GROUP_MINIMUM_REPORT = lambda: tr("SettingsDialog", "Minimum dB signal for reply (FT8/FT4 Mode only)")
    LABEL_MINIMUM_REPORT = lambda: tr("SettingsDialog", "Minimum report")
    # Priority Manager
    GROUP_PRIORITY_MANAGER = lambda: tr("SettingsDialog", "Priority Manager Settings")
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
        "<p>LoTW (Logbook of The World®) is ARRL's online QSO confirmation system.</p><p>Enable it to limit sound alerts and only respond to callsigns who use LoTW especially <u>if you use a Wildcard in your Wanted callsigns</u>.</p><p>Wait and Pounce will always respond to the callsign if it exactly matches a wanted callsign that is not LoTW.</p><p><u>This setting is ignored for Marathon</u> but is used for GridTracker and if you make use of Wildcard.</p>"
    )
    LOTW_CACHE_STATUS = lambda callsigns, last_update: tr("SettingsDialog",
        f"LoTW Cache Status: {callsigns} callsigns<br />Last updated: {last_update}"
    )
    LOTW_NO_DATA = lambda: tr("SettingsDialog", "No LoTW data available yet")
    GROUP_LOTW_SETTINGS = lambda: tr("SettingsDialog", "LoTW Settings")
    CHECK_LOTW_ONLY = lambda: tr("SettingsDialog", "Enable reply only for callsigns that use LoTW")
    # LoTW Upload/Download
    GROUP_LOTW_UPLOAD_SETTINGS = lambda: tr("SettingsDialog", "LoTW Upload/Download Settings")
    CHECK_ENABLE_LOTW_SYNCH = lambda: tr("SettingsDialog", "Enable automatic synch to LoTW")
    LABEL_LOTW_USERNAME = lambda: tr("SettingsDialog", "Username:")
    LABEL_LOTW_PASSWORD = lambda: tr("SettingsDialog", "Password:")
    LABEL_LOTW_LOCATION = lambda: tr("SettingsDialog", "Station Location:")
    LABEL_LOTW_SIGNING_PASSWORD = lambda: tr("SettingsDialog", "Signing Password:")
    LABEL_LOTW_QSO_SINCE_DATE = lambda: tr("SettingsDialog", "Download QSLs since (UTC):")
    LABEL_LOTW_DOWNLOAD_INTERVAL = lambda: tr("SettingsDialog", "Download interval (minutes):")
    LABEL_TQSL_PATH = lambda: tr("SettingsDialog", "TQSL Path:")
    LABEL_TQSL_DIR = lambda: tr("SettingsDialog", ".tqsl Folder:")
    BUTTON_BROWSE_TQSL = lambda: tr("SettingsDialog", "Browse...")
    BUTTON_BROWSE_TQSL_DIR = lambda: tr("SettingsDialog", "Browse...")
    BUTTON_TEST_LOTW_UPLOAD = lambda: tr("SettingsDialog", "Test Upload Last QSO")
    BUTTON_TEST_LOTW_DOWNLOAD = lambda: tr("SettingsDialog", "Test Download QSLs")
    PLACEHOLDER_LOTW_USERNAME = lambda: tr("SettingsDialog", "Your LoTW username (usually callsign)")
    PLACEHOLDER_LOTW_PASSWORD = lambda: tr("SettingsDialog", "Your LoTW account password")
    PLACEHOLDER_LOTW_LOCATION = lambda: tr("SettingsDialog", "Station location name in TQSL")
    PLACEHOLDER_LOTW_SIGNING_PASSWORD = lambda: tr("SettingsDialog", "Certificate signing password (if set)")
    LOTW_UPLOAD_STATUS = lambda total, last_upload, callsign, band: (
        tr("SettingsDialog", "LoTW Upload Status:") + f" {total} " + tr("SettingsDialog", "QSOs uploaded") + f"<br />" +
        tr("SettingsDialog", "Last upload:") + f" {last_upload}<br />" +
        tr("SettingsDialog", "Last QSO:") + f" {callsign} " + tr("SettingsDialog", "on") + f" {band}"
    )
    LOTW_NO_UPLOADS = lambda: tr("SettingsDialog", "No uploads yet")
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
        "<p>While using Wait and Pounce, you can let this program analyze your working ADIF files from WSJT-x or JTDX.<p><p>Wait and Pounce won't update your ADIF files. Still, it can read, parse and analyse them. You can set several ADIF files, for exemple your main WSJT-X ADIF and a full export of your log.</p>"
    )
    GROUP_FILE_SELECTION = lambda: tr("SettingsDialog", "ADIF Files for log analysis")
    BUTTON_SELECT_ADIF = lambda: tr("SettingsDialog", "Select new ADIF File for analysis")
    HEADER_ADIF_FILES = lambda: tr("SettingsDialog", "ADIF Files for analysis")
    # Worked Before
    WORKED_B4_NOTICE = lambda: tr("SettingsDialog",
        "<p>Wait and Pounce, will show the year of the Worked B4 stations you decode.<p><p>You can select from this panel, how the program will behave when it decodes some already worked callsign on the same band.</p>"
    )
    GROUP_WKB4_SETTINGS = lambda: tr("SettingsDialog", "What should we do with Worked B4?")
    RADIO_REPLY_ALWAYS = lambda: tr("SettingsDialog", "Reply to any Wanted Callsign even if Worked B4")
    RADIO_REPLY_CURRENT_YEAR = lambda year: tr("SettingsDialog", "Reply to Wanted Callsign if not Worked B4 in current year") + f" ({year})"
    RADIO_REPLY_NEVER = lambda: tr("SettingsDialog", "Do not reply to any Callsign Worked B4")
    # Marathon
    MARATHON_NOTICE = lambda: tr("SettingsDialog",
        "<p>Marathon feature has to be used with caution.</p><p>Wait and Pounce will analyze your log and check for any missing entities you haven't worked on selected band. If a missing entity is decoded, Wait and Pounce will reply to this callsign.</p><p>Note that rules set for <u>Worked Before</u> will remain in effect.</p>"
    )
    GROUP_MARATHON_SETTINGS = lambda: tr("SettingsDialog", "Enable Marathon for selected bands")
    CHECK_ENABLE_MARATHON = lambda: tr("SettingsDialog", "Enable Marathon mode")
    LABEL_SELECT_BANDS = lambda: tr("SettingsDialog", "Select bands for Marathon:")
    # DXCC Program
    DXCC_NOTICE = lambda: tr("SettingsDialog",
        "<p>DXCC Program tracks DXCC entities you have not worked on the selected bands (all-time, regardless of year).</p><p>When a new DXCC is decoded, Wait and Pounce will reply to this callsign. If you keep working stations from the same DXCC until it is confirmed, enable the option below.</p><p>Enable <u>Unlimited</u> to chase any DXCC not yet worked on any band.</p>"
    )
    GROUP_DXCC_SETTINGS = lambda: tr("SettingsDialog", "Enable DXCC Program for selected bands")
    CHECK_ENABLE_DXCC_UNCONFIRMED = lambda: tr("SettingsDialog", "Keep replying to an entity until it is confirmed (QSL)")
    # Grid Tracker
    GRID_TRACKER_NOTICE = lambda: tr("SettingsDialog",
        "<p>Grid Tracker feature monitors for new grids (4 or 6 character Maidenhead) that haven't been worked yet.</p><p>When enabled, the program will reply to stations in grids you haven't worked on the selected bands.</p>"
    )
    GRID_TRACKER_PER_BAND_NOTICE = lambda: tr("SettingsDialog",
        "<p>Select band for which Wait and Pounce will reply to callsign, if callsign is a new grid for the selected band.</p>"
    )
    GROUP_GRID_TRACKER_SETTINGS = lambda: tr("SettingsDialog", "Select bands for Grid Tracker")
    CHECK_ENABLE_GRID_TRACKER = lambda: tr("SettingsDialog", "Reply to callsign if grid not yet confirmed and not worked before")
    CHECK_ENABLE_GRID_TRACKER_NEW_GRID = lambda: tr("SettingsDialog", "Enable grid tracker to reply to callsign if new grid regardless of band")
    LABEL_SELECT_BANDS_GRID = lambda: tr("SettingsDialog", "Select bands for Grid Tracker:")
    # Club Log
    CLUB_LOG_NOTICE = lambda: tr("SettingsDialog",
        "<p>Club Log is a web service for amateur radio logging and statistics.</p><p>You can enable automatic upload of your QSO data to Club Log.</p><p>Use your registered email, an Application Password and your own API key (create them in your Club Log account settings).</p>"
    )
    GROUP_CLUB_LOG_SETTINGS = lambda: tr("SettingsDialog", "Club Log Settings")
    CHECK_ENABLE_CLUB_LOG = lambda: tr("SettingsDialog", "Enable automatic upload to Club Log")
    LABEL_CALLSIGN = lambda: tr("SettingsDialog", "Callsign:")
    LABEL_EMAIL = lambda: tr("SettingsDialog", "Email:")
    LABEL_PASSWORD = lambda: tr("SettingsDialog", "Password:")
    LABEL_API_KEY = lambda: tr("SettingsDialog", "API Key:")
    BUTTON_TEST_CONNECTION = lambda: tr("SettingsDialog", "Test Connection")
    BUTTON_TEST_CLUB_LOG_UPLOAD = lambda: tr("SettingsDialog", "Test Upload Last QSO")
    PLACEHOLDER_EMAIL = lambda: tr("SettingsDialog", "Registered email address in Club Log")
    PLACEHOLDER_PASSWORD = lambda: tr("SettingsDialog", "Application password")
    PLACEHOLDER_CALLSIGN = lambda: tr("SettingsDialog", "Your callsign")
    PLACEHOLDER_CLUB_LOG_API_KEY = lambda: tr("SettingsDialog", "Your Club Log API key")
    CLUB_LOG_STATUS = lambda total, last_sync, callsign, band: (
        tr("SettingsDialog", "Club Log Status:") + f" {total} " + tr("SettingsDialog", "QSOs uploaded") + f"<br />" +
        tr("SettingsDialog", "Last upload:") + f" {last_sync}<br />" +
        tr("SettingsDialog", "Last QSO:") + f" {callsign} " + tr("SettingsDialog", "on") + f" {band}"
    )
    CLUB_LOG_NO_UPLOADS = lambda: tr("SettingsDialog", "No Club Log uploads yet")
    # Logbook Backup
    BACKUP_NOTICE = lambda: tr("SettingsDialog",
        "<p>Wait and Pounce will write a new entry on a dedicated and specific ADIF File for each logged QSO.</p><p>This file can be used as a backup of your main logging sequence with JTDX or WSJT-x.</p><p>This log will always be analyzed even if you have an empty list of ADIF files for logbook analysis.</p>"
    )
    GROUP_BACKUP_FILE = lambda: tr("SettingsDialog", "Wait and Pounce Backup File")
    CHECK_SAVE_LOG = lambda: tr("SettingsDialog", "Save debugging to log") 
    BUTTON_OPEN_LOG_FOLDER = lambda: tr("SettingsDialog", "Open log folder")
    BUTTON_SELECT_BACKUP = lambda: tr("SettingsDialog", "Select Backup File")
    BACKUP_STATUS_NO_FILE = lambda: tr("SettingsDialog", "<p>Backup File Status: No file selected</p>")
    BACKUP_STATUS_READY = lambda status, total, unique, first, last: (
        tr("SettingsDialog", "Backup File Status:") + f" {status}<br />" +
        tr("SettingsDialog", "Total Entries:") + f" {total:,}<br />" +
        tr("SettingsDialog", "Unique Callsigns:") + f" {unique:,}<br />" +
        tr("SettingsDialog", "First Entry:") + f" {first}<br />" +
        tr("SettingsDialog", "Last Updated:") + f" {last}"
    )
    BACKUP_STATUS_OTHER = lambda status: tr("SettingsDialog", "<p>Backup File Status:") + f" {status}</p>"

    # Automate tasks
    def AUTOMATE_TASKS_NOTICE():
        import platform
        os_name = platform.system()
        if os_name == "Darwin":
            os_display = "macOS"
        elif os_name == "Windows":
            os_display = "Windows"
        elif os_name == "Linux":
            os_display = "Linux"
        else:
            os_display = os_name
        translated = QCoreApplication.translate("SettingsDialog", "<p>Wait and Pounce can automatically take actions for certain windows in your %1 environment.</p><p>For example, it can automatically close the JTDX Log QSO window after each new QSO.</p><p>Automate tasks can be done if Wait and Pounce is running on the same computer as the targeted window.</p><p>It won't work when running Wait and Pounce as slave or on another computer.</p>")
        return translated.replace("%1", os_display)

    GROUP_AUTOMATE_TASKS_SETTINGS = lambda: tr("SettingsDialog", "Automation Options")
    CLOSE_JTDX_LOG_QSO_PROMPT = lambda: tr("SettingsDialog", "Close JTDX Log QSO window prompt")
    JTDX_CLICK_DELAY_LABEL = lambda: tr("SettingsDialog", "Delay before clicking:")
    BUTTON_AUTOMATE_TASKS_TEST = lambda: tr("SettingsDialog", "Test it")
    BUTTON_TEST_WINDOWS_MONITORING = lambda: tr("SettingsDialog", "Test Windows Monitoring Permissions")

    # Antenna Rotator (PstRotatorAz)
    PSTROTATOR_NOTICE = lambda: tr("SettingsDialog",
        "<p>Wait and Pounce can drive a <b>PstRotatorAz</b> antenna rotator over UDP.</p>"
        "<p>In PstRotatorAz: set <u>Communication &gt; UDP Control Port</u> to the port below and enable <u>UDP Control</u> in Setup.</p>"
        "<p>Two automation modes are available and can be combined. Wanted tracking takes priority over the hourly schedule.</p>")
    GROUP_PSTROTATOR_CONNECTION = lambda: tr("SettingsDialog", "PstRotatorAz Connection")
    LABEL_PSTROTATOR_CURRENT_AZIMUTH = lambda: tr("SettingsDialog", "Current azimuth:")
    PSTROTATOR_AZIMUTH_UNKNOWN = lambda: tr("SettingsDialog", "—")
    PSTROTATOR_AZIMUTH_VALUE = lambda az: tr("SettingsDialog", "%1°").replace("%1", str(az))
    GROUP_PSTROTATOR_WANTED = lambda: tr("SettingsDialog", "Wanted Tracking")
    CHECK_PSTROTATOR_WANTED = lambda: tr("SettingsDialog", "Point the antenna at decoded Wanted callsigns automatically")
    LABEL_PSTROTATOR_THRESHOLD = lambda: tr("SettingsDialog", "Only move if azimuth changes by more than:")
    SUFFIX_PSTROTATOR_DEGREES = lambda: tr("SettingsDialog", "°")
    GROUP_PSTROTATOR_PARK = lambda: tr("SettingsDialog", "Return to Rest Position")
    CHECK_PSTROTATOR_PARK = lambda: tr("SettingsDialog", "Return the antenna to a rest position when idle")
    LABEL_PSTROTATOR_PARK_AZIMUTH = lambda: tr("SettingsDialog", "Rest azimuth:")
    LABEL_PSTROTATOR_PARK_DELAY = lambda: tr("SettingsDialog", "Return after inactivity of:")
    SUFFIX_PSTROTATOR_MINUTES = lambda: tr("SettingsDialog", " min")
    GROUP_PSTROTATOR_SCHEDULE = lambda: tr("SettingsDialog", "Hourly Schedule")
    CHECK_PSTROTATOR_SCHEDULE = lambda: tr("SettingsDialog", "Rotate to a fixed azimuth at given times (UTC)")
    HEADER_PSTROTATOR_TIME = lambda: tr("SettingsDialog", "Time (UTC)")
    HEADER_PSTROTATOR_AZIMUTH = lambda: tr("SettingsDialog", "Azimuth (°)")
    BUTTON_PSTROTATOR_ADD = lambda: tr("SettingsDialog", "Add")
    BUTTON_PSTROTATOR_REMOVE = lambda: tr("SettingsDialog", "Remove")

    # Automation test results
    AUTOMATION_ADMIN_REQUIRED_TITLE = lambda: tr("SettingsDialog", "Administrator Rights Required")
    AUTOMATION_ADMIN_REQUIRED_MESSAGE = lambda: tr("SettingsDialog",
        "On Windows, this automation feature requires administrator privileges. Please restart the application as Administrator to use this feature.")
    AUTOMATION_TEST_SUCCESS_TITLE = lambda: tr("SettingsDialog", "Test Successful")
    AUTOMATION_TEST_SUCCESS_MESSAGE = lambda window: tr("SettingsDialog", "Found and sent keys to: %1").replace("%1", str(window))
    AUTOMATION_TEST_FAILED_TITLE = lambda: tr("SettingsDialog", "Test Failed")
    AUTOMATION_TEST_FAILED_MESSAGE = lambda window: tr("SettingsDialog", "Found window but failed to send keys: %1").replace("%1", str(window))
    AUTOMATION_WINDOW_NOT_FOUND_TITLE = lambda: tr("SettingsDialog", "Window Not Found")
    AUTOMATION_WINDOW_NOT_FOUND_MESSAGE = lambda: tr("SettingsDialog",
        "Could not find a window containing both JTDX and Log QSO. Please make sure the JTDX Log QSO window is open and try again.")
    AUTOMATION_ERROR_TITLE = lambda: tr("SettingsDialog", "Error")
    AUTOMATION_ERROR_MESSAGE = lambda error: tr("SettingsDialog", "An error occurred while testing: %1").replace("%1", str(error))

    # Window Monitoring Dialog
    WINDOW_MONITORING_TITLE = lambda: tr("WindowMonitoringDialog", "Test Windows Monitoring")
    WINDOW_MONITORING_HEADER = lambda: tr("WindowMonitoringDialog", "Window Title Monitoring Test")
    WINDOW_MONITORING_COUNT = lambda count: tr("WindowMonitoringDialog", f"Windows found: {count}")
    WINDOW_MONITORING_REFRESH = lambda: tr("WindowMonitoringDialog", "Refresh Now")
    WINDOW_MONITORING_PAUSE = lambda: tr("WindowMonitoringDialog", "Pause Auto-Refresh")
    WINDOW_MONITORING_RESUME = lambda: tr("WindowMonitoringDialog", "Resume Auto-Refresh")
    WINDOW_MONITORING_MACOS_LIBS_MISSING = lambda: tr("WindowMonitoringDialog", "Required macOS accessibility libraries not installed.")
    WINDOW_MONITORING_MACOS_PERMISSION_REQUIRED = lambda: tr("WindowMonitoringDialog",
        "<p>macOS Accessibility Permission Required: To monitor window titles, Wait and Pounce needs Accessibility permissions.</p><p>Go to: System Settings > Privacy & Security > Accessibility and make sure this application is listed and checked.</p>")
    WINDOW_MONITORING_UNSUPPORTED_PLATFORM = lambda: tr("WindowMonitoringDialog",
        "<p>Unsupported platform: Window monitoring is only available on macOS and Windows.</p>")

    # Debugging
    DEBUG_NOTICE = lambda: tr("SettingsDialog",
        "<p>Enable debugging options to help troubleshoot issues.</p><p>Warning: These options may generate large log files and affect performance.</p>"
    )
    GROUP_DEBUG_SETTINGS = lambda: tr("SettingsDialog", "Debugging Options")
    CHECK_ENABLE_POUNCE_LOG = lambda: tr("SettingsDialog", "Enable pounce log")
    CHECK_ENABLE_GUI_DEBUG = lambda: tr("SettingsDialog", "Enable extra GUI debug output")
    CHECK_LOG_PACKET_DATA = lambda: tr("SettingsDialog", "Log UDP packet data")

    # File dialogs
    DIALOG_SELECT_ADIF = lambda: tr("SettingsDialog", "Select ADIF File")
    DIALOG_SELECT_BACKUP = lambda: tr("SettingsDialog", "Select ADIF Backup File")
    FILE_FILTER_ADIF = lambda: tr("SettingsDialog", "ADIF Files (*.adif *.adi);;All Files (*)")

    # Messages
    MESSAGE_FILE_ALREADY_ADDED = lambda: tr("SettingsDialog", "File Already Added")
    MESSAGE_FILE_ALREADY_IN_LIST = lambda filename: tr("SettingsDialog", f"The file '{filename}' is already in the list.")
    MESSAGE_NO_DATA_FOUND = lambda: tr("SettingsDialog", "No Data found")
    MESSAGE_FILE_EMPTY_OR_CORRUPTED = lambda: tr("SettingsDialog", "Seems your file is either empty or corrupted")


# GRID MAP VIEWER
class GridMapStrings:
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
    LABEL_BAND = lambda: tr("GridMapViewer", "Band:")
    LABEL_WORKED = lambda: tr("GridMapViewer", "Worked:")
    LABEL_CONFIRMED = lambda: tr("GridMapViewer", "Confirmed:")
    STATUS_BAND = lambda band: tr("GridMapViewer", "Band:") + f" <u>{band}</u>"
    STATUS_ALL_BANDS = lambda: tr("GridMapViewer", "All bands")
    STATUS_WORKED = lambda count: tr("GridMapViewer", "Worked:") + f" {count}"
    STATUS_CONFIRMED = lambda count: tr("GridMapViewer", "Confirmed:") + f" {count}"
    # Zoom controls
    ZOOM_IN = lambda: tr("GridMapViewer", "Zoom In")
    ZOOM_OUT = lambda: tr("GridMapViewer", "Zoom Out")
    RESET_VIEW = lambda: tr("GridMapViewer", "Reset View")
    # Keyboard shortcuts help
    SHORTCUTS_HELP = lambda: tr("GridMapViewer",
        "Keyboard Shortcuts:\nG - Toggle Grid\nH - Toggle Heatmap\nW - Toggle Worked\nL - Toggle Night/Day"
    )

    # Tooltip headers
    TOOLTIP_DECODED_GRID = lambda grid: tr("GridMapViewer", "Decoded Grid: <b>%1</b>").replace("%1", str(grid))
    TOOLTIP_WORKED_GRID = lambda grid: tr("GridMapViewer", "Worked Grid: <b>%1</b>").replace("%1", str(grid))

    # Table headers
    TABLE_HEADER_CALLSIGN = lambda: tr("GridMapViewer", "Callsign")
    TABLE_HEADER_BAND = lambda: tr("GridMapViewer", "Band")
    TABLE_HEADER_TIME = lambda: tr("GridMapViewer", "Time")
    TABLE_HEADER_DATE = lambda: tr("GridMapViewer", "Date")
    TABLE_HEADER_REPORT = lambda: tr("GridMapViewer", "Report")
    TABLE_HEADER_DT = lambda: tr("GridMapViewer", "DT")
    TABLE_HEADER_FREQ = lambda: tr("GridMapViewer", "Freq")
    TABLE_HEADER_MODE = lambda: tr("GridMapViewer", "Mode")
    TABLE_HEADER_SENT = lambda: tr("GridMapViewer", "Sent")
    TABLE_HEADER_RCVD = lambda: tr("GridMapViewer", "Rcvd")
    TABLE_HEADER_QSL = lambda: tr("GridMapViewer", "QSL")

    # Tooltip messages
    TOOLTIP_QSO_LIMIT = lambda limit, total, grid: tr("GridMapViewer", "* The last <u>%1</u> are displayed out of a total of <b>%2</b> for <b>%3</b>").replace("%1", str(limit)).replace("%2", str(total)).replace("%3", str(grid))
    TOOLTIP_RIGHT_CLICK = lambda: tr("GridMapViewer", "* Right click on Grid for context-menu")


# ADIF SUMMARY DIALOG
class AdifSummaryStrings:
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


# ACTIVE USERS WINDOW
class ActiveUsersStrings:
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


# CONTEXT MENU
class ContextMenuStrings:
    CONTEXT = "ContextMenu"
    COPY = lambda: tr("ContextMenu", "Copy")
    COPY_CALLSIGN = lambda: tr("ContextMenu", "Copy Callsign")
    COPY_GRID = lambda: tr("ContextMenu", "Copy Grid")
    COPY_MESSAGE = lambda: tr("ContextMenu", "Copy Message")
    COPY_MESSAGE_TO_CLIPBOARD = lambda: tr("ContextMenu", "Copy message to Clipboard")
    ADD_TO_WANTED = lambda: tr("ContextMenu", "Add to Wanted")
    ADD_TO_MONITORED = lambda: tr("ContextMenu", "Add to Monitored")
    ADD_TO_EXCLUDED = lambda: tr("ContextMenu", "Add to Excluded")
    REMOVE_FROM_WANTED = lambda: tr("ContextMenu", "Remove from Wanted")
    REMOVE_FROM_MONITORED = lambda: tr("ContextMenu", "Remove from Monitored")
    REMOVE_FROM_EXCLUDED = lambda: tr("ContextMenu", "Remove from Excluded")
    LOOKUP_QRZ = lambda: tr("ContextMenu", "Lookup on QRZ.com")
    LOOKUP_QRZCQ = lambda: tr("ContextMenu", "Lookup on QRZCQ.com")
    LOOKUP_HAMQTH = lambda: tr("ContextMenu", "Lookup on HamQTH.com")

    # Dynamic context menu items
    REMOVE_ENTRY_FROM_WORKED_HISTORY = lambda callsign, band: tr("ContextMenu", "Remove %1 on %2 from Worked History").replace("%1", str(callsign)).replace("%2", str(band))
    REMOVE_CALLSIGN_FROM_WORKED_HISTORY = lambda callsign, bands: tr("ContextMenu", "Remove %1 on all bands from Worked History (%2)").replace("%1", str(callsign)).replace("%2", str(bands))
    EXCLUSION_FOR = lambda excluded, callsign: tr("ContextMenu", "Exclusion for <b>%1</b> and matches with <b>%2</b>").replace("%1", str(excluded)).replace("%2", str(callsign))
    APPLY_TO_BAND = lambda band: tr("ContextMenu", "Apply to <b>%1</b> band").replace("%1", str(band))

    # Wanted callsigns
    ADD_CALLSIGN_TO_WANTED = lambda callsign: tr("ContextMenu", "Add %1 to Wanted Callsigns").replace("%1", str(callsign))
    REMOVE_CALLSIGN_FROM_WANTED = lambda callsign: tr("ContextMenu", "Remove %1 from Wanted Callsigns").replace("%1", str(callsign))
    MAKE_ONLY_WANTED_CALLSIGN = lambda callsign: tr("ContextMenu", "Make %1 your only Wanted Callsign").replace("%1", str(callsign))

    # Excluded callsigns
    TEMPORARILY_ADD_TO_EXCLUDED = lambda callsign: tr("ContextMenu", "Temporarily add %1 to Excluded Callsigns").replace("%1", str(callsign))
    ADD_CALLSIGN_TO_EXCLUDED = lambda callsign: tr("ContextMenu", "Add %1 to Excluded Callsigns").replace("%1", str(callsign))
    REMOVE_CALLSIGN_FROM_EXCLUDED = lambda callsign: tr("ContextMenu", "Remove %1 from Excluded Callsigns").replace("%1", str(callsign))

    # Monitored callsigns
    ADD_CALLSIGN_TO_MONITORED = lambda callsign: tr("ContextMenu", "Add %1 to Monitored Callsigns").replace("%1", str(callsign))
    REMOVE_CALLSIGN_FROM_MONITORED = lambda callsign: tr("ContextMenu", "Remove %1 from Monitored Callsigns").replace("%1", str(callsign))

    # Directed callsigns
    ADD_DIRECTED_TO_WANTED = lambda directed: tr("ContextMenu", "Add %1 to Wanted Callsigns").replace("%1", str(directed))
    REMOVE_DIRECTED_FROM_WANTED = lambda directed: tr("ContextMenu", "Remove %1 from Wanted Callsigns").replace("%1", str(directed))
    MAKE_DIRECTED_ONLY_MONITORED = lambda directed: tr("ContextMenu", "Make %1 your only Monitored Callsign").replace("%1", str(directed))
    ADD_DIRECTED_TO_MONITORED = lambda directed: tr("ContextMenu", "Add %1 to Monitored Callsigns").replace("%1", str(directed))
    REMOVE_DIRECTED_FROM_MONITORED = lambda directed: tr("ContextMenu", "Remove %1 from Monitored Callsigns").replace("%1", str(directed))

    # CQ Zones
    ADD_ZONE_TO_MONITORED = lambda zone: tr("ContextMenu", "Add Zone %1 to Monitored CQ Zones").replace("%1", str(zone))
    REMOVE_ZONE_FROM_MONITORED = lambda zone: tr("ContextMenu", "Remove Zone %1 from Monitored CQ Zones").replace("%1", str(zone))

    # QRZ.com
    OPEN_QRZ_COM = lambda callsign: tr("ContextMenu", "Open QRZ.com for %1").replace("%1", str(callsign))


# ERROR MESSAGES
class ErrorStrings:
    CONTEXT = "Errors"
    CONNECTION_FAILED = lambda: tr("Errors", "Connection failed")
    FILE_NOT_FOUND = lambda file: tr("Errors", f"File not found: {file}")
    INVALID_FORMAT = lambda: tr("Errors", "Invalid format")
    PARSE_ERROR = lambda: tr("Errors", "Parse error")
    NETWORK_ERROR = lambda: tr("Errors", "Network error")
    PERMISSION_DENIED = lambda: tr("Errors", "Permission denied")
    TIMEOUT = lambda: tr("Errors", "Operation timed out")

# TIME FORMATS
class TimeStrings:
    CONTEXT = "Time"
    JUST_NOW = lambda: tr("Time", "just now")
    SECONDS_AGO = lambda n: tr("Time", f"{n}s ago")
    MINUTES_AGO = lambda n: tr("Time", f"{n}m ago")
    HOURS_AGO = lambda n: tr("Time", f"{n}h ago")
    DAYS_AGO = lambda n: tr("Time", f"{n}d ago")

# ENTITIES
def translate_entity(entity_name, language='en'):
    if not entity_name:
        return entity_name

    translated = QCoreApplication.translate("Entities", entity_name.upper())
    if translated == entity_name.upper():
        return entity_name
    return translated
