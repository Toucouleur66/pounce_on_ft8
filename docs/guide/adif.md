# ADIF Logbook Analysis

Wait and Pounce reads your **ADIF logbook** to power [Worked-Before](/guide/worked-before),
[Marathon](/guide/marathon) and [Grid](/guide/grid-tracker) tracking, and provides a built-in
analyzer to inspect what you've worked.

## Loading a log

In **Settings → Logbook Analysis (ADIF)**:

1. **Select new ADIF File for analysis** — pick your master log export (e.g. from your everyday
   logger). You can add multiple files.
2. The file appears in a table; click **Summary** to open the analyzer, or **Clear** to remove.

## How monitoring works

Wait and Pounce **polls each file's modification time and size every ~5 seconds**:

- If a file only **grew** (new contacts appended), it does a fast **incremental** parse of just
  the new records.
- If a file changed otherwise, it does a **full** re-parse.

In addition to your files, the app always monitors its own backup log, so QSOs you make *inside*
Wait and Pounce are folded into the worked-before / marathon / grid data immediately.

Parsing runs in the background so a large logbook never freezes the UI.

## What gets extracted

For each record, the parser reads: callsign, band, QSO date and time, grid square (Maidenhead),
mode/submode, RST sent/received, frequency, and the QSL confirmation fields (LoTW, paper, and
eQSL). From these it builds three sets of tracking data:

| Tracking data | Powers |
|---|---|
| **Worked-before** | [WkB4](/guide/worked-before) |
| **Entities** (DXCC) | [Marathon](/guide/marathon) |
| **Grids** | [Grid Tracker / Map](/guide/grid-tracker) |

## The ADIF File Analyzer

After you load/test a file, the **ADIF File Analyzer** dialog opens. It
shows a table of **unique callsign counts per year × band**, with:

- a **Show all bands** toggle, and
- a per-band totals table.

This is a quick way to see your activity profile — how many uniques you worked each year on each
band — and to confirm the file parsed correctly before relying on it for pouncing.

## Confirmed status

"Confirmed" is computed on the fly from the QSL fields: a QSO counts as confirmed when it carries a
positive LoTW, paper, or eQSL confirmation. This feeds the worked-vs-confirmed colouring in the
[Grid Map](/guide/grid-tracker) and the *reply-to-unconfirmed* grid option. The
[LoTW sync](/guide/lotw) writes confirmation fields back into the backup log so confirmations stay
current.
