# Running Several Instances

Wait and Pounce can run as **multiple cooperating instances** — for example, one per radio in a
multi-rig station — so they share one wanted/excluded configuration and reply state. You run one
**main copy** (talks to WSJT-X and keys the radio); the **extra copies** mirror its wanted lists,
stay in sync, and never transmit.

## Roles are detected automatically

You don't pick a role in a menu. An instance that receives packets directly from WSJT-X/JTDX acts
as the main copy; an instance that receives packets forwarded by the main copy acts as an extra,
receive-only copy.

The status bar turns **blue-violet** on an extra copy so you always know which is which.

## Setting it up

The mechanism rides on the **secondary UDP forwarding** feature:

1. Configure the **main copy** to listen to WSJT-X on the primary UDP port (`2237`).
2. In the main copy's **Server settings**, enable the **secondary UDP forwarding** and point it at
   the extra copy's address/port.
3. Start the extra copy listening on that forwarded port.

The main copy now forwards every WSJT-X packet to the extra copy, and the two negotiate settings
sync.

## What gets synced

The main copy serves its configuration to extra copies on request:

- Band
- Wanted, monitored and excluded callsigns
- Wanted, monitored and excluded CQ zones
- Whether auto-reply is enabled

An extra copy only accepts settings when it is on the **same band** as the main copy and the
incoming configuration is **newer** (stale updates are ignored). On an extra copy the synced input
fields are greyed out — edit them on the main copy.

## Staying in sync

An extra copy requests the configuration on startup and re-requests periodically until it is
synced, then reports "synched" in the status bar. It also watches the main copy's heartbeat: if no
heartbeat arrives within about 30 seconds, it drops its synced state and re-requests, so a
restarted main copy re-syncs cleanly.

## TX authority

::: danger Only the main copy transmits
Every transmit action — replying, halting TX, setting the TX frequency — is suppressed on an extra
copy. Extra copies observe, display and stay in sync, but never key a radio. This prevents two
instances from both replying to the same station. The [watchdog's](/guide/watchdog) halt-TX
behaviour is therefore handled only by the main copy.
:::

## Why use it

- **Multi-rig / SO2R-style operating** — one shared wanted list across bands/radios.
- **A second screen / monitor position** — watch the same pounce activity on another machine
  without risk of double-TX.
- **Forwarding to a logger** — the same forwarding feature can also feed a separate logging
  program.
