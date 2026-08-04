# Antenna Rotator (PstRotator)

Wait and Pounce can steer a rotatable antenna so your beam follows the DX you're working. It drives
**PstRotatorAz** over the network, and can either **turn to every station you reply to** or rotate to
**preset headings on a schedule** — or both.

::: info Requires PstRotatorAz
This feature talks to the **PstRotatorAz** application (which in turn controls your rotator). You
need PstRotatorAz installed and configured for your hardware.
:::

## Connecting to PstRotatorAz

In **Settings → Antenna Rotator → PstRotatorAz Connection**:

1. In **PstRotatorAz**, open **Communication → UDP Control Port**, set it to a port of your choice,
   and enable **UDP Control** in its Setup.
2. In Wait and Pounce, enter the same **UDP Server** address and **UDP Server port number**.
3. Once connected, the **Current azimuth** field (and the status bar) show your antenna's live
   heading in degrees.

## Two automation modes

The two modes can be combined. **Track on Reply takes priority** over the hourly schedule — while
the antenna is following a station you're replying to, it overrides any scheduled heading.

### Track on Reply

In the **Track on Reply** group:

- **Point the antenna at every station we reply to** — when on, the antenna turns to the bearing of
  whatever station Wait and Pounce is replying to (computed from its location), not only wanted
  callsigns.
- A **per-band selector** lets you enable tracking only on the bands where your rotatable antenna is
  actually used — so it won't try to swing for a band on a fixed antenna.
- **Only move if azimuth changes by more than:** *(degrees)* — a dead-band so the rotator doesn't
  hunt back and forth for tiny bearing changes. Set a few degrees to spare the motor.

### Return to Previous Position

In the **Return to Previous Position** group:

- **Return the antenna to its previous azimuth when idle** — after you stop replying to stations,
  the antenna swings back to where it was pointing before.
- **Return after not replying to any station for:** *(minutes)* — how long to wait with no reply
  before returning. While the countdown runs, the status bar shows how long until the antenna
  returns.

### Hourly Schedule

In the **Hourly Schedule** group:

- **Rotate to a fixed azimuth at given times (UTC)** — turn the antenna to preset headings at preset
  times, ideal for following a known opening (e.g. long-path at a certain hour).
- A small table with **Time (UTC)** and **Azimuth (°)** columns; use **Add** / **Remove** to manage
  rows. Rows are kept sorted by time automatically.

## Status bar read-out

While the rotator is connected, the **current azimuth** is shown in the status bar in near real
time, so you can confirm at a glance that the antenna is following along. When a return-to-previous
countdown is active, that is shown too.

::: tip Tracking vs schedule
If you mostly chase whatever decodes, leave **Track on Reply** on and the schedule off. If you run
fixed skeds or follow predictable openings, the schedule is handy — and you can keep tracking on too,
since a station you're actively replying to always wins.
:::
