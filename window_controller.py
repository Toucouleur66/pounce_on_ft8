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

        # Try to import pywinauto for Qt automation
        try:
            from pywinauto import Application
            PYWINAUTO_AVAILABLE = True
        except ImportError:
            PYWINAUTO_AVAILABLE = False
            log.warning("pywinauto not available. Install with: pip install pywinauto")
    except ImportError:
        log.error("Please install pywin32 and pynput: pip install pywin32 pynput")
        sys.exit(1)

def is_admin_windows():
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False


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
                app.activateWithOptions_(1)  
                time.sleep(0.2)  

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
        """Focus window on Windows - simplified version"""
        try:
            hwnd = window_info['hwnd']

            # Restore if minimized
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.2)

            # Bring to foreground
            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception as e:
                log.debug(f"SetForegroundWindow: {e}")

            time.sleep(0.3)
            return True

        except Exception as e:
            log.error(f"Error focusing window on Windows: {e}")
            return False

    def send_enter(self):
        """Send Enter key using pynput (used by macOS)"""
        self.keyboard.press(Key.enter)
        self.keyboard.release(Key.enter)
        time.sleep(0.05)

    def click_ok_button_jtdx(self, window_info):        
        if not self.focus_window(window_info):
            log.error("Failed to focus on JTDX window")
            return False

        time.sleep(0.3)

        if platform.system() == "Darwin":
            return self._click_ok_button_mac(window_info)
        elif platform.system() == "Windows":
            return self._click_ok_button_windows(window_info)

        return False

    def _click_ok_button_mac(self, window_info):
        try:
            window_element = window_info.get('window_element')
            if not window_element:
                log.error("No window_element in window_info")
                return False

            err, children = AXUIElementCopyAttributeValue(
                window_element,
                'AXChildren',
                None
            )

            if err != 0 or not children:
                log.error("Could not get window children")
                return False

            buttons = []
            self._find_buttons_recursive(children, buttons)

            valid_buttons = []
            for idx, btn in enumerate(buttons):
                err_title, title = AXUIElementCopyAttributeValue(btn, 'AXTitle', None)
                err_enabled, enabled = AXUIElementCopyAttributeValue(btn, 'AXEnabled', None)

                # Check if button has a title (skip disclosure triangles, etc.)
                if err_title == 0 and title:
                    # Check if enabled
                    is_enabled = (err_enabled != 0) or (enabled == True)
                    log.debug(f"Button {idx}: '{title}' (enabled: {is_enabled})")

                    if is_enabled:
                        valid_buttons.append(btn)
                else:
                    log.debug(f"Button {idx}: (no title, skipping)")

            log.debug(f"Found {len(valid_buttons)} valid buttons with titles")

            # Click the second-to-last button (OK is before Cancel)
            if len(valid_buttons) >= 2:
                # Second to last
                ok_button = valid_buttons[-2]  

                # Get title for confirmation
                err_title, title = AXUIElementCopyAttributeValue(ok_button, 'AXTitle', None)
                if err_title == 0 and title:
                    log.warning(f"Clicking button: '{title}' (second-to-last valid button)")

                # Focus the button first, then press Enter (more reliable than AXPress)
                from ApplicationServices import kAXFocusedAttribute
                AXUIElementSetAttributeValue(ok_button, kAXFocusedAttribute, True)
                time.sleep(0.1)
                self.send_enter()
                log.debug("Pressed Enter on focused button")
                return True

            elif len(valid_buttons) == 1:
                # Only one button, probably just OK
                from ApplicationServices import kAXFocusedAttribute
                AXUIElementSetAttributeValue(valid_buttons[0], kAXFocusedAttribute, True)
                time.sleep(0.1)
                self.send_enter()
                return True
            else:
                log.error("No valid buttons found")
                return False

        except Exception as e:
            log.error(f"Error in _click_ok_button_mac: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _find_buttons_recursive(self, elements, buttons):
        if not elements:
            return

        for element in elements:
            try:
                # Check if this is a button
                err_role, role = AXUIElementCopyAttributeValue(element, 'AXRole', None)
                if err_role == 0 and role == 'AXButton':
                    buttons.append(element)

                # Check children
                err_children, children = AXUIElementCopyAttributeValue(element, 'AXChildren', None)
                if err_children == 0 and children:
                    self._find_buttons_recursive(children, buttons)
            except:
                pass


    def _click_ok_button_windows(self, window_info):
        try:
            hwnd = window_info.get('hwnd')
            if not hwnd:
                log.error("No hwnd in window_info")
                return False

            if PYWINAUTO_AVAILABLE:
                log.warning("Using PyWinAuto subprocess to click OK button...")
                try:
                    import subprocess
                    import os

                    # Get path to subprocess helper script
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    subprocess_script = os.path.join(current_dir, 'jtdx_clicker_subprocess.py')

                    if not os.path.exists(subprocess_script):
                        log.error(f"Subprocess script not found: {subprocess_script}")
                        raise Exception("jtdx_clicker_subprocess.py not found")

                    # Run the subprocess with clean environment
                    log.debug(f"Running subprocess with hwnd {hwnd}...")

                    # Create clean environment without Qt variables
                    env = os.environ.copy()
                    # Remove Qt-related environment variables that might interfere
                    for key in list(env.keys()):
                        if 'QT' in key.upper() or 'PYQT' in key.upper():
                            del env[key]

                    result = subprocess.run(
                        [sys.executable, subprocess_script, str(hwnd)],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        env=env,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )

                    # Check result
                    output = result.stdout.strip()
                    log.warning(f"Subprocess output: {output}")
                    if result.stderr:
                        log.debug(f"Subprocess stderr: {result.stderr}")

                    if output == "SUCCESS":
                        log.warning("✓ Subprocess successfully clicked OK button!")
                        return True
                    else:
                        log.warning(f"Subprocess failed: {output}")

                except subprocess.TimeoutExpired:
                    log.error("Subprocess timed out")
                except Exception as e:
                    log.warning(f"Subprocess approach failed: {e}")

            # If pywinauto not available or failed, return False
            log.error("Failed to click OK button - pywinauto subprocess did not succeed")
            return False

        except Exception as e:
            log.error(f"Error in _click_ok_button_windows: {e}")
            import traceback
            traceback.print_exc()
            return False

    def find_and_click_jtdx_log_qso(self):
        try:
            if platform.system() == "Windows" and not is_admin_windows():
                return {
                    'success': False,
                    'message_type': 'admin_required',
                    'title': 'Administrator Rights Required',
                    'message': "<p>On Windows, this automation feature requires administrator privileges.</p>"
                              "<p>Please restart the application as Administrator to use this feature.</p>",
                    'window_title': None
                }

            windows = self.get_windows_list()

            target_window = None
            for window in windows:
                window_display = window.get('display', '')
                if "JTDX" in window_display and "Log QSO" in window_display:
                    target_window = window
                    break

            if target_window:
                # Use specialized method to click OK button
                success = self.click_ok_button_jtdx(target_window)

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
