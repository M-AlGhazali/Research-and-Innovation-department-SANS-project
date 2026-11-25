# Credits

Masar (مسار) is a team effort. Thank you to everyone whose work is in this repo. This page says exactly what came from each person and from each outside source.

## Team

### Khalid Al Amoudi ([@iKhalidf](https://github.com/iKhalidf))

Thank you, Khalid, for the data and the pipeline that everything else stands on.

- You collected the raw data for all layers, A1 to A6. It lives in your data repository [iKhalidf/OEJN-Noise-Fuel-Capacity](https://github.com/iKhalidf/OEJN-Noise-Fuel-Capacity) (private), which this repo links to and does not copy.
- You built the A2 pipeline that rebuilds departures from ADS-B reports and ranks which published procedure each one fits: [`src/sans_a2/`](src/sans_a2), with its docs in [`docs/A2_SETUP.md`](docs/A2_SETUP.md), [`docs/A2_METHODS.md`](docs/A2_METHODS.md) and [`docs/A2_READINESS.md`](docs/A2_READINESS.md).
- You built the recorded-flight mode in Map 2 ([`map-2/observed-layer.mjs`](map-2/observed-layer.mjs), [`map-2/observed-model.mjs`](map-2/observed-model.mjs)).

### Hala Alali ([@Hala-Alali](https://github.com/Hala-Alali), also [@Hala-Alali2](https://github.com/Hala-Alali2))

Thank you, Hala, for the aircraft performance and weather work behind every fuel number.

- A3 aircraft performance and A4 ERA5 weather: your analysis notebook, moved here with its history from [Hala-Alali/OEJN_Aircraft_Fuel_Weather](https://github.com/Hala-Alali/OEJN_Aircraft_Fuel_Weather), is in [`fuel-weather/`](fuel-weather).
- The OpenAP fuel model that the Masar engine uses for fuel and CO₂: your fuel stage for the A2 pipeline, [`src/sans_a2/fuel_weather.py`](src/sans_a2/fuel_weather.py) (`sans_a2 fuel`), and the fuel estimate shown for recorded flights in Map 2. The Scenario generator follows the same OpenAP approach.

### Maha Alamri ([@M40aha](https://github.com/M40aha))

Thank you, Maha, for the noise and population work behind every noise result.

- A5 aircraft-noise data and A6 population layers, moved here with their history from [M40aha/oejn-noise-population](https://github.com/M40aha/oejn-noise-population) into [`noise-population/`](noise-population).
- The ECAC Doc 29 noise model that the Masar engine uses for every noise result: the Scenario generator ([`tools/scenarios/`](tools/scenarios)) runs your model in [`noise-population/src/noise/`](noise-population/src/noise) for every contour and resident count.
- The 3D noise map ([`noise-population/map3d/`](noise-population/map3d)) and the results panel, which Map 2 shows as the "Observed noise" layer.

### Muhannad AlGhazali ([@M-AlGhazali](https://github.com/M-AlGhazali))

- A1 published procedures from the SANS eAIP: [`data/A1_Procedures.csv`](data/A1_Procedures.csv), [`data/External_Airport_Runways.csv`](data/External_Airport_Runways.csv) and their sources in [`sources/`](sources).
- Map 2 ([`map-2/`](map-2)) and the Scenario (what-if) engine ([`tools/scenarios/`](tools/scenarios), [`map-2/scenario-layer.mjs`](map-2/scenario-layer.mjs)) that joins the layers.

## Outside sources

| Source | What it gives Masar | Licence |
| --- | --- | --- |
| [SANS eAIP](https://aimss.sans.com.sa/) (AIRAC AMDT 10/26) | Published departure procedures (SIDs) and aerodrome data for A1 | SANS material, kept in `sources/` for checking only; not covered by this repo's licences. Not for navigation. |
| [OpenAP](https://github.com/TUDelft-CNS-ATM/openap) (TU Delft) | Aircraft properties, fuel flow and climb profiles | GNU LGPL v3 |
| [EASA Aircraft Noise and Performance (ANP) database](https://www.easa.europa.eu/en/domains/environment/policy-support-and-research/aircraft-noise-and-performance-anp-data) 2.3 | Aircraft noise and performance data for the Doc 29 model (A5) | EASA terms of use. The raw files are not stored here; `noise-population/config/a5.yaml` locks each one by SHA-256, and `noise-population/docs/README_detailed.md` says where to download them. |
| [ECAC Doc 29](https://www.ecac-ceac.org/), 5th edition | The noise calculation method and its reference test cases | ECAC publication. The PDFs are not stored here; they are locked by SHA-256 in `noise-population/config/a5.yaml`. |
| [ERA5](https://cds.climate.copernicus.eu/) (Copernicus Climate Change Service, ECMWF) | Surface and pressure-level weather for A4 | CC BY 4.0 (since July 2025). Generated using Copernicus Climate Change Service information. |
| [WorldPop](https://www.worldpop.org/) R2025A, 100 m | Residents per grid cell for A6 | CC BY 4.0 |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | Ground features, place names and basemap | ODbL. © OpenStreetMap contributors |
| [Natural Earth](https://www.naturalearthdata.com/) | Small-scale basemap in `noise-population/` | Public domain |
| [three.js](https://threejs.org/) | 3D rendering in Map 2 and the 3D noise map | MIT |
| [Wingbits](https://wingbits.com/data-sample) ADS-B sample | Recorded flights for A2 | Evaluation use only. Not stored in this repo. |

See [DATA_LICENSE.md](DATA_LICENSE.md) for the licences of the files in this repo.
