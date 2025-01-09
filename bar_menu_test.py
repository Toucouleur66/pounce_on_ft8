import objc

from Foundation import NSTimer
from AppKit import (
    NSApplication, 
    NSStatusBar, 
    NSVariableStatusItemLength,
    NSMenu, 
    NSMenuItem,
    NSObject,
    NSApplicationActivationPolicyAccessory,
    NSRunningApplication, 
    NSApplicationActivateIgnoringOtherApps,
    NSColor, 
    NSFont, 
    NSAttributedString,
    NSMakeRect, 
    NSMakePoint, 
    NSBezierPath,
    NSView,
    NSForegroundColorAttributeName,
    NSFontAttributeName
)

from constants import (
    GUI_LABEL_NAME,
    BG_COLOR_FOCUS_MY_CALL,
    FG_COLOR_FOCUS_MY_CALL
)

def color_from_hex(hex_str, alpha=1.0):
    if hex_str.startswith('#'):
        hex_str = hex_str[1:]

    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0

    return NSColor.colorWithSRGBRed_green_blue_alpha_(r, g, b, alpha)

class MyStatusView(NSView):
    def initWithFrame_(self, frame):
        self = objc.super(MyStatusView, self).initWithFrame_(frame)
        if self is None:
            return None

        self._text          = "F5UKW DU6/PE1NSQ +12"
        self._bgColorHex    = BG_COLOR_FOCUS_MY_CALL
        self._fgColorHex    = FG_COLOR_FOCUS_MY_CALL

        self._timer         = None
        self._offset        = 0.0
        self._direction     = +1

        return self

    @objc.python_method
    def setText_(self, new_text):
        self._text = new_text

        self._offset = 0.0
        self._direction = +1
        self.setNeedsDisplay_(True)

    def startScrolling(self):
        if self._timer:
            self._timer.invalidate()
            self._timer = None

        self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.06, self, b'animate:', None, True
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
            rect.size.width - 2 * inset,
            rect.size.height - 2 * inset
        )

        corner_radius = 3.0
        rounded_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            sub_rect, corner_radius, corner_radius
        )
        bg_color = color_from_hex("#000000")  # noir
        bg_color.setFill()
        rounded_path.fill()

        # Préparation du texte (couleur + police)
        txt_color = color_from_hex("#01FFFF")  # cyan
        my_font = NSFont.fontWithName_size_("Monaco", 12)
        if not my_font:
            my_font = NSFont.menuFontOfSize_(13)

        attributes = {
            NSForegroundColorAttributeName: txt_color,
            NSFontAttributeName: my_font
        }
        text_to_draw = NSAttributedString.alloc().initWithString_attributes_(
            self._text, attributes
        )
        text_size = text_to_draw.size()

        # Largeur totale disponible (dans sub_rect)
        W = sub_rect.size.width

        # --- MARGE à gauche et à droite ---
        margin = 5.0
        # zone "utile" pour le ping-pong = (W - 2*margin)
        usable_width = W - 2 * margin

        # Si le texte rentre tout entier dans usable_width, on le centre => pas d'animation
        if text_size.width <= usable_width:
            x = sub_rect.origin.x + margin + (usable_width - text_size.width) / 2.0

        else:
            # -- Ping-pong --

            # min_offset = texte aligné à droite dans la zone "utile"
            # (valeur négative si text_size > usable_width)
            min_offset = usable_width - text_size.width
            # max_offset = 0 => texte aligné complètement à gauche (dans la zone "utile")
            max_offset = 0.0

            # Contrôle si offset sort des bornes
            if self._offset < min_offset:
                self._offset = min_offset
                self._direction = +1  # rebond => maintenant on va vers la gauche => droite
            elif self._offset > max_offset:
                self._offset = max_offset
                self._direction = -1  # rebond => on repart vers la droite => gauche

            # On applique la marge + offset
            x = sub_rect.origin.x + margin + self._offset

        # Centrage vertical
        y = sub_rect.origin.y + (sub_rect.size.height - text_size.height) / 2.0

        # Dessin
        text_to_draw.drawAtPoint_(NSMakePoint(x, y))

    def mouseDown_(self, event):
        """
        Clic => quitte l'application.
        """
        print("End of the program")
        NSApplication.sharedApplication().terminate_(None)


class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        """
        Création du status item, association de MyStatusView,
        et lancement de l'animation.
        """
        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength
        )

        custom_rect = NSMakeRect(0, 0, 100, 22)
        self.custom_view = MyStatusView.alloc().initWithFrame_(custom_rect)

        # On lance le défilement
        self.custom_view.startScrolling()

        self.status_item.setView_(self.custom_view)

        # Menu (clic droit) minimal
        self.menu = NSMenu.alloc().init()
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit", "quitApp:", ""
        )
        self.menu.addItem_(quit_item)
        self.status_item.setMenu_(self.menu)

    @objc.IBAction
    def quitApp_(self, sender):
        """Action du menu => quitter l'app."""
        NSApplication.sharedApplication().terminate_(None)


def main():
    app = NSApplication.sharedApplication()

    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)

    # Cache l'icône Dock
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    NSRunningApplication.currentApplication().activateWithOptions_(
        NSApplicationActivateIgnoringOtherApps
    )

    app.run()

if __name__ == "__main__":
    main()
