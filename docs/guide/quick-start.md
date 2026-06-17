# Quick Start

This is the shortest path to your first automated pounce. It assumes WSJT-X / JTDX is already
running with **Accept UDP requests** enabled (see [Installation](/guide/installation)).

## 1. Launch and connect

Start Wait and Pounce. Look at the **status bar** at the bottom:

- **Red / "Waiting for data packets…"** — no UDP yet. Check the port and that WSJT-X is decoding.
- **Yellow / connected, no decodes** — connected but nothing heard yet.
- **Green** — receiving decodes. You're connected. 🎉

The status bar also shows your **mode** (FT8/FT4), **frequency**, buffered packet count, and the
heartbeat state.

## 2. Choose your band tab

Wait and Pounce has one tab per band (160m … 3cm). The tab matching your radio's dial frequency
**auto-selects**. Targets are configured **per band**, so enter them on the right tab.

## 3. Add a wanted callsign

In the **Wanted Callsign(s):** field for the current band, type the call you want, e.g.:

```
TX5S
```

You can enter several (comma-separated) and use wildcards:

```
TX5S, 3D2*, VP8*
```

That's it — the moment `TX5S` decodes on this band, Wait and Pounce will reply to it.

::: tip Right-click is faster
You don't have to type. **Right-click any decode** in the table and choose
*"Add to Wanted Callsigns (this band)"* or *"Make &lt;call&gt; your only Wanted Callsign"*.
:::

## 4. Start monitoring

Click **Start Monitoring** (or press <kbd>Ctrl</kbd>+<kbd>M</kbd>). The button cycles through:

- **Monitoring…** — listening
- **Decoding…** — decodes arriving
- **Transmitting…** — replying to a target

The large **focus label** at the top shows the station currently being worked, with a suffix that
tells you *why* it was chosen: `/ WANTED`, `/ ZONE`, `/ MARATHON`, `/ GRID`, `/ WILDCARD`, or
`/ POLITENESS`.

## 5. Let it work

When your target answers, Wait and Pounce completes and **logs the QSO** automatically:

- It writes an ADIF record to its backup log.
- It removes the call from your Wanted list for that band.
- It appears in the **Worked Callsigns** history panel on the right.
- If enabled, it uploads to [LoTW](/guide/lotw) and [Club Log](/guide/clublog).

## 6. Stop

Click **Stop all** (or <kbd>Ctrl</kbd>+<kbd>M</kbd> again) to stop monitoring and TX.

---

## A recommended starter configuration

| Setting | Suggested value | Why |
|---|---|---|
| **Enable reply** | On | Actually transmit replies. |
| **Worked-before mode** | *Not worked B4 in current year* | Avoids dupes but lets you re-work for a new year. |
| **Watchdog** | On, 10 attempts / 20 min | Don't loop forever on a deaf station. |
| **Minimum report** | −22 to −24 dB | Skip the truly un-completable decodes. |
| **Offset / Gap Finder** | On | Find a clear TX slot automatically. |

Then explore [Wanted / Monitored / Excluded](/guide/targets) and the
[Reply & Priority Engine](/guide/reply-engine) to fine-tune behaviour.
