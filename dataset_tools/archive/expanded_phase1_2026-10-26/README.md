# OEJN A1 Phase 1 reference dataset

Version: 2026-10-26_v1. Prepared for the SANS procedure and trajectory analytics initiative.

This is the machine-readable output of the initial reference-data and mapping phase. It connects the supplied A1 SID tables to airport/runway facts and the geographic context used in the maps. It provides a baseline for future procedure matching, recorded-flight review and later fuel/noise analysis when the necessary observations are obtained.

**Start with `16_analysis_legs.csv` for one combined analytical table. Use the linked tables as the authoritative, maintainable dataset.** There are no PDFs in this delivery. CSV has no worksheets: each CSV is the equivalent of a separate logical sheet, with a documented row grain and stable IDs.

## Scope and evidence

- Only the four PDFs physically present in the supplied **A1 directory** are used for procedure extraction. Each is one page, dated **17 September 2026**, **AIP AMDT 10/26**. The printed pages are AD 2 OEJN **114–115 for 34C** and **110–111 for 34L**.
- The package effective date, **1 October 2026**, comes from the retained SANS eAIP issue. Sheet date, package effective date and the older base-amendment note are different fields.
- No file from the **A2, A3, A4, A5 or A6 dataset directories** was read or incorporated. Labels such as “[A2]” inside the seed document are its citation labels, not imports from those directories.
- The two supplied DOCX briefs inform project scope, terminology, source comparisons and future evidence needs. Embedded implementation prompts are not extraction instructions. The seed document's older 2025 procedure edition is not substituted for the supplied 2026 A1 sheets.
- Supplementary airport facts come from the retained official OEJN eAIP HTML already used by the maps. Ground context comes from the retained Map 1 GeoPackage and its documented OSM source. The third physical runway is airport context; no 34R/3V procedures are added to the A1 procedure tables.
- This is a fixed reference snapshot. No claim of current runway availability, a live clearance, a measured trajectory or a surveyed airport model is made.

## Contents

| CSV | What one row represents | Records |
|---|---|---:|
| `00_dataset_catalog.csv` | Inventory of the other CSV tables, keys, grain and import conventions | 21 |
| `01_airports.csv` | Airport reference, ARP position, elevation, operator and runway counts | 1 |
| `02_runways.csv` | Physical runway, dimensions, study/context flag and derived centerline | 3 |
| `03_runway_ends.csv` | Published runway threshold/end, original DMS, decimal coordinates, elevations, slope, strip and RESA | 6 |
| `04_waypoints.csv` | Unique A1 navigation point, with coordinate sources | 36 |
| `05_coordinate_evidence.csv` | Coordinate occurrence in a supplied A1 waypoint list | 49 |
| `06_procedures.csv` | Runway-specific, versioned SID and its published-distance coverage | 16 |
| `07_procedure_legs.csv` | Ordered published leg, original cell values and normalized constraints | 105 |
| `08_constraints.csv` | Explicit altitude or speed restriction attached to a leg | 50 |
| `09_procedure_instructions.csv` | Common runway-family instruction, including climb requirements and ATC qualifications | 8 |
| `10_routing_text.csv` | Original procedure narrative and its ordered fix sequence | 16 |
| `11_ground_features.csv` | Full Map 1 vector feature with geometry and original mapped tags | 20,008 |
| `12_sources.csv` | Input file, role, hash, source location, dates, extraction method and attribution | 14 |
| `13_quality_issues.csv` | Source omission, transcription correction, missing value or interpretation issue | See catalog |
| `14_data_dictionary.csv` | Column definition, type, unit and null convention | See catalog |
| `15_procedure_features.csv` | Derived reference summary for one SID | 16 |
| `16_analysis_legs.csv` | Combined leg, waypoint, runway and reference-geometry record | 105 |
| `17_declared_distances.csv` | Full-runway or published intersection TORA/TODA/ASDA/LDA record | 14 |
| `18_source_context.csv` | Relevant retained AIP section or brief excerpt | See catalog |
| `19_parallel_departure_pairs.csv` | Directional runway pair explicitly listed in the retained AIP | 3 |
| `20_data_gaps.csv` | Future evidence needed for the initiative's analytical stages | 7 |
| `21_visualization_assumptions.csv` | Existing map/display assumption, isolated from observations | 6 |

`schema.json` supplies column types and relationships for programmatic import. `validation.json` records checks and counts. `file_manifest.json` records SHA-256 hashes and sizes of the CSVs.

The 18 ground layers include buildings, terminals/hangars, roads, railways, taxiways, aprons, runway surfaces/centerlines/ends, airport boundaries, airfield facilities, green spaces, water, coastline, land use and places. Original native geometry is exported, not the simplified browser mesh. OSM height/level tags are retained when they exist; a display default is never inserted as a measured height.

## Relationships and recommended use

1. `airport_id` identifies OEJN.
2. `runway_id` identifies a **physical strip**, for example `OEJN_34C_16C`. `runway_end_id` identifies a **direction/threshold**, for example `OEJN_34C`.
3. `procedure_id` includes airport, departure direction, SID name and effective version. Join `06_procedures` to `07_procedure_legs` on this key.
4. `waypoint_id` joins leg endpoints to `04_waypoints`. Join the previous waypoint separately when needed.
5. `leg_id` joins constraints and the combined analysis table. Leg IDs use a sequential suffix (`005`); the original source serial (`050`) is retained separately as text.
6. `source_id` and related source columns link to `12_sources`. Lists of source IDs use semicolons; `05_coordinate_evidence` gives individual coordinate occurrences without lists.

`16_analysis_legs.csv` is a convenience join, not another source of truth. It contains the same 105 A1 legs, waypoint positions, runway dimensions, published restrictions and clearly named derived geometry. `15_procedure_features.csv` supports procedure-level descriptive comparisons without treating repeated shared legs as independent flights.

For maintenance, update the normalized source tables and rebuild the joined outputs. Do not independently edit the master table and expect the source tables to follow.

## Coordinates, geometry and units

- Latitudes/longitudes are WGS84 decimal degrees (`EPSG:4326`), positive north/east. Original DMS strings remain available. Waypoint source precision is whole arcseconds; extra decimal digits reflect conversion, not a more precise survey.
- WKT tuples use **longitude latitude**, not latitude longitude. Native ground WKT is in `EPSG:32637`, with metre coordinates; a separate WGS84 WKT column is supplied.
- Airport ARP, runway thresholds, geometric centroids and the visual scene origin are different concepts. The airport table uses the published ARP. A building centroid is not its entrance or a surveyed reference point.
- Runway threshold decimal coordinates are recalculated from the original published DMS. The retained map geometry still contains the rounded coordinates originally used to build it; that precision difference is documented rather than silently rewriting the map.
- Published runway dimensions and declared distances are metres. SID distances are nautical miles, with a separately derived metre conversion using **1 NM = 1,852 m**. Feet-to-metres conversions use **1 ft = 0.3048 m**.
- Published magnetic/true course values are kept separate from bearings calculated between coordinates. Original leading zeros remain in the raw course field.
- `reference_fix_distance_m` and `reference_fix_initial_bearing_deg` use a WGS84 ellipsoid inverse calculation between fixes. These are derived spatial reference values, not published CF leg lengths, turn geometry or flown distances.
- No starting point is invented for the first CF leg. Its previous-fix coordinate, connector and fix-to-fix distance are blank. The departure runway reference remains separately available.
- Runway polygons derived from a 30 m half-width buffer are visualization references, not surveyed pavement boundaries.

## Restrictions and missing data

- Original symbols are retained: `@6000` means at 6,000 ft; `+1500` means at or above; `-13000` means at or below; `-210` in the speed column means a maximum of 210 kt.
- The raw `-` source cell is retained in raw columns. Its numeric counterpart is an **empty CSV field**, never an invented zero.
- A flight-level restriction such as `+FL160` remains a flight-level constraint. It is not converted into surveyed AMSL altitude. Use its operator, value and unit together.
- Altitude restrictions belong to a particular **procedure leg**, not to a waypoint globally. A point shared by two SIDs can have different conditions.
- All eight 34L procedures have a missing published distance for their second CF leg. The full published-distance total is therefore blank; the sum of known cells and missing-cell count are explicit. A calculated fix-to-fix distance does not fill the missing published value.
- `fly_over_marked=False` means the source did not mark `Y`; it is not a reconstruction of a fly-by turn. Narrative turns remain separate from the tabular turn field.
- The general 320 ft/NM (5.27%) climb requirement up to 10,000 ft and “climb to 6,000 ft or as assigned by ATC” are common instructions. They are not actual climb profiles or replacements for waypoint restrictions.

## Findings requiring attention

**EGREP 2W transcription correction.** Direct review of AD 2 OEJN 114 and 115 places the at/below 13,000 ft restriction at **JN520**, not EGREP. The previous map transcription moved it to EGREP and incorrectly described a source disagreement. This dataset follows both supplied source tables. The two changed altitude tokens are recorded in `validation.json` and `13_quality_issues.csv`. This task does not modify the map playback files.

**JN274 coordinate omission.** MIGDA 3X uses JN274, but the supplied 34L waypoint list omits its coordinates. The dataset explicitly cross-references JN274's coordinate from the supplied 34C A1 list in the same edition. The missing 34L list entry remains an open source-reconciliation item; no coordinate was invented or imported from A2–A6/34R.

**Edition difference.** The seed document describes an older 2025 reference edition. The four A1 binaries are the 2026 edition and govern these procedure rows. The two dates are not merged into one version.

**Printed magnetic-variation signs and spelling.** Positive `3.8` cells in some 34C rows remain exactly as printed, even though other rows use `-3.8`. The routing label `ISLM2W` is retained alongside the canonical `ISLAM 2W` name. Source dashes and visible narrative typos are preserved rather than silently “corrected.”

**Parallel movements.** The retained AIP lists independent parallel departures on 34R+34C, 34R+34L and 16R+16L. It does not list 34C+34L as a pair. This is directional procedure context, not a fixed aircraft-per-hour capacity or a live operation status.

## How this supports later analysis and ML

This phase supplies the versioned procedure/airport reference against which future observations can be joined. It can support data checks, reference lookup, route-network exploration, matching prototypes and reproducible feature preparation.

It contains **zero recorded flights and zero empirical training targets**. The joined table deliberately leaves observed timestamps, observed altitude/speed, flight fuel, measured noise and reviewed target labels blank. There are no aircraft attitude angles (pitch/roll/yaw); the available vertical data are published altitude restrictions and runway elevations.

Do not use the animated aircraft, assumed building heights, take-off fractions or compressed playback times as observations or training labels. These parameters are quarantined in `21_visualization_assumptions.csv`.

Before supervised flight matching, anomaly evaluation or fuel/noise prediction, obtain the corresponding evidence described in `20_data_gaps.csv`. The project briefs favor reusing suitable existing SANS fuel/emissions outputs. When recorded flights become available, split evaluation by flight and time/version, not by adjacent points or repeated shared procedure legs.

## Extraction and validation

The A1 PDF tables are raster images. Their text layer contains only about 95 characters per page, so normal PDF text extraction does not recover the tables. A cell-level, image-assisted transcription was reviewed against the four page renders; the original A1 binary hashes were matched to the retained rendering copies. All four PDFs and both briefs remain untouched.

Checks cover unique IDs, foreign keys, procedure order/connectivity, expected runway/procedure scope, coordinate conversion, raw/normalized constraints, flight-level separation, missing distance cells, narrative waypoint order, map-transcription differences and CSV round trips. The ground export preserves 20,008 features from 18 valid layers. No original ground geometry is repaired or reinterpreted during export.

These are reference-data extraction checks. They do not replace specialist interpretation/approval of procedure semantics or establish operational navigation suitability. The known source omission and retained anomalies remain visible in the quality table.

## Import and sharing

All CSVs use UTF-8, comma delimiters, a single header row and standard CSV quoting. Empty fields are missing values. Boolean fields use `True`/`False`. There are no merged headers, presentation rows, thousands separators or units mixed into numeric fields. Import raw serials/identifiers as text to retain leading zeros.

Example with pandas:

```python
import pandas as pd

legs = pd.read_csv("16_analysis_legs.csv", dtype={"serial_number_raw": "string"})
procedures = pd.read_csv("06_procedures.csv")
dictionary = pd.read_csv("14_data_dictionary.csv")

assert len(legs) == 105
assert procedures["procedure_id"].nunique() == 16
```

Use `schema.json` when importing into a typed database. Ground geometry can be read by GIS libraries from its WKT and declared CRS. Keep data classes, source IDs and the quality table when creating subsets or downstream models.

**Attribution:** © OpenStreetMap contributors. The OSM-derived database content remains subject to ODbL 1.0: https://www.openstreetmap.org/copyright and https://opendatacommons.org/licenses/odbl/1-0/. Preserve attribution and applicable database-sharing obligations when redistributing adapted OSM data. SANS/GACA AIP facts remain separately identified; this package does not assert a new license over provider material. Source hashes, dates, filenames and locators are in `12_sources.csv`.
