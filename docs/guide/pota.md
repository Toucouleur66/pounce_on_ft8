# Parks On The Air (POTA)

**Parks On The Air** is a program where operators *activate* parks and other reference areas, and
*hunters* chase those activations. Because one operator activates many different parks over time —
and each park reference counts as a fresh catch — POTA hunting works differently from your normal
wanted list. Wait and Pounce's POTA mode turns it into an activator-hunter: it will reply to any
station that is **currently spotted as a POTA activator**, and show you which park they're in.

## What it does

Unlike [Marathon](/guide/marathon) or the [DXCC Program](/reference/settings#dxcc-program) — which
decide what you need from your local [logbook](/guide/adif) — POTA status can't be read from your
log. It is **spot-driven**: Wait and Pounce fetches the live list of activator spots from
[pota.app](https://pota.app) and cross-references it against every decoded callsign.

When a decoded station matches a currently-spotted activator:

- the row is highlighted in **green**, and
- the focus label shows the **park reference** it was spotted at (for example `/ US-1234`).

If that station later answers *you*, the display switches to the normal "calling you" style, just
like any other QSO.

## Configuring it

In **Settings → Parks On The Air**, tick **Enable reply to POTA**. That's the only switch — there is
no per-band selection. Once enabled, a **POTA** entry appears in your
[Priority Manager](/guide/reply-engine#your-priority-order) so you can decide where park activators
rank against your other reasons to call.

## How activations are found

- Live activator spots are fetched from pota.app every few minutes.
- Only **FT8 and FT4** spots are kept — this is an FT8/FT4 assistant, so activators spotted only on
  CW or SSB are ignored.
- A decoded callsign that matches a spotted activator becomes a reply candidate, tagged with that
  activator's current park reference.

## Same operator, new park

A hunter wants each *park*, not each *operator*. So POTA tracking is by
**callsign + park reference**, reset at **00:00 UTC**:

- Once you've replied to an activator at a given reference, that exact pairing won't be chased again
  the same UTC day.
- If the same operator moves to (or is re-spotted at) a **different** reference, they become a fresh
  candidate and Wait and Pounce will call them again.

Because a park is a new catch every time, **Worked-Before rules are ignored for POTA** — an operator
you've already worked today is still worth calling from a different park.

## POTA vs the other programs

POTA feeds the same [reply engine](/guide/reply-engine) as everything else and can be active
alongside Wanted, Marathon, DXCC and Grid:

- **Wanted / CQ Zone / Marathon / DXCC / Grid** decide need from *your logbook*.
- **POTA** decides need from *live pota.app spots* — who's on the air in a park right now.

Where a park activator ranks against those is entirely up to your
[Priority Manager](/guide/reply-engine#your-priority-order) order.
