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
| **.tqsl Folder** | Your TQSL config directory (`TQSLDIR`). |
| **Test Upload Last QSO** | Upload your most recent contact as a test. |
| **Test Download QSLs** | Fetch confirmations as a test. |

The corresponding config keys are `enable_reply_to_lotw_only`, `enable_lotw_upload`,
`lotw_username`, `lotw_password`, `lotw_location`, `lotw_signing_password`, `lotw_qso_since_date`,
`lotw_download_interval`, `tqsl_path`, `tqsl_dir`.

## How uploading works

When a QSO completes and auto-sync is on, Wait and Pounce signs and uploads it via the **TQSL**
command-line tool (`LoTWClient.sign_and_upload_with_tqsl`):

```
tqsl -d -u -a compliant -x [-l <station location>] [-p <signing password>] <adif tempfile>
```

The app auto-locates `tqsl` in the standard install locations for your OS, but you can override
the path. Uploaded QSOs are tracked in a cache so they aren't sent twice.

::: warning TQSL must be installed
Uploading requires the ARRL **TQSL** application installed and a valid certificate. If TQSL or
the certificate is missing, uploads fail — use **Test Upload Last QSO** to verify your setup.
:::

## How downloading works

Confirmations are fetched from the LoTW report endpoint and matched to your log by
`(callsign, date, band)`. Matches are written back into the backup log
(`wait_pounce_log.adif`) as `lotw_qsl_rcvd` / `lotw_qsl_sent`, and recorded in an audit file
(`lotw_qsl_log.json`).

## Viewing confirmations

**Tools → Show LoTW QSLs received** opens the **LoTW Incoming** dialog
(`LoTWIncomingDialog`), which lists received confirmations (date, time, call, band, mode, QSL-rcvd
date) and reports stats like *"N QSL(s) rcvd, M QSO(s) not in log."* You can also clear the LoTW
QSL log from there.

## LoTW user activity (the • indicator)

Separately from confirmations, the app downloads the public **LoTW user-activity** list (via
**Tools → Update LoTW Info**) into a local cache. Any decode from a callsign on that list is
flagged with a **•** in the table and is favoured in [tie-breaking](/guide/reply-engine#tie-breaking)
— these stations are more likely to confirm. This is also what the *reply-only-to-LoTW* filter
uses.

::: info Auto-sync scheduling on this branch
The on-demand **Test Upload / Test Download** actions and per-QSO upload are active. The periodic
background **download** worker (`LoTWSyncWorker`) exists in the code but is not yet wired to a
timer on the `handle_slave` branch — so scheduled auto-download of confirmations may not run
automatically here even though the interval setting is exposed. Uploading of new QSOs is
unaffected.
:::
