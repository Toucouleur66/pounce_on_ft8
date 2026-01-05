"""
Subprocess helper to click JTDX OK button on Windows.
This must run in a separate process to avoid COM threading conflicts with PyQt6.
"""

import sys
import time
import os

def click_jtdx_ok_button(hwnd):
    import sys

    try:
        # Import here to ensure fresh loading
        from pywinauto import Application
        from pywinauto import timings
        import pythoncom

        print(f"Subprocess PID: {os.getpid()}", file=sys.stderr)
        print(f"Target HWND: {hwnd}", file=sys.stderr)

        # Force COM to uninitialize first, then reinitialize
        try:
            pythoncom.CoUninitialize()
        except:
            pass

        # Initialize COM in this thread
        try:
            result = pythoncom.CoInitialize()
            print(f"CoInitialize result: {result}", file=sys.stderr)
        except Exception as e:
            print(f"CoInitialize failed: {e}", file=sys.stderr)

        try:
            timings.Timings.window_find_timeout = 10

            # Add more debug output
            print(f"Connecting to hwnd {hwnd}...", file=sys.stderr)

            # Verify window exists first
            import win32gui
            if not win32gui.IsWindow(hwnd):
                print("FAIL:Window handle invalid", file=sys.stdout)
                return 1

            window_title = win32gui.GetWindowText(hwnd)
            print(f"Window title: {window_title}", file=sys.stderr)

            app = Application(backend='uia').connect(handle=hwnd, timeout=10)
            dialog = app.window(handle=hwnd)

            print("Connected! Waiting for accessibility...", file=sys.stderr)
            time.sleep(2.0)  # Longer wait

            print("Getting button descendants...", file=sys.stderr)

            # Try multiple times to get buttons (sometimes takes time to appear)
            buttons = []
            for attempt in range(3):
                buttons = dialog.descendants(control_type="Button")
                print(f"Attempt {attempt + 1}: Found {len(buttons)} buttons", file=sys.stderr)
                if len(buttons) > 0:
                    break
                time.sleep(1.0)
            print(f"Found {len(buttons)} buttons", file=sys.stderr)

            dialog_buttons = []
            for btn in buttons:
                try:
                    text = btn.window_text()
                    print(f"Button: '{text}'", file=sys.stderr)
                    if text not in ['Réduire', 'Agrandir', 'Fermer', 'Minimize', 'Maximize', 'Close']:
                        dialog_buttons.append({'control': btn, 'text': text})
                except:
                    pass

            print(f"Found {len(dialog_buttons)} dialog buttons", file=sys.stderr)

            if len(dialog_buttons) >= 1:
                ok_button = dialog_buttons[0]
                print(f"Clicking: '{ok_button['text']}'", file=sys.stderr)
                ok_button['control'].click()
                print("SUCCESS", file=sys.stdout)
                return 0
            else:
                print("FAIL:No buttons found", file=sys.stdout)
                return 1

        finally:
            pythoncom.CoUninitialize()

    except Exception as e:
        print(f"FAIL:{str(e)}", file=sys.stdout)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("FAIL:No hwnd provided", file=sys.stdout)
        sys.exit(1)

    hwnd = int(sys.argv[1])
    sys.exit(click_jtdx_ok_button(hwnd))
