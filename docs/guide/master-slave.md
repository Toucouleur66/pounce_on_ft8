# Master / Slave Sync

Wait and Pounce can run as **multiple cooperating instances** — for example, one per radio in a
multi-rig station — so they share one wanted/excluded configuration and reply state. One instance
is the **Master** (talks to WSJT-X and keys the radio); the others are **Slaves** (mirror the
config, receive-only).

## Roles are auto-detected

You don't pick a role in a menu — it's inferred from the **packet source**:

- An instance receiving packets **directly from WSJT-X/JTDX** becomes the **Master**.
- An instance receiving packets **forwarded by a Master** (the Master prefixes them with an
  `IP:port|` header) becomes a **Slave**.

The status bar turns **blue-violet** on a Slave so you always know which is which.

## Setting it up

The mechanism rides on the **secondary UDP forwarding** feature:

1. Configure the **Master** to listen to WSJT-X on the primary UDP port (`2237`).
2. In the Master's **Server settings**, enable the **secondary UDP forwarding** and point it at
   the Slave's address/port.
3. Start the Slave listening on that forwarded port.

The Master now forwards every WSJT-X packet to the Slave, and the two negotiate settings sync.

## What gets synced

The Master serves its configuration to Slaves on request:

- `band`
- `wanted_callsigns`, `monitored_callsigns`, `excluded_callsigns`
- `wanted_cq_zones`, `monitored_cq_zones`, `excluded_cq_zones`
- `enable_sending_reply`

A Slave only accepts settings when it is on the **same band** as the Master and the incoming
configuration is **newer** (a monotonic `synch_time` guards against stale updates). On a Slave the
synced input fields are greyed out — edit them on the Master.

## The sync handshake

1. **Slave** sends a *Request Setting* packet (re-requesting every ~60 s until synced).
2. **Master** replies with a *Setting* packet containing the JSON config above, header-prefixed.
3. **Slave** applies it, updates its fields and reply-enable state, and reports "synched" in the
   status bar.

### Liveness

The Slave watches the Master's **heartbeat**. If no heartbeat arrives within ~30 seconds, the
Slave drops its synced state and re-requests, so a restarted Master re-syncs cleanly.

## TX authority

::: danger Only the Master transmits
Every transmit action — **Reply**, **Halt TX**, **Set TX frequency** — is suppressed on a Slave.
Slaves observe, display and stay in sync, but never key a radio. This prevents two instances from
both replying to the same station. The [watchdog's](/guide/watchdog) "halt TX" (build 2.20) is
therefore a Master-only action.
:::

## Why use it

- **Multi-rig / SO2R-style operating** — one shared wanted list across bands/radios.
- **A second screen / monitor position** — watch the same pounce activity on another machine
  without risk of double-TX.
- **Forwarding to a logger** — the same forwarding feature can also feed a separate logging
  program (see [Server settings](/reference/settings#server-udp)).
