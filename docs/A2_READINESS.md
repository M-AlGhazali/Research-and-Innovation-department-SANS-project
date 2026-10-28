# A2 readiness — 27 October 2026

**Ready for local trajectory/SID feasibility review and iterative research development.** Actual assignment accuracy and downstream environmental/operational claims remain unvalidated.

The integration is based on `e108908` and is prepared on `codex/a2-integration` for review into `main`. Raw observations and generated traffic exports remain outside the application checkout. Pushing this topic branch does not run the main-branch Pages deployment; merging into `main` retains the repository's existing deployment behavior.

## Delivered

| Requirement | Implementation | Verification evidence |
| --- | --- | --- |
| One canonical A1 study reference | `reference.py`; generated study JSON; CSV-derived compatibility tokens; separate 34R context | 105 legs/16 procedures/36 study fixes; 24 combined viewer routes; correction and deterministic export tests |
| Efficient real A2 ingestion | Disk-backed DuckDB discovery/retrieval and vector pyproj conversion | Full 24-file source day processed; bounded memory; 622,080 retained reports; audit accounting |
| UTC/unit/provenance preservation | Provider mapping, separate measurement columns, source-file/row IDs, native UTC Parquet time | Footer/schema checks, cross-hour tests, explicit schema contract and datum documentation |
| Flight and runway reconstruction | Deterministic event IDs, ranked evidence, ambiguous/insufficient/rejected categories | Both runways and repeat/intersection/missing-ground cases tested; 213/28 real candidates |
| Defensible SID candidate ranking | Ordered alignment, explicit geometric/direction/order/gap terms, shared-trunk ambiguity | Synthetic ambiguity/continuation/remote-track cases; all 872 events have outcomes; 22-event review set and sensitivity results |
| Recorded multi-flight playback | Flight-ID state, recorded UTC timeline, partitioned loading, gap-aware sampling | Real same-runway aircraft viewed together; gap seek, play/pause, filters and candidate detail exercised |
| Existing viewer retained | Separate illustrative mode, cameras, ground assets, 34R context | 24-route/198-endpoint Node checks and 34R browser playback |
| Reproducible CLI/build | Individual stages plus full `run`, configuration, lockfile, allowlisted localhost server and CI checks | Forced second run: 877 byte-identical outputs; dependency/diff checks; offline build |
| Reviewable artifacts and schemas | Observation/flight/match/viewer contracts, intermediate Parquet, audit, manifests, per-flight exports, review/sensitivity reports | Schema, identity, count, temporal ordering and content-hash checks |
| Documentation | Setup, schemas, methods, validation and this readiness report | Reproduction commands and actual metrics recorded; interpretation and outstanding research prerequisites explicit |
| A3–A6 extension interfaces | Versioned nullable metadata/model-link contracts, per-flight unresolved extensions | Core A2 uses no metadata API; no fuel/noise/capacity values fabricated |

## Where the local results are

The `output_dir` configured in `config/oejn-2026-10-01.json` (by default, the sibling directory `SANS-output/a2/2026-10-01`).

That folder contains `observations.parquet`, `observation-audit.parquet`, `flights.json`/`.parquet`, `matches.json`, ranked-candidate Parquet/JSON, `viewer/manifest.json`, per-flight viewer partitions, `review-sample.json`, `sensitivity.json`, `validation.json`, `preflight.json`, `run-manifest.json`, and `reproducibility.json`. These traffic artifacts are not tracked by the application repository or copied by its Pages workflow.

The local viewer runs at `http://127.0.0.1:8765/map-2/`. Select recorded mode. Use [setup](A2_SETUP.md) to restart processing or serving; the existing `Start Map 2.cmd` remains the original map-only launcher, so use the documented A2 server command for external observation exports.

## Interpretation that remains required

Only **two events** were geometry-consistent and **one** had a unique partial candidate under the default heuristic; 60 remained ambiguous and 176 unmatched, with the other 633 lacking sufficient matching data. Those counts include rejected/uncertain local activity and do not establish assignment accuracy. Seven of 22 review events changed interpretation under alternative geometric tolerances. Independent labels or expert review are needed before relying on SID classifications.

The current Wingbits dictionary confirms field identities. Some unit/datum conventions rely on the documented readsb correspondence and the provider's altitude example; measurement calibration is not independently verified. Approximate display offsets are explicitly not a physical AGL or QNH conversion. Raw observations remain unchanged and source identities were checked, with no claim of newly verified full raw-file SHA-256 integrity.

Aircraft/type mapping, validated fuel models, weather interpolation, reference-case-validated noise calculations, population exposure, and operational capacity analysis are separate later work. The interfaces and prerequisites are prepared; those calculations are intentionally absent from this A2 delivery. Data redistribution permission and single-day representativeness also remain unresolved research prerequisites.
