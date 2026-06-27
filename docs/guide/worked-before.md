# Worked-Before (WkB4)

Wait and Pounce reads your ADIF logbook so it knows what you've already worked and can avoid
wasting time on duplicates — while still letting you re-work a station when it counts (a new year,
for example).

## What counts as "worked before"?

**WkB4 = the same callsign on the same band, in any year.** It is *not* based on DXCC entity or
mode — it is a per-call, per-band check derived from your loaded ADIF log.

The most recent year you worked a call+band is available to the engine, and is shown in the
decodes table's **★ (WkB4)** column.

## Choosing the behaviour

In **Settings → Worked before** you choose one of three reply modes (the section only appears once
you've loaded an [ADIF file](/guide/adif)):

| Mode | Behaviour |
|---|---|
| **Reply to any Wanted Callsign even if Worked B4** | Always reply — ignore worked-before entirely. |
| **Reply to Wanted Callsign if not Worked B4 in current year (YYYY)** | Reply unless already worked this calendar year. |
| **Do not reply to any Callsign Worked B4** *(default)* | Never re-work a station already in your log. |

The current year is shown live in the middle option's label.

## How it affects the engine

WkB4 acts as an early gate in the [reply pipeline](/guide/how-it-works):

- A wanted call that fails the WkB4 test is **demoted to monitored** — you still get the alert and
  the highlight, but the engine won't auto-call it.
- Marathon and grid tracking have their own logic and can still flag a station as needed even if
  worked before on another band/year (see [Marathon](/guide/marathon) and
  [Grid Tracker](/guide/grid-tracker)).

## The ★ column

The table's **★** column shows the worked-before status:

- A **★** / year marks a station you've worked before on that band.
- The column is **hidden** when WkB4 mode is set to *Always* (there's nothing to act on).

## Where the data comes from

Your log is parsed so the app knows, for each year and band, which callsigns you've worked. The
app's own contacts are also folded in, so stations you work *during* a session immediately count
as worked-before too. See [ADIF Logbook Analysis](/guide/adif) for how the log is monitored and
parsed.
