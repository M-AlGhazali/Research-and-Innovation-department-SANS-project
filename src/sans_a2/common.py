from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
from datetime import datetime, timezone
import duckdb
from pyproj import Transformer, Geod

ROOT = Path(__file__).resolve().parents[2]
TRANSFORM = Transformer.from_crs(4326, 32637, always_xy=True)
GEOD = Geod(ellps="WGS84")
ALGORITHM_VERSION = "a2-0.1.0"

def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()

def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()

def config(path):
    path = Path(path).resolve()
    c = load(path)
    c["config_path"] = str(path)
    for k in ("input_glob", "output_dir"):
        c[k] = str((path.parent / c[k]).resolve())
    for k in ("discovery_radius_m", "tracking_radius_m", "tracking_duration_s", "event_gap_s", "interpolation_gap_s", "threads"):
        if c[k] <= 0: raise ValueError(f"{k} must be positive")
    if c["tracking_radius_m"] <= c["discovery_radius_m"]: raise ValueError("Tracking radius must exceed discovery radius")
    datetime.strptime(c["date"], "%Y-%m-%d")
    return c

def connect(c, database=":memory:"):
    con = duckdb.connect(str(database))
    con.execute("SET TimeZone='UTC'")
    con.execute("SET threads=?", [c["threads"]])
    con.execute("SET memory_limit=?", [c["memory_limit"]])
    spill = Path(c["output_dir"]) / "spill"
    spill.mkdir(parents=True, exist_ok=True)
    con.execute("SET temp_directory=?", [str(spill)])
    con.execute("CREATE OR REPLACE MACRO hypot(x,y) AS sqrt(x*x+y*y)")
    return con

def rows(con, query, params=None):
    cursor = con.execute(query, params or [])
    names = [x[0] for x in cursor.description]
    return [dict(zip(names, r)) for r in cursor.fetchall()]

def utc(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def distance_m(lat, lon, lat2, lon2):
    return GEOD.inv(lon, lat, lon2, lat2)[2]

def circular_difference(a, b):
    return abs((a - b + 180) % 360 - 180)

def finite_or_none(value):
    return value if value is None or not isinstance(value, float) or math.isfinite(value) else None
