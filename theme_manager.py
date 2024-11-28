# theme_manager.py

from PyQt6.QtCore import QObject, pyqtSignal

import sys

class ThemeManager(QObject):
    theme_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.dark_mode = self.is_dark_apperance()

    def check_theme_change(self):
        current_dark_mode = self.is_dark_apperance()
        if current_dark_mode != self.dark_mode:
            self.dark_mode = current_dark_mode
            self.theme_changed.emit(self.dark_mode)

    def is_dark_apperance(self):
        try:
            if sys.platform == 'darwin':
                from Foundation import NSUserDefaults
                defaults = NSUserDefaults.standardUserDefaults()
                osx_appearance = defaults.stringForKey_("AppleInterfaceStyle")
                return osx_appearance == 'Dark'
            elif sys.platform == 'win32':
                import winreg
                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return value == 0
        except Exception as e:
            print(f"Can't know if we are either using Dark or Light mode: {e}")
            return False            
