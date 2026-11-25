"""Map 2 scenario files: all 48 SID x aircraft records exist and hold sane, modelled values."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCN = ROOT / "map-2" / "scenarios"


@pytest.fixture(scope="module")
def index():
    return json.loads((SCN / "index.json").read_text(encoding="utf-8"))


def test_all_48_combinations(index):
    import csv
    with open(ROOT / "data" / "A1_Procedures.csv", encoding="utf-8") as f:
        sids = {(r["departure_runway"], r["procedure_name"]) for r in csv.DictReader(f)}
    assert len(sids) == 16
    got = {(s["runway"], s["sid"], s["aircraft"]) for s in index["scenarios"]}
    assert len(index["scenarios"]) == 48
    assert got == {(rw, sid, ac) for rw, sid in sids for ac in ("A320", "A20N", "B77W")}


def test_values_are_sane(index):
    for s in index["scenarios"]:
        t = s["to10k"]
        assert 200 < t["fuel_kg"] < 8000, s["id"]
        assert t["co2_kg"] == pytest.approx(t["fuel_kg"] * 3.16, abs=0.2), s["id"]
        assert 200 < t["time_s"] < 1500 and 15 < t["distance_nm"] < 120, s["id"]
        r = s["residents"]
        assert r["60"] >= r["65"] >= r["70"] >= 0 and r["60"] > 1000, s["id"]
        prof = s["profile"]
        assert len(prof) > 10 and prof[0][1] < 100 and max(p[1] for p in prof) >= 10000, s["id"]
        assert all(b[0] >= a[0] for a, b in zip(prof, prof[1:])), s["id"]          # distance never decreases
        assert all(38.0 < p[2] < 40.5 and 21.0 < p[3] < 23.5 for p in prof), s["id"]
        assert s["places"] and all(p["name"] and p["lamax_db"] >= 0 for p in s["places"]), s["id"]
        assert not s["flags"], (s["id"], s["flags"])
    b77w = [s["to10k"]["fuel_kg"] for s in index["scenarios"] if s["aircraft"] == "B77W"]
    a320 = [s["to10k"]["fuel_kg"] for s in index["scenarios"] if s["aircraft"] == "A320"]
    assert min(b77w) > max(a320)


def test_contour_files(index):
    for s in index["scenarios"]:
        gj = json.loads((SCN / s["geojson"]).read_text(encoding="utf-8"))
        assert gj["type"] == "FeatureCollection"
        assert [f["properties"]["lamax_db"] for f in gj["features"]] == [60, 65, 70], s["id"]
        for f in gj["features"]:
            assert f["geometry"]["type"] in ("Polygon", "MultiPolygon")
            assert f["properties"]["residents"] == s["residents"][str(f["properties"]["lamax_db"])]
            lon, lat = (f["geometry"]["coordinates"][0][0] if f["geometry"]["type"] == "Polygon"
                        else f["geometry"]["coordinates"][0][0][0])
            assert 38.5 < lon < 40 and 21 < lat < 22.5
