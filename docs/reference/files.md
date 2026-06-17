# Files & Data Stores

Wait and Pounce keeps its config, caches and logs in an **application data directory** (resolved by
`get_app_data_dir()`), and ships reference data alongside the program. This page lists the
important files.

## Configuration & state

| File | Constant | Contents |
|---|---|---|
| `params.json` | `PARAMS_FILE` | All user settings (current format). |
| `params.pkl` | `PARAMS_FILE_LEGACY` | Legacy pickled settings (migrated to JSON). |
| `app_version.json` | `SAVED_VERSION_FILE` | Last-run version (first-launch detection). |
| `window_position.json` | `POSITION_FILE` | Window geometry. |
| `marathon.json` | `MARATHON_FILE` | DX-Marathon progress (see note). |
| `worked_callsigns.pkl` | `WORKED_CALLSIGNS_FILE` | Worked-callsigns history (UI panel). |
| `temp_excluded_callsigns.pkl` | `TEMP_EXCLUDED_CALLSIGNS_FILE` | Persisted temporary exclusions. |

## Logs

| File | Contents |
|---|---|
| `wait_pounce_log.adif` | The app's own ADIF backup of every QSO it logs (`ADIF_WORKED_CALLSIGNS_FILE`). |
| `pounce.log`, `pounce.log.YYMMDD` | Rotating application log (enable via Settings → Debugging). |

## Reference / lookup data

| File | Source | Used by |
|---|---|---|
| `cty.xml` | Club Log | Primary DXCC entity/zone resolution. |
| `CTY_WT_MOD.DAT` | country-files.com | WT-mod overrides. |
| `cq-zones.go` | bundled | CQ-zone polygons. |
| `lotw-user-activity.csv` → `lotw_cache.json` | ARRL LoTW | LoTW user flag (•). |
| `lookup_cache.json` | generated | Persistent lookup LRU cache. |
| `GRD_WP.txt` | bundled | Callsign → grid fallback. |
| `sounds/` | bundled | Alert WAV files. |
| `translations/` | bundled | Compiled `.qm` localisation files. |

## Integration caches / logs

| File | Constant | Contents |
|---|---|---|
| `club_log_cache.json` | `CLUB_LOG_CACHE_FILE` | Club Log upload dedup. |
| `lotw_upload_cache.json` | `LOTW_UPLOAD_CACHE_FILE` | LoTW upload dedup. |
| `lotw_qsl_log.json` | `LOTW_QSL_LOG_FILE` | Audit of downloaded LoTW confirmations. |
| `~/.dx-pounce/telemetry_config.json` | — | Installation id/secret for telemetry. |

::: warning Notes for this branch
- **`marathon.json`** is *read* at startup but the write-back is commented out on the
  `handle_slave` branch — session marathon progress is not persisted to it (the ADIF log remains
  the source of truth). See [Marathon](/guide/marathon).
- `.gitignore` excludes most generated artefacts (`*.json`, `*.pkl`, `*.log*`, `*.adif`, `*.png`,
  `test*.*`, `build*`, `dist/`) — except `lotw_cache.json`, which is intentionally tracked.
:::

## Remote endpoints

| URL | Purpose |
|---|---|
| `https://f5ukw.com/public/update_info.json` | Update check. |
| `https://f5ukw.com/public/readme.txt` | Remote README. |
| `https://f5ukw.com/api` | Telemetry (register/heartbeat/users). |
| `https://cdn.clublog.org/cty.php?api=…` | `cty.xml` download. |
| `https://www.country-files.com/cty/cty_wt_mod.dat` | Country file download. |
| `https://lotw.arrl.org/…` | LoTW report download / user activity. |
| `https://clublog.org/realtime.php` | Club Log real-time upload. |
