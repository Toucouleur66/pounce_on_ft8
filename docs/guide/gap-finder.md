# Offset / Gap Finder

The **Offset Updater** (a.k.a. *Gap Finder*) automatically moves your transmit audio offset to a
clear part of the passband before replying, so you don't transmit on top of another station.

## What it does

While monitoring, Wait and Pounce watches which audio frequencies are already in use (it collects
the offsets of incoming decodes). When it's about to reply, it picks a **gap** — an unused slot —
and sends a *Set TX Delta Frequency* packet to WSJT-X so your transmission lands there.

## Settings

In **Settings → Offset Updater**:

| Setting | Meaning |
|---|---|
| **Enable frequencies offset updater** | Turn the gap finder on/off. |
| **Mode selector** (Normal / Fox-Hound / SuperFox / Custom) | Which operating mode's frequency range to use. |
| **Min Freq (Hz)** / **Max Freq (Hz)** | The passband window to search for gaps (0–10000). |

The default windows match WSJT-X conventions:

| Mode | Default range |
|---|---|
| **Regular** | 200 – 2900 Hz |
| **Fox/Hound** | from 1050 Hz |
| **SuperFox** | up to 3200 Hz |
| **Custom** | your Min/Max values |

## Custom ranges

Choosing **Custom** lets you define and save your own Min/Max offsets — useful if your station has
a restricted clean passband or you want to keep replies inside a specific sub-band.

## When it runs

The frequency is set at reply time, just before the Reply packet is sent
(in `process_pending_reply`). If the gap finder is disabled, Wait and Pounce leaves your TX offset
untouched and WSJT-X behaves normally.

::: tip Fox/Hound and SuperFox
For DXpeditions running Fox/Hound or SuperFox, pick the matching mode so the gap finder searches
the correct hound passband instead of the regular one.
:::
