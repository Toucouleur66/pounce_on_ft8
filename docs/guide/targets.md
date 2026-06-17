# Wanted / Monitored / Excluded

Your *targets* are the heart of the configuration. Each band tab has six comma-separated input
fields. Everything is **per band** — `TX5S` wanted on 20 m does not affect 40 m.

These lists are stored in a thread-safe shared store (`MonitoringSettings`) that bridges the GUI
and the listener, and pushed live to the running engine as you type (debounced).

## The six fields

| Field | Accepts | Effect |
|---|---|---|
| **Wanted Callsign(s)** | calls, wildcards | Actively work / auto-reply. |
| **Monitored Callsign(s)** | calls, wildcards | Alert only (sound + highlight); **not** auto-worked. |
| **Wanted CQ Zone(s)** | numbers | Auto-reply to any station in these CQ zones. |
| **Monitored CQ Zone(s)** | numbers | Alert only for these zones. |
| **Excluded Callsign(s)** | calls | **Never** reply, regardless of any other rule. |
| **Excluded CQ Zone(s)** | numbers | Never reply to these zones. |

## Wanted vs Monitored

- **Wanted** = "work this for me." A match becomes a reply candidate and the engine will transmit.
- **Monitored** = "tell me, but don't transmit." A match plays a [sound](/guide/sounds) and
  highlights the row so *you* can decide whether to act. Useful for nets, skeds, or watching a
  call without auto-pouncing.

## Wildcards

Wanted/Monitored callsign fields accept wildcards, so you can chase whole prefixes:

```
3D2*        → any Clipperton/Fiji-style 3D2 call
VP8*, VP6*  → South Atlantic / Pitcairn
*/MM        → maritime mobile suffix
```

When a reply is chosen via a wildcard match, the focus label shows the **`/ WILDCARD`** suffix.

## Excluded — hard vs temporary

There are **two** kinds of exclusion:

1. **Hard exclusion** — anything you type into *Excluded Callsign(s)*. The engine will *never*
   reply to it, overriding wanted/marathon/grid and even the watchdog.
2. **Temporary exclusion** — added automatically by the [Watchdog](/guide/watchdog), or manually
   via the context menu (**Temporarily add to Excluded**). It auto-expires.

### Adding a temporary exclusion manually

Right-click a decode → **Temporarily add &lt;call&gt; to Excluded**. A dialog
(`ExclusionDialog`) offers a row of durations:

> **2 min · 10 min (default) · 1 hour · 1 day · 1 week · 1 month**

The call is suppressed until the timer expires, then silently removed. The Excluded field's
tooltip shows the remaining time for each temporarily-excluded call.

::: tip A station answering you is never blocked
If a temporarily-excluded station *replies directly to your callsign*, the exclusion is lifted
immediately so an in-progress QSO is never dropped.
:::

## Editing quickly

- **Type** into the fields (comma-separated). Edits apply live and, in
  [Master/Slave](/guide/master-slave) mode, sync to the paired instance.
- **Right-click a decode** to add/remove without typing.
- **"Make &lt;call&gt; your only Wanted Callsign"** clears the Wanted field and sets just that one
  call — handy when you want to lock onto a single DXpedition.

Next: how the engine turns these matches into a single reply — the
[Reply & Priority Engine](/guide/reply-engine).
