# Architecture

A developer-oriented map of the codebase. Wait and Pounce is a Python 3 / PyQt6 application; the
GUI thread stays responsive while a background thread runs the UDP listener and pounce engine.

## Threading model

```
Main (GUI) thread ── pounce_gui.pyw (MainWindow)
   │  signals/slots (Qt)
   ▼
Worker (QObject on a QThread) ── worker.py
   │  owns
   ▼
Listener ── wsjtx_listener.py
   ├── Receiver thread  ── receiver_worker.py  (socket → queue)
   ├── Processor thread ── processor_worker.py (queue → handlers)
   └── Watchdog sweep   ── threading.Timer (2 s)

AdifMonitor thread ── adif_monitor.py (polls files every 5 s)
   └── AdifProcessor ── adif_processor.py (parses in a separate OS process)
```

- The GUI never touches the socket directly — it sends Qt signals to the `Worker`, which mutates
  the live `Listener`.
- Settings changes are pushed into the running listener via `update_listener_settings()`.
- ADIF parsing runs in a **separate process** (`multiprocessing`) so big logbooks don't block.

## Module map

### Engine / networking
| File | Role |
|---|---|
| `wsjtx_listener.py` | `Listener` — UDP receive, packet dispatch, **all pounce/reply logic**, watchdog, logging, Master/Slave sync. |
| `worker.py` | `Worker` — hosts the Listener on a QThread; bridges GUI signals. |
| `receiver_worker.py` / `processor_worker.py` | Thin thread wrappers for receive/process loops. |
| `send_udp.py` | Standalone packet builder + CLI for **testing** the listener (not used in production). |
| `pywsjtx/` | Bundled WSJT-X UDP protocol library (packet classes + builders). |

### GUI
| File | Role |
|---|---|
| `pounce_gui.pyw` | Main window, menus, band tabs, table, status bar, workflows. |
| `setting_dialog.py` | The full Settings dialog (15 pages). |
| `raw_data_model.py` / `raw_data_filter_proxy_model.py` | Table model + filtering. |
| `context_menu_handler.py` | Right-click menu (table + grid map). |
| `grid_map_viewer.py` | Grid map window (QPainter over OSM tiles). |
| `active_users_window.py` | Live users (telemetry). |
| `adif_summary_dialog.py` | ADIF File Analyzer dialog. |
| `exclusion_dialog.py` | Temporary-exclusion duration picker. |
| `lotw_incoming_dialog.py` | LoTW confirmations viewer. |
| `tooltip.py`, `activity_bar.py`, `animated_*`, `custom_*`, `style.py`, `theme_manager.py` | UI widgets / styling. |
| `tray_icon.py`, `status_menu.py` | Tray (Windows) / menu-bar agent (macOS). |

### Data / lookup / logging
| File | Role |
|---|---|
| `callsign_lookup.py` | DXCC / CQ-zone / grid / LoTW resolution + caching. |
| `adif_monitor.py` / `adif_processor.py` | Watch + parse ADIF logs. |
| `lotw_uploader.py` / `lotw_sync_worker.py` / `lotw_manager.py` | LoTW upload (TQSL), confirmation download, user-activity cache. |
| `clublog.py` | Club Log real-time upload + `cty.xml` download. |
| `country_files.py` / `bulk_downloader.py` | Country-file management + bulk data download. |
| `monitoring_setting.py` | Thread-safe shared store of wanted/monitored/excluded + band. |
| `telemetry_service.py` | Heartbeat telemetry. |
| `updater.py` | Update check + reusable download dialog. |

### Support
| File | Role |
|---|---|
| `constants.py` | All constants, defaults, URLs, fonts. |
| `utils.py` | Message parsing (`parse_wsjtx_message`), band/grid/continent/WkB4 helpers, ADIF field parsing. |
| `translatable_strings.py` / `translations.py` | i18n strings + loader. |
| `logger.py` | Rotating file logging (`iLog`). |
| `version.py` | First-launch / version-change detection. |

## Key data structures

| Structure | Where | Shape |
|---|---|---|
| Wanted/monitored/excluded | `MonitoringSettings` | per-band lists + zones |
| Session worked | `Listener.worked_callsigns` | `{band: [call]}` (in-memory) |
| Worked history (UI) | `MainWindow.worked_callsigns_history` | list of dicts → `worked_callsigns.pkl` |
| Worked-before | ADIF parse | `year → band → {call}` |
| Marathon entities | ADIF parse + `wanted_callsigns_per_entity` | `band → {entity → [call]}` |
| Grids | ADIF parse | `band → grid → [qso]` |
| Reply buffer | `Listener.reply_message_buffer` | `deque` of candidates per period |
| Watchdog exclusions | `Listener.watchdog_exclusions` | `{call: expiry_utc}` |

See [UDP Protocol & Packets](/reference/udp-protocol) for the wire format and
[Files & Data Stores](/reference/files) for on-disk artefacts.
