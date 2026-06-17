# Callsign Lookup & Data Files

Every decode is enriched with its **DXCC entity**, **CQ zone**, **continent** and **grid** so the
engine can colour rows, evaluate marathon/zone targets, and flag LoTW users. This page explains
the lookup and the data files behind it.

## The lookup chain

For each callsign, `CallsignLookup.lookup_callsign()` resolves in priority order:

1. **In-memory cache** — a fast LRU of recent lookups.
2. **Invalid operations** — known bogus/illegal operations are rejected.
3. **Club Log callsign exceptions** — per-call overrides (e.g. a call operating from a different
   entity). Highest confidence.
4. **CTY data** — the primary entity/zone source (longest-prefix match, plus exact-call
   overrides).
5. **Club Log prefix fallback** — longest-first prefix scan.

The result includes `entity`, `cq_zone`, `continent`, `grid` (with a `grid_source` of
*provided* → *cache* → *guessed*), and a `lotw` flag.

## Data files

| File | Source | Purpose |
|---|---|---|
| **`cty.xml`** | Club Log | Primary DXCC entities, prefixes, exceptions, invalid operations. |
| **`CTY_WT_MOD.DAT`** | country-files.com (AD1C) | "WT-mod" country file with exact-call and zone overrides. |
| **`cq-zones.go`** | bundled | CQ-zone polygon geometry (point-in-polygon zone lookup from a grid). |
| **`lotw-user-activity.csv`** → `lotw_cache.json` | ARRL LoTW | Which callsigns use LoTW (the **•** indicator + LoTW filter). |
| **`lookup_cache.json`** | generated | Persistent LRU cache of resolved lookups (up to ~32,000). |
| **`GRD_WP.txt`** → grids cache | bundled | Callsign → grid fallback. |

## Keeping data current

From the **Tools** menu:

- **Update DXCC Info** → refreshes `cty.xml` from Club Log.
- **Update country and region files** → refreshes `CTY_WT_MOD.DAT` from country-files.com.
- **Update LoTW Info** → refreshes the LoTW user-activity cache.

A bulk downloader can fetch all three in one pass (used during update flows).

## CQ-zone resolution

To find a CQ zone from a grid, the app converts the Maidenhead locator to latitude/longitude and
runs a **point-in-polygon** test against the CQ-zone polygons (with a nearest-zone fallback near
borders). This is what makes **Wanted CQ Zone(s)** targeting work even when the decode doesn't
explicitly state a zone.

## Caching and performance

- Lookups are memoised in memory and persisted to `lookup_cache.json`, flushed on exit.
- Prefix tables are pre-indexed for fast longest-prefix matching.
- Grid/coordinate helpers are cached, so heavy band openings don't bog down the UI.

::: info Developer note
`zone_exceptions` from `cty.xml` is currently parsed but not consulted in the lookup path — a
minor latent gap noted during source analysis. It does not affect normal entity/zone resolution.
:::
