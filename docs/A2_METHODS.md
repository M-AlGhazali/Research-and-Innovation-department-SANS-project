# A2 methods and research limits

## Reference

The committed `data/A1_Procedures.csv` is the study source of truth. Its deterministic exporter generates the viewer's 34C/34L routes and the matcher's reference, preserving IDs, sequence, raw restrictions, separate flight-level units, sources, and caveats. The 34R context has a separate versioned file. The EGREP 2W ceiling is at JN520; MIGDA 3X retains the JN274 coordinate cross-reference caveat. No published missing CF distance is filled using straight-line geometry.

Git attributes require LF line endings for canonical CSVs, keeping the recorded source-byte hashes identical across Windows and Linux checkouts. A regression test compares checkout hashes with the committed Git bytes.

The optional QGIS ground rebuild consumes compatibility tokens derived from the CSV and 34R context, then applies the canonical exporter. Ordinary A2 work does not rerun the old full-dataset rebuild with its external document dependencies.

## Provider adapter

Field identities were confirmed in the [current Wingbits sample dictionary modal](https://wingbits.com/data-sample) on 27 October 2026, consistent with the [historical sample dictionary](https://sample.wingbits.com/). Units follow the matching readsb field conventions, documented in [readsb JSON](https://github.com/wiedehopf/readsb/blob/dev/README-json.md); the [Wingbits API example](https://wingbits.com/business-solutions/flight-data-api) also identifies altitude in feet. This correspondence is a documented provider-semantic assumption, not independent calibration of the historical sample. The exact input schema and mapping are saved with every run. `t` is the sample's message type; no aircraft type is inferred from it.

Unmapped raw fields remain in the unchanged input rather than receiving guessed meanings. Pressure altitude, ellipsoid altitude, indicated airspeed, ground speed, track, heading, and the two vertical rates remain distinct. No QNH correction, IAS substitution, physical terrain model, or constraint-compliance classifier is applied.

## Ingestion and cleaning

A bounding-box-filtered spherical 40 km search finds airport-area aircraft for the configured UTC day. A second selective pass retrieves their records over per-aircraft time windows and a configurable 240 km envelope. Those windows span all observed local encounters; the event extractor separately caps each departure at 60 minutes. The discovery boundary does not truncate tracks at 40 km.

Selected invalid positions/timestamps/addresses, stale reports, and out-of-envelope positions enter the audit. At duplicate aircraft/timestamps, the deterministic preference is higher NAC-p, lower position age, available geometric altitude, then file/row identity. Conflicting same-time reports are audited under the same duplicate rule; the retained report remains traceable.

An isolated jump requires both adjacent implied speeds to exceed 1,500 kt while the bridge between neighboring reports remains below that threshold. Other implausible edges are flagged and excluded from departure/matching evidence, not silently smoothed. Missing optional measurements remain null. Source-row audit counts reconcile to selected/retained totals.

## Flight and runway reconstruction

Time gaps above 900 seconds divide aircraft activity. Candidate take-off evidence combines along/cross-runway position, northbound direction, speed above 80 kt, climb above 150 ft/min or a recorded ground/air transition, and an initial low-altitude filter. Published thresholds define runway axes. A candidate may start at an intersection or already airborne. Position-integrity radius can widen a corridor, capped to avoid unbounded certainty claims.

Climb/direction/speed derived from short consecutive reports are used only when corresponding source measurements are absent; derived quantities remain in event evidence rather than replacing source fields. Runway scores combine distance, direction, climb, and ground-state support. Weak scores or small margins remain ambiguous.

These heuristics can miss sparse departures and can include go-arounds or other similar low-altitude events. Ground transitions are incomplete for some flights. Results are departure candidates, not a certified movement count. An aircraft without a candidate produces an explicit rejected/insufficient-evidence event instead of disappearing from review.

## Procedure matching

Airborne reports after the event anchor are compared with ordered straight connectors between reference fixes. Up to approximately 1,200 observations per event are used for scoring; original full-resolution observations and viewer samples remain available. Dynamic alignment permits staying on a leg or advancing, with penalties for skipped reference legs. The score combines median distance, fraction within a configurable tolerance, and track agreement, with penalties for reversed fix-visit order and the fraction of observation time in long gaps. All score components are exported.

Candidates are ranked independently of the runway score. Scores are uncalibrated heuristic values, not probabilities. Weak geometric agreement becomes unmatched. A small margin, uncertain runway, or evidence confined to a shared trunk remains ambiguous with no selected best candidate. A distinguishable but incomplete route can be partial. Geometry-consistent means agreement under these heuristics, not a proven filed/cleared SID.

All 34C procedures share JN254, JN276, and JN383; JN383 is about 58 km from OEJN. Short initial tracks cannot distinguish these procedures. The wider extraction envelope makes later evidence available when source coverage supports it.

CF intercept geometry, fly-over turns, aircraft dynamics, wind response, and ATC clearances are not reconstructed. An observed deviation is not proof of vectoring, violation, or an anomaly requiring operational action. Evaluate heuristic sensitivity and independent reviewed examples before any accuracy claim.

## Playback

Recorded mode has independent flight-ID state and one UTC timeline, preserving multiple flights from the same runway. It loads active time-window partitions and the selected flight, limits drawn aircraft to 12, and bounds retained payloads to approximately 24. Reports appear as dots; short-gap interpolation is labeled; gaps over 15 seconds are not bridged. Missing altitude hides the aircraft at an unknown height while preserving its known horizontal-position marker.

For visualization only, barometric altitude is offset by the published 50 ft airport elevation. Geometric fallback uses 65 ft, combining that elevation with approximate published 15 ft geoid undulation. These are explicitly approximate display offsets, not QNH reconciliation or a surveyed physical AGL conversion. Raw altitude readouts retain their datum. Negative display height may be clamped to the scene plane without changing measurements. Vertical exaggeration affects rendering only.

## A3–A6 prerequisites

`extensions.py` supplies nullable metadata/model contracts, not calculations. Aircraft type needs sourced ICAO-address resolution, supported performance/acoustic mappings, and documented unknowns/substitutions. Fuel needs aircraft/engine/mass and operating assumptions plus validated OpenAP use. Weather needs spatial/temporal/vertical interpolation and ERA5T preliminary-status retention. Noise requires an implemented, reference-case-validated Doc 29 method, acoustic mapping, power/trajectory assumptions, and uncertainty. Population exposure requires a validated noise footprint and correct people-per-cell handling. Operational capacity requires separation, conflict, demand/delay, simulation, and independent validation; departure counts alone do not establish capacity.

## Permission and scope

The [current Wingbits sample page](https://wingbits.com/data-sample) describes evaluation use. Data remains local and excluded from public packaging; final research/distribution permissions remain a separate prerequisite. A single day does not establish annual traffic, weather, noise exposure, or representative operational effects.
