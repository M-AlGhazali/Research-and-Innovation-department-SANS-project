"""Copy the aggregated observed-noise layer of the noise repo into Map 2 (map-2/noise/noise-layer.json).

    python tools/import_noise_layer.py [path to oejn-noise-population]   (default: cloned next to this repo)

Source: github.com/M40aha/oejn-noise-population, map3d/noise-layer.json (release noise-doc29e5-oejn-2026-10-01-v1,
ECAC Doc 29 on the departures observed on 1 Oct 2026). Only aggregated results are kept: the Lden / Lnight / N70 grids
and contours, the residents per band, the summary statistics of the Results panel and the OpenStreetMap place names.
The median observed flight paths ("paths") and the illustrative live-footprint block ("live") are dropped: no flight
tracks or per-flight data enter this repo. Aircraft-type rows built from fewer than 3 flights are suppressed too.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN_GROUP = 3
KEEP = ("release", "crs", "arp_utm", "modelled", "n", "cell_km", "x0", "y0", "grids", "contours", "pop", "stats", "places")


def main():
    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "oejn-noise-population"
    src = repo / "map3d" / "noise-layer.json"
    raw = src.read_bytes()
    d = json.loads(raw)
    missing = [k for k in KEEP if k not in d]
    if missing:
        raise SystemExit(f"noise-layer.json lacks {missing}")
    commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() or None
    out = {k: d[k] for k in KEEP}
    # groups of fewer than MIN_GROUP flights would show one or two flights' footprint: suppress them
    st = out["stats"]
    st["types"] = [t for t in st["types"] if t["n"] >= MIN_GROUP]
    for row in st["same_type"]:
        for rw in ("34C", "34L"):
            if (row.get(f"{rw}_n") or 0) < MIN_GROUP:
                row[f"{rw}_l65"] = row[f"{rw}_l70"] = None
    st["min_group_flights"] = MIN_GROUP
    out["note"] = "Departures observed on 1 Oct 2026, ECAC Doc 29. Aggregated grids and statistics only; no flight tracks."
    out["source"] = {"repo": "https://github.com/M40aha/oejn-noise-population", "file": "map3d/noise-layer.json",
                     "commit": commit, "sha256": hashlib.sha256(raw).hexdigest(), "dropped": ["paths", "live"]}
    dst = ROOT / "map-2" / "noise" / "noise-layer.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {dst.relative_to(ROOT)} ({dst.stat().st_size // 1024} KB), kept {', '.join(KEEP)}")


if __name__ == "__main__":
    main()
