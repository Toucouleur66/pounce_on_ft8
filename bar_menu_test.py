import objc
import time

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

def ease_in_out_cubic(t):
    """
    Fonction d'easing InOutCubic.
    t doit être dans l'intervalle [0, 1].
    """
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - pow(-2 * t + 2, 3) / 2

class MyStatusView(NSView):
    def initWithFrame_(self, frame):
        self = objc.super(MyStatusView, self).initWithFrame_(frame)
        if self is None:
            return None

        self._text          = "F5UKW DU6/PE1NSQ RR73"
        self._bgColorHex    = BG_COLOR_FOCUS_MY_CALL
        self._fgColorHex    = FG_COLOR_FOCUS_MY_CALL

        self._timer         = None
        self._offset        = 0.0
        self._direction     = +1

        self.usable_width   = 0.0
        self.text_size      = NSMakeRect(0, 0, 0, 0)

        # Variables pour l'easing
        self.animation_duration = 1.0  # Durée totale d'une va-et-vient en secondes
        self.animation_start_time = None
        self.animation_direction = 1  # 1 pour aller, -1 pour revenir

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

        self.animation_start_time = time.time()
        self.animation_direction = 1  # Démarrer par l'aller

        self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.016, self, b'animate:', None, True  # ~60 FPS
        )

    def stopScrolling(self):
        if self._timer:
            self._timer.invalidate()
            self._timer = None
        self.animation_start_time = None

    def animate_(self, timer):
        current_time = time.time()
        elapsed = current_time - self.animation_start_time

        t = elapsed / self.animation_duration  # Progression [0, 1]

        if t > 1.0:
            t = 1.0

        eased_t = ease_in_out_cubic(t)

        # Calculer l'offset en fonction de la direction de l'animation
        if self.animation_direction == 1:
            # Aller de min_offset à max_offset
            self._offset = self.min_offset + (self.max_offset - self.min_offset) * eased_t
        else:
            # Revenir de max_offset à min_offset
            self._offset = self.max_offset - (self.max_offset - self.min_offset) * eased_t

        self.setNeedsDisplay_(True)

        if t >= 1.0:
            # Inverser la direction et réinitialiser le temps de départ
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
        self.text_size = text_size

        # Largeur totale disponible (dans sub_rect)
        W = sub_rect.size.width

        # --- MARGE à gauche et à droite ---
        margin = 5.0
        # zone "utile" pour le ping-pong = (W - 2*margin)
        self.usable_width = W - 2 * margin

        # Calcul du dépassement
        overflow = text_size.width - self.usable_width
        threshold = 10.0  # Seuil minimal pour animer

        if overflow <= 0 or overflow <= threshold:
            # Le texte tient dans la zone ou dépasse légèrement, centrer
            x = sub_rect.origin.x + margin + (self.usable_width - text_size.width) / 2.0
            self.stopScrolling()
            self._offset = x - (sub_rect.origin.x + margin)
        else:
            # Animation ping-pong avec easing
            self.min_offset = self.usable_width - text_size.width
            self.max_offset = 0.0

            if not self._timer:
                self.startScrolling()

            # Centrage vertical
            y = sub_rect.origin.y + (sub_rect.size.height - text_size.height) / 2.0

            # Dessin
            x = sub_rect.origin.x + margin + self._offset
            y = sub_rect.origin.y + (sub_rect.size.height - text_size.height) / 2.0
            text_to_draw.drawAtPoint_(NSMakePoint(x, y))
            return  # Exit early since animate_ will handle the drawing

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
