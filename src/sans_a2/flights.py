"""Deterministic event windows and separately scored runway evidence."""
from pathlib import Path
from itertools import groupby
import math
from collections import defaultdict
from .common import connect, dump, digest, utc, circular_difference
from .reference import runways

def iter_records(cursor):
    names = [x[0] for x in cursor.description]
    while batch := cursor.fetchmany(10000):
        for row in batch: yield dict(zip(names, row))

def iter_event_tracks(con, flights, observation_path):
    """One ordered Parquet pass, bounded by one aircraft's local observations."""
    by_aircraft = defaultdict(list)
    for flight in flights: by_aircraft[flight["icao24"]].append(flight)
    cursor = con.execute("SELECT * FROM read_parquet(?) ORDER BY icao24,timestamp_ms", [str(observation_path)])
    for aircraft, group in groupby(iter_records(cursor), key=lambda o: o["icao24"]):
        track = list(group)
        for flight in by_aircraft.get(aircraft, []):
            yield flight, [o for o in track if flight["start_ms"] <= o["timestamp_ms"] <= flight["end_ms"]]

def runway_evidence(obs, runway, c, previous=None):
    if "implausible_movement" in (obs.get("quality_flags") or ""): return None
    e, n = obs["easting_m"], obs["northing_m"]
    sx, sy = runway["start"]
    dx, dy = runway["end"][0] - sx, runway["end"][1] - sy
    length = math.hypot(dx, dy)
    along = ((e - sx) * dx + (n - sy) * dy) / length
    cross = abs((e - sx) * dy - (n - sy) * dx) / length
    corridor = max(c["runway_corridor_m"], min(obs.get("quality_rc") or 0, 1000))
    if cross > corridor * 2 or not -500 <= along <= length + c["runway_max_along_extension_m"]: return None
    alt = obs.get("barometric_altitude_ft")
    if alt is None: alt = obs.get("geometric_altitude_ft")
    if alt is not None and not -500 <= alt <= c["departure_max_altitude_ft"]: return None
    speed = obs.get("ground_speed_kt")
    track = obs.get("track_deg")
    rate = obs.get("barometric_rate_fpm")
    if rate is None: rate = obs.get("geometric_rate_fpm")
    derived_direction = None
    derived_speed = None
    derived_climb = None
    if previous and obs["timestamp_ms"] > previous["timestamp_ms"]:
        dt = (obs["timestamp_ms"] - previous["timestamp_ms"]) / 1000
        if dt <= 30:
            de, dn = e - previous["easting_m"], n - previous["northing_m"]
            derived_speed = math.hypot(de, dn) / dt / .514444
            if math.hypot(de, dn) > 20: derived_direction = math.degrees(math.atan2(de, dn)) % 360
            old_alt = previous.get("barometric_altitude_ft")
            if old_alt is not None and obs.get("barometric_altitude_ft") is not None:
                derived_climb = (obs["barometric_altitude_ft"] - old_alt) / dt * 60
    if speed is None: speed = derived_speed
    if track is None: track = derived_direction
    if rate is None: rate = derived_climb
    if speed is None or speed < c["departure_min_speed_kt"]: return None
    if track is None or circular_difference(track, runway["bearing_deg"]) > 40: return None
    transition = bool(previous and previous.get("on_ground") is True and obs.get("on_ground") is False)
    if not transition and (rate is None or rate < c["departure_min_climb_fpm"]): return None
    score = .45 * math.exp(-cross / corridor) + .25 * (1 - circular_difference(track, runway["bearing_deg"]) / 40) + .20 * min(max(rate or 0, 0) / 1000, 1) + .1 * (1 if transition or obs.get("on_ground") is False else .5)
    return {"runway": runway["id"], "score": round(score, 6), "cross_track_m": round(cross, 2), "along_runway_m": round(along, 2), "track_difference_deg": round(circular_difference(track, runway["bearing_deg"]), 2), "ground_speed_kt": speed, "climb_fpm": rate, "ground_air_transition": transition, "timestamp_ms": obs["timestamp_ms"], "altitude_evidence_reference": "barometric pressure or geometric; threshold filter only, not compliance"}

def extract_aircraft(observations, runway_refs, c):
    if not observations: return []
    chunks = [[]]
    for obs in observations:
        if chunks[-1] and obs["timestamp_ms"] - chunks[-1][-1]["timestamp_ms"] > c["event_gap_s"] * 1000: chunks.append([])
        chunks[-1].append(obs)
    events = []
    for chunk in chunks:
        hits = []
        for i, obs in enumerate(chunk):
            for runway in runway_refs:
                evidence = runway_evidence(obs, runway, c, chunk[i-1] if i else None)
                if evidence: hits.append(evidence)
        hits.sort(key=lambda h: (h["timestamp_ms"], h["runway"]))
        clusters = []
        for hit in hits:
            if not clusters or hit["timestamp_ms"] - clusters[-1][-1]["timestamp_ms"] > 600000: clusters.append([])
            clusters[-1].append(hit)
        windows = []
        for cluster in clusters:
            best = {}
            for hit in cluster:
                if hit["runway"] not in best or hit["score"] > best[hit["runway"]]["score"]: best[hit["runway"]] = hit
            candidates = sorted(best.values(), key=lambda h: (-h["score"], h["runway"]))
            # Event anchoring uses the first eligible observation, not the best-score time.
            windows.append((cluster[0]["timestamp_ms"], candidates))
        if not windows:
            windows = [(chunk[0]["timestamp_ms"], [])]
        for i, (anchor, candidates) in enumerate(windows):
            start = max(chunk[0]["timestamp_ms"], anchor - c["pre_roll_s"] * 1000)
            end = min(chunk[-1]["timestamp_ms"], anchor + c["tracking_duration_s"] * 1000)
            if i + 1 < len(windows): end = min(end, windows[i+1][0] - c["pre_roll_s"] * 1000 - 1)
            track = [o for o in chunk if start <= o["timestamp_ms"] <= end]
            if len(track) < 2: continue
            if candidates:
                margin = candidates[0]["score"] - (candidates[1]["score"] if len(candidates) > 1 else 0)
                status = "accepted_departure_candidate" if candidates[0]["score"] >= .55 and margin >= c["runway_score_margin"] else "ambiguous_runway"
                runway = candidates[0]["runway"] if status == "accepted_departure_candidate" else None
            else:
                margin, runway = None, None
                descending = any((o.get("barometric_rate_fpm") or 0) < -300 for o in track)
                status = "rejected_non_departure" if descending else "insufficient_evidence"
            gaps = [(a["timestamp_ms"], b["timestamp_ms"]) for a, b in zip(track, track[1:]) if b["timestamp_ms"] - a["timestamp_ms"] > c["interpolation_gap_s"] * 1000]
            icao = track[0]["icao24"]
            callsigns = list(dict.fromkeys(o["callsign"] for o in track if o.get("callsign")))
            events.append({"schema_version": 1, "flight_id": f"OEJN-{c['date']}-{icao}-{anchor}", "icao24": icao, "callsigns": callsigns, "start_ms": track[0]["timestamp_ms"], "end_ms": track[-1]["timestamp_ms"], "anchor_ms": anchor, "start_utc": utc(track[0]["timestamp_ms"]), "end_utc": utc(track[-1]["timestamp_ms"]), "runway": runway, "runway_status": status, "runway_candidates": candidates, "runway_score_margin": margin, "observation_count": len(track), "max_gap_s": max((b["timestamp_ms"] - a["timestamp_ms"]) / 1000 for a, b in zip(track, track[1:])), "gaps": gaps, "missing_altitude_count": sum(o.get("barometric_altitude_ft") is None and o.get("geometric_altitude_ft") is None for o in track), "evidence_note": "Reconstructed departure candidate, not an official movement or assigned clearance", "extensions": {"aircraft_type": None, "aircraft_type_status": "unresolved", "fuel": None, "noise": None, "weather": None, "population_exposure": None}})
    return events

def extract(c):
    out = Path(c["output_dir"])
    con = connect(c)
    cursor = con.execute("SELECT * FROM read_parquet(?) ORDER BY icao24,timestamp_ms", [str(out / "observations.parquet")])
    events = []
    refs = runways()
    for _, group in groupby(iter_records(cursor), key=lambda o: o["icao24"]): events.extend(extract_aircraft(list(group), refs, c))
    events.sort(key=lambda f: (f["anchor_ms"], f["flight_id"]))
    if len({e["flight_id"] for e in events}) != len(events): raise AssertionError("Duplicate flight IDs")
    dump(out / "flights.json", events)
    if events:
        con.execute("COPY (SELECT * FROM read_json_auto($1)) TO $2 (FORMAT PARQUET, COMPRESSION ZSTD)", [str(out / "flights.json"), str(out / "flights.parquet")])
    else:
        con.execute("COPY (SELECT NULL::VARCHAR flight_id,NULL::VARCHAR runway_status WHERE false) TO ? (FORMAT PARQUET)", [str(out / "flights.parquet")])
    report = {"events": len(events), "runways": {}, "statuses": {}}
    for f in events:
        report["statuses"][f["runway_status"]] = report["statuses"].get(f["runway_status"], 0) + 1
        if f["runway"]: report["runways"][f["runway"]] = report["runways"].get(f["runway"], 0) + 1
    report["content_sha256"] = digest(events)
    dump(out / "flight-report.json", report)
    con.close()
    return report
