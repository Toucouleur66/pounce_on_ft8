# Grid Tracker & Map

The **Grid Tracker** chases new Maidenhead grid squares, and the **Grid Map** window visualises
which grids you've worked and confirmed.

## Grid Tracker (reply logic)

In **Settings → Grid Tracker** you can enable:

- **"Enable grid tracker to reply to callsign if new grid regardless of band"** — when on, a
  station broadcasting a **grid you haven't worked** becomes a reply candidate, *independent of
  band*. A reply chosen this way shows the **`/ GRID`** suffix in the focus label.
- A **per-band button grid** to scope which bands participate.
- **"Reply to callsign if grid not yet confirmed and not worked before"** — extends the trigger to
  grids that are worked but **not yet confirmed**, so you can chase confirmations too.

Grid need is derived from your [ADIF log](/guide/adif), where worked and confirmed grids are
tracked separately. A "confirmed" grid is one where any QSO carries a positive QSL status (LoTW,
paper, or eQSL).

## Grid Map window

Open it with **View → Grid Monitoring** (<kbd>Ctrl</kbd>+<kbd>G</kbd>). It is a map painted over
OpenStreetMap raster tiles.

### What it shows

- **Maidenhead grid** overlay that refines as you zoom: fields → squares → subsquares.
- A **day/night terminator** (grey line) showing where it's dark.
- A **signal-density heatmap** built from live decodes.
- **Worked vs confirmed colouring** for the current operating band:
  - **Pink** — worked grids.
  - **Blue** — confirmed grids (painted on top of worked).
  - **Blinking** — a brand-new grid just pounced.

### Context menu

The grid map supports a right-click context menu (e.g. to set an *Excluded* trigger), the same one
available on the main table.

::: info Data source
The map reads its per-band worked and confirmed grids from your logbook, so its colouring stays in
sync with what you've worked.
:::
