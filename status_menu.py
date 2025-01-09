# status_menu.py

import objc
import CoreFoundation

from Foundation import NSTimer, NSObject

from AppKit import (
    NSApplication,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSMenu,
    NSMenuItem,
    NSView,
    NSMakeRect,
    NSBezierPath,
    NSColor,
    NSFont,
    NSAttributedString,
    NSForegroundColorAttributeName,
    NSFontAttributeName
)

from PyQt6 import QtCore

def color_from_hex(hex_str, alpha=1.0):
    if hex_str.startswith('#'):
        hex_str = hex_str[1:]
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return NSColor.colorWithSRGBRed_green_blue_alpha_(r, g, b, alpha)

class MyStatusBarView(NSView):
    def initWithFrame_(self, frame):
        self = objc.super(MyStatusBarView, self).initWithFrame_(frame)
        if self is None:
            return None

        self._text = "READY TO WAIT AND POUNCE"
        self._bgColorHex = "#000000"
        self._fgColorHex = "#FFFFFF"
        self._timer = None
        self._offset = 0.0
        self._direction = +1
        return self

    @objc.python_method
    def setTextAndColors(self, txt, bg, fg):
        self._text = txt
        self._bgColorHex = bg
        self._fgColorHex = fg
        self._offset = 0.0
        self._direction = +1
        self.setNeedsDisplay_(True)

    def startScrolling(self):
        if self._timer:
            self._timer.invalidate()
        self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.05, self, b'animate:', None, True
        )

    def stopScrolling(self):
        if self._timer:
            self._timer.invalidate()
            self._timer = None

    def animate_(self, timer):
        self._offset += self._direction
        self.setNeedsDisplay_(True)

    def drawRect_(self, rect):
        inset = 3
        sub_rect = NSMakeRect(
            rect.origin.x + inset,
            rect.origin.y + inset,
            rect.size.width - 2*inset,
            rect.size.height - 2*inset
        )

        path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            sub_rect, 3.0, 3.0
        )
        bg = color_from_hex(self._bgColorHex)
        bg.setFill()
        path.fill()

        fg = color_from_hex(self._fgColorHex)
        font = NSFont.fontWithName_size_("Monaco", 12) or NSFont.menuFontOfSize_(13)
        attr = {
            NSForegroundColorAttributeName: fg,
            NSFontAttributeName: font
        }
        text_to_draw = NSAttributedString.alloc().initWithString_attributes_(
            self._text, attr
        )
        text_size = text_to_draw.size()

        margin = 5.0
        W = sub_rect.size.width
        usable_width = W - 2*margin

        if text_size.width <= usable_width:
            x = sub_rect.origin.x + margin + (usable_width - text_size.width) / 2
        else:
            min_offset = usable_width - text_size.width
            max_offset = 0.0
            if self._offset < min_offset:
                self._offset = min_offset
                self._direction = +1
            elif self._offset > max_offset:
                self._offset = max_offset
                self._direction = -1
            x = sub_rect.origin.x + margin + self._offset

        y = sub_rect.origin.y + (sub_rect.size.height - text_size.height) / 2.0
        text_to_draw.drawAtPoint_((x, y))

    def mouseDown_(self, event):
        if self.delegate and hasattr(self.delegate, 'on_click'):
            self.delegate.on_click()

class AppDelegate(NSObject):
    def initWithSignal_(self, signal):
        self = objc.super(AppDelegate, self).init()
        if self is None:
            return None
        self.signal = signal 
        self.statusItem = None 
        self.view = None 
        return self

    def show_status_bar(self, text, bg_color, fg_color):
        if self.statusItem is None:
            self.statusItem = NSStatusBar.systemStatusBar().statusItemWithLength_(
                NSVariableStatusItemLength
            )
            view = MyStatusBarView.alloc().initWithFrame_(NSMakeRect(0, 0, 120, 22))
            view.startScrolling()
            view.delegate = self  
            self.statusItem.setView_(view)

            menu = NSMenu.alloc().init()
            quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Leave", "quitApp:", ""
            )
            menu.addItem_(quit_item)
            self.statusItem.setMenu_(menu)

            self.view = view

        if self.view:
            self.view.setTextAndColors(text, bg_color, fg_color)

    def hide_status_bar(self):
        if self.statusItem:
            NSStatusBar.systemStatusBar().removeStatusItem_(self.statusItem)
            self.statusItem = None
            self.view = None

    @objc.IBAction
    def quitApp_(self, sender):
        NSApplication.sharedApplication().terminate_(None)

    def on_click(self):
        if self.signal:
            print("AppDelegate: Emitting clicked signal")  
            self.signal.emit()

class StatusMenuAgent(QtCore.QObject):
    # Définir un signal pour les clics
    clicked = QtCore.pyqtSignal()

    def __init__(self):
        super(StatusMenuAgent, self).__init__() 
        self.app = NSApplication.sharedApplication()
        self.delegate = AppDelegate.alloc().initWithSignal_(self.clicked)
        self.app.setDelegate_(self.delegate)

    def run(self):
        pass

    def process_events(self):
        CoreFoundation.CFRunLoopRunInMode(CoreFoundation.kCFRunLoopDefaultMode, 0.01, False)

    def set_text_and_colors(self, text, bg_color, fg_color):
        if hasattr(self.delegate, 'view') and self.delegate.view:
            self.delegate.view.setTextAndColors(text, bg_color, fg_color)
        else:
            self.delegate.show_status_bar(text, bg_color, fg_color)

    def hide_status_bar(self):
        self.delegate.hide_status_bar()
