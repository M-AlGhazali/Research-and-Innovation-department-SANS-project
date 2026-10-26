# Flight analysis reference handoff

Use these **two CSVs**. They replace the previous 22-file handoff.

| File | Purpose | Rows |
|---|---|---:|
| **A1_Procedures.csv** | **Complete procedure-analysis reference: all four A1 PDFs plus relevant outsourced airport/runway facts** | 105 legs |
| **External_Airport_Runways.csv** | Relevant outsourced airport/runway reference facts | 6 runway ends |

## 1. The replacement for A1

**A1_Procedures.csv contains all tabulated A1 procedure data, waypoint coordinates, routing narratives and common instructions, plus the related outsourced airport/runway data directly on each leg row. No manual join to the second CSV is required.** The four PDFs describe 16 SIDs from 34C and 34L, using 36 unique waypoints. One CSV row is one ordered procedure leg. Procedure-level text and instructions repeat on its leg rows so the file works independently.

Included: SID/runway names; sequence and original serial; CF/TF path descriptor; fly-over marker; magnetic and true courses; printed magnetic variation; leg distance; table and narrative turns; altitude and speed restrictions; RNAV specification; original DMS and decimal coordinates; route text and full waypoint sequence; all four common instructions; climb values and ATC qualification; sheet dates, amendments, change notes, source filenames, page locators and hashes.

Use `procedure_id` to group a SID and sort by `sequence_number`. `leg_id` identifies a leg. `serial_number_raw` preserves source numbering such as `010`. `procedure_id` retains the previous export's version key for continuity; the printed sheet date is **17 September 2026**. The matching external AIP issue is effective **1 October 2026**, as recorded in the external CSV.

Important preserved source details:

- EGREP 2W's 13,000 ft ceiling is at **JN520**. Both supplied A1 tables agree; the earlier map transcription was wrong. This CSV corrects that transcription.
- MIGDA 3X references **JN274**, but the 34L waypoint list omits its coordinate. Its coordinate is explicitly cross-referenced from the supplied 34C A1 list. `coordinate_in_departure_runway_list=False` identifies this case.
- Source positive `3.8` magnetic-variation cells, the `ISLM2W` narrative label and visible routing typos remain in their raw fields. Notes are carried on the affected rows.

No source PDF is required to import this CSV. Original source files remain unchanged for verification.

## Related external data included directly in A1

Each A1 leg now also carries airport ARP coordinates/elevation; runway identity, dimensions, surface and bearing; departure and opposite thresholds and elevations; runway slope; full-length and intersection declared distances; published parallel-departure partners; and the external AIP source URL, sections, snapshot hash and effective date. The matching 34C or 34L reference is repeated on that procedure’s rows.

Previous-waypoint coordinates and derived WGS84 fix-to-fix distance/bearing are included for later legs. Published distance cells remain unchanged. Procedure leg counts and distance-completeness summaries are repeated as convenient reference features. Source facts and derived geometry remain distinguishable through column names and `reference_data_note`. These are static references, not observed flights, actual weather or fuel/noise measurements.

## 2. Standalone airport/runway lookup

**External_Airport_Runways.csv** contains airport ARP position/elevation, all three physical runways and their dimensions, six threshold positions/elevations, reciprocal-end references, true bearings, slope, full-length declared distances, intersection departure distances, published independent-departure partners, and the official source/version.

Airport information is repeated on each runway-end row, replacing the separate one-row airport file. Six rows represent directions/thresholds, not six physical runways. `in_initial_study` marks the two study strips; `a1_departure_direction` is true only for 34C and 34L.

The second CSV remains a reusable lookup for all six airport runway ends, including the third runway for context. Its matching study-runway facts are already embedded in A1_Procedures.csv. If refreshing the references later, the join is:

```text
A1_Procedures.airport_icao      = External_Airport_Runways.airport_icao
A1_Procedures.departure_runway  = External_Airport_Runways.runway_end
```

The airport name is descriptive; use the codes as keys. `intersection_departures_json` contains a JSON list of taxiway/TORA/TODA/ASDA records. An empty list means no intersection record was supplied in this snapshot. Partner lists use semicolons and describe published procedure availability, not current runway use or a capacity measurement.

## What was removed from the main handoff

Buildings, roads, railways, land-use polygons, map buffers, WKT display geometry, 3D heights, animation parameters, blank future-observation columns, duplicate feature summaries and separate one-row metadata tables are excluded. They are outside the current A1-to-flight matching reference; relevant airport/runway facts and derived leg reference features remain in the main A1 CSV. Necessary provenance and source caveats are embedded in the two CSVs.

The expanded export is preserved internally at `Research-and-Innovation-department-SANS-project/dataset_tools/archive/expanded_phase1_2026-10-26`. It is an audit/rebuild copy, not another team input.

## Quick review of A2–A6 and how they connect

These were reviewed using their local acquisition/coverage notes and available archive headers. The 10 GB global flight sample was not reprocessed, and no fuel/noise model was run for this simplification.

| Existing folder | Keep for analysis | How to connect |
|---|---|---|
| **A2: observed flights** | Keep the Wingbits sample. The existing local coverage assessment reports useful OEJN coverage. Exclude the separate ADSB.lol archive from this OEJN/date analysis because its recorded coverage check found no nearby positions. | Build departure/flight segments using aircraft identifier, UTC time and position. Use external thresholds to identify runway candidates, then compare ordered tracks with A1 legs. Proximity alone does not prove the assigned SID. |
| **A3: OpenAP 2.6.2** | Keep as a later aircraft-performance/fuel model input. | Resolve A2 aircraft identifiers to ICAO aircraft types first. Select supported aircraft/engine and operating assumptions explicitly. Model outputs are not measured fuel. |
| **A4: ERA5T weather** | Keep both surface and pressure-level files in NetCDF. | Join/interpolate by UTC time, position and appropriate vertical coordinate. Preserve units and preliminary ERA5T status. Do not repeat the entire weather grid on every A1 leg. |
| **A5: ANP/ECAC noise** | Keep the ANP aircraft/NPD tables and method/reference cases for the noise stage. | Map aircraft type to ANP `ACFT_ID`, retaining substitutions, then link aircraft to its `NPD_ID`. ANP/reference cases are model inputs, not observed airport noise. |
| **A6: WorldPop population** | Keep for the later community-noise exposure stage; it is not needed for SID matching itself. Keep the raster format. | Spatially combine population cells with a calculated noise footprint. People per cell is not a measured noise value or people per square kilometre. |

Keep A2–A6 in their existing native formats. Their observation/model/grid grains differ from A1 legs, so they should be joined during the relevant analytical step rather than appended into this reference CSV. The immediate next combination is **A2 tracks + A1_Procedures.csv** (the second CSV is an optional airport-wide lookup); aircraft/weather support subsequent interpretation, and ANP/population support the later environmental stage.

## Import conventions

- UTF-8, comma-delimited, one header row. Empty numeric fields mean missing/not supplied, not zero. Booleans use `True`/`False`.
- Raw `-` cells remain beside normalized numeric columns. `@` = at; `+` = at or above; `-` preceding a numeric altitude/speed = at or below. A plain raw dash means no value supplied.
- `altitude_value` must be read with `altitude_operator` and `altitude_unit`. `FL160` is a standard-pressure flight level, not a surveyed 16,000 ft AMSL height. Feet-valued limits and flight-level limits occupy separate columns.
- Coordinates are WGS84 decimal degrees, positive north/east. Waypoint DMS is preserved. Extra decimal places are conversions, not additional source precision.
- Distances use NM in source fields and metres in converted fields (1 NM = 1,852 m). A blank published CF distance is not filled from a straight-line measurement.
- The first CF leg has no invented previous-fix coordinate. Published course and turn behavior are not reconstructed by joining dots.
- Match A2 altitude datum/type and pressure reference before comparing it with A1 constraints or runway AMSL elevations.

This is the published reference for analysing flights. The actual observations remain in A2. Neither CSV contains simulated flight samples or invented training labels.
