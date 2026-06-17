# Sound Alerts

Wait and Pounce can play distinct sounds for the events you care about, so you can step away from
the screen and still know when something worth working appears.

## Settings

In **Settings → Sound Alerts**:

| Setting | Plays when… |
|---|---|
| **Message from any Wanted Callsign** | A wanted callsign decodes. |
| **Message directed to my Callsign** | Someone is calling/answering *you*. |
| **Message from any Monitored Callsign** | A monitored callsign decodes. |
| **Delay between each monitored callsigns detected** (seconds) | Rate-limits monitored-call sounds so a busy band doesn't spam you. |

## Global sound toggle

A single master switch mutes/un-mutes all alerts: **App menu → sound toggle**
(<kbd>Ctrl</kbd>+<kbd>S</kbd>). A sound also plays to confirm when **reply is disabled**, so you
get audible feedback when toggling transmit on/off.

## Where the sounds come from

The bundled `sounds/` folder ships a set of short WAV files that the app plays through Qt's
multimedia output. Different events use different clips so you can tell them apart by ear.

## Tips

- Set a sensible **delay between monitored callsigns** (e.g. 60–120 s) during contests — otherwise
  a packed band triggers a near-continuous stream of monitored-call beeps.
- Keep **"directed to my Callsign"** on even when pouncing unattended — it's the cue that a QSO is
  actually happening.
