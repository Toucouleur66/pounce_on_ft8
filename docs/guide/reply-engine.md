# Choosing Who to Reply To

When several wanted stations decode at the same time, Wait and Pounce must pick *one* to call.
This page covers the settings that shape that choice. For the full picture of *how* the decision is
made, see [How It Decides Who to Call](/guide/how-it-works).

## Turn replying on

Nothing transmits unless **Enable reply** is on (in **Settings → General Settings**). With it off,
Wait and Pounce becomes a smart **monitor** — it highlights decodes and plays alerts but never keys
the radio. You can also flip replying on and off quickly with the sound/reply toggle, and a sound
confirms when replying has been turned off.

## Your priority order

When more than one wanted station is available, the order you set here decides who wins. In
**Settings → Priority Manager**, drag the reasons into the order you prefer:

| Priority | Reason |
|---|---|
| Highest | **Wanted Callsign** |
| | **Wanted CQ Zone** |
| | **Marathon** |
| | **New Grid** |
| Lowest | **Politeness reply** |

That's the default order — a wanted callsign beats a wanted zone, which beats a marathon entity,
and so on. Reorder it to match how *you* hunt.

::: tip Someone answering you always wins
Whatever your order, a station that is **calling your callsign** is answered first — you're already
in a QSO and finishing it comes before chasing anything new.
:::

The same page also sets how long the software persists with one station:

- **Maximum number of attempts** (4–30) — how many times to call a station before giving up.
- **Maximum waiting delay** (1–10 min) — how long to keep trying a target with no answer.

## Polite reply

**Enable polite reply** (General Settings) makes the software answer a station that is *calling you*
even if it isn't on your wanted list — so you're never rude to someone trying to work you. A reply
chosen this way is labelled **/ POLITENESS** in the focus display.

## Filters that skip a station

In **General Settings** you can require every candidate to pass extra checks:

- **Minimum report** — ignore signals weaker than your chosen level (from +10 dB down to −26 dB).
- **Ignore callsign if prefix is invalid** — skip calls that don't resolve to a real country.
- **Ignore callsign if it targets another continent** — skip stations beaming away from you.
- **Reply only for callsigns that use LoTW** (on the LoTW page) — chase confirmable contacts only.

## Completing a contact

When your target sends its final acknowledgement, Wait and Pounce:

1. Sends a final reply if one is needed.
2. Logs the contact (and uploads it to [LoTW](/guide/lotw) / [Club Log](/guide/clublog) if enabled).
3. Marks the station worked for that band and removes it from your wanted list.
4. Frees up to choose the next target.

If a contact **can't** be completed within your limits, the [Watchdog](/guide/watchdog) steps in
and sets that station aside so you move on.
