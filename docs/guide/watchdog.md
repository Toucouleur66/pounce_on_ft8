# Watchdog & Exclusions

The **watchdog** prevents Wait and Pounce from getting stuck endlessly calling a station that
never comes back — a deaf DXpedition, a station that worked someone else, or a bad propagation
moment. When a target is given up on, the watchdog **temporarily excludes** it so the engine moves
on to other wanted stations, then automatically gives it another chance later.

## Settings

In **Settings → Watchdog and retry**:

| Setting | Default | Range | Meaning |
|---|---|---|---|
| **Enable Watchdog** | Off | — | Turn the watchdog on/off. |
| **Number of attempts** | 10 | 1–9999 | Calls to a station before giving up. |
| **Wait time** (minutes) | 20 | 1–9999 | How long the temporary exclusion lasts. |

When the watchdog is **off**, the attempt cap falls back to the
[*Maximum number of attempts*](/guide/reply-engine) set in the Priority Manager.

## What happens when the limit is hit

When the targeted station reaches the attempt limit:

1. The call is added to a **temporary exclusion list** until the wait time elapses.
2. WSJT-X is told to **stop transmitting**, so the radio actually stops calling — you're not left
   transmitting into the void.
3. The target is cleared and the next-best station is chosen.
4. A **temporarily-excluded** notice appears for that call (with the band and the number of minutes).

## Automatic re-try (the sweep)

Temporary exclusions expire on their own. A recurring background check regularly inspects the
exclusion list and **lifts** any whose window has elapsed — even when no decodes are currently
arriving.

::: info Why the sweep matters
Exclusions expire on schedule regardless of activity, so a quiet band will never leave a station
excluded long past its timer.
:::

When an exclusion is lifted, the call's attempt counter is cleared so it starts fresh.

## Direct reply overrides exclusion

If a temporarily-excluded station **answers your callsign directly**, the exclusion is lifted
*immediately* (reason: "direct reply received"). You will never lose a QSO that's actually in
progress because of the watchdog.

## Hard exclusions are different

Anything you type into the **Excluded Callsign(s)** field is a *hard* exclusion: it is never
replied to and is **not** subject to the watchdog timer. See
[Wanted / Monitored / Excluded](/guide/targets#excluded-hard-vs-temporary).

## Manual temporary exclusions

You can also exclude a station by hand: right-click a decode →
**Temporarily add &lt;call&gt; to Excluded**, then choose a duration
(2 min · 10 min · 1 hour · 1 day · 1 week · 1 month). These use the same expiry/sweep machinery as
the watchdog.
