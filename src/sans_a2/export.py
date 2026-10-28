from pathlib import Path
from .common import ROOT, connect, load, dump, rows, digest, finite_or_none
from .flights import iter_event_tracks

def export_viewer(c):
    out = Path(c["output_dir"])
    viewer = out / "viewer"
    flights = load(out / "flights.json")
    matches = {r["flight_id"]: r for r in load(out / "matches.json")}
    origin = load(ROOT / "map-2/data.json")["origin"]["utm"]
    con = connect(c)
    summaries = []
    for f, observations in iter_event_tracks(con, flights, out / "observations.parquet"):
        samples = []
        for o in observations:
            samples.append([o["timestamp_ms"], round((o["easting_m"]-origin[0])/1000, 6), round(-(o["northing_m"]-origin[1])/1000, 6), o["barometric_altitude_ft"], o["geometric_altitude_ft"], finite_or_none(o["ground_speed_kt"]), finite_or_none(o["track_deg"]), o["on_ground"], o["quality_flags"], o["observation_id"]])
        payload = {"schema_version": 1, "flight": f, "match": matches[f["flight_id"]], "samples": samples, "sample_columns": ["timestamp_ms", "x_km", "z_km", "barometric_altitude_ft", "geometric_altitude_ft", "ground_speed_kt", "track_deg", "on_ground", "quality_flags", "observation_id"]}
        dump(viewer / "flights" / (f["flight_id"]+".json"), payload)
        summaries.append({"flight_id": f["flight_id"], "icao24": f["icao24"], "callsign": "/".join(f["callsigns"]) or f["icao24"], "runway": f["runway"], "runway_status": f["runway_status"], "match_status": matches[f["flight_id"]]["status"], "start_ms": f["start_ms"], "end_ms": f["end_ms"], "anchor_ms": f["anchor_ms"], "observations": len(samples), "gaps": len(f["gaps"]), "url": "flights/"+f["flight_id"]+".json", "sha256": digest(payload)})
    manifest = {"schema_version": 1, "source": "Wingbits evaluation sample", "date": c["date"], "airport": c["airport"], "reference_sha256": load(ROOT / "map-2/reference/study-procedures.json")["source_sha256"], "origin_utm_m": origin, "crs": "EPSG:32637", "interpolation_gap_s": c["interpolation_gap_s"], "start_ms": min((f["start_ms"] for f in summaries), default=None), "end_ms": max((f["end_ms"] for f in summaries), default=None), "flights": summaries, "altitude_display": "Barometric pressure altitude minus 50 ft airport reference for display only; fallback ellipsoid altitude minus 65 ft (airport elevation plus published geoid undulation). No physical AGL or compliance inference.", "publication": "Local evaluation only; distribution permission not established", "matching": "Heuristic geometric candidates; no assigned clearances or accuracy claim"}
    order = {f["flight_id"]: i for i, f in enumerate(flights)}
    summaries.sort(key=lambda f: order[f["flight_id"]])
    dump(viewer / "manifest.json", manifest)
    con.close()
    return {"flights_exported": len(summaries), "manifest_sha256": digest(manifest), "viewer_bytes": sum(p.stat().st_size for p in viewer.rglob("*.json"))}
