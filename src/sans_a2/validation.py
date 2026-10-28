from pathlib import Path
from collections import defaultdict
import jsonschema
from .common import ROOT, connect, load, dump, digest, file_hash

def validate(c):
    out = Path(c["output_dir"])
    pre = load(out / "preflight.json")
    for item in pre["inputs"]:
        stat = Path(item["file"]).stat()
        if stat.st_size != item["bytes"] or stat.st_mtime_ns != item["mtime_ns"]: raise AssertionError("Source identity changed")
    con = connect(c)
    duplicates = con.execute("SELECT count(*)-count(DISTINCT observation_id) FROM read_parquet(?)", [str(out / "observations.parquet")]).fetchone()[0]
    if duplicates: raise AssertionError("Duplicate observation IDs")
    columns = {r[0]: r[1] for r in con.execute("DESCRIBE SELECT * FROM read_parquet(?)", [str(out / "observations.parquet")]).fetchall()}
    contract = load(ROOT / "schemas/observation.schema.json")
    if set(contract["required"]) - set(columns): raise AssertionError("Missing normalized observation columns")
    if columns["timestamp_utc"] != "TIMESTAMP WITH TIME ZONE": raise AssertionError("Lost UTC timestamp type")
    invalid = con.execute("""SELECT count(*) FROM read_parquet(?) WHERE schema_version<>1 OR observation_id IS NULL OR NOT regexp_full_match(observation_id,'[0-9a-f]{64}') OR icao24 IS NULL OR NOT regexp_full_match(icao24,'[0-9a-f]{6}') OR timestamp_ms IS NULL OR latitude_deg IS NULL OR longitude_deg IS NULL OR NOT isfinite(easting_m) OR NOT isfinite(northing_m) OR abs(latitude_deg)>90 OR abs(longitude_deg)>180 OR source_row<0""", [str(out / "observations.parquet")]).fetchone()[0]
    if invalid: raise AssertionError("Invalid normalized observation records")
    retained = con.execute("SELECT count(*) FROM read_parquet(?)", [str(out / "observations.parquet")]).fetchone()[0]
    audited = con.execute("SELECT count(*) FROM read_parquet(?)", [str(out / "observation-audit.parquet")]).fetchone()[0]
    if retained + audited != load(out / "ingest-report.json")["selected_reports"]: raise AssertionError("Output accounting mismatch")
    flights = load(out / "flights.json")
    matches = load(out / "matches.json")
    if len({f["flight_id"] for f in flights}) != len(flights): raise AssertionError("Flight IDs not unique")
    if {f["flight_id"] for f in flights} != {m["flight_id"] for m in matches}: raise AssertionError("Flight/match mismatch")
    for f in flights: jsonschema.validate(f, load(ROOT / "schemas/flight.schema.json"))
    for m in matches: jsonschema.validate(m, load(ROOT / "schemas/match.schema.json"))
    manifest = load(out / "viewer/manifest.json")
    jsonschema.validate(manifest, load(ROOT / "schemas/viewer-manifest.schema.json"))
    study = load(ROOT / "map-2/reference/study-procedures.json")
    if manifest["reference_sha256"] != study["source_sha256"]: raise AssertionError("Viewer reference drift")
    if file_hash(ROOT / "data/A1_Procedures.csv") != study["source_sha256"]: raise AssertionError("Canonical reference changed")
    for summary in manifest["flights"]:
        payload = load(out / "viewer" / summary["url"])
        if digest(payload) != summary["sha256"]: raise AssertionError("Viewer flight content drift")
        ts = [s[0] for s in payload["samples"]]
        if ts != sorted(set(ts)): raise AssertionError("Viewer timestamps not strictly increasing")
    # Deterministic review strata by runway and match status. Include empty strata explicitly.
    by_match = {m["flight_id"]: m for m in matches}
    strata = defaultdict(list)
    for f in sorted(flights, key=lambda f: f["flight_id"]): strata[(f["runway"] or "uncertain", by_match[f["flight_id"]]["status"])].append(f["flight_id"])
    sample = [{"runway": rw, "match_status": status, "available": len(strata[(rw, status)]), "flight_ids": strata[(rw, status)][:3]} for rw in ("34C", "34L", "uncertain") for status in ("geometry_consistent", "ambiguous", "partial", "unmatched", "insufficient_data")]
    dump(out / "review-sample.json", {"selection": "First three stable flight IDs per runway/status; reproducible strata, not independent truth labels", "strata": sample})
    # Parameter sensitivity on exactly the same reproducible review set. This is
    # stability evidence, not accuracy validation against clearance truth.
    from .flights import iter_event_tracks
    from .matching import match_flight
    selected = {fid for s in sample for fid in s["flight_ids"]}
    sensitivity = []
    for f, observations in iter_event_tracks(con, [f for f in flights if f["flight_id"] in selected], out / "observations.parquet"):
        for tolerance in (2000, 3000, 5000):
            varied = {**c, "matching_distance_m": tolerance}
            result = match_flight(f, observations, study, varied)
            sensitivity.append({"flight_id": f["flight_id"], "tolerance_m": tolerance, "status": result["status"], "best_candidate": result["best_candidate"], "score_margin": result["score_margin"]})
    dump(out / "sensitivity.json", {"interpretation": "Uncalibrated parameter stability, not assignment accuracy", "results": sensitivity})
    report = {"input_identities_unchanged": True, "unique_observation_and_flight_ids": True, "flight_match_and_viewer_consistency": True, "schema_validation": True, "review_sample": "review-sample.json; use viewer flight selector for plots and evidence", "accuracy": "Not established; independent assigned-SID labels/expert review still required", "flights": len(flights), "review_sample_flights": sum(len(s["flight_ids"]) for s in sample)}
    dump(out / "validation.json", report)
    con.close()
    return report
