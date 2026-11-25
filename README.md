# Masar (مسار)

Masar is a student initiative for SANS, the Saudi Air Navigation Services: an explainable workspace for the published departure routes (SIDs) from runways 34C and 34L at King Abdulaziz International Airport, Jeddah (OEJN). It joins six data layers, from the published procedures (A1) and recorded flights (A2) to aircraft performance (A3), weather and fuel (A4), aircraft noise (A5) and population (A6), so that anyone can pick a route and an aircraft and see, step by step, the fuel, CO₂, noise and residents behind every number. This repo is the single home of the project: code, docs, sources and results from the whole team. See [CREDITS.md](CREDITS.md) for who did what.

![3D overview of King Abdulaziz International Airport showing all three runways, with the two study runways, 34C and 34L, highlighted](map-1/report-assets/airport-overview.png)

**Live demo:** [Map 2, 3D departure explorer with Scenario mode](https://m-alghazali.github.io/Research-and-Innovation-department-SANS-project/map-2/) · [Map 1, ground atlas](https://m-alghazali.github.io/Research-and-Innovation-department-SANS-project/map-1/Open-ground-map.html)

## Map of the repo

| Layer or part | Folder | From |
| --- | --- | --- |
| **A1** published procedures (SANS eAIP) | [`data/`](data) (datasets), [`sources/`](sources) (original AIP tables), [`dataset_tools/`](dataset_tools) (rebuild) | Muhannad |
| **A2** recorded departures from ADS-B | [`src/sans_a2/`](src/sans_a2), [`config/`](config), [`schemas/`](schemas), [`docs/`](docs) (`A2_*.md`) | Khalid |
| **A3** aircraft performance, **A4** ERA5 weather and fuel | [`fuel-weather/`](fuel-weather) (analysis notebook), [`src/sans_a2/fuel_weather.py`](src/sans_a2/fuel_weather.py) (`sans_a2 fuel`) | Hala |
| **A5** aircraft-noise data, **A6** population, Doc 29 noise model, 3D noise map | [`noise-population/`](noise-population) (`src/a5`, `src/a6`, `src/noise`, `map3d/`) | Maha |
| **Engine:** Scenario (what-if) generator that joins the layers | [`tools/scenarios/`](tools/scenarios/README.md) → [`map-2/scenarios/`](map-2/scenarios) | Muhannad |
| **Demo:** Map 2 (3D departure explorer) and Map 1 (ground atlas) | [`map-2/`](map-2), [`map-1/`](map-1), [`index.html`](index.html) | Muhannad; recorded-flight mode by Khalid, fuel display by Hala, observed-noise layer from Maha |
| Tests | [`tests/`](tests), [`noise-population/tests/`](noise-population/tests) | everyone |
| Map and data build scripts | [`tools/`](tools) | Muhannad |

The raw data for all layers (A1 to A6) was collected by Khalid and lives in his separate data repository, [iKhalidf/OEJN-Noise-Fuel-Capacity](https://github.com/iKhalidf/OEJN-Noise-Fuel-Capacity) (private, about 26 GB). It is not copied here.

## What Map 2 shows

- **Published procedure demo:** the 16 published SIDs from 34C and 34L in 3D, with an illustrative flight playback.
- **Scenario (what-if) mode:** pick a runway, SID, aircraft (A320, A20N or B77W) and departures per day, and see modelled fuel and CO₂ to 10,000 ft, time and distance, the climb profile, the LAmax 60 / 65 / 70 dB footprint, the residents inside each contour and the nearest named places, with daily and yearly totals. All 48 combinations are pre-computed from simulated flights by [`tools/scenarios/`](tools/scenarios/README.md): OpenAP for fuel, Maha's Doc 29 model and WorldPop grid for noise and residents.
- **Observed noise (1 Oct 2026):** Maha's Lden, Lnight and N70 surfaces and results panel, as aggregated grids only (no flight tracks).
- **Recorded flights:** Khalid's A2 replay of real departures, with Hala's fuel estimate. This mode needs the local A2 output; the recorded data is never published.

## Run the demo

Map 2 is static files. From the repo root:

```
python tools/serve_map2.py --open
```

It opens <http://127.0.0.1:8765/map-2/>. On Windows you can double-click `Start Map 2.cmd` instead.

## Run the tests

One environment (Python 3.12) and one command for all three parts (A2 and fuel, Scenario files, noise-population) and the two Node suites:

```
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m pytest -q
```

On Linux or macOS use `.venv/bin/python`. The Node suites run when Node.js is installed and are skipped otherwise. CI ([`.github/workflows/a2-checks.yml`](.github/workflows/a2-checks.yml)) runs the same command on every push and pull request. [`.github/workflows/pages.yml`](.github/workflows/pages.yml) publishes the maps to GitHub Pages from `main`.

To rebuild the 48 scenarios, see [`tools/scenarios/README.md`](tools/scenarios/README.md). To run the A2 pipeline on the recorded data, see [`docs/A2_SETUP.md`](docs/A2_SETUP.md).

## Data policy

- **Never in this repo:** raw ADS-B reports, per-flight tracks, per-flight fuel or noise results, or anything else derived flight by flight from the Wingbits sample. The sample is for evaluation only. The A2 pipeline writes outside the repo, and `.gitignore` keeps the per-flight outputs of the noise model out.
- **In this repo:** published procedures, aggregated grids, contours and summary tables, and modelled results for simulated flights.
- **Not redistributed:** the licensed raw files of the noise model (EASA ANP, ECAC Doc 29 PDFs). They are locked by SHA-256 in `noise-population/config/a5.yaml`, with download steps in `noise-population/docs/README_detailed.md`.
- **Linked, not copied:** Khalid's raw data repository (above).
- No file over 50 MB.
- When the teammates' repos were moved in, their history was cleaned of per-flight data first; see the import commits for the details.

## Status and limitations

Masar is a visual and explainable prototype for a proposal to SANS. Scenario results are modelled for simulated flights on the published SIDs; they do not measure real traffic. The recorded-flight work covers one day (1 October 2026) and does not show annual traffic, weather or exposure. The datasets cover runways 34C and 34L; Map 2 also shows 34R for context. Reference only, not for navigation.

## Data sources

- **SANS eAIP, AIRAC AMDT 10/26, effective 1 October 2026:** OEJN aerodrome data and the RNAV SID tables. Copies are in `sources/`.
- **OpenStreetMap**, snapshot of 25 October 2026, pulled with the Overpass query in [`sources/overpass-query.txt`](sources/overpass-query.txt). © OpenStreetMap contributors, ODbL.
- **OpenAP, EASA ANP 2.3, ECAC Doc 29, ERA5, WorldPop R2025A, Natural Earth, three.js:** see [CREDITS.md](CREDITS.md) for what each gives and its licence.

## How to cite

If you use the maps or the datasets, please cite this repo. The "Cite this repository" button on GitHub reads [CITATION.cff](CITATION.cff), or use:

> Alghazali, M. (2026). *OEJN departure mapping: ground atlas, departure explorer and published-procedure datasets* [Software and data]. GitHub. https://github.com/M-AlGhazali/Research-and-Innovation-department-SANS-project

Please also credit the team members whose layers you use ([CREDITS.md](CREDITS.md)).

## Licence

Code is [MIT](LICENSE). The A1 CSV datasets are CC BY 4.0. OpenStreetMap-derived data stays ODbL, and the SANS AIP material in `sources/` isn't covered. Details are in [DATA_LICENSE.md](DATA_LICENSE.md). The folders moved in from teammates' repos (`fuel-weather/`, `noise-population/`) came without a licence file; their authors keep their rights until they choose one. Their external data keeps its own licence (see [CREDITS.md](CREDITS.md)).
