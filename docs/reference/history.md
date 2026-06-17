# Feature History

A timeline of how Wait and Pounce grew, reconstructed from the git history. It started in **July
2024** as a command-line frequency-hopping script and evolved into the full PyQt6 pounce assistant
documented here (build **2.20**).

## 2024 — From script to GUI

### July 2024 — Origins
- Initial command-line script: an FT8 listener that could **frequency-hop** and reply to a wanted
  callsign, with expected-sequence priorities.
- First **GUI** to launch/stop the script (Windows only).

### Sept–Oct 2024 — A real application
- Settings panel, enhanced GUI, log-analysis view, error/traceback capture.
- **Tooltips**, **sounds**, status updates from parsed packets.
- "Focus on wanted callsign" and **automatic QSO logging to ADIF** when a contact completes.

### Nov 2024 — The core matures
- **Watchdog** logic and TX-disabled handling; watchdog bypass setting.
- **Gap finder** (frequency suggestion / used-frequency collection).
- **Sound settings**, wildcard wanted callsigns, band-change sound.
- **ThemeManager** introduced; generic **PyInstaller builder**.
- Large refactor splitting `ToolTip`, `TrayIcon`, `ActivityBar`, `MonitoringSettings` into modules.

### Dec 2024 — Bands & frequency
- Separate **operating band** vs **selected tab**; per-band frequency awareness.
- Frequency range settings moved into the Settings dialog.

## 2025 — Logbook intelligence & multi-instance

### Jan 2025 — ADIF & priority
- **AdifMonitor** added — the app now reads your logbook continuously.
- Grid/report detection in message parsing; **ADIF summary dialog**.
- **Message priority buffer** — choose the best of several simultaneous decodes.
- Table size/row-limit management for performance.

### Feb 2025 — Lookup & marathon foundations
- **DXCC ADIF parsing**, larger callsign-lookup cache, sorted monitoring values.
- Context-menu entries; major **Listener refactor**; priority computed in the Listener (not GUI).

### Mar 2025 — Master / Slave
- The **multi-instance sync** system landed: `RequestSettingPacket` / `SettingPacket`, header
  prefixing for role detection, slave GUI handling, `apply_master_setting` /
  `restore_slave_settings`, `halt_packet` fixes.
- **Marathon** behaviour stabilised (`marathon_preference`).
- QTimer used instead of `time.sleep` to avoid GUI freezes.

### Apr–May 2025 — Polish & lookups
- Set frequency even with no decodes yet; GUI messages when the server can't open.
- Distinct sound when a wanted call decodes **for the first time**.
- **QRZ.com** lookup from the context menu; RawDataModel changes.
- Exact-callsign matching even on a grid-less CQ.

### Jun 2025 — Priority Manager & politeness
- **Politeness reply** setting.
- User-configurable **Priority Manager** (`PriorityTableWidget`, `get_priority_bonus`) — drag to
  order wanted / zone / marathon / grid / politeness.
- Better sound management.

### Mid/late 2025 — Maps, zones, telemetry
- **Active Users** window and **telemetry** service.
- **Club Log** real-time importer; **grid map** with worked/confirmed colouring, heatmap, and
  all-bands grid view; CQ-zone work.
- Theme refinements, dark-mode fixes, macOS window appearance.
- **Language selector** with Chinese, Japanese, French, Ukrainian translations.
- Improved ADIF analyzer; settings save optimised to a single load/save cycle.
- Callsign-lookup performance: CTY prefix index, `lru_cache`, larger local cache.

## 2026 — LoTW, JTDX automation, watchdog hardening

### Early 2026
- **LoTW** integration: uploader (TQSL), automatic upload, downloader to update ADIF files,
  `LoTWIncomingDialog`, "Show LoTW QSLs received".
- **JTDX auto-click**: window controller, admin-privilege checks, direct `pywinauto` usage,
  configurable click delay (slider), OK-button fallback.
- **Always on top**; **open log folder** button; spin-box → slider conversions.
- Clean shutdown (release multimedia/threads/handles before exit).

### Build 2.20 (current, `handle_slave` branch)
- **Watchdog settings** surfaced (enable / attempts / retry time).
- Watchdog threshold checked on all switch paths; recurring **`_schedule_watchdog_sweep`** timer so
  exclusions expire even with no decodes.
- Fixed `temporarily_excluded` so a timed exclusion no longer leaked into the permanent excluded
  list, with a clearer GUI message.
- **"Ask instance to halt TX"** — the watchdog now sends a Halt TX packet when giving up on a
  station.

::: info Branches
Development happens on feature branches (`handle_slave`, `heatmap`, `table_filters`,
`handle_message_priority`, `status_menu_agent`, …) that merge into `main`. This guide reflects
`handle_slave` at build 2.20.
:::
