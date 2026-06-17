# All Settings

The **Settings** dialog (`setting_dialog.py`) uses a left **sidebar of pages** (not tabs) with
**OK / Cancel**. Open it from the App menu (<kbd>Ctrl</kbd>+<kbd>,</kbd>) or by clicking the status
bar. Language, theme, master/slave and telemetry are **not** here — they live in the menus.

[[toc]]

## Server (UDP) {#server-udp}

Three independent UDP endpoints, each with an enable checkbox plus **UDP Server:** address and
**UDP Server port number:**:

- **Main UDP instance** — the WSJT-X/JTDX server (default `127.0.0.1:2237`).
- **Secondary UDP forwarding** — re-broadcast packets to another address (a Slave instance or a
  logging program). This is what powers [Master/Slave sync](/guide/master-slave).
- **External logging program** — forward to a logger that consumes WSJT-X UDP.

Also: **Enable auto start monitoring when program launched**.

## General Settings

- **Enable reply** — master switch for transmitting.
- **Enable polite reply** — answer stations calling you even if not wanted.
- **Log all valid contacts (not only from Wanted)**.
- **Ignore callsign if prefix is invalid**.
- **Ignore callsign if it targets another continent**.
- **Minimum report** — SNR threshold dropdown (`+10` … `−26 dB`).

## Watchdog and retry

- **Enable Watchdog**
- **Number of attempts** (1–9999)
- **Wait time** in minutes (1–9999)

See [Watchdog & Exclusions](/guide/watchdog).

## Offset Updater (Gap Finder)

- **Enable frequencies offset updater**
- Mode selector: **Normal / Fox-Hound / SuperFox / Custom**
- **Min Freq (Hz)** / **Max Freq (Hz)** (0–10000)

See [Offset / Gap Finder](/guide/gap-finder).

## Sound Alerts

- **Message from any Wanted Callsign**
- **Message directed to my Callsign**
- **Message from any Monitored Callsign**
- **Delay between each monitored callsigns detected** (seconds)

## Logbook of The World

- **Enable reply only for callsigns that use LoTW**
- **Enable automatic synch to LoTW**
- **Username / Password / Station Location / Signing Password**
- **Download QSLs since (UTC)**
- **Download interval (minutes)** (5–1440)
- **TQSL Path** / **.tqsl Folder** (Browse)
- **Test Upload Last QSO** / **Test Download QSLs**

See [LoTW](/guide/lotw).

## DX Marathon

- Per-band checkable buttons
- **Unlimited** (mutually exclusive, any-band)

See [DX Marathon](/guide/marathon).

## Grid Tracker

- **Enable grid tracker to reply to callsign if new grid regardless of band**
- Per-band button grid
- **Reply to callsign if grid not yet confirmed and not worked before**

See [Grid Tracker](/guide/grid-tracker).

## Priority Manager

- **Maximum number of attempts** (4–30)
- **Maximum waiting delay** (1–10 min)
- Drag-and-drop **Priority / Reply to** order table

See [Reply & Priority Engine](/guide/reply-engine).

## Logbook Analysis (ADIF)

- **Select new ADIF File for analysis**
- File table · **Summary** · **Clear**

See [ADIF Logbook Analysis](/guide/adif).

## Worked before

Radio group (appears once an ADIF file is loaded):

- **Reply to any Wanted Callsign even if Worked B4**
- **Reply to Wanted Callsign if not Worked B4 in current year (YYYY)**
- **Do not reply to any Callsign Worked B4** *(default)*

See [Worked-Before](/guide/worked-before).

## Club Log

- **Enable automatic upload to Club Log**
- **Email** (labelled "Callsign:" — enter your registered email)
- **API Key**
- **Callsign** (your station callsign)

See [Club Log](/guide/clublog).

## Logbook Backup

- **Select File** + path field + status info — backup location for the app's own log.

## Automate tasks (JTDX auto-click)

- **Close JTDX Log QSO window prompt** + **Test it**
- **Delay before clicking** slider (0–30 s)
- **Test Windows Monitoring Permissions**

See [JTDX Auto-Click](/guide/jtdx-autoclick).

## Debugging

- **Save debugging to log**
- **Log UDP packet data**
- **Enable extra GUI debug output**
- **Enable pounce log**
- **Open log folder**

## Default values

Key defaults from `constants.py`:

| Constant | Default |
|---|---|
| UDP port | `2237` |
| Watchdog | off · 10 attempts · 20 min |
| Max reply attempts | 10 |
| Max waiting delay | 2 min |
| Minimum report | −25 dB |
| Delay between sounds | 120 s |
| Reply debounce | 200 ms |
| Heartbeat timeout | 30 s |
| Band-change settle | 10 s |
| LoTW download interval | 10 min (5–1440) |
| JTDX click delay | 0 s |
