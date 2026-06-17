# DX Marathon

The **CQ DX Marathon** is an annual award for working as many DXCC entities and CQ zones as
possible within a calendar year. Wait and Pounce's Marathon mode turns the engine into an
entity-hunter: it will reply to *any* station from a DXCC entity you still need this year, even if
that exact callsign isn't on your wanted list.

## What it does

When Marathon is enabled for a band, a decode is treated as a reply candidate if its **DXCC
entity** has not yet been worked this year (per the rules below). When a station is chosen on this
basis the focus label shows the **`/ MARATHON`** suffix.

## Configuring it

In **Settings → DX Marathon** you get a grid of per-band toggle buttons plus a special
**Unlimited** button:

- **Per-band buttons** — enable Marathon hunting on specific bands. The "need an entity" check is
  evaluated **per band** (you need the entity once on each enabled band).
- **Unlimited** — a mutually-exclusive mode where you need each entity only **once on any band**
  (band-agnostic). Selecting Unlimited disables the individual per-band buttons.

## How "needed" is decided

Marathon need is derived from your loaded [ADIF log](/guide/adif), grouped as
`year → band → set(entity codes)`:

- **Per-band mode** — an entity is needed if you haven't worked it *this year on this band*.
- **Unlimited mode** — an entity is needed if you haven't worked it *this year on any band*.

As you complete contacts, the worked entities for the year are tracked in memory
(`wanted_callsigns_per_entity`) so the engine stops chasing an entity once you've worked it.

::: warning Persistence on this branch
On the current development branch, Marathon progress is **loaded** from `marathon.json` at
startup, but the write-back (`save_marathon_wanted_data()`) is commented out — so progress made
during a session is not written to that file. The live ADIF log remains the source of truth for
what you've worked, so reloading your log restores accurate state. This is a known rough edge on
the `handle_slave` branch.
:::

## Marathon vs Wanted vs Grid

These can all be active at once and feed the same [priority engine](/guide/reply-engine):

- **Wanted** chases *specific* callsigns/zones you typed.
- **Marathon** chases *any* station from a *needed entity*.
- **Grid Tracker** chases *new grid squares*.

Their relative importance is set by your
[Priority Manager](/guide/reply-engine#priority-manager) order — by default a wanted callsign
outranks a marathon entity, which outranks a new grid.
