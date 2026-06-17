# Club Log

Wait and Pounce can upload your contacts to **Club Log** in real time, so your online logbook and
DXpedition leaderboards stay current automatically.

## Settings

In **Settings → Club Log**:

| Field | Meaning |
|---|---|
| **Enable automatic upload to Club Log** | Turn real-time upload on/off. |
| **Email** | The email registered with your Club Log account. |
| **API Key** | Your Club Log API key. |
| **Callsign** | Your station callsign. |

Config keys: `enable_club_log_synch`, `club_log_email`, `club_log_password`, `club_log_callsign`.

::: tip Label note
The first credential field is labelled "Callsign:" in the dialog but expects your **registered
email address**. Enter the email you signed up to Club Log with.
:::

## How it works

When a QSO completes and Club Log sync is enabled, the contact is POSTed to the Club Log real-time
endpoint (`https://clublog.org/realtime.php`) as an ADIF record, authenticated with your email,
password and API key (`ClubLogUploader`). Responses are handled so that:

- **403** → authentication failure (sync stops; check credentials).
- **500** → transient server error (retried).
- **400** → invalid record.

Uploaded contacts are tracked in a cache (`club_log_cache.json`) to avoid duplicate uploads.

## DXCC reference data

Club Log is also the source of the app's primary DXCC reference file, **`cty.xml`**. Use
**Tools → Update DXCC Info** to refresh it from Club Log's distribution endpoint. This file powers
the [callsign → entity/zone lookup](/guide/lookup) used to colour decodes and decide marathon
eligibility.
