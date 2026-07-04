# What's New

Wait and Pounce keeps improving. This page lists the latest releases and then summarises the main
capabilities the program offers — written for users, not a line-by-line changelog. The current
version is **2.30**.

## Latest releases

### Version 2.30

- **Parks On The Air (POTA) hunting.** A new *Parks On The Air* settings tab with a single
  **Enable reply to POTA** switch. Wait and Pounce fetches live activator spots from
  [pota.app](https://pota.app), highlights matching decodes in green, and shows the park reference
  in the focus label. The same operator is called again whenever their park reference changes, and a
  **POTA** entry appears in the Priority Manager so you decide where park activators rank. See
  [Parks On The Air](/guide/pota).

### Version 2.21

- **Antenna rotator control (PstRotator).** A new *Antenna Rotator* settings tab lets Wait and
  Pounce steer your rotator (via PstRotator / PstRotatorAz) toward the station you're working, with:
  - automatic tracking of the wanted station's heading,
  - a **schedule** to change azimuth at the times you choose,
  - a configurable movement threshold, and an automatic **return to the previous azimuth** when
    tracking ends,
  - the live azimuth shown in the status bar while connected.
- **Double-click to reply.** Double-click any decode row to reply to that station immediately — and
  this works from an extra (receive-only) instance too, routed through the main copy.
- **DXCC Program tracking.** A setting to choose exactly which bands the entity check applies to,
  for DXCC-by-band hunting.
- **Time / Age hint.** A small symbol on the **Time** column header reminds you that you can click
  to switch to *Show age* mode, and back.

*Fixes:* Club Log real-time upload, smoother zoom on the grid map, and the harmless
temporary-folder warning on shutdown is gone.

### Version 2.20

- **Watchdog & retry settings.** Enable the watchdog, set the number of attempts and the retry
  time; a station that can't be completed is set aside *and* the radio is told to stop transmitting.
- **Automatic LoTW download.** New confirmations are pulled from LoTW and your logbook backup is
  updated automatically.
- **QO-100 satellite support.**
- **Open log folder** button to jump straight to where the logs are saved.

*Fix:* don't reply to a directed CQ (e.g. "CQ EU", "CQ NA", "CQ USA") unless your callsign matches
what the caller is asking for.

::: tip Full official changelog
The complete release notes for every version live in the application's README, also published at
[f5ukw.com/public/readme.txt](https://f5ukw.com/public/readme.txt).
:::

## Award hunting

- **DX Marathon** — chase every DXCC entity once per year, per band or across all bands.
- **DXCC Program by band** — track which bands still need a given entity.
- **Parks On The Air (POTA)** — reply to activators currently spotted on pota.app, re-calling the
  same operator each time their park reference changes.
- **Grid Tracker & map** — chase new grid squares regardless of band, with an interactive map that
  shows worked vs confirmed grids, a day/night line, and a live signal-density heatmap.
- **Worked-Before rules** — flexible per-year logic so you never waste time on dupes, while still
  being able to re-work a station for a new year.

## Smarter replying

- **Configurable priority** — decide the order in which wanted callsigns, CQ zones, marathon
  entities, new grids and politeness replies are chosen.
- **Best-of-the-batch selection** — when many stations decode at once, the best one is picked rather
  than whoever decoded first.
- **Double-click to reply** — override the automatic choice and call a station instantly.
- **Politeness reply** — never ignore a station that's calling you.
- **Clear-frequency finder** — automatically move your transmit slot to an open frequency.
- Filters to skip weak signals, invalid prefixes, or stations beaming at another continent.

## Station control

- **Antenna rotator** — point your beam at the station being worked, on a schedule or automatically,
  via PstRotator.
- **QO-100** and a wide range of HF/VHF/UHF bands, including 4 m, 2 m, 70 cm and 13 cm.

## Logbook & confirmations

- **Reads your ADIF logbook** continuously, so new contacts count immediately.
- **Built-in logbook analyzer** showing your worked totals per year and band.
- **Club Log** real-time upload.
- **Logbook of The World** upload and automatic confirmation download.

## Awareness & comfort

- **Colour-coded decodes**, a focus display telling you *why* a station was chosen, and a live
  activity bar.
- **Sound alerts** for wanted, monitored, and directed-to-you messages.
- **Grid map**, **Active Users** window, and a status bar that shows connection health at a glance.
- **Five languages** — English, Français, 中文, 日本語, Українська — and **Light / Dark / System**
  themes.
- **Compact and alternate views**, always-on-top, and a tray / menu-bar icon.

## Multi-station operating

- **Run several copies** — one main copy keys the radio; extra copies mirror its wanted lists and
  stay in sync without ever transmitting, ideal for multi-rig stations or a second monitoring
  screen. Double-click reply works from the extra copies too.

---

For downloads and the official release notes, see the
[SourceForge project page](https://sourceforge.net/projects/wait-and-pounce-ft8/).
