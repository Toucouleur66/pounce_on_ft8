# Telemetry & Privacy

Wait and Pounce includes a lightweight **telemetry** service that reports a small "I'm online"
heartbeat to the project's server. This page documents exactly what is sent so you can make an
informed decision.

## What it does

Once a callsign is configured, the app registers an installation and then sends a **heartbeat
roughly every 60 seconds** to the project API (`https://f5ukw.com/api`). The server keeps each
user for a short TTL (about 5 minutes) before they "expire" from the live list — this is what
powers the **Active Users** window (<kbd>Ctrl</kbd>+<kbd>L</kbd>).

Requests are signed (HMAC-SHA256) using a per-installation secret stored locally in
`~/.dx-pounce/telemetry_config.json`.

## What is sent

| Field | Notes |
|---|---|
| **Callsign** | Your station callsign. |
| **Grid square** | Approximate location (~70 km resolution). |
| **Band** | Current operating band. |
| **IP address** | As seen by the server. |
| **Installation ID** | A random per-install identifier. |
| **Last-seen time** | Heartbeat timestamp. |
| **App version / OS** | Build number and platform. |

## Privacy considerations

::: warning No opt-out switch on this build
There is currently **no `enable_telemetry` setting** to disable telemetry from within the app. The
project describes it as transparent and tied to the live-users feature. The only ways to prevent it
are to **not run the app** or to **block `f5ukw.com`** at your firewall/hosts file.
:::

Be aware that for licensed amateurs a **callsign maps to your name and address** in public license
databases, so callsign + grid + IP is potentially identifying. The only mitigation in the service
itself is the short server-side expiry (data isn't anonymised, just aged out of the live list).

If telemetry is a concern for your station, blocking the API host disables it without affecting any
of the radio-side functionality (pouncing, logging, LoTW/Club Log uploads all work independently).

See [TELEMETRY_README.md](https://github.com) in the repository root for the project's own
description of the service and its backend.
