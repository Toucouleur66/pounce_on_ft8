# window_monitoring_dialog.py

import platform
from PyQt6 import QtWidgets, QtCore

from custom_button import CustomButton
from constants import (
    CUSTOM_FONT,
    CUSTOM_FONT_SMALL,
    CUSTOM_FONT_MONO
)

from style import set_macos_window_appearance, get_setting_qss
from style import (
    EVEN_COLOR
)

from translatable_strings import CommonStrings, SettingsStrings

# Platform-specific imports for window monitoring
if platform.system() == "Darwin":  # macOS
    try:
        from Quartz import (CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly,
                           kCGNullWindowID)
        from AppKit import NSWorkspace, NSRunningApplication
        from ApplicationServices import (AXUIElementCreateApplication, AXUIElementCopyAttributeValue,
                                        kAXWindowsAttribute, kAXTitleAttribute, kAXRoleAttribute)
        from Cocoa import (NSAccessibilityRoleAttribute, NSAccessibilityWindowRole,
                          NSAccessibilityTitleAttribute, NSAccessibilityChildrenAttribute)
        MACOS_ACCESSIBILITY_AVAILABLE = True
    except ImportError as e:
        MACOS_ACCESSIBILITY_AVAILABLE = False
elif platform.system() == "Windows":
    try:
        import win32gui
        WINDOWS_WIN32GUI_AVAILABLE = True
    except ImportError:
        WINDOWS_WIN32GUI_AVAILABLE = False

class WindowMonitoringDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, dark_mode=False):
        super().__init__(parent)
        self.setWindowTitle(SettingsStrings.WINDOW_MONITORING_TITLE())
        self.setGeometry(100, 100, 400, 600)
        self.setMinimumWidth(400)
        
        self.dark_mode = dark_mode

        # Create main layout
        layout = QtWidgets.QVBoxLayout(self)

        # Permission status label
        self.permission_label = QtWidgets.QLabel()
        self.permission_label.setFont(CUSTOM_FONT_SMALL)
        self.permission_label.setWordWrap(True)
        self.permission_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        layout.addWidget(self.permission_label)

        # Count label
        self.count_label = QtWidgets.QLabel(SettingsStrings.WINDOW_MONITORING_COUNT(0))
        self.count_label.setFont(CUSTOM_FONT_SMALL)
        self.count_label.setStyleSheet("padding: 5px;")
        layout.addWidget(self.count_label)

        # List widget to display window titles
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setFont(CUSTOM_FONT)
        layout.addWidget(self.list_widget)

        # Button layout
        button_layout = QtWidgets.QHBoxLayout()

        # Refresh button
        refresh_button = CustomButton(SettingsStrings.WINDOW_MONITORING_REFRESH())
        refresh_button.clicked.connect(self.update_window_list)
        button_layout.addWidget(refresh_button)

        # Toggle auto-refresh button
        self.auto_refresh_button = CustomButton(SettingsStrings.WINDOW_MONITORING_PAUSE())
        self.auto_refresh_button.clicked.connect(self.toggle_auto_refresh)
        button_layout.addWidget(self.auto_refresh_button)

        # Close button
        close_button = CustomButton(CommonStrings.CLOSE())
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        # Timer for auto-refresh every second
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_window_list)
        self.timer.start(1000)
        self.auto_refresh_enabled = True

        # Check permissions and update initial status
        self.check_permissions()
        self.update_window_list()

        # Apply dark mode if needed
        if self.dark_mode:
            set_macos_window_appearance(self, True)

    def check_permissions(self):
        if platform.system() == "Darwin":
            if not MACOS_ACCESSIBILITY_AVAILABLE:
                self.permission_label.setText(
                    SettingsStrings.WINDOW_MONITORING_MACOS_LIBS_MISSING()
                )
                self.permission_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
            else:
                self.permission_label.setText(
                    SettingsStrings.WINDOW_MONITORING_MACOS_PERMISSION_REQUIRED()
                )
                self.permission_label.setStyleSheet(get_setting_qss(EVEN_COLOR))
        elif platform.system() == "Windows":
            # No message needed for Windows
            self.permission_label.hide()
        else:
            self.permission_label.setText(
                SettingsStrings.WINDOW_MONITORING_UNSUPPORTED_PLATFORM()
            )
            self.permission_label.setStyleSheet(get_setting_qss(EVEN_COLOR))

    def get_window_titles_mac(self):
        if not MACOS_ACCESSIBILITY_AVAILABLE:
            return ["<p>Error: macOS accessibility libraries not available</p>"]

        windows = []
        try:
            workspace = NSWorkspace.sharedWorkspace()
            running_apps = workspace.runningApplications()

            for app in running_apps:
                activation_policy = app.activationPolicy()
                if activation_policy != 0:
                    continue

                app_name = app.localizedName()
                if not app_name:
                    continue

                try:
                    pid = app.processIdentifier()
                    ax_app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)

                    if not ax_app:
                        continue

                    ax_element = AXUIElementCreateApplication(pid)
                    if not ax_element:
                        continue

                    err, windows_list = AXUIElementCopyAttributeValue(
                        ax_element,
                        NSAccessibilityChildrenAttribute,
                        None
                    )

                    if err == 0 and windows_list:
                        for window in windows_list:
                            err_role, role = AXUIElementCopyAttributeValue(
                                window,
                                NSAccessibilityRoleAttribute,
                                None
                            )

                            if err_role == 0 and role == NSAccessibilityWindowRole:
                                err_title, title = AXUIElementCopyAttributeValue(
                                    window,
                                    NSAccessibilityTitleAttribute,
                                    None
                                )

                                if err_title == 0 and title:
                                    windows.append(f"{app_name}: {title}")
                                else:
                                    windows.append(f"{app_name}: (untitled window)")

                except Exception:
                    pass

        except Exception as e:
            windows.append(f"Error: {str(e)}")

        return windows

    def get_window_titles_windows(self):
        if not WINDOWS_WIN32GUI_AVAILABLE:
            return ["<p>Error: Windows win32gui library not available</p>"]

        windows = []

        def callback(hwnd, windows_list):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    windows_list.append(title)
            return True

        try:
            win32gui.EnumWindows(callback, windows)
        except Exception as e:
            windows.append(f"Error: {str(e)}")

        return windows

    def update_window_list(self):
        if platform.system() == "Darwin":
            windows = self.get_window_titles_mac()
        elif platform.system() == "Windows":
            windows = self.get_window_titles_windows()
        else:
            windows = ["Unsupported platform"]

        self.list_widget.clear()
        windows.sort()

        for window in windows:
            self.list_widget.addItem(window)

        self.count_label.setText(SettingsStrings.WINDOW_MONITORING_COUNT(len(windows)))

    def toggle_auto_refresh(self):
        if self.auto_refresh_enabled:
            self.timer.stop()
            self.auto_refresh_button.setText(SettingsStrings.WINDOW_MONITORING_RESUME())
            self.auto_refresh_enabled = False
        else:
            self.timer.start(2000)
            self.auto_refresh_button.setText(SettingsStrings.WINDOW_MONITORING_PAUSE())
            self.auto_refresh_enabled = True

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)
