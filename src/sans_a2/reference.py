"""One study reference for both the matcher and the viewer; no QGIS dependency."""
import csv
from collections import defaultdict
from .common import ROOT, TRANSFORM, dump, load, file_hash

def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))

def export_reference(root=ROOT):
    source = root / "data/A1_Procedures.csv"
    records = read_csv(source)
    if len({r["leg_id"] for r in records}) != len(records): raise ValueError("Duplicate leg ID")
    data_path = root / "map-2/data.json"
    data = load(data_path)
    origin = data["origin"]["utm"]
    context_path = root / "map-2/reference/context-34R.json"
    if not context_path.exists():
        routes = [r for r in data["routes"] if r["runway"] == "34R"]
        names = {l["fix"] for r in routes for l in r["legs"]}
        dump(context_path, {"schema_version": 1, "scope": "34R context only; independent of the study CSV", "source": "Retained six-page map transcription, AIP AMDT 10/26", "routes": routes, "fixes": {k: v for k, v in data["fixes"].items() if k in names}})
    context = load(context_path)
    fixes = dict(context["fixes"])
    groups = defaultdict(list)
    for r in records: groups[r["procedure_id"]].append(r)
    routes = []
    for pid, group in sorted(groups.items()):
        group.sort(key=lambda r: int(r["sequence_number"]))
        if [int(r["sequence_number"]) for r in group] != list(range(1, len(group) + 1)): raise ValueError(f"Invalid sequence: {pid}")
        first = group[0]
        legs = []
        notes = []
        for r in group:
            if r["departure_runway"] != first["departure_runway"]: raise ValueError("Mixed runway in procedure")
            lat, lon = float(r["waypoint_latitude_deg"]), float(r["waypoint_longitude_deg"])
            if not (-90 <= lat <= 90 and -180 <= lon <= 180): raise ValueError("Invalid fix coordinate")
            e, n = TRANSFORM.transform(lon, lat)
            fix = {"lat": lat, "lon": lon, "xz": [round((e - origin[0]) / 1000, 6), round(-(n - origin[1]) / 1000, 6)], "rawDms": [r["waypoint_latitude_dms_raw"], r["waypoint_longitude_dms_raw"]]}
            if r["waypoint_id"] in fixes and (abs(fixes[r["waypoint_id"]]["lat"] - lat) > 1e-8 or abs(fixes[r["waypoint_id"]]["lon"] - lon) > 1e-8): raise ValueError("Conflicting fix coordinate")
            fixes[r["waypoint_id"]] = fix
            if r["data_notes"]: notes.append(r["data_notes"])
            numeric = lambda key: float(r[key]) if r[key] else None
            legs.append({"leg_id": r["leg_id"], "sequence_number": int(r["sequence_number"]), "fix": r["waypoint_id"], "altitude": r["altitude_raw"] if r["altitude_raw"] != "-" else "", "altitude_operator": r["altitude_operator"] or None, "altitude_value": numeric("altitude_value"), "altitude_unit": r["altitude_unit"] or None, "speed": r["speed_raw"] if r["speed_raw"] != "-" else "", "speed_limit_kt": numeric("speed_limit_kt"), "path": r["path_descriptor_raw"], "flyOver": r["fly_over_marked"] == "True", "true_course_deg": numeric("true_course_deg"), "magnetic_course_deg": numeric("magnetic_course_deg"), "published_distance_nm": numeric("distance_nm"), "source_sha256": r["leg_source_sha256"], "source_locator": r["leg_source_locator"], "notes": r["data_notes"]})
        caveat = "JN274 omitted from the 34L coordinate list; cross-referenced from 34C; specialist reconciliation remains open." if first["procedure_name"] == "MIGDA 3X" else ""
        routes.append({"id": first["procedure_name"].replace(" ", "-"), "procedure_id": pid, "name": first["procedure_name"], "runway": first["departure_runway"], "legs": legs, "sheetDate": first["sheet_date"], "effectiveDate": first["aip_effective_date"], "amendment": first["amendment"], "warning": caveat, "notes": sorted(set(notes))})
    study = {"schema_version": 1, "source_sha256": file_hash(source), "runway_source_sha256": file_hash(root / "data/External_Airport_Runways.csv"), "scope": "34C/34L published reference; not observed tracks or assigned clearances", "routes": routes, "fixes": {k: fixes[k] for k in sorted({l["fix"] for r in routes for l in r["legs"]})}}
    dump(root / "map-2/reference/study-procedures.json", study)
    data["routes"] = routes + context["routes"]
    data["fixes"] = fixes
    data["reference_source_sha256"] = study["source_sha256"]
    # Keep the large ground dataset compact and deterministic.
    import json
    data_path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    return {"study_procedures": len(routes), "study_legs": len(records), "study_fixes": len(study["fixes"]), "viewer_procedures": len(data["routes"]), "source_sha256": study["source_sha256"]}

def runways(root=ROOT):
    result = []
    for r in read_csv(root / "data/External_Airport_Runways.csv"):
        if r["runway_end"] not in ("34C", "34L"): continue
        start = TRANSFORM.transform(float(r["threshold_longitude_deg"]), float(r["threshold_latitude_deg"]))
        end = TRANSFORM.transform(float(r["opposite_threshold_longitude_deg"]), float(r["opposite_threshold_latitude_deg"]))
        result.append({"id": r["runway_end"], "start": start, "end": end, "bearing_deg": float(r["runway_true_bearing_deg"]), "elevation_ft_amsl": float(r["threshold_elevation_ft_amsl"]), "geoid_undulation_ft": float(r["geoid_undulation_ft"]), "airport_lat": float(r["airport_arp_latitude_deg"]), "airport_lon": float(r["airport_arp_longitude_deg"])})
    return sorted(result, key=lambda r: r["id"])
