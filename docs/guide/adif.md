# ADIF Logbook Analysis

Wait and Pounce reads your **ADIF logbook** to power [Worked-Before](/guide/worked-before),
[Marathon](/guide/marathon) and [Grid](/guide/grid-tracker) tracking, and provides a built-in
analyzer to inspect what you've worked.

## Loading a log

In **Settings → Logbook Analysis (ADIF)**:

1. **Select new ADIF File for analysis** — pick your master log export (e.g. from your everyday
   logger). You can add multiple files.
2. The file appears in a table; click **Summary** to open the analyzer, or **Clear** to remove.

The config key is `adif_file_paths` (a list of monitored paths).

## How monitoring works

A background thread (`AdifMonitor`) **polls each file's modification time and size every ~5
seconds**:

- If a file only **grew** (new contacts appended), it does a fast **incremental** parse of just
  the new records.
- If a file changed otherwise, it does a **full** re-parse.

In addition to your files, the app always monitors its own backup log
(`wait_pounce_log.adif`), so QSOs you make *inside* Wait and Pounce are folded into the
worked-before / marathon / grid data immediately.

Parsing runs in a **separate OS process** (`AdifProcessor`) so a large logbook never freezes the
UI.

## What gets extracted

For each record (`<EOR>`-delimited), the parser reads: `CALL`, `BAND`, `QSO_DATE`, `TIME_ON`,
`GRIDSQUARE`, `MODE`/`SUBMODE`, `RST_SENT`/`RST_RCVD`, `FREQ`, and the QSL confirmation fields
`LOTW_QSL_RCVD`, `QSL_RCVD`, `EQSL_QSL_RCVD`. From these it builds three structures:

| Structure | Shape | Powers |
|---|---|---|
| **Worked-before** | `year → band → {callsigns}` | [WkB4](/guide/worked-before) |
| **Entities** | `year → band → {DXCC codes}` | [Marathon](/guide/marathon) |
| **Grids** | `band → grid → [QSOs]` | [Grid Tracker / Map](/guide/grid-tracker) |

## The ADIF File Analyzer

After you load/test a file, the **ADIF File Analyzer** dialog (`AdifSummaryDialog`) opens. It
shows a table of **unique callsign counts per year × band**, with:

- a **Show all bands** toggle, and
- a per-band totals table.

This is a quick way to see your activity profile — how many uniques you worked each year on each
band — and to confirm the file parsed correctly before relying on it for pouncing.

## Confirmed status

"Confirmed" is computed on the fly from the QSL fields: a QSO is confirmed when
`LOTW_QSL_RCVD` ∈ {V, Y}, `QSL_RCVD` ∈ {V, Y, S}, or `EQSL_QSL_RCVD` = Y. This feeds the
worked-vs-confirmed colouring in the [Grid Map](/guide/grid-tracker) and the
*reply-to-unconfirmed* grid option. The [LoTW sync](/guide/lotw) writes confirmation fields back
into the backup log so confirmations stay current.
