# Privacy

Wait and Pounce sends a small "I'm online" heartbeat to the project's server. This page explains
exactly what is shared so you can make an informed choice.

## What it does

Once your callsign is set, the app periodically reports a short heartbeat to the project server.
Each station stays in the live list for a few minutes before expiring — this is what powers the
**Active Users** window (<kbd>Ctrl</kbd>+<kbd>L</kbd>), where you can see who else is currently
running Wait and Pounce.

## What is shared

| Item | Notes |
|---|---|
| **Callsign** | Your station callsign. |
| **Grid square** | Your approximate location (around 70 km resolution). |
| **Band** | The band you're operating on. |
| **IP address** | As seen by the server. |
| **Last-seen time** | When your last heartbeat arrived. |
| **App version / system** | Which version and platform you're running. |

## Privacy considerations

::: warning No in-app off switch
There is currently no setting to turn the heartbeat off from inside the app — it's tied to the
live-users feature. If you'd rather not share it, the practical options are to **not run the app**
or to **block the project server (`f5ukw.com`)** in your firewall or hosts file.
:::

For licensed amateurs, a **callsign already maps to your name and address** in public licence
databases, so callsign + grid + IP is potentially identifying. The data is kept only briefly (it
ages out of the live list) and is not used for anything beyond the Active Users display.

Blocking the server disables the heartbeat **without affecting any radio functionality** — pouncing,
logging, and LoTW / Club Log uploads all keep working normally.
