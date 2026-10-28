"""Explainable geometric candidate ranking, not an inference of ATC clearance."""
from pathlib import Path
import math
import numpy as np
from .common import ROOT, TRANSFORM, connect, rows, load, dump, digest
from .reference import runways
from .flights import iter_event_tracks

def ordered_alignment(cost):
    """O(reports * legs) dynamic alignment, including skipped-leg penalties."""
    count = len(cost[0])
    previous = [j*.5 for j in range(count)]
    back = []
    for report_cost in cost:
        current, predecessors = [], []
        prefix_value, prefix_index = math.inf, 0
        for j in range(count):
            if j and previous[j-1]-(j-1)*.4 < prefix_value:
                prefix_value, prefix_index = previous[j-1]-(j-1)*.4, j-1
            advance_cost = prefix_value+(j-1)*.4
            index = prefix_index if advance_cost < previous[j] else j
            current.append(report_cost[j] + (advance_cost if index != j else previous[j]))
            predecessors.append(index)
        previous = current
        back.append(predecessors)
    index = min(range(count), key=lambda j: previous[j])
    assigned = []
    for predecessors in reversed(back):
        assigned.append(index)
        index = predecessors[index]
    return np.asarray(assigned[::-1])

def route_geometry(route, fixes, runway):
    points = [runway["start"]]
    for leg in route["legs"]:
        f = fixes[leg["fix"]]
        points.append(TRANSFORM.transform(f["lon"], f["lat"]))
    return np.asarray(points, dtype=float)

def rank_route(observations, route, fixes, runway, c, quality):
    pts = np.asarray([(o["easting_m"], o["northing_m"]) for o in observations], dtype=float)
    geometry = route_geometry(route, fixes, runway)
    a, b = geometry[:-1], geometry[1:]
    vectors = b-a
    squared = np.sum(vectors*vectors, axis=1)
    delta = pts[:, None, :] - a[None, :, :]
    fractions = np.clip(np.sum(delta*vectors[None, :, :], axis=2) / np.maximum(squared, 1), 0, 1)
    distances = np.linalg.norm(delta-fractions[:, :, None]*vectors[None, :, :], axis=2)
    # Ordered dynamic alignment. Skipping a leg has a recorded geometric penalty.
    cost = np.minimum(distances / c["matching_distance_m"], 8)
    track = np.asarray([o.get("track_deg") if o.get("track_deg") is not None else np.nan for o in observations])
    bearing = np.degrees(np.arctan2(vectors[:, 0], vectors[:, 1])) % 360
    direction = np.abs((track[:, None] - bearing[None, :] + 180) % 360-180)
    cost += np.nan_to_num(direction / 180 * .25)
    assigned = ordered_alignment(cost.tolist())
    fitted = distances[np.arange(len(pts)), assigned]
    tolerance = c["matching_distance_m"]
    near = fitted <= tolerance
    median = float(np.median(fitted))
    within = float(np.mean(near))
    direction_mean = float(np.nanmean(direction[np.arange(len(pts)), assigned])) if np.isfinite(track).any() else None
    visited = []
    for j, leg in enumerate(route["legs"]):
        # A fix visit is a measured proximity, independent of alignment progress.
        close = np.linalg.norm(pts-b[j], axis=1)
        best = int(np.argmin(close))
        if close[best] <= tolerance:
            visited.append({"leg_id": leg["leg_id"], "fix": leg["fix"], "sequence": j+1, "minimum_distance_m": round(float(close[best]), 2), "timestamp_ms": observations[best]["timestamp_ms"]})
    visited.sort(key=lambda v: v["timestamp_ms"])
    order_errors = sum(y["sequence"] < x["sequence"] for x, y in zip(visited, visited[1:]))
    score = .55 * math.exp(-median/tolerance) + .35*within + .1*(1-min((direction_mean or 0)/90, 1))
    score *= max(.5, 1-order_errors*.1)
    score *= 1-.25*quality["gap_fraction"]
    max_progress = max((int(j)+float(fractions[i, j]) for i, j in enumerate(assigned) if near[i]), default=0)
    return {"procedure_id": route["procedure_id"], "procedure_name": route["name"], "runway": route["runway"], "score": round(score, 6), "score_is_probability": False, "median_distance_m": round(median, 2), "within_tolerance_fraction": round(within, 6), "mean_track_difference_deg": round(direction_mean, 2) if direction_mean is not None else None, "ordered_fix_visits": visited, "order_errors": order_errors, "observed_route_coverage": round(max_progress/len(a), 6), "maximum_supported_leg_progress": round(max_progress, 6), "gap_count": quality["gap_count"], "scoring_reports": len(observations), "score_components": {"distance_weight": .55, "within_tolerance_weight": .35, "direction_weight": .1, "tolerance_m": tolerance, "order_penalty": order_errors*.1, "gap_fraction": quality["gap_fraction"], "gap_penalty_weight": .25}}

def match_flight(flight, observations, study, c, refs=None):
    refs = refs or runways()
    eligible = [o for o in observations if o["timestamp_ms"] >= flight["anchor_ms"] and o.get("on_ground") is not True and "implausible_movement" not in (o.get("quality_flags") or "")]
    intervals = [(b["timestamp_ms"]-a["timestamp_ms"])/1000 for a, b in zip(eligible, eligible[1:])]
    quality = {"gap_count": sum(dt > c["interpolation_gap_s"] for dt in intervals), "gap_fraction": round(sum(max(0, dt-c["interpolation_gap_s"]) for dt in intervals)/max(sum(intervals), 1), 6)}
    eligible = eligible[::max(1, len(eligible)//1200)]
    base = {"schema_version": 1, "flight_id": flight["flight_id"], "status": "insufficient_data", "best_candidate": None, "score_margin": None, "candidates": [], "reasons": [], "geometry_method": "Ordered straight fix connectors; CF/fly-over turns not reconstructed; no compliance inference"}
    if len(eligible) < 5 or not flight["runway_candidates"]:
        base["reasons"] = ["Too few usable airborne observations or no departure runway evidence"]
        return base
    candidate_runways = [flight["runway"]] if flight["runway"] else [x["runway"] for x in flight["runway_candidates"]]
    routes = [r for r in study["routes"] if r["runway"] in candidate_runways]
    by_id = {r["procedure_id"]: r for r in routes}
    scores = [rank_route(eligible, r, study["fixes"], next(x for x in refs if x["id"] == r["runway"]), c, quality) for r in routes]
    scores.sort(key=lambda r: (-r["score"], r["procedure_id"]))
    for i, score in enumerate(scores, 1): score["rank"] = i
    base["candidates"] = scores
    best = scores[0]
    margin = best["score"] - (scores[1]["score"] if len(scores)>1 else 0)
    base["score_margin"] = round(margin, 6)
    if best["score"] < c["matching_min_score"] or best["within_tolerance_fraction"] < .35:
        base["status"], base["reasons"] = "unmatched", ["Insufficient geometric agreement under configured tolerance"]
        return base
    indistinguishable = []
    for other in scores[1:]:
        common = 0
        for a, b in zip(by_id[best["procedure_id"]]["legs"], by_id[other["procedure_id"]]["legs"]):
            if a["fix"] != b["fix"]: break
            common += 1
        # Require evidence beyond the common trunk; early timing cannot select a SID.
        if common and best["maximum_supported_leg_progress"] <= common + .15:
            indistinguishable.append(other["procedure_id"])
    if indistinguishable or margin < c["matching_score_margin"] or flight["runway"] is None:
        base["status"] = "ambiguous"
        base["reasons"] = ["Observed common trunk or score margin does not distinguish a unique procedure"]
        base["indistinguishable_candidates"] = [best["procedure_id"]] + indistinguishable
    else:
        base["status"] = "geometry_consistent" if best["observed_route_coverage"] >= .9 else "partial"
        base["best_candidate"] = best["procedure_id"]
        base["reasons"] = ["Unique geometric candidate under configured heuristic; assigned clearance unknown"]
    return base

def match(c):
    out = Path(c["output_dir"])
    flights = load(out / "flights.json")
    study = load(ROOT / "map-2/reference/study-procedures.json")
    refs = runways()
    con = connect(c)
    indexed = {}
    for flight, observations in iter_event_tracks(con, flights, out / "observations.parquet"):
        indexed[flight["flight_id"]] = match_flight(flight, observations, study, c, refs)
    results = [indexed[f["flight_id"]] for f in flights]
    dump(out / "matches.json", results)
    flattened = [{"flight_id": r["flight_id"], "status": r["status"], "best_candidate": r["best_candidate"], "score_margin": r["score_margin"], **candidate} for r in results for candidate in r["candidates"]]
    dump(out / "match-candidates.json", flattened)
    if flattened: con.execute("COPY (SELECT * FROM read_json_auto($1)) TO $2 (FORMAT PARQUET, COMPRESSION ZSTD)", [str(out / "match-candidates.json"), str(out / "matches.parquet")])
    else: con.execute("COPY (SELECT NULL::VARCHAR flight_id,NULL::VARCHAR status,NULL::VARCHAR procedure_id WHERE false) TO ? (FORMAT PARQUET)", [str(out / "matches.parquet")])
    report = {"flights": len(results), "statuses": {}, "content_sha256": digest(results), "accuracy": "Not established: no independent assigned-SID labels"}
    for r in results: report["statuses"][r["status"]] = report["statuses"].get(r["status"], 0) + 1
    dump(out / "match-report.json", report)
    con.close()
    return report
