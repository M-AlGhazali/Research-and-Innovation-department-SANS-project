# Scenario generator (Map 2 "Scenario (what-if)" mode)

`generate_scenarios.py` pre-computes every published SID × aircraft combination at OEJN (16 SIDs on runways 34C and 34L × A320, A20N, B77W = 48 scenarios) and writes the static files that Map 2 loads:

- `map-2/scenarios/index.json`: one record per combination (fuel, CO₂, time and distance to 10,000 ft, residents inside each contour, climb profile, fixes, named places with their level, notes).
- `map-2/scenarios/<runway>_<SID>_<aircraft>.geojson`: the LAmax 60 / 65 / 70 dB contours in WGS84, for example `34C_ISLAM2W_A320.geojson`.

Every value is modelled from a simulated flight, not measured.

## Method (one per output)

| Output | Method |
| --- | --- |
| Flight path | The aircraft follows the published SID in `data/A1_Procedures.csv` fix by fix. "At" and "at or below" altitude limits act as a ceiling until their fix is passed; "at or above" limits are checked; the published 210 kt limit on the 34L SIDs caps the speed until JN272. |
| Fuel | OpenAP fuel flow, mass 80% of MTOW, standard OpenAP WRAP climb, 250 kt below 10,000 ft, no wind. Fuel covers brake release to 10,000 ft only. |
| CO₂ | fuel × 3.16 |
| Noise | ECAC Doc 29 (5th ed.) through Maha's noise model in [`noise-population/`](../../noise-population) (from [M40aha/oejn-noise-population](https://github.com/M40aha/oejn-noise-population)), one daytime departure (12:00 local), still air, 33 °C, QNH 1010 hPa, 250 m grid. The grid extends 60 km from the airport instead of the repo's 40 km, because the B77W 60 dB footprint north of 34C reaches 40 km; the spacing is unchanged, so results inside 40 km are the same. |
| Residents | WorldPop R2025A 100 m grid in `noise-population/`, summed where the per-flight LAmax reaches each level. |
| Places | OpenStreetMap place points from `map-1/OEJN-ground.gpkg` (points, not boundaries). |

The flight model is adapted from `masar-reference/reference_trajectory_fuel.py`, the noise run from `reference_noise_run.py`, and the contour step from `reference_footprint_map.py`.

## Re-run

The noise model is in `noise-population/` in this repo; the generator uses it in place (read only).

1. Make a Python 3.12 environment at the repo root and install the root pins:

   ```
   python -m venv .venv
   .venv/Scripts/python -m pip install -r requirements.txt
   ```

2. From the repo root:

   ```
   .venv/Scripts/python tools/scenarios/generate_scenarios.py
   ```

   About 10 minutes on a laptop. `--only "34C/ISLAM 2W/A320"` runs one combination and prints it without writing to `map-2/`. `--noise-repo PATH` (or `NOISE_REPO`) points to another copy of the noise model. Keep `--workers 1` on Windows: the noise model's process pool fails there.

Intermediate files go to `tools/scenarios/.work/` (ignored by git). Only the derived scenario files in `map-2/scenarios/` are committed.

## Check

A320, ISLAM 2W, runway 34C: fuel to 10,000 ft 643.4 kg, 464 s, 30.8 NM; residents at LAmax ≥ 60 / 65 / 70 dB 77,927 / 38,906 / 8,707. The reference run gave 77,334 / 38,600 / 8,355 with an 8 kt METAR wind; the generator uses still air as the method requires (difference +0.8% / +0.8% / +4.3%).

## Credits

- Noise and population model: Maha, [M40aha/oejn-noise-population](https://github.com/M40aha/oejn-noise-population) (ECAC Doc 29 5th ed., EASA ANP 2.3, WorldPop R2025A).
- Fuel and weather work used as a reference: Hala, [Hala-Alali/OEJN_Aircraft_Fuel_Weather](https://github.com/Hala-Alali/OEJN_Aircraft_Fuel_Weather).
- Fuel flow and climb profiles: [OpenAP](https://github.com/TUDelft-CNS-ATM/openap).
