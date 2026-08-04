# Choosing Who to Reply To

When several wanted stations decode at the same time, Wait and Pounce must pick *one* to call.
This page covers the settings that shape that choice. For the full picture of *how* the decision is
made, see [How It Decides Who to Call](/guide/how-it-works).

## Turn replying on

Nothing transmits unless **Enable reply** is on (in **Settings → General Settings**). With it off,
Wait and Pounce becomes a smart **monitor** — it highlights decodes and plays alerts but never keys
the radio. You can also flip replying on and off quickly with the sound/reply toggle, and a sound
confirms when replying has been turned off.

## Reply Rules

When more than one wanted station is available, the order you set here decides who wins. In
**Settings → Reply Rules**, drag the rows into the order you prefer — the **top row has the highest
priority**:

| Priority | Row |
|---|---|
| Highest | **Excluded Callsigns** |
| | **Excluded Zones** |
| | **Wanted Callsign** |
| | **Wanted CQ Zone** |
| | **Marathon** |
| | **DXCC Program** |
| | **New Grid** |
| | **POTA** |
| Lowest | **Politeness reply** |

That's the default order. A wanted callsign beats a wanted zone, which beats a marathon entity,
and so on — reorder it to match how *you* hunt.

::: info Some rows only appear when enabled
**DXCC Program**, **New Grid** and **POTA** show up in the list only once you've enabled the
matching feature (and, for the logbook-based ones, selected at least one band).
:::

::: tip Someone answering you always wins
Whatever your order, a station that is **calling your callsign** is answered first — you're already
in a QSO and finishing it comes before chasing anything new.
:::

### Exclusions are a threshold

The **Excluded Callsigns** and **Excluded Zones** rows aren't reply targets — they act as a
**threshold**. A target placed **above** an exclusion row is still called *despite* the exclusion;
a target placed **below** it is blocked.

- Put an exclusion row at the **very top** (the default) to block everything it matches — a hard
  block, like a classic exclusion list.
- Drop it **below** a target row to let that target through. For example, with **Excluded Zones**
  *below* **Marathon** but *above* **New Grid**, a station in an excluded zone is still called if it
  gives you a new marathon entity, but ignored if it would only be a new grid.

Because the two rows are separate, you can be strict about specific callsigns (keep **Excluded
Callsigns** near the top) while letting award targets slip past a broad zone exclusion (move
**Excluded Zones** down). The callsigns and zones themselves are still typed in the per-band
**Excluded Callsign(s)** / **Excluded CQ Zone(s)** fields — see
[Wanted / Monitored / Excluded](/guide/targets).

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

If a station won't complete, the [Watchdog](/guide/watchdog) — when enabled — gives up after a set
number of attempts and sets it aside so you move on.
