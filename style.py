# style.py
# All color constants, style functions, and QSS stylesheets
import platform

# Color constants
EVEN_COLOR                      = "#9DFFFE"
ODD_COLOR                       = "#FFFE9F"
FG_TIMER_COLOR                  = "#3D25FB"

BG_COLOR_FOCUS_MY_CALL          = ODD_COLOR
FG_COLOR_FOCUS_MY_CALL          = "#FF0000"

BG_COLOR_REGULAR_FOCUS          = "#000000"
FG_COLOR_REGULAR_FOCUS          = "#01FFFF"

BG_COLOR_BLACK_ON_YELLOW        = "#FFFF00"
FG_COLOR_BLACK_ON_YELLOW        = "#000000"

BG_COLOR_BLACK_ON_SAUMON        = "#FFDFBC"
FG_COLOR_BLACK_ON_SAUMON        = "#000000"

BG_COLOR_WHITE_ON_BLUE          = "#AEB4FF"
FG_COLOR_WHITE_ON_BLUE          = "#000000"

BG_COLOR_BLACK_ON_LIGHT_BLUE    = "#b8d7ff"
FG_COLOR_BLACK_ON_LIGHT_BLUE    = "#000000"

BG_COLOR_BLACK_ON_PURPLE        = "#FFBDFF"
FG_COLOR_BLACK_ON_PURPLE        = "#000000"

BG_COLOR_BLACK_ON_WHITE         = "#000000"
FG_COLOR_BLACK_ON_WHITE         = "#FFFFFF"

BG_COLOR_BLACK_ON_CYAN          = "#C8F0C9"
FG_COLOR_BLACK_ON_CYAN          = "#000000"

BG_COLOR_BLACK_ON_LIGHT_TEAL    = "#E5F7F7"
FG_COLOR_BLACK_ON_LIGHT_TEAL    = "#000000"

BG_COLOR_WHITE_ON_BLUE_VIOLET   = FG_TIMER_COLOR
FG_COLOR_WHITE_ON_BLUE_VIOLET   = EVEN_COLOR

STATUS_MONITORING_COLOR         = "#0D81FF"
STATUS_DECODING_COLOR           = "#2BBE7E"
STATUS_TRX_COLOR                = "#FF5600"

STATUS_COLOR_LABEL_OFF          = "#E5E5E5"
STATUS_COLOR_LABEL_SELECTED     = "#808080"

import constants
CUSTOM_FONT                     = constants.CUSTOM_FONT
CUSTOM_FONT_SMALL               = constants.CUSTOM_FONT

# Theme-aware style functions
def get_setting_qss(color):
    return f"""
        background-color: {color};
        color: #555BC2;
        padding: 6px;
        margin-bottom: 10px;
        font-size: 12px;
        border-radius: 6px;
    """

def get_main_table_qss(dark_mode=False):
    if dark_mode:
        table_bg = '#353535'
        table_alt_bg = '#3f3f3f'
        table_text = '#FFFFFF'
    else:
        table_bg = '#FFFFFF'
        table_alt_bg = '#F4F5F5'
        table_text = '#000000'

    gridline_color = '#D3D3D3' if not dark_mode else '#171717'        

    return f"""
            QTableView {{
                background-color: {table_bg};
                alternate-background-color: {table_alt_bg};
                color: {table_text};
                gridline-color: {gridline_color};
                border: 1px solid palette(Mid);
            }}
            QTableView::item {{
                padding: 5px;
            }}
            QHeaderView::section {{
                font-weight: normal;
                border: none;
                font: {CUSTOM_FONT_SMALL.pointSize()}pt '{CUSTOM_FONT_SMALL.family()}';
                padding: 0 3px 0 3px;
                border-right: 1px solid {gridline_color};
            }}
            QHeaderView::section:horizontal:last {{
                border-right: none;
            }}
        """

def get_table_setting_qss(dark_mode=False):
    _ = dark_mode  # Suppress unused warning
    return f"""
        QTableWidget {{
            gridline-color: transparent;
            selection-background-color: {BG_COLOR_BLACK_ON_PURPLE};
            outline: none;
        }}
        QTableWidget::item:selected {{
            background-color: {BG_COLOR_BLACK_ON_PURPLE};
            color: {FG_COLOR_BLACK_ON_PURPLE};
            padding: 0px;
            padding-left: 8px;
            border: 0px solid transparent;
            outline: none;
        }}
        QTableWidget::item {{
            padding: 0px;
            padding-left: 8px;
            border: 0px solid transparent;
            outline: none;
        }}
    """

def get_odd_color(dark_mode=False):
    if dark_mode:
        return "#3A3A3A"
    else:
        return ODD_COLOR

def get_groupbox_qss(dark_mode=False):
    if dark_mode:
        return """
            QGroupBox {
                background-color: #2A2A2A;
                border: 1px solid #404040;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 6px;
                background-color: #2A2A2A;
                color: #FFFFFF;
            }
        """
    else:
        return """
            QGroupBox {
                background-color: #F5F5F5;
                border: 1px solid #D0D0D0;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 6px;
                background-color: #F5F5F5;
                color: #000000;
            }
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
            QMenu::item:selected {{
                background-color: #499EFF;
                border-radius: 4px;
                color: white;
            }}
            QMenu::item:disabled {{
                color: grey;
            }}
            QMenu::separator {{
                height: 1px;
                background: #CCCCCC;
                margin: 4px 0;
            }}
        """

QSLIDER_QSS                     = f"""
            QSlider::groove:horizontal {{
                border: 1px solid #999999;
                height: 10px;
            }}
            QSlider::handle:horizontal {{
                background: #fff;
                width: 10px;
                margin: -1px -1px;
                border: 1px solid #5555ff;
            }}
            QSlider::handle:horizontal:hover {{
                background: #000;
                border-color:#000;
            }}
            QSlider::add-page:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
            }}
            QSlider::sub-page:horizontal {{
                background: {STATUS_MONITORING_COLOR};
            }}
        """

SLIDER_VALUE_LABEL_QSS          = f"""
            QLabel {{
                background-color: {STATUS_MONITORING_COLOR};
                color: white;
                border-radius: 8px;
                padding: 2px 5px;
                height: 10px;
            }}
        """

CONTEXT_MENU_HEADER_QSS         = f"""
                background-color: {STATUS_TRX_COLOR};
                color: white;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
        """

CONTEXT_MENU_EXCLUDED_QSS         = f"""
                background-color: {STATUS_MONITORING_COLOR};
                color: white;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
        """

def set_macos_window_appearance(window, dark_mode):
    if platform.system() != 'Darwin':
        return

    try:
        from ctypes import c_void_p, c_char_p, cdll, util

        # Load the Objective-C runtime
        objc = cdll.LoadLibrary(util.find_library('objc'))
        objc.objc_getClass.restype = c_void_p
        objc.sel_registerName.restype = c_void_p
        objc.objc_msgSend.restype = c_void_p

        # Get the native window handle
        win_id = int(window.winId())
        ns_view = c_void_p(win_id)

        # Get NSWindow from NSView
        window_sel = objc.sel_registerName(b'window')
        objc.objc_msgSend.argtypes = [c_void_p, c_void_p]
        ns_window = objc.objc_msgSend(ns_view, window_sel)

        if ns_window:
            # Create NSString for appearance name
            ns_string_class = objc.objc_getClass(b'NSString')
            string_with_utf8_sel = objc.sel_registerName(b'stringWithUTF8String:')

            # Set proper argtypes for string creation
            objc.objc_msgSend.argtypes = [c_void_p, c_void_p, c_char_p]

            # Choose appearance based on theme
            if dark_mode:
                appearance_name_str = b'NSAppearanceNameDarkAqua'
            else:
                appearance_name_str = b'NSAppearanceNameAqua'

            appearance_name = objc.objc_msgSend(
                ns_string_class,
                string_with_utf8_sel,
                appearance_name_str
            )

            appearance_class = objc.objc_getClass(b'NSAppearance')
            appearance_sel = objc.sel_registerName(b'appearanceNamed:')
            set_appearance_sel = objc.sel_registerName(b'setAppearance:')

            objc.objc_msgSend.argtypes = [c_void_p, c_void_p, c_void_p]
            appearance = objc.objc_msgSend(appearance_class, appearance_sel, appearance_name)
            objc.objc_msgSend(ns_window, set_appearance_sel, appearance)
    except Exception:
        pass

def set_windows_titlebar_theme(window, dark_mode):
    """Set Windows title bar to match dark/light theme"""
    if platform.system() != 'Windows':
        return

    try:
        from ctypes import windll, byref, sizeof, c_int

        # Get the window handle
        hwnd = int(window.winId())

        # DWMWA_USE_IMMERSIVE_DARK_MODE attribute
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20

        # Set the attribute (1 for dark mode, 0 for light mode)
        use_dark_mode = c_int(1 if dark_mode else 0)
        windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            byref(use_dark_mode),
            sizeof(use_dark_mode)
        )
    except Exception:
        pass

def get_menubar_qss(dark_mode=False):
    """Get menu bar stylesheet for Windows"""
    if dark_mode:
        return """
            QMenuBar {
                background-color: #323232;
                color: #FFFFFF;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 8px;
            }
            QMenuBar::item:selected {
                background-color: #42A5F5;
            }
            QMenuBar::item:pressed {
                background-color: #1E88E5;
            }
            QMenu {
                background-color: #323232;
                color: #FFFFFF;
                border: 1px solid #555555;
            }
            QMenu::item {
                padding: 6px 20px;
            }
            QMenu::item:selected {
                background-color: #42A5F5;
            }
            QMenu::item:disabled {
                color: #808080;
            }
            QMenu::separator {
                height: 1px;
                background: #555555;
                margin: 4px 0;
            }
        """
    else:
        return """
            QMenuBar {
                background-color: #F0F0F0;
                color: #000000;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 8px;
            }
            QMenuBar::item:selected {
                background-color: #308CC6;
                color: #FFFFFF;
            }
            QMenuBar::item:pressed {
                background-color: #1976D2;
                color: #FFFFFF;
            }
            QMenu {
                background-color: #FFFFFF;
                color: #000000;
                border: 1px solid #D0D0D0;
            }
            QMenu::item {
                padding: 6px 20px;
            }
            QMenu::item:selected {
                background-color: #308CC6;
                color: #FFFFFF;
            }
            QMenu::item:disabled {
                color: #808080;
            }
            QMenu::separator {
                height: 1px;
                background: #D0D0D0;
                margin: 4px 0;
            }
        """
