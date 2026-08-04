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
- **Do not reply to callsigns longer than** — skip unusually long callsigns (special event / compound
  calls) above a length you set.
- **Minimum report** — ignore signals weaker than this (+10 dB down to −26 dB).

## Watchdog and retry

- **Enable Watchdog** — the single attempts limit; when off, attempts are unlimited
- **Number of attempts** (1–20) before giving up on a station
- **Wait time** (2–30 minutes) the station stays set aside

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
- **Enable automatic upload of logged QSOs to LoTW** — upload and download are now separate switches,
  so you can turn on one, the other, or both.
- **Enable automatic download of QSLs from LoTW**
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

## Antenna Rotator

- **PstRotatorAz Connection** — UDP Server address + port, and the live **Current azimuth**.
- **Track on Reply** — *Point the antenna at every station we reply to*, with a per-band selector and
  an *Only move if azimuth changes by more than* threshold.
- **Return to Previous Position** — *Return the antenna to its previous azimuth when idle*, after a
  configurable number of minutes with no reply.
- **Hourly Schedule** — *Rotate to a fixed azimuth at given times (UTC)*, with a Time / Azimuth
  table.

See [Antenna Rotator](/guide/rotator).

## DXCC Program

- Per-band buttons to choose which bands the entity check applies to (all-time, regardless of year).
- **Keep replying to an entity until it is confirmed (QSL)** — keep calling stations from a needed
  entity until you have a confirmation, not just a contact.
- **Unlimited** — chase any DXCC entity not yet worked on any band.

## Parks On The Air

- **Enable reply to POTA** — reply to activators currently spotted on
  [pota.app](https://pota.app). Live FT8/FT4 spots are fetched every few minutes; a matched
  activator is highlighted in green and its park reference is shown in the focus label. When
  enabled, a **POTA** entry appears in the Reply Rules order.

See [Parks On The Air](/guide/pota).

## Reply Rules

- The drag-and-drop **reply order** list (top row = highest priority)
- **Excluded Callsigns** and **Excluded Zones** appear as reorderable rows: a target above an
  exclusion row is still called, a target below it is blocked

See [Choosing Who to Reply To](/guide/reply-engine).

## Logbook Analysis

- **Select new ADIF File for analysis**
- The file list, with **Summary** and **Clear**
- **Ignore entries if prop_mode is set to SAT in ADIF Files** — skip satellite QSOs so they don't
  count toward your HF worked / worked-before / marathon tracking.

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
| Minimum report | −25 dB |
| Delay between monitored sounds | 120 seconds |
| LoTW download interval | 10 minutes |
| JTDX click delay | 0 seconds |
