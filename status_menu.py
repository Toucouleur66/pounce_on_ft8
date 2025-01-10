# status_menu.py

import objc
import time
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
    NSMakePoint, 
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

def ease_in_out_cubic(t):
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - pow(-2 * t + 2, 3) / 2

class MyStatusBarView(NSView):
    def initWithFrame_(self, frame):
        self = objc.super(MyStatusBarView, self).initWithFrame_(frame)
        if self is None:
            return None

        self._text                  = ''
        self._bgColorHex            = '#000000'
        self._fgColorHex            = '#FFFFFF'
        self._timer                 = None
        self._offset                = 0.0
        self._direction             = +1

        self.animation_duration     = 2.3
        self.animation_start_time   = None
        self.animation_direction    = 1

        self.text_size              = None
        self.usable_width           = 0.0
        self.min_offset             = 0.0
        self.max_offset             = 0.0

        return self

    @objc.python_method
    def setTextAndColors(self, txt, bg, fg):
        self._text       = txt
        self._bgColorHex = bg
        self._fgColorHex = fg
        self._offset     = 0.0
        self._direction  = +1
        self.stopScrolling()

        fg_color = color_from_hex(self._fgColorHex)
        font = NSFont.fontWithName_size_("Monaco", 12) or NSFont.menuFontOfSize_(13)
        attributes = {
            NSForegroundColorAttributeName: fg_color,
            NSFontAttributeName: font
        }
        text_to_draw = NSAttributedString.alloc().initWithString_attributes_(self._text, attributes)
        text_size = text_to_draw.size()
        self.text_size = text_size

        inset = 3
        margin = 4.0
        self.usable_width = self.frame().size.width - 2 * margin - 2 * inset

        overflow = text_size.width - self.usable_width
        threshold = 10.0

        if overflow > threshold:
            scroll_range = text_size.width - self.usable_width
            self.min_offset = -scroll_range / 2
            self.max_offset = scroll_range / 2
            self._offset = self.min_offset
            self.animation_start_time = time.time()
            self.animation_direction = 1
            self.startScrolling()
        else:
            self._offset = 0.0

        self.setNeedsDisplay_(True)

    def startScrolling(self):
        if self._timer:
            self._timer.invalidate()
            self._timer = None

        self.animation_start_time = time.time()
        self.animation_direction  = 1 

        self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.016, self, b'animate:', None, True  
        )

    def stopScrolling(self):
        if self._timer:
            self._timer.invalidate()
            self._timer = None
        self.animation_start_time = None    

    def animate_(self, timer):
        if not self.animation_start_time:
            return

        current_time = time.time()
        elapsed = current_time - self.animation_start_time

        t = elapsed / self.animation_duration  

        if t > 1.0:
            t = 1.0

        eased_t = ease_in_out_cubic(t)

        if self.animation_direction == 1:
            self._offset = self.min_offset + (self.max_offset - self.min_offset) * eased_t
        else:
            self._offset = self.max_offset - (self.max_offset - self.min_offset) * eased_t

        self.setNeedsDisplay_(True)

        if t >= 1.0:
            self.animation_direction *= -1
            self.animation_start_time = current_time

    def drawRect_(self, rect):
        inset = 3

        sub_rect = NSMakeRect(
            rect.origin.x + inset,
            rect.origin.y + inset,
            rect.size.width - 2 * inset,
            rect.size.height - 2 * inset
        )

        corner_radius = 3.0
        rounded_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            sub_rect, corner_radius, corner_radius
        )
        
        rounded_path.setClip()
                    
        bg_color = color_from_hex(self._bgColorHex)
        bg_color.setFill()
        rounded_path.fill()

        fg_color = color_from_hex(self._fgColorHex)
        font = NSFont.fontWithName_size_("Monaco", 12) or NSFont.menuFontOfSize_(13)
        attributes = {
            NSForegroundColorAttributeName: fg_color,
            NSFontAttributeName: font
        }
        text_to_draw = NSAttributedString.alloc().initWithString_attributes_(self._text, attributes)

        if self.text_size and self.usable_width:
            x_center = sub_rect.origin.x + (sub_rect.size.width - self.text_size.width) / 2.0
            x = x_center + self._offset
            y = sub_rect.origin.y + (sub_rect.size.height - self.text_size.height) / 2.0
            text_to_draw.drawAtPoint_(NSMakePoint(x, y))

    def mouseDown_(self, event):
        if self.delegate and hasattr(self.delegate, 'on_click'):
            self.delegate.on_click()

class AppDelegate(NSObject):
    def initWithSignal_(self, signal):
        self = objc.super(AppDelegate, self).init()
        if self is None:
            return None
        self.signal     = signal 
        self.statusItem = None 
        self.view       = None 

        return self

    def show_status_bar(self, text, bg_color, fg_color):
        if self.statusItem is None:
            self.statusItem = NSStatusBar.systemStatusBar().statusItemWithLength_(
                NSVariableStatusItemLength
            )
            view = MyStatusBarView.alloc().initWithFrame_(NSMakeRect(0, 0, 90, 22))
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
            # print("AppDelegate: Emitting clicked signal")  
            self.signal.emit()

class StatusMenuAgent(QtCore.QObject):
    clicked = QtCore.pyqtSignal()

    def __init__(self):
        super(StatusMenuAgent, self).__init__() 
        self.delegate = AppDelegate.alloc().initWithSignal_(self.clicked)
        self.thread = QtCore.QThread()
        self.moveToThread(self.thread)
        self.thread.started.connect(self.run)
        self.thread.start()

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
