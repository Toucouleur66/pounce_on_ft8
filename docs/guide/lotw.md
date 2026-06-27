# Logbook of The World (LoTW)

Wait and Pounce integrates with ARRL's **Logbook of The World** to automatically **upload** your
contacts (signed with TQSL) and **download** confirmations back into your log. LoTW data also
drives the "reply only to LoTW users" filter and the **•** indicator in the decodes table.

## Settings

In **Settings → Logbook of The World**:

| Setting | Meaning |
|---|---|
| **Enable reply only for callsigns that use LoTW** | Restrict auto-reply to stations known to upload to LoTW. |
| **Enable automatic synch to LoTW** | Auto-upload each logged QSO. |
| **Username / Password** | Your LoTW (TQSL) account credentials. |
| **Station Location** | The TQSL station location to sign with. |
| **Signing Password** | Your certificate signing password (if set). |
| **Download QSLs since (UTC)** | Start date for downloading confirmations. |
| **Download interval (minutes)** | How often to poll for new confirmations (5–1440). |
| **TQSL Path** | Path to the `tqsl` executable. |
| **.tqsl Folder** | Your TQSL configuration folder (where your certificates live). |
| **Test Upload Last QSO** | Upload your most recent contact as a test. |
| **Test Download QSLs** | Fetch confirmations as a test. |

## How uploading works

When a QSO completes and auto-sync is on, Wait and Pounce signs and uploads the contact with
**TQSL**. The app auto-locates the TQSL executable in the standard install locations for your OS,
but you can override the path. Uploaded QSOs are tracked in a local cache so they aren't sent
twice.

::: warning TQSL must be installed
Uploading requires the ARRL **TQSL** application installed and a valid certificate. If TQSL or
the certificate is missing, uploads fail — use **Test Upload Last QSO** to verify your setup.
:::

## How downloading works

Confirmations are fetched from LoTW and matched to your log by callsign, date and band. Matches
are written back into your logbook and recorded for review.

## Viewing confirmations

**Tools → Show LoTW QSLs received** opens a dialog listing received confirmations (date, time,
call, band, mode, QSL-rcvd date) and reports stats like *"N QSL(s) rcvd, M QSO(s) not in log."*
You can also clear the LoTW QSL log from there.

## LoTW user activity (the • indicator)

Separately from confirmations, the app downloads the public **LoTW user list** (via
**Tools → Update LoTW Info**) into a local cache. Any decode from a callsign on that list is
flagged with a **•** in the table and is given a slight edge when [choosing who to reply
to](/guide/reply-engine) — these stations are more likely to confirm. This is also what the
*reply-only-to-LoTW* filter uses.
