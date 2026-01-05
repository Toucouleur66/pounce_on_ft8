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
                log.warning("Could not get window children, trying tab fallback")
                return self._click_ok_button_tab_fallback()

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
                log.warning("No valid buttons found, trying tab fallback")
                return self._click_ok_button_tab_fallback()

        except Exception as e:
            log.error(f"Error in _click_ok_button_mac: {e}")
            import traceback
            traceback.print_exc()
            return self._click_ok_button_tab_fallback()

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

    def _click_ok_button_tab_fallback(self):
        log.debug("Using Shift+Tab fallback method")

        for i in range(3):
            self.send_shift_tab()
            time.sleep(0.1)

        self.send_enter()
        return True

    def _click_ok_button_windows(self, window_info):
        try:
            hwnd = window_info.get('hwnd')
            if not hwnd:
                log.error("No hwnd in window_info")
                return False

            # Find all button controls in the window
            buttons = []

            def enum_child_callback(child_hwnd, _):
                try:
                    class_name = win32gui.GetClassName(child_hwnd)
                    if 'button' in class_name.lower():
                        control_text = win32gui.GetWindowText(child_hwnd)
                        buttons.append({
                            'hwnd': child_hwnd,
                            'text': control_text,
                            'class': class_name
                        })
                        log.debug(f"Found button: '{control_text}' (class: {class_name})")
                except:
                    pass
                return True

            # Enumerate all child windows (controls)
            win32gui.EnumChildWindows(hwnd, enum_child_callback, None)

            log.debug(f"Found {len(buttons)} buttons in window")

            # Click the second-to-last button (OK is before Cancel)
            if len(buttons) >= 2:
                ok_button = buttons[-2]  # Second to last
                log.debug(f"Clicking button: '{ok_button['text']}' (second-to-last button)")

                # Set focus and click
                try:
                    win32gui.SetFocus(ok_button['hwnd'])
                    time.sleep(0.1)
                    self.send_enter()
                    log.debug("Successfully clicked OK button")
                    return True
                except Exception as e:
                    log.warning(f"Failed to focus button: {e}, trying tab fallback")
                    return self._click_ok_button_tab_fallback()

            elif len(buttons) == 1:
                # Only one button, probably just OK
                log.debug("Only one button found, clicking it")
                try:
                    win32gui.SetFocus(buttons[0]['hwnd'])
                    time.sleep(0.1)
                    self.send_enter()
                    return True
                except:
                    return self._click_ok_button_tab_fallback()
            else:
                log.warning("No buttons found, trying tab fallback")
                return self._click_ok_button_tab_fallback()

        except Exception as e:
            log.error(f"Error in _click_ok_button_windows: {e}")
            return self._click_ok_button_tab_fallback()

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
