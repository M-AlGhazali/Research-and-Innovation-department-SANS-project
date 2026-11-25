"""Map 2 observed-noise layer: the static data file loads, holds the three grids and only aggregated data."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_noise_layer_loads_with_aggregates_only():
    d = json.loads((ROOT / "map-2" / "noise" / "noise-layer.json").read_text(encoding="utf-8"))
    assert d["crs"] == "EPSG:32637" and d["n"] > 100 and d["cell_km"] > 0
    for metric in ("lden", "lnight", "n70"):
        assert d["grids"][metric] and d["contours"][metric], metric
    assert d["stats"]["kpi"] and d["stats"]["coverage"]["modelled"] == d["modelled"]
    # no flight tracks or per-flight data
    assert "paths" not in d and "live" not in d
    assert all(t["n"] >= 3 for t in d["stats"]["types"])
    for row in d["stats"]["same_type"]:
        for rw in ("34C", "34L"):
            if row[f"{rw}_n"] < 3:
                assert row[f"{rw}_l65"] is None and row[f"{rw}_l70"] is None
