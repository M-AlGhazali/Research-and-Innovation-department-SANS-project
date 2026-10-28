# Local A2 setup

Use Python 3.12 and Node.js 22 or later. No cloud account, aircraft metadata API, QGIS, or pyarrow is needed for ordinary A2 processing. QGIS remains optional for rebuilding ground geometry; retained references and map assets are sufficient for this pipeline.

From the application checkout:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m sans_a2 run --config config/oejn-2026-10-01.json
.\.venv\Scripts\python.exe -m sans_a2 serve --config config/oejn-2026-10-01.json
```

Open `http://127.0.0.1:8765/map-2/` and select **Recorded flights · local A2**. The page also retains the published procedure demonstration. Press Ctrl+C in the serving terminal to stop the local server. Use `--port` when 8765 is occupied.

The example configuration expects sibling `SANS/A2/wingbits_2026-10-01_00.parquet` through `_23.parquet`. It writes to sibling `SANS-output/a2/2026-10-01`, outside the application checkout. Relative paths resolve against the configuration file, not the shell working directory. Adjust those two paths for another layout.

The run command performs reference export, ingestion, flight extraction, matching, viewer export, and validation. Each operation can also be run independently:

```powershell
python -m sans_a2 reference
python -m sans_a2 preflight
python -m sans_a2 ingest
python -m sans_a2 flights
python -m sans_a2 match
python -m sans_a2 export
python -m sans_a2 validate
```

Use the virtual-environment Python when it is not activated. `ingest --force` bypasses its observation cache. After changing processing configuration, rerun `run` rather than applying a later stage to old intermediates. Preflight validates all input schemas and records physical row totals from file footers; this is not an integrity hash verification of all raw bytes.

## Resource use

The example permits four DuckDB threads and 768 MB of database working memory, with spill files beneath the configured output root. That setting does not include every Python/native allocation; measured process RSS is reported separately. Only selected aircraft/time windows are materialized after airport discovery. Coordinate projection operates on 25,000-row pandas/NumPy batches through pyproj, outside DuckDB worker callbacks. This avoids a native Windows pyproj callback failure encountered during development. pandas never receives the full global day.

Allow disk space for selected observations, audit rows, work database, spill, and compact per-flight exports. The CLI reports stage durations and sampled peak process RSS in `run-manifest.json`. Stages are sequential; do not run two ingestion writers against the same output directory.

## Local serving and publishing

The A2 server binds to localhost and exposes an allowlist of viewer assets plus JSON beneath the configured viewer export root. It does not serve `.git`, raw A2, arbitrary workspace files, or directory listings. Real flight exports are not copied into the repository or the static deployment. GitHub Pages can serve the illustrative viewer and its recorded-mode controls without distributing traffic data; absent data produces a local-dataset explanation.

The self-contained `Open Map 2.html` continues to support the illustrative scene. Recorded data is intentionally not embedded in that shareable file. Use the local server for recorded playback.

The Wingbits sample is evaluation data. The current provider page states evaluation-only use and restricts commercial/revenue-generating use without prior written consent. This implementation does not establish permission to publish derived traffic exports.

## Troubleshooting

- No files: check `input_glob` and the date; the separate ADSB.lol archive is excluded.
- Schema drift or non-UTC annotation: processing fails explicitly; update and verify the provider adapter instead of guessing conversions.
- No local observations in the browser: finish `run`, use `sans_a2 serve`, and reload. The original map-only server does not expose external traffic outputs.
- Reference version mismatch: rerun `reference`, then `export`, and reload. For changed source inputs/configuration, run the complete pipeline.
- Long gaps: a missing aircraft during a gap is intentional. Select a recorded timestamp to inspect the next report.
- Unknown altitude: a ground projection marker represents known horizontal position; no aircraft is rendered at an invented height.
- Stale browser view: hard reload after source changes; the development server sends `Cache-Control: no-store`.

## Development checks

```powershell
python -m pytest -q
node tests/test-observed-model.mjs
node map-2/test-flight-model.mjs
python tools/build_map2_offline.py
```

Synthetic fixtures are confined to temporary test directories. They are never mixed into the configured real output root. The CI workflow uses only synthetic data and committed references.
