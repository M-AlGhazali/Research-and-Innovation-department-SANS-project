# A2 data contracts

Contracts use `schema_version=1`, UTF-8 JSON or Parquet, null for unavailable measurements, and explicit field units. JSON contract schemas are in `schemas/`. Filenames and source-row numbers are provenance, not an invitation to publish local data paths.

## Observations

`observations.parquet` contains one retained report per aircraft/report timestamp. Records sort by ICAO address and UTC timestamp. Its logical JSON form is documented by `observation.schema.json`; Parquet additionally stores the native UTC timestamp column.

| Columns | Meaning |
| --- | --- |
| `observation_id`, `source_file`, `source_row`, `source` | SHA-256 of source path and zero-based Parquet row index; raw report can be located exactly. Identity is stable for unchanged files/paths, not across arbitrary relocation. |
| `icao24`, `callsign_raw`, `callsign` | Normalized address, untouched callsign, and trimmed nullable callsign. A callsign is not a flight ID. |
| `timestamp_utc`, `timestamp_ms` | UTC TIMESTAMPTZ and UTC Unix milliseconds; no Riyadh-time shift. |
| `latitude_deg`, `longitude_deg` | WGS84 decimal degrees. |
| `easting_m`, `northing_m` | EPSG:32637 metres; no display exaggeration. |
| `barometric_altitude_ft`, `geometric_altitude_ft` | Pressure altitude and WGS84 ellipsoid altitude, separately nullable. |
| `ground_speed_kt`, `indicated_airspeed_kt` | Ground speed and indicated airspeed, separately nullable. |
| `track_deg`, `true_heading_deg`, `magnetic_heading_deg` | Distinct direction quantities. |
| `barometric_rate_fpm`, `geometric_rate_fpm` | Separate vertical rates. |
| `on_ground`, `position_age_s`, `message_type` | Nullable source status, position age, and message/source category. |
| `quality_*`, `quality_flags` | Original selected integrity indicators and semicolon-delimited processing flags. |

`observation-audit.parquet` identifies rejected/duplicate source records with reasons and, for duplicates, the retained source identity. Reasons include invalid timestamp/address/position, outside tracking envelope, stale position, duplicate timestamp, and isolated jump. Audit scope is selected aircraft/time windows; it is not a global invalid-report census. Raw input records remain unchanged.

## Flights

`flights.json` and `flights.parquet` contain reconstructed event records. IDs combine airport, source date, aircraft address, and an event anchor timestamp. Same inputs/configuration produce the same IDs; changing extraction thresholds or clipping the source window can change event identity.

Each record includes start/end/anchor UTC timestamps, callsign history, runway candidate scores/evidence, status, report count, gap intervals, maximum gap, missing-altitude count, and nullable downstream extensions. Runway statuses are `accepted_departure_candidate`, `ambiguous_runway`, `insufficient_evidence`, and `rejected_non_departure`. Scores are not probabilities.

## Matches

`matches.json` contains one result for every reconstructed event, including events with no plausible SID. `match-candidates.json` and `matches.parquet` are the ranked flight/procedure candidate relation. Records contain heuristic score components, distances, track agreement, order errors, observed reference progress, fix-proximity evidence, gap counts, margin, status, and reasons.

`best_candidate` stays null for ambiguous, unmatched, and insufficient-data outcomes. A unique partial candidate is a geometric hypothesis; it is not an assigned SID. Progress is the portion of reference-leg indexing supported by the simplified geometry, not a validated flown-distance fraction.

## Viewer

`viewer/manifest.json` contains source/reference versions, date, scene origin/CRS, gap limit, UTC bounds, interpretation, and flight summaries with per-flight JSON URLs and content digests. A flight payload contains event and match metadata plus timestamped samples with an explicit column list:

```text
timestamp_ms, x_km, z_km, barometric_altitude_ft,
geometric_altitude_ft, ground_speed_kt, track_deg,
on_ground, quality_flags, observation_id
```

Samples retain report timing/values. Display interpolation is computed in the browser; it is never written back as a source observation. A manifest with no events remains a valid empty export and is explained in the viewer.

## Manifests and review

`preflight.json` identifies input paths, sizes, mtimes, footer row counts, schema, mapping, and cache key. Raw-byte hashes are not claimed. `run-manifest.json` holds configuration, algorithm/dependency versions, stage results, sampled RSS, and elapsed times. Runtime measurements are intentionally volatile and excluded from deterministic content comparisons.

`review-sample.json` selects up to three stable IDs per runway/status stratum, including explicit empty strata. Use the flight selector, overlaid tracks, and ranked explanations to review them. `validation.json` reports structural and content checks and explicitly leaves assignment accuracy unestablished.
