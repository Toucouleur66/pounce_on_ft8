# All Settings

The **Settings** window has a list of pages down the left side, with **OK** and **Cancel** at the
bottom. Open it from the menu (<kbd>Ctrl</kbd>+<kbd>,</kbd>) or by clicking the status bar. A few
options — language, theme and privacy — live in the main menus instead.

[[toc]]

## Server (network) {#server-udp}

Three network connections, each with an on/off checkbox plus a **server address** and **port**:

- **Main connection** — the link to WSJT-X / JTDX (default `127.0.0.1`, port `2237`).
- **Secondary forwarding** — pass decodes on to another address, such as a second copy of Wait and
  Pounce or a logging program. This is what powers [running several instances](/guide/master-slave).
- **External logging program** — forward to a separate logger.

Also here: **Enable auto start monitoring when program launched**.

## General Settings

- **Enable reply** — the master switch for transmitting.
- **Enable polite reply** — answer stations calling you even if they aren't wanted.
- **Log all valid contacts (not only from Wanted)**.
- **Ignore callsign if prefix is invalid**.
- **Ignore callsign if it targets another continent**.
- **Minimum report** — ignore signals weaker than this (+10 dB down to −26 dB).

## Watchdog and retry

- **Enable Watchdog**
- **Number of attempts** before giving up on a station
- **Wait time** (minutes) the station stays set aside

See [Watchdog & Exclusions](/guide/watchdog).

## Offset Updater (clear-frequency finder)

- **Enable frequencies offset updater**
- Mode: **Normal / Fox-Hound / SuperFox / Custom**
- **Min Freq** / **Max Freq** — the part of the passband to search

See [Finding a Clear Frequency](/guide/gap-finder).

## Sound Alerts

- **Message from any Wanted Callsign**
- **Message directed to my Callsign**
- **Message from any Monitored Callsign**
- **Delay between each monitored callsign detected** (seconds)

See [Sound Alerts](/guide/sounds).

## Logbook of The World

- **Enable reply only for callsigns that use LoTW**
- **Enable automatic synch to LoTW**
- **Username / Password / Station Location / Signing Password**
- **Download QSLs since** (date)
- **Download interval** (minutes)
- **TQSL Path** / **.tqsl Folder**
- **Test Upload Last QSO** / **Test Download QSLs**

See [Logbook of The World](/guide/lotw).

## DX Marathon

- A button per band to enable marathon hunting
- **Unlimited** — work each entity once on any band

See [DX Marathon](/guide/marathon).

## Grid Tracker

- **Enable grid tracker to reply to callsign if new grid regardless of band**
- A button per band
- **Reply to callsign if grid not yet confirmed and not worked before**

See [Grid Tracker & Map](/guide/grid-tracker).

## Priority Manager

- **Maximum number of attempts** (4–30)
- **Maximum waiting delay** (1–10 min)
- The drag-and-drop **priority order** list

See [Choosing Who to Reply To](/guide/reply-engine).

## Logbook Analysis

- **Select new ADIF File for analysis**
- The file list, with **Summary** and **Clear**

See [Your Logbook](/guide/adif).

## Worked before

A choice that appears once you've loaded a logbook:

- **Reply to any Wanted Callsign even if Worked Before**
- **Reply to Wanted Callsign if not Worked Before in current year**
- **Do not reply to any Callsign Worked Before** *(default)*

See [Worked-Before](/guide/worked-before).

## Club Log

- **Enable automatic upload to Club Log**
- **Email** (your registered Club Log email)
- **API Key**
- **Callsign** (your station callsign)

See [Club Log](/guide/clublog).

## Logbook Backup

- Choose where Wait and Pounce keeps its own backup copy of the contacts it logs.

## Automate tasks (JTDX auto-click)

- **Close JTDX Log QSO window prompt** + **Test it**
- **Delay before clicking** (0–30 s)
- **Test Windows Monitoring Permissions**

See [JTDX Auto-Click](/guide/jtdx-autoclick).

## Debugging

For diagnosing problems (see [Troubleshooting](/guide/troubleshooting)):

- **Save debugging to log**
- **Log extra detail**
- **Enable pounce log**
- **Open log folder**

## Useful defaults

| Setting | Default |
|---|---|
| Network port | 2237 |
| Watchdog | off · 10 attempts · 20 minutes |
| Maximum waiting delay | 2 minutes |
| Minimum report | −25 dB |
| Delay between monitored sounds | 120 seconds |
| LoTW download interval | 10 minutes |
| JTDX click delay | 0 seconds |
