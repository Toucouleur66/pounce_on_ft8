# The Main Window

The main window (`pounce_gui.pyw`) is where you watch decodes and steer the pounce engine.

## Layout, top to bottom

```
┌──────────────────────────────────────────────────────────────────┐
│  FOCUS VALUE (currently targeted decode)            12:34:56  UTC │  ← focus + clock bar
├──────────────────────────────────────────────────────────────────┤
│ [160m][80m][40m][30m][20m]…[6m]      │ Worked Callsigns (42):     │  ← band tabs + history
│  Wanted Callsign(s): [ TX5S, 3D2*  ]│  TX5S  20m  12:30          │
│  Monitored Callsign(s): [        ]  │  K1ABC 40m  12:18          │
│  Wanted CQ Zone(s): [ 31, 32     ]  │  …                         │
│  Excluded Callsign(s): [         ]  │                            │
├──────────────────────────────────────────────────────────────────┤
│ Time │Band│Rep│ DT │Freq│ Message        │•│Country│Zone│Cont│★   │  ← decodes table
│ 12:34│20m │-12│0.1 │1320│ CQ DX TX5S BG23│•│ Clipperton │…       │  │
├──────────────────────────────────────────────────────────────────┤
│ [filters – hidden, Ctrl+F to open]                          ▕▏   │  ← filter bar + activity bar
├──────────────────────────────────────────────────────────────────┤
│ (toggles)            [Clear] [Start Monitoring] [Stop all]        │  ← bottom bar
├──────────────────────────────────────────────────────────────────┤
│ FT8 · 14.074 · 12 pkts · 8MB · last 2s · ♥ ok · Master          │  ← status bar
└──────────────────────────────────────────────────────────────────┘
```

### Focus + clock bar

- **Focus label** (left): the decode currently being worked, plus a reason suffix
  (`/ WANTED`, `/ ZONE`, `/ MARATHON`, `/ GRID`, `/ WILDCARD`, `/ POLITENESS`).
- **UTC clock** (right): `HH:MM:SS`. Its background **alternates colour every FT8/FT4 period**,
  giving you a visual EVEN/ODD cadence cue at a glance.

### Band tabs

One tab per amateur band: **160, 80, 60, 40, 30, 20, 17, 15, 12, 10, 6, 4, 2 m and 70, 13, 3 cm**.
The tab matching the radio's dial frequency auto-selects; the active "operating" tab is
highlighted while monitoring. In [Slave mode](/guide/master-slave) the synced input fields are
greyed out (the Master owns them).

### Per-band input fields

Six comma-separated fields, each scoped to the selected band — see
[Wanted / Monitored / Excluded](/guide/targets) for full semantics.

### Worked Callsigns history

A panel on the right listing completed QSOs (`call · band · time`). It is persisted between
sessions. Right-click an entry to remove it; **View → Clear Worked Callsigns History** wipes it.

## The decodes table

Each row is one decoded message. Columns:

| Column | Meaning |
|---|---|
| **Time / Age** | Decode timestamp, or elapsed age — click the header to toggle. |
| **Band** | Band of the decode. |
| **Report** | SNR in dB. |
| **DT** | Time delta (sync offset) in seconds. |
| **Freq** | Audio offset in Hz. |
| **Message** | The raw decoded text. |
| **•** | LoTW indicator — the station uploads to LoTW. |
| **Country** | Resolved DXCC entity. |
| **CQ Zone** | Resolved CQ zone. |
| **Cont** | Continent. |
| **★ (WkB4)** | Worked-before marker / year (hidden when WkB4 mode = *Always*). |

### Row colours (priority cue)

| Colour | Meaning |
|---|---|
| Highlighted (top) | Station is **directed at your callsign** (answering you). |
| Black on yellow | **Wanted callsign**. |
| Salmon | **Wanted CQ zone**. |
| Yellow | **Wanted grid**. |
| Purple | **Monitored callsign**. |
| Cyan | **Monitored CQ zone**. |
| White on blue | A wanted call being **called by others**. |

## Right-click / left-click context menu

The context menu is band-scoped ("Apply to &lt;band&gt; band") and offers:

- Add / remove call to **Wanted**, **Monitored**, or **Excluded**
- **Make &lt;call&gt; your only Wanted Callsign**
- **Temporarily add &lt;call&gt; to Excluded** → opens the time picker (2 min … 1 month)
- Add / remove **CQ zone** to Monitored
- **Open QRZ.com for &lt;call&gt;**
- **Copy message to Clipboard**
- (history table) remove from Worked History

## Status bar

Click it to open **Settings**. It shows: mode (or "Waiting for data packets…"), frequency,
buffered packet count + memory usage, time since last decode, heartbeat status, and Master/Slave
connection info. The **background colour** reflects health:

- **Red** — connection lost
- **Yellow** — connected, no decodes yet
- **Green** — healthy, decoding
- **Blue-violet** — running as a **Slave** instance

## Activity bar

A thin vertical histogram on the far right showing live decode density / band busyness.

## Tray / menu-bar icon

- **Windows** — a blinking tray square indicates monitoring is active; right-click to quit.
- **macOS** — a status-menu agent; clicking raises the window and scrolls to the latest decode.

## Bottom bar buttons

- **Clear / Erase** — clear the decodes table.
- **Start Monitoring** — start the engine (cycles Monitoring → Decoding → Transmitting).
- **Stop all** — stop monitoring and any TX.
- **Restart** (macOS) — restart the app.

See the full [menu reference and shortcuts](/reference/shortcuts).
