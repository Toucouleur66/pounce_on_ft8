# tray_icon.py

import platform
import time
import threading

from PIL import Image, ImageDraw

from constants import (
    FG_COLOR_REGULAR_FOCUS,
    BG_COLOR_REGULAR_FOCUS,
    )

if platform.system() == 'Windows':
    from pystray import Icon, MenuItem

class TrayIcon:
    def __init__(self):
        self.color1 = FG_COLOR_REGULAR_FOCUS
        self.color2 = BG_COLOR_REGULAR_FOCUS
        self.current_color = self.color1
        self.icon = None
        self.blink_thread = None
        self._running = False

    def create_icon(self, color, size=(64, 64)):
        img = Image.new('RGB', size, color)
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, size[0], size[1]], fill=color)
        return img

    def blink_icon(self):
        while self._running:
            self.icon.icon = self.create_icon(self.current_color)
            self.icon.update_menu()
            self.current_color = self.color2 if self.current_color == self.color1 else self.color1
            time.sleep(1)

    def quit_action(self, icon):
        self._running = False
        icon.stop()

    def start(self):
        self._running = True
        self.icon = Icon('Pounce Icon', self.create_icon(self.color1))

        self.blink_thread = threading.Thread(target=self.blink_icon, daemon=True)
        self.blink_thread.start()

        self.icon.run()

    def stop(self):
        self._running = False
        if self.icon:
            self.icon.stop()
