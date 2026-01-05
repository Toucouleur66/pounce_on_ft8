"""
Subprocess helper to click JTDX OK button on Windows.
This must run in a separate process to avoid COM threading conflicts with PyQt6.
"""

import sys
import time

def click_jtdx_ok_button(hwnd):
    try:
        from pywinauto import Application
        from pywinauto import timings
        import pythoncom

        pythoncom.CoInitialize()

        try:
            timings.Timings.window_find_timeout = 5
            app = Application(backend='uia').connect(handle=hwnd, timeout=5)
            dialog = app.window(handle=hwnd)
            time.sleep(1.0)

            buttons = dialog.descendants(control_type="Button")
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
