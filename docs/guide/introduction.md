# Introduction

**Wait and Pounce** is a desktop assistant that automates the act of *pouncing* on DX stations in
the FT8 and FT4 digital modes. It does **not** decode audio or key your transmitter directly —
instead it works together with **WSJT-X** or **JTDX**, which stay in charge of the radio and the
mode.

You declare your *targets* — specific callsigns, CQ zones, new grid squares, or DX-Marathon
entities — and Wait and Pounce watches every decode. When a target is heard, it tells WSJT-X to
reply, picking the most valuable contact when several appear at the same time.

## Why use it?

During a contest, a DXpedition, or a band opening, decodes scroll faster than any operator can
react to. Wait and Pounce:

- **Never misses a wanted station** — it reacts almost instantly to a decode.
- **Prioritises** — when five wanted stations decode at once, it picks the best one according to
  *your* priority order (wanted call → CQ zone → marathon → new grid → politeness).
- **Knows your logbook** — it reads your log so it won't waste time on stations you've already
  worked (with flexible per-year rules — see [Worked-Before](/guide/worked-before)).
- **Tracks awards** — DX Marathon (one entity per year) and grid-chasing are built in.
- **Confirms automatically** — optional upload to [LoTW](/guide/lotw) and [Club Log](/guide/clublog),
  and download of confirmations back into your log.

## Key facts

| | |
|---|---|
| **Modes** | FT8, FT4 (Regular, Fox/Hound, SuperFox) |
| **Works with** | WSJT-X, JTDX |
| **Platforms** | Windows, macOS |
| **Languages** | English, Français, 中文, 日本語, Українська |
| **Where to get it** | [SourceForge](https://sourceforge.net/projects/wait-and-pounce-ft8/) |

## The big picture

```
┌────────────┐   audio    ┌─────────────┐   network   ┌──────────────────┐
│   Radio    │ ─────────► │  WSJT-X /   │ ◄─────────► │ Wait and Pounce  │
│            │ ◄───────── │   JTDX      │  decodes /   │  (this program)  │
└────────────┘            └─────────────┘   replies     └──────────────────┘
                                                              │
                                       reads your logbook, identifies country /
                                       zone / grid, uploads to LoTW & Club Log,
                                       shows a live grid map
```

Wait and Pounce sits *beside* WSJT-X. It sees the same decodes, makes a decision, and tells WSJT-X
to call the chosen station — exactly as if you had double-clicked the decode yourself.

Continue to [How It Decides Who to Call](/guide/how-it-works), or jump straight to
[Installation & Setup](/guide/installation).
