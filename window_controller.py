import sys
import platform
import time

from PyQt6 import QtWidgets, QtCore

from constants import CUSTOM_FONT

from custom_button import CustomButton
from custom_qlabel import CustomQLabel
from translatable_strings import CommonStrings

from logger import get_logger

log = get_logger(__name__)

if platform.system() == "Darwin":  
    try:
        from AppKit import NSWorkspace, NSRunningApplication
        from ApplicationServices import (AXUIElementCreateApplication, AXUIElementCopyAttributeValue,
                                        AXUIElementSetAttributeValue, kAXMainWindowAttribute,
                                        kAXFocusedAttribute, kAXRaiseAction, AXUIElementPerformAction)
        from Cocoa import NSAccessibilityRoleAttribute, NSAccessibilityWindowRole, NSAccessibilityTitleAttribute
        from pynput.keyboard import Key, Controller
    except ImportError as e:
        log.error(f"Import error: {e}")
        log.error("Please install required packages:")
        log.error("pip install pyobjc-framework-Quartz pyobjc-framework-Cocoa pynput")
        sys.exit(1)
elif platform.system() == "Windows":
    try:
        import win32gui
        import win32con
        from pynput.keyboard import Key, Controller
    except ImportError:
        log.error("Please install pywin32 and pynput: pip install pywin32 pynput")
        sys.exit(1)

class WindowController:
    def __init__(self):
        self.keyboard = Controller()

    def get_windows_list(self):
        if platform.system() == "Darwin":
            return self._get_windows_list_mac()
        elif platform.system() == "Windows":
            return self._get_windows_list_windows()
        return []

    def _get_windows_list_mac(self):
        windows = []
        try:
            workspace = NSWorkspace.sharedWorkspace()
            running_apps = workspace.runningApplications()

            for app in running_apps:
                if app.activationPolicy() != 0:
                    continue

                app_name = app.localizedName()
                if not app_name:
                    continue

                pid = app.processIdentifier()
                ax_element = AXUIElementCreateApplication(pid)
                if not ax_element:
                    continue

                err, windows_list = AXUIElementCopyAttributeValue(
                    ax_element,
                    "AXWindows",
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
                                windows.append({
                                    'app_name': app_name,
                                    'title': title,
                                    'display': f"{app_name}: {title}",
                                    'pid': pid,
                                    'window_element': window
                                })
        except Exception as e:
            log.error(f"Error getting windows list: {e}")

        return windows

    def _get_windows_list_windows(self):
        windows = []

        def callback(hwnd, windows_list):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    windows_list.append({
                        'title': title,
                        'display': title,
                        'hwnd': hwnd
                    })
            return True

        try:
            win32gui.EnumWindows(callback, windows)
        except Exception as e:
            log.error(f"Error getting windows list: {e}")

        return windows

    def focus_window(self, window_info):
        if platform.system() == "Darwin":
            return self._focus_window_mac(window_info)
        elif platform.system() == "Windows":
            return self._focus_window_windows(window_info)
        return False

    def _focus_window_mac(self, window_info):
        try:
            pid = window_info['pid']

            # First, activate the application
            app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
            if app:
                app.activateWithOptions_(1)  # NSApplicationActivateIgnoringOtherApps
                time.sleep(0.2)  # Give time for activation

            # Then raise the specific window
            window_element = window_info['window_element']
            if window_element:
                # Try to raise the window
                AXUIElementPerformAction(window_element, kAXRaiseAction)
                time.sleep(0.1)

                # Set it as focused
                AXUIElementSetAttributeValue(window_element, kAXFocusedAttribute, True)
                time.sleep(0.1)

            return True
        except Exception as e:
            log.error(f"Error focusing window on macOS: {e}")
            return False

    def _focus_window_windows(self, window_info):
        try:
            hwnd = window_info['hwnd']

            # Restore window if minimized
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

            # Bring to foreground
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.1)

            return True
        except Exception as e:
            log.error(f"Error focusing window on Windows: {e}")
            return False

    def send_shift_tab(self):
        with self.keyboard.pressed(Key.shift):
            self.keyboard.press(Key.tab)
            self.keyboard.release(Key.tab)
        time.sleep(0.05)

    def send_alt_shift_tab(self):
        with self.keyboard.pressed(Key.alt):
            with self.keyboard.pressed(Key.shift):
                self.keyboard.press(Key.tab)
                self.keyboard.release(Key.tab)
        time.sleep(0.05)

    def send_enter(self):
        self.keyboard.press(Key.enter)
        self.keyboard.release(Key.enter)
        time.sleep(0.05)

    def send_keys_to_window(self, window_info, keys_sequence):
        if not self.focus_window(window_info):
            log.error("Failed to focus window")
            return False

        time.sleep(0.3)

        # Send each key sequence
        for key_action in keys_sequence:
            key_action = key_action.lower().strip()

            if key_action == 'shift+tab':
                self.send_shift_tab()
            elif key_action == 'alt+shift+tab':
                self.send_alt_shift_tab()
            elif key_action == 'enter':
                self.send_enter()
            elif key_action == 'tab':
                self.keyboard.press(Key.tab)
                self.keyboard.release(Key.tab)
                time.sleep(0.05)
            else:
                log.error(f"Unknown key action: {key_action}")

        return True

    def find_and_click_jtdx_log_qso(self):
        """
            Find JTDX Log QSO window and simulate clicking OK button

            Returns:
                dict: {
                    'success': bool,
                    'message_type': str ('success', 'window_not_found', 'failed_to_send_keys', 'exception'),
                    'title': str,
                    'message': str,
                    'window_title': str or None
                }
        """
        try:
            # Get all windows
            windows = self.get_windows_list()

            # Search for JTDX Log QSO window
            target_window = None
            for window in windows:
                window_display = window.get('display', '')
                if "JTDX" in window_display and "Log QSO" in window_display:
                    target_window = window
                    break

            if target_window:
                success = self.send_keys_to_window(target_window, ['shift+tab', 'enter'])

                if success:
                    return {
                        'success': True,
                        'message_type': 'success',
                        'title': 'Test Successful',
                        'message': f"<p>Found and sent keys to:</p><p>{target_window['display']}</p>",
                        'window_title': target_window['display']
                    }
                else:
                    return {
                        'success': False,
                        'message_type': 'failed_to_send_keys',
                        'title': 'Test Failed',
                        'message': f"<p>Found window but failed to send keys:</p><p>{target_window['display']}</p>",
                        'window_title': target_window['display']
                    }
            else:
                return {
                    'success': False,
                    'message_type': 'window_not_found',
                    'title': 'Window Not Found',
                    'message': "<p>Could not find a window containing both JTDX and Log QSO.</p><p>Please make sure the JTDX Log QSO window is open and try again.</p>",
                    'window_title': None
                }

        except Exception as e:
            log.error(f"Error in find_and_click_jtdx_log_qso: {e}")
            return {
                'success': False,
                'message_type': 'exception',
                'title': 'Error',
                'message': f"<p>An error occurred while testing:</p><p>{str(e)}</p>",
                'window_title': None
            }

    @staticmethod
    def show_test_result_dialog(parent, result):
        dialog = QtWidgets.QDialog(parent)
        dialog.setWindowTitle(result['title'])
        dialog.setFixedWidth(400)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        message_label = CustomQLabel(result['message'])
        message_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        message_label.setWordWrap(True)
        message_label.setFont(CUSTOM_FONT)
        layout.addWidget(message_label)

        layout.addStretch()

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        ok_button = CustomButton(CommonStrings.OK())
        ok_button.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        dialog.exec()

def main():
    controller = WindowController()

    log.debug(f"Running on {platform.system()}\n")

    # Get list of all windows
    log.debug("Available windows:")
    windows = controller.get_windows_list()
    for i, window in enumerate(windows):
        log.warning(f"{i}: {window['display']}")

    if not windows:
        log.error("No windows found!")
        return

if __name__ == "__main__":
    main()
