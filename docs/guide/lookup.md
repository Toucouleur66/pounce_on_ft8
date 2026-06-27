# Callsign Lookup & Data Files

Every decode is enriched with its **DXCC entity**, **CQ zone**, **continent** and **grid** so the
engine can colour rows, evaluate marathon/zone targets, and flag LoTW users. This page explains
the lookup and the data files behind it.

## The lookup chain

For each callsign, the app resolves the entity in priority order:

1. **In-memory cache** — a fast cache of recent lookups.
2. **Invalid operations** — known bogus/illegal operations are rejected.
3. **Club Log callsign exceptions** — per-call overrides (e.g. a call operating from a different
   entity). Highest confidence.
4. **Country data** — the primary entity/zone source (longest-prefix match, plus exact-call
   overrides).
5. **Prefix fallback** — longest-first prefix scan.

The result includes the entity, CQ zone, continent and grid (noting whether the grid was
provided, cached or guessed), plus a LoTW flag.

## Data files

The app relies on a few reference data sets:

- **Country data files** (from Club Log and country-files.com) — DXCC entities, prefixes, exact-call
  and zone overrides, and invalid operations.
- **CQ-zone geometry** (bundled) — used to find the CQ zone from a grid.
- **The LoTW user list** (from ARRL LoTW) — which callsigns use LoTW (the **•** indicator + LoTW
  filter).
- **A local cache** of resolved lookups and callsign→grid fallbacks, for speed.

## Keeping data current

From the **Tools** menu:

- **Update DXCC Info** → refreshes the DXCC country data from Club Log.
- **Update country and region files** → refreshes the country file from country-files.com.
- **Update LoTW Info** → refreshes the LoTW user list.

These can also be refreshed together in one pass during update flows.

## CQ-zone resolution

To find a CQ zone from a grid, the app converts the Maidenhead locator to latitude/longitude and
tests it against the CQ-zone areas (with a nearest-zone fallback near borders). This is what makes
**Wanted CQ Zone(s)** targeting work even when the decode doesn't explicitly state a zone.

## Caching and performance

- Lookups are kept in memory and persisted to a local cache, flushed on exit.
- Prefix tables are pre-indexed for fast longest-prefix matching.
- Grid/coordinate helpers are cached, so heavy band openings don't bog down the UI.
