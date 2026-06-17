# Installation & Setup

## Requirements

- **WSJT-X** or **JTDX** already installed and working with your radio.
- **Windows 10/11** or **macOS**. (The app also runs from source on Linux.)
- A few hundred MB of disk for the bundled DXCC and LoTW data files.

## Installing the application

The packaged builds are distributed from the project's
[SourceForge page](https://sourceforge.net/projects/wait-and-pounce-ft8/). Download the build for
your platform and run it.

- **Windows** — the app may request **administrator privileges**. This is required for the
  optional [JTDX auto-click](/guide/jtdx-autoclick) feature, which interacts with another
  window. The app expires after a built-in date and will prompt you to update.
- **macOS** — a `.app` bundle; a small status-menu agent provides the menu-bar icon.

::: tip Running from source
Developers can run it directly — see [Building from Source](/reference/building). The main entry
point is `pounce_gui.pyw` and dependencies are pinned in `requirements.txt` (PyQt6 6.8, numpy,
shapely, requests, …).
:::

## Configuring WSJT-X / JTDX

Wait and Pounce talks to WSJT-X over UDP. You must point WSJT-X at the same UDP server.

1. In **WSJT-X → File → Settings → Reporting** (JTDX: similar dialog):
   - **UDP Server**: `127.0.0.1` (same machine) — set the address Wait and Pounce listens on.
   - **UDP Server port number**: `2237` (the default both sides use).
   - Enable **Accept UDP requests** — this is what lets Wait and Pounce send Reply packets that
     key your radio.
2. (Optional) If you also run a logging program (Log4OM, N1MM, …) that expects WSJT-X UDP, use
   Wait and Pounce's **secondary UDP forwarding** so packets reach both — see
   [Server settings](/reference/settings#server-udp).

::: warning "Accept UDP requests" is mandatory
If *Accept UDP requests* is off, Wait and Pounce can still **read** decodes but cannot make
WSJT-X reply. You'll see decodes light up but no transmissions.
:::

## First launch

On first launch (or after an update) the app may download/refresh its data files. From the
**Tools** menu you can force these at any time:

- **Update DXCC Info** — ClubLog `cty.xml`
- **Update country and region files** — `CTY_WT_MOD.DAT` from country-files.com
- **Update LoTW Info** — the LoTW user-activity list

See [Callsign Lookup & Data Files](/guide/lookup) for what each file does.

## Pointing it at your logbook

To get [Worked-Before](/guide/worked-before), [Marathon](/guide/marathon) and
[grid](/guide/grid-tracker) tracking, load your ADIF log:

1. Open **Settings → Logbook Analysis (ADIF)**.
2. **Select new ADIF File for analysis** and pick your master log export.
3. Wait for the analyzer to finish; the summary shows worked calls per year × band.

Your log is monitored for changes (polled every ~5 s) so new contacts are picked up live.

Next: the [Quick Start](/guide/quick-start) walks through your first pounce.
