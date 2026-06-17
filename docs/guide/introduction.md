# Introduction

**Wait and Pounce** (internal name *DX Pounce on FT8*) is a desktop assistant that automates
the act of *pouncing* on DX stations in the FT8 and FT4 digital modes. It does **not** decode
audio or key your transmitter directly — instead it cooperates with **WSJT-X** or **JTDX**,
which remain in charge of the radio and the protocol.

You declare your *targets* — specific callsigns, CQ zones, new grid squares, or DX-Marathon
entities — and Wait and Pounce monitors every decode WSJT-X produces. When a target is heard,
it instructs WSJT-X to reply, prioritising the most valuable contact when several appear in the
same transmit period.

## Why use it?

During a contest, a DXpedition, or a band opening, decodes scroll faster than any operator can
react to. Wait and Pounce:

- **Never misses a wanted station** — it reacts within ~200 ms of the decode.
- **Prioritises** — when five wanted stations decode at once, it picks the best one according to
  *your* priority order (wanted call → CQ zone → marathon → new grid → politeness).
- **Knows your logbook** — it reads your ADIF log so it won't waste time on stations you've
  already worked (configurable per-year, see [Worked-Before](/guide/worked-before)).
- **Tracks awards** — DX Marathon (one entity per year) and grid-chasing are built in.
- **Confirms automatically** — optional real-time upload to [LoTW](/guide/lotw) and
  [Club Log](/guide/clublog), and download of confirmations back into your log.

## Key facts

| | |
|---|---|
| **Modes** | FT8, FT4 (Regular, Fox/Hound, SuperFox) |
| **Companion software** | WSJT-X, JTDX (via UDP) |
| **Platforms** | Windows, macOS (Linux runnable from source) |
| **Language / toolkit** | Python 3, PyQt6 |
| **Default UDP port** | `2237` |
| **Current build** | 2.20 |
| **Languages (UI)** | English, Français, 中文, 日本語, Українська |
| **License/distribution** | Distributed via [SourceForge](https://sourceforge.net/projects/wait-and-pounce-ft8/) |

## The big picture

```
┌────────────┐   audio    ┌─────────────┐   UDP :2237   ┌──────────────────┐
│   Radio    │ ─────────► │  WSJT-X /   │ ◄───────────► │ Wait and Pounce  │
│  (CAT/PTT) │ ◄───────── │   JTDX      │   decodes /   │  (this program)  │
└────────────┘            └─────────────┘   replies      └──────────────────┘
                                                              │
                                       reads ADIF log, looks up DXCC/zone/grid,
                                       uploads to LoTW / Club Log, shows grid map
```

Wait and Pounce sits *beside* WSJT-X on the network. It receives the same decode packets WSJT-X
broadcasts, makes a decision, and sends back a **Reply packet** that tells WSJT-X to call the
chosen station — exactly as if you had double-clicked the decode yourself.

Continue to [How It Works](/guide/how-it-works) for the engine details, or jump to
[Installation & Setup](/guide/installation).
