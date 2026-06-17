# Glossary

Terms used throughout this guide.

**ADIF** — *Amateur Data Interchange Format.* The standard text format for ham radio logbooks.
Wait and Pounce reads your ADIF log to know what you've worked and writes its own QSOs to an ADIF
backup.

**Band** — An amateur frequency range (160m … 3cm). All targets in Wait and Pounce are configured
*per band*.

**CQ Zone** — One of 40 worldwide zones defined by CQ magazine, used for awards (WAZ) and contests.
You can target whole zones.

**CTY / cty.xml** — Country-data files (from Club Log and country-files.com) that map callsign
prefixes to DXCC entities, CQ/ITU zones and coordinates.

**Confirmed** — A QSO that has a positive QSL (LoTW, paper, or eQSL). Distinct from merely
*worked*.

**DXCC** — *DX Century Club.* The ARRL award for working 100+ "entities" (countries). An *entity*
is one DXCC unit.

**DX Marathon** — The CQ award for working as many DXCC entities and zones as possible within a
calendar year. Wait and Pounce can auto-hunt needed entities.

**FT8 / FT4** — Weak-signal digital modes by Joe Taylor et al., decoded by WSJT-X / JTDX. FT8 uses
15-second transmit periods, FT4 uses ~6-second periods.

**Fox/Hound, SuperFox** — Special FT8 modes for DXpeditions where a "fox" works many "hounds"
efficiently. Affects the TX frequency window used by the gap finder.

**Gap Finder / Offset Updater** — The feature that moves your TX audio offset to a clear slot
before replying.

**Grid (Maidenhead locator)** — A compact geographic code (e.g. `JN18`). Grid-chasing is a popular
award pursuit.

**JTDX** — A fork of WSJT-X popular for weak-signal DX. Notable for a Log-QSO confirmation prompt
that Wait and Pounce can auto-click.

**LoTW** — *Logbook of The World*, ARRL's online confirmation service. Wait and Pounce uploads via
TQSL and downloads confirmations.

**Master / Slave** — Roles for multiple cooperating instances. The Master talks to WSJT-X and keys
the radio; Slaves mirror the config receive-only.

**Pounce** — To quickly reply to a wanted station the instant it decodes — the core action this app
automates.

**QSO** — A two-way radio contact.

**RR73 / RRR / 73** — FT8 acknowledgement messages. `RR73`/`RRR` confirm receipt; `73` is "best
regards" / end of QSO. Wait and Pounce uses these to detect a completed contact.

**SNR / Report** — Signal-to-noise ratio in dB, the "report" exchanged in FT8 (e.g. `−12`).

**TQSL** — ARRL's signing/uploading tool for LoTW. Required for LoTW uploads.

**UDP** — The network protocol WSJT-X uses to broadcast decodes and accept reply requests
(default port `2237`).

**Watchdog** — The mechanism that stops the app calling a station forever, temporarily excluding it
after a set number of attempts.

**WkB4 (Worked Before)** — Whether you've already worked a callsign on a band (any year). Controls
whether the engine will re-work it.

**WSJT-X** — The original weak-signal software by K1JT that Wait and Pounce works alongside.
