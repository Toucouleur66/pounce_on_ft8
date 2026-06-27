# DX Marathon

The **CQ DX Marathon** is an annual award for working as many DXCC entities and CQ zones as
possible within a calendar year. Wait and Pounce's Marathon mode turns it into an entity-hunter:
it will reply to *any* station from a DXCC entity you still need this year, even if that exact
callsign isn't on your wanted list.

## What it does

When Marathon is enabled for a band, a decoded station becomes a reply candidate if its **DXCC
entity** has not yet been worked this year. When a station is chosen on this basis, the focus
label shows the **`/ MARATHON`** suffix.

## Configuring it

In **Settings → DX Marathon** you get a grid of per-band toggle buttons plus a special
**Unlimited** button:

- **Per-band buttons** — enable Marathon hunting on specific bands. The "need an entity" check is
  evaluated **per band** (you need the entity once on each enabled band).
- **Unlimited** — a mutually-exclusive mode where you need each entity only **once on any band**.
  Selecting Unlimited disables the individual per-band buttons.

## How "needed" is decided

Marathon need is read from your loaded [logbook](/guide/adif):

- **Per-band mode** — an entity is needed if you haven't worked it *this year on this band*.
- **Unlimited mode** — an entity is needed if you haven't worked it *this year on any band*.

As you complete contacts, worked entities for the year are tracked so the app stops chasing an
entity once you've worked it. Your live logbook stays the source of truth for what you've worked,
so reloading your log always restores accurate progress.

## Marathon vs Wanted vs Grid

These can all be active at once and feed the same [reply engine](/guide/reply-engine):

- **Wanted** chases *specific* callsigns/zones you typed.
- **Marathon** chases *any* station from a *needed entity*.
- **Grid Tracker** chases *new grid squares*.

Their relative importance is set in [Choosing Who to Reply To](/guide/reply-engine) — by default a
wanted callsign outranks a marathon entity, which outranks a new grid.
