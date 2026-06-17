# How It Works

This page explains the engine behind Wait and Pounce — the path a single FT8 decode takes from
the network to a reply keying your radio. Understanding it makes every setting easier to reason
about.

## The pipeline at a glance

```
WSJT-X UDP ──► Receiver thread ──► Queue ──► Processor thread ──► assign_packet()
                                                                       │
                          ┌────────────────────────────────────────────┤
                          ▼                ▼                ▼            ▼
                    HeartBeat        Status         Decode        Setting/Reply/…
                          │                │                │
                          │       updates band/freq/   handle_decode_packet()
                          │       my_call/mode             │
                          │                          parse + classify
                          │                          (wanted? zone? grid?
                          │                           marathon? excluded?
                          │                           worked-before?)
                          │                                │
                          │                        reply_message_buffer (deque)
                          │                                │
                          │                   debounce 200 ms, pick highest
                          │                   priority of this TX period
                          │                                │
                          │                        process_pending_reply()
                          │                                │
                          │                   reply_to_packet()  ──► WSJT-X Reply packet
                          ▼                                            (keys the radio)
                  liveness / sync
```

The core lives in **`wsjtx_listener.py`** in a class called `Listener`, hosted on a background
thread by **`worker.py`** so the GUI never blocks.

## 1. Receiving packets

Wait and Pounce opens a UDP socket on the same address/port WSJT-X uses (default `2237`). Two
threads cooperate:

- A **receiver thread** does nothing but read datagrams off the socket and drop them onto an
  in-memory queue (up to 1000 deep).
- A **processor thread** pops packets, decodes them with the bundled `pywsjtx` library, and
  dispatches each to a handler by type.

WSJT-X emits several packet types; the ones that matter here are:

| Packet | What Wait and Pounce does |
|---|---|
| **Heartbeat** | Tracks that WSJT-X is alive; replies with its own heartbeat. |
| **Status** | Learns your callsign, grid, current dial frequency → **band**, mode (FT8/FT4), and whether the radio is transmitting. Detects band changes. |
| **Decode** | The important one — every decoded message flows through the pounce logic. |
| **QSO Logged** | A contact was logged in WSJT-X → recorded in the worked history. |
| **Request/Setting** | Used for [Master/Slave sync](/guide/master-slave) between instances. |

## 2. Classifying a decode

When a Decode packet arrives, the message text (e.g. `CQ DX TX5S BG23`) is parsed and matched
against your lists for the **current band**. Each decode is tagged with a set of flags:

- `wanted` / `wanted_cq_zone` — matches a wanted callsign or CQ zone
- `monitored` — matches a monitored call/zone (alert only, no auto-reply)
- `excluded` — on your excluded list (never reply)
- `directed` — the message is *directed at your callsign* (someone is answering you)
- `cqing` — the station is calling CQ
- Enrichment: `report` (SNR), `grid`, `lotw` (uses LoTW?), `entity_code` (DXCC), CQ zone

A decode becomes a **reply candidate** only after passing a cascade of gates:

1. **Worked-Before** — if you've already worked this call+band, it may be demoted depending on
   your [WkB4 mode](/guide/worked-before).
2. **Marathon** — needed for the [DX Marathon](/guide/marathon)? → candidate.
3. **Grid tracker** — a [new/unconfirmed grid](/guide/grid-tracker)? → candidate.
4. **Valid callsign** filter — optionally drop calls with no resolvable DXCC entity.
5. **Direction** filter — optionally drop calls beaming at another continent.
6. **LoTW-only** filter — optionally only reply to LoTW users.
7. **Minimum report** — drop decodes weaker than your threshold.

If a decode is *directed at your callsign* with `RRR` / `RR73` / `73`, the engine instead
**logs the QSO** (ADIF + optional LoTW/Club Log upload), marks the call worked, and clears it
from your wanted list.

## 3. Choosing who to reply to

Multiple candidates can appear in the **same FT8/FT4 transmit period**. Wait and Pounce does not
reply to the first one — it waits and scores them all:

- A station **answering you** always wins.
- Otherwise each candidate gets a **priority score** from your configurable
  [Priority Manager](/guide/reply-engine#priority-manager) order.
- Ties are broken by: most recent worked-before year → LoTW user → strongest SNR → earliest
  received.

A short **200 ms debounce timer** (`WAITING_TIME_BEFORE_REPLY`) lets the full period's decodes
arrive before the *single best* candidate is chosen. That candidate becomes the `targeted_call`.

## 4. Replying (keying the radio)

For the winning candidate, the engine sends a **Reply packet** back to WSJT-X. WSJT-X then calls
that station exactly as if you'd double-clicked it. Optionally the engine also:

- Moves your TX frequency to a clear slot ([Gap Finder](/guide/gap-finder)).
- Sends a **Halt TX** packet when it gives up on a station (e.g. the
  [watchdog](/guide/watchdog) limit is reached).

::: info Slave instances never key the radio
In a [Master/Slave](/guide/master-slave) setup, only the **Master** sends Reply/Halt/frequency
packets. Slave instances mirror the configuration but stay receive-only.
:::

## 5. Sticking with, or abandoning, a target

Once `targeted_call` is set, Wait and Pounce keeps replying to that station until:

- the QSO completes (it sees `RR73`/`73`), **or**
- the **maximum waiting delay** elapses (default 2 minutes) with no answer, **or**
- the **maximum number of attempts** is reached.

When it gives up, the [watchdog](/guide/watchdog) can *temporarily exclude* the station so the
engine moves on to other targets instead of looping forever.

Next: see this reflected in [The Main Window](/guide/main-window).
