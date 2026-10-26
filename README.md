# SANS Project — OEJN mapping phase
# Research and Innovation Dept

This initiative maps King Abdulaziz International Airport ground features and published departure procedures, as the visual groundwork for a proposal to SANS. The longer-term aim is to assess operational efficiency, fuel consumption, CO₂ emissions, and community noise using observed flights and suitable models. These maps are a visual prototype for that proposal; they do not measure those outcomes.

| Open | Contents |
|---|---|
| [Map 1 — Ground atlas](https://m-alghazali.github.io/Research-and-Innovation-department-SANS-project/map-1/Open-ground-map.html) | Airport, runways, and labeled neighborhoods in a browser. [QGIS project](map-1/OEJN-ground-atlas.qgz) and [GeoPackage](map-1/OEJN-ground.gpkg) are available for editing. |
| [Map 2 — Departure explorer](https://m-alghazali.github.io/Research-and-Innovation-department-SANS-project/map-2/) | 3D view of the published departure fixes with illustrative flight playback. |
| [A1 procedure dataset (CSV)](data/A1_Procedures.csv) | 16 published procedures from the initial 34C/34L scope. |
| [Airport and runway lookup (CSV)](data/External_Airport_Runways.csv) | Six runway ends and airport reference facts. |

The [dataset notes](data/README.md) explain fields and provenance. Map 2 additionally shows 34R for context. Both browser maps are prepared for GitHub Pages hosting; no Supabase account is needed.

**Folders:** `map-1/` and `map-2/` are the two maps; `data/` holds the handoff CSVs; `sources/` keeps the original evidence; `tools/` has the scripts that rebuild the maps (run from the repo root); `dataset_tools/` rebuilds the dataset. `Start Map 2.cmd` runs Map 2 locally.
