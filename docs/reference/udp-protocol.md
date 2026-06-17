# UDP Protocol & Packets

Wait and Pounce speaks the standard **WSJT-X UDP protocol**. It binds the same UDP server WSJT-X
uses (default `127.0.0.1:2237`) and exchanges the protocol's message types. The bundled
`pywsjtx/` library handles encoding/decoding.

## Packets consumed (from WSJT-X)

| Packet | Type | Handler | Used for |
|---|---|---|---|
| **Heartbeat** | 0 | `assign_packet` → heartbeat | Liveness; Master replies, Slave checks 30 s timeout. |
| **Status** | 1 | `handle_status_packet` | my_call, grid, dial freq → band, mode, TX state, band-change detection. |
| **Decode** | 2 | `handle_decode_packet` | The pounce pipeline. |
| **Clear** | 3 | logged | — |
| **QSO Logged** | 5 | logged | Recorded into worked history. |
| **Close** | 6 | logged | WSJT-X is closing. |
| **Reply** | (echo) | logged | — |
| **Logged ADIF** | 12 | logged | ADIF of a logged QSO. |

## Packets sent (to WSJT-X) — Master only

These are **suppressed on Slave instances**; only the Master keys the radio.

| Packet | Builder | Purpose |
|---|---|---|
| **Reply** | `pywsjtx.ReplyPacket.Builder` | The pounce — make WSJT-X call a decode. |
| **Halt TX** | `pywsjtx.HaltTxPacket.Builder` | Stop transmitting (watchdog give-up). |
| **Set TX Delta Freq** | `pywsjtx.SetTxDeltaFreqPacket.Builder` | Move TX offset ([Gap Finder](/guide/gap-finder)). |
| **Configure** | `pywsjtx.ConfigurePacket.Builder` | Switch mode (e.g. FT4). |
| **Heartbeat** | — | Keep-alive reply. |

## Master/Slave sync packets

| Packet | Direction | Carries |
|---|---|---|
| **Request Setting** | Slave → Master | `synch_time` — "send me your config." |
| **Setting** | Master → Slave | JSON config (band, wanted/monitored/excluded lists & zones, `enable_sending_reply`), prefixed with an `IP:port|` header. |

The header prefix is also how an instance **detects its role**: packets arriving *with* the
`IP:port|` header came from a Master (so this instance is a Slave); packets *without* it came
straight from WSJT-X (so this instance is the Master). See
[Master/Slave Sync](/guide/master-slave).

## Forwarding rules

When secondary UDP forwarding is configured, the listener forwards WSJT-X packets to the secondary
target — **except** Request/Setting packets, and it won't forward when the secondary address is
empty or identical to the primary.

## Testing without a radio

`send_udp.py` is a standalone CLI that builds and injects simulated packets
(decode / heartbeat / QSO-logged / delta-F) at a target `IP:port`, so the listener can be exercised
without a live WSJT-X. It implements its own minimal Qt-style encoder (MAGIC `0xadbccbda`,
schema 3) and is independent of the production `pywsjtx` path.

```bash
# Example: inject a simulated decode packet (see the script's argparse for full options)
python send_udp.py --help
```

## Timing constants

| Constant | Value | Meaning |
|---|---|---|
| `DEFAULT_UDP_PORT` | 2237 | Default server port. |
| `HEARTBEAT_TIMEOUT_THRESHOLD` | 30 s | Slave drops sync if no Master heartbeat. |
| `WAITING_TIME_BEFORE_REPLY` | 0.2 s | Reply debounce. |
| `BAND_CHANGE_WAITING_DELAY` | 10 s | Ignore decodes right after a band change. |
| `DECODE_PACKET_TIMEOUT_THRESHOLD` | 60 s | "No decodes" status threshold. |
| `MAXIMUM_ALLOWED_DT` | 1.9 s | Max sync delta tolerated. |
