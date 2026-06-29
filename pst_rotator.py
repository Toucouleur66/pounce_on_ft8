# pst_rotator.py
#
# PstRotatorAz antenna rotator control over UDP.
#
# Two automation sources feed into one rotator:
#   1. Wanted tracking  - when a wanted callsign is decoded, point the antenna at
#      the great-circle azimuth from my_grid to the wanted station's grid.
#   2. Hourly schedule  - rotate to a fixed azimuth at given UTC times.
#
# Wanted tracking takes priority: a freshly decoded wanted overrides the schedule.
# The schedule only fires when no recent wanted azimuth is holding the antenna.
#
# PREREQUISITES in PstRotatorAz:
#   - Communication > UDP Control Port > Port = <configured port> (default 12000)
#   - Setup > enable "UDP Control"

import re
import socket
import threading

from datetime import datetime, timezone

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from constants import (
    DEFAULT_PSTROTATOR_HOST,
    DEFAULT_PSTROTATOR_PORT,
)

from logger import get_logger

log = get_logger(__name__)

# Official PstRotatorAz UDP command format (see manual).
CMD_TRACK_ON = "<PST><TRACK>1</TRACK></PST>"
CMD_AZ_QUERY = "<PST>AZ?</PST>"

# How long (seconds) a wanted-driven azimuth holds the antenna before the
# hourly schedule is allowed to take over again.
WANTED_HOLD_SECONDS = 5 * 60

# How often (seconds) we poll PstRotatorAz for the current azimuth.
AZ_POLL_INTERVAL_SECONDS = 10

# Reply format on UDP port+1, e.g. "AZ:297.0".
_AZ_REPLY_RE = re.compile(r'AZ\s*[:=]\s*(-?\d+(?:\.\d+)?)', re.IGNORECASE)


def _cmd_azimuth(az):
    return f"<PST><AZIMUTH>{int(az)}</AZIMUTH></PST>"


class PstRotatorController(QObject):
    """
    Owns the UDP link to PstRotatorAz plus the hourly scheduler QTimer.
    Stateless about the GUI; it is driven entirely through configure() and
    handle_wanted_azimuth().

    Emits azimuth_read(float) every poll cycle with the rotator's current
    azimuth (or None when the rotator did not answer), so the GUI can display it.
    """

    azimuth_read = pyqtSignal(object)  # float current azimuth, or None on timeout

    def __init__(self, parent=None):
        super().__init__(parent)

        self.host = DEFAULT_PSTROTATOR_HOST
        self.port = DEFAULT_PSTROTATOR_PORT

        self.enable_wanted   = False
        self.enable_schedule = False

        # Schedule entries: list of dicts {'hour': int, 'minute': int, 'azimuth': int}
        self.schedule = []

        # Last azimuth actually sent, to avoid spamming identical commands.
        self._last_sent_azimuth = None

        # UTC timestamp of the last wanted-driven move (priority hold).
        self._last_wanted_time = None

        # Schedule slot already fired today, keyed by "HH:MM", to fire once per day.
        self._fired_slots = set()

        self._timer = QTimer(self)
        self._timer.setInterval(15_000)  # check the schedule every 15 s
        self._timer.timeout.connect(self._on_schedule_tick)

        # Background azimuth-polling thread (blocking recvfrom on port+1).
        self._poll_thread = None
        self._poll_stop = threading.Event()
        self._poll_lock = threading.Lock()

    """
        Configuration
    """
    def configure(self, params):
        """
        Apply settings coming from the params dict (saved by the settings dialog).
        Safe to call repeatedly (e.g. after the user changes settings).
        """
        self.host = params.get('pstrotator_host', DEFAULT_PSTROTATOR_HOST) or DEFAULT_PSTROTATOR_HOST
        try:
            self.port = int(params.get('pstrotator_port', DEFAULT_PSTROTATOR_PORT))
        except (TypeError, ValueError):
            self.port = DEFAULT_PSTROTATOR_PORT

        self.enable_wanted   = bool(params.get('enable_pstrotator_wanted', False))
        self.enable_schedule = bool(params.get('enable_pstrotator_schedule', False))
        self.schedule        = self._sanitize_schedule(params.get('pstrotator_schedule', []))

        if self.enable_schedule and self.schedule:
            if not self._timer.isActive():
                self._timer.start()
            # Re-evaluate the schedule immediately so a current slot applies on save.
            self._on_schedule_tick()
        else:
            self._timer.stop()

        # (Re)start the azimuth poller so it picks up any host/port change.
        self.start_polling()

        log.debug(
            f"PstRotator configured host={self.host} port={self.port} "
            f"wanted={self.enable_wanted} schedule={self.enable_schedule} "
            f"slots={len(self.schedule)}"
        )

    @staticmethod
    def _sanitize_schedule(raw):
        clean = []
        for entry in raw or []:
            try:
                hour    = int(entry.get('hour'))
                minute  = int(entry.get('minute'))
                azimuth = int(entry.get('azimuth'))
            except (AttributeError, TypeError, ValueError):
                continue
            if 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= azimuth <= 359:
                clean.append({'hour': hour, 'minute': minute, 'azimuth': azimuth})
        clean.sort(key=lambda e: (e['hour'], e['minute']))
        return clean

    """
        Wanted tracking
    """
    def handle_wanted_azimuth(self, azimuth):
        """
        Called by the GUI when a wanted callsign is decoded and its azimuth has
        been computed. Takes priority over the schedule.
        """
        if not self.enable_wanted or azimuth is None:
            return
        self._last_wanted_time = datetime.now(timezone.utc)
        log.info(f"PstRotator wanted tracking -> {azimuth}°")
        self._send_azimuth(azimuth)

    """
        Hourly schedule
    """
    def _on_schedule_tick(self):
        if not self.enable_schedule or not self.schedule:
            return

        now = datetime.now(timezone.utc)
        today_key = now.strftime('%Y%m%d')

        # Reset the per-day fired set when the date rolls over.
        if getattr(self, '_fired_day', None) != today_key:
            self._fired_day = today_key
            self._fired_slots = set()

        # Wanted tracking holds priority for a while after a wanted move.
        if self._wanted_hold_active(now):
            return

        for entry in self.schedule:
            slot_key = f"{entry['hour']:02d}:{entry['minute']:02d}"
            if slot_key in self._fired_slots:
                continue
            if now.hour == entry['hour'] and now.minute == entry['minute']:
                self._fired_slots.add(slot_key)
                log.info(f"PstRotator schedule {slot_key} UTC -> {entry['azimuth']}°")
                self._send_azimuth(entry['azimuth'])
                break

    def _wanted_hold_active(self, now):
        if self._last_wanted_time is None:
            return False
        return (now - self._last_wanted_time).total_seconds() < WANTED_HOLD_SECONDS

    """
        UDP transport
    """
    def _send_azimuth(self, azimuth):
        azimuth = int(azimuth)
        if azimuth == self._last_sent_azimuth:
            return

        # Force Tracking mode first, otherwise PstRotatorAz ignores the command.
        if self._send_udp(CMD_TRACK_ON):
            if self._send_udp(_cmd_azimuth(azimuth)):
                self._last_sent_azimuth = azimuth

    def _send_udp(self, message):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(2)
                sock.sendto(message.encode("ascii"), (self.host, self.port))
            log.debug(f"PstRotator UDP -> {self.host}:{self.port} | {message!r}")
            return True
        except OSError as e:
            log.error(f"PstRotator UDP error -> {e}")
            return False

    """
        Azimuth polling (current rotator position)

        PstRotatorAz answers <PST>AZ?</PST> on UDP port+1 with "AZ:297.0".
        We bind a listening socket on port+1, send the query to port, and read
        the reply. This runs in a daemon thread because recvfrom() blocks.
    """
    def start_polling(self):
        with self._poll_lock:
            # Restart the thread so a host/port change takes effect cleanly.
            self._poll_stop.set()
            if self._poll_thread is not None and self._poll_thread.is_alive():
                self._poll_thread.join(timeout=3)

            self._poll_stop = threading.Event()
            self._poll_thread = threading.Thread(
                target=self._poll_loop,
                args=(self.host, self.port, self._poll_stop),
                name="PstRotatorAzPoller",
                daemon=True,
            )
            self._poll_thread.start()

    def _poll_loop(self, host, port, stop_event):
        listen_port = port + 1
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(2)
            sock.bind(("", listen_port))
        except OSError as e:
            log.error(f"PstRotator poll: cannot bind UDP {listen_port} -> {e}")
            if sock is not None:
                sock.close()
            return

        log.debug(f"PstRotator poll started (query {host}:{port}, listen {listen_port})")

        while not stop_event.is_set():
            # Send the AZ query.
            try:
                sock.sendto(CMD_AZ_QUERY.encode("ascii"), (host, port))
            except OSError as e:
                log.debug(f"PstRotator poll send error -> {e}")

            # Read the reply (a single recvfrom; ignore if it times out).
            azimuth = None
            try:
                data, _ = sock.recvfrom(256)
                match = _AZ_REPLY_RE.search(data.decode("ascii", errors="ignore"))
                if match:
                    azimuth = float(match.group(1))
            except socket.timeout:
                pass
            except OSError as e:
                log.debug(f"PstRotator poll recv error -> {e}")

            self.azimuth_read.emit(azimuth)

            # Wait the poll interval, but wake up immediately on stop.
            stop_event.wait(AZ_POLL_INTERVAL_SECONDS)

        sock.close()
        log.debug("PstRotator poll stopped")

    def stop(self):
        self._timer.stop()
        with self._poll_lock:
            self._poll_stop.set()
            if self._poll_thread is not None and self._poll_thread.is_alive():
                self._poll_thread.join(timeout=3)
            self._poll_thread = None
