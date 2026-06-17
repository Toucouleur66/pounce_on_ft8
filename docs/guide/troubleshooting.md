# Troubleshooting

## No decodes / "Waiting for data packets…"

The status bar stays red and no rows appear.

- Confirm WSJT-X / JTDX is actually **decoding** (you see decodes in its own window).
- Check the **UDP port** matches on both sides (default `2237`) — Settings → Server.
- Confirm the **UDP Server address** in WSJT-X points to where Wait and Pounce listens
  (`127.0.0.1` if on the same PC).
- Only one program can bind a given UDP port as the primary server; if another logger already owns
  `2237`, use Wait and Pounce's [secondary forwarding](/reference/settings#server-udp) or change
  ports.

## Decodes appear but it never transmits

- **Enable reply** must be on (Settings → General Settings).
- In WSJT-X, **Accept UDP requests** must be enabled — without it, Reply packets are ignored.
- Check you're on the right **band tab** — targets are per-band.
- If you're running a **Slave** instance (blue-violet status bar), it will **never** transmit by
  design — only the Master keys the radio. See [Master/Slave](/guide/master-slave).
- A target may be **temporarily excluded** by the [watchdog](/guide/watchdog) — check the Excluded
  field tooltip for an expiry time.
- The candidate may be failing a filter: **minimum report**, **valid callsign**, **direction**, or
  **LoTW-only**.

## It keeps calling a deaf station

Enable the [Watchdog](/guide/watchdog) (e.g. 10 attempts / 20 min). When the limit is hit, the
station is temporarily excluded and the radio is halted, so the engine moves on.

## Worked-before / Marathon not working

- Load your **ADIF log** (Settings → Logbook Analysis) — without it there's no worked-before data.
- Confirm the analyzer summary shows your contacts (right years/bands).
- Check your **WkB4 mode** — *Always* means worked-before is ignored on purpose.

## LoTW upload fails

- Install ARRL **TQSL** and verify your certificate.
- Set the correct **TQSL Path** and **.tqsl Folder**.
- Use **Test Upload Last QSO** to see the error.
- Note: periodic auto-**download** of confirmations isn't scheduled on this branch — see the note
  in [LoTW](/guide/lotw); manual **Test Download QSLs** still works.

## Club Log upload fails

- A **403** means bad credentials — re-check email, password and API key.
- Remember the first field labelled "Callsign" expects your **registered email**.

## JTDX prompt isn't auto-clicked

- Windows only; needs admin + monitoring permissions.
- Run **Test Windows Monitoring Permissions** and **Test it**.
- Doesn't run in Slave mode.

## Grid map is blank

- It paints for the **operating band** — switch to the band you have grids on.
- Tiles need internet on first view (they're cached afterwards).

## Where are the logs?

Enable **Save debugging to log** (Settings → Debugging) and use **Open log folder** to find the
rotating `pounce.log*` files. **Log UDP packet data** adds raw packet dumps for deep debugging.

## Still stuck?

Join the [Discord support server](https://discord.gg/fqCu24naCM).
