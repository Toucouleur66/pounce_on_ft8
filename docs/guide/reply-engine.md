# Reply & Priority Engine

When several wanted stations decode in the same transmit period, Wait and Pounce must pick
*one* to call. This page covers how that decision is made and the settings that shape it.

## Enable reply

Nothing transmits unless **Enable reply** is on (Settings → General Settings). With it off, Wait
and Pounce becomes a smart **monitor** — it highlights and sounds alerts but never keys the radio.
There is also a one-click toggle (<kbd>Ctrl</kbd>+<kbd>S</kbd> plays a sound when reply is
disabled) and the reply state can be synced between instances.

## The candidate buffer

Every decode that passes the [gates](/guide/how-it-works#_2-classifying-a-decode) and has reply
enabled is appended to a buffer. **Only decodes from the same FT8/FT4 period compete** — the
engine matches their decode time (HH:MM:SS) so it always reasons about one period at a time.

## Priority scoring

Each candidate gets a score:

1. A station **answering your callsign** gets the top priority (and even higher if it's the call
   you're already working).
2. **CQ** messages get a base bonus over non-CQ.
3. A per-property bonus is added by walking your **Priority Manager** order.

### Priority Manager

In **Settings → Priority Manager** you drag-and-drop to order these reply reasons:

| Reason | Key |
|---|---|
| Wanted Callsign(s) | `wanted` |
| Wanted CQ Zone(s) | `wanted_cq_zone` |
| Marathon | `marathon` |
| New Grid | `wanted_grid` |
| Politeness reply | `polite_reply` |

The default order is exactly the list above (wanted call is most important). A candidate matching
a higher item in the list outscores one matching a lower item.

The same page sets:

- **Maximum number of attempts** (4–30) — how many times to call a station before giving up.
- **Maximum waiting delay** (1–10 min) — how long to keep trying a target with no answer.

## Tie-breaking

When two candidates tie on priority, the engine breaks the tie in this order:

1. **Most recent worked-before year** (prefer something fresher)
2. **LoTW user** (more likely to confirm)
3. **Strongest SNR** (more likely to complete)
4. **Earliest received** packet

## The 200 ms debounce

The engine does **not** fire on the first candidate. When the best candidate changes, it arms a
**200 ms timer** (`WAITING_TIME_BEFORE_REPLY`). This lets the rest of the period's decodes arrive
so the *final* best pick wins, instead of whoever happened to decode first. When the timer fires,
`process_pending_reply()` sets the `targeted_call`, optionally retunes the TX frequency
([Gap Finder](/guide/gap-finder)), and sends the Reply packet.

## Polite reply

**Enable polite reply** (General Settings) makes the engine answer stations that are *calling you*
even if they aren't on your wanted list — i.e. don't be rude and ignore someone working you.
Selecting on this basis shows the **`/ POLITENESS`** suffix in the focus label.

## Filters that drop candidates

In **General Settings** you can additionally require candidates to pass:

- **Minimum report** — drop anything weaker than your chosen SNR (`+10` … `−26 dB`).
- **Ignore callsign if prefix is invalid** — drop calls with no resolvable DXCC entity.
- **Ignore callsign if it targets another continent** — drop stations beaming away from you.
- **Reply only for callsigns that use LoTW** (on the LoTW page) — chase confirmable contacts only.

## Completing and logging a QSO

When the targeted station sends `RRR` / `RR73` / `73` directed at you, the engine:

1. Sends one final reply if needed (except in Hound mode).
2. Logs the QSO to ADIF (and optional [LoTW](/guide/lotw) / [Club Log](/guide/clublog) upload).
3. Marks the call worked for the band and removes it from Wanted.
4. Resets `targeted_call` so the next target can be chosen.

When it *cannot* complete (no answer within limits), the [Watchdog](/guide/watchdog) steps in.
