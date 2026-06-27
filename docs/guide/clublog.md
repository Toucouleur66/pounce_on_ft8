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

::: tip Label note
The first credential field is labelled "Callsign:" in the dialog but expects your **registered
email address**. Enter the email you signed up to Club Log with.
:::

## How it works

When a QSO completes and Club Log sync is enabled, the contact is uploaded to Club Log in real
time as an ADIF record, authenticated with your email, password and API key. If authentication
fails, sync stops so you can check your credentials; transient server errors are retried
automatically. Uploaded contacts are tracked in a local cache to avoid duplicate uploads.

## DXCC reference data

Club Log is also the source of the app's primary DXCC country data. Use
**Tools → Update DXCC Info** to refresh it from Club Log. This data powers the
[callsign → entity/zone lookup](/guide/lookup) used to colour decodes and decide marathon
eligibility.
