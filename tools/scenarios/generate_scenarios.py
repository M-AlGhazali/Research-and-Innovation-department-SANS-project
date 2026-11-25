"""Pre-compute the Map 2 "Scenario (what-if)" results: 16 published SIDs x 3 aircraft = 48 simulated departures.

    python tools/scenarios/generate_scenarios.py [--noise-repo PATH] [--only "34C/ISLAM 2W/A320"] [--work DIR]

For each runway / SID / aircraft:
  1. fly a simulated aircraft along the published SID (data/A1_Procedures.csv) with an OpenAP climb profile and
     integrate fuel to 10,000 ft (adapted from masar-reference/reference_trajectory_fuel.py);
  2. write that trajectory in the input format of the noise model (github.com/M40aha/oejn-noise-population,
     cloned next to this repo, never copied in) and run its ECAC Doc 29 pipeline for one daytime departure
     (adapted from masar-reference/reference_noise_run.py);
  3. read the per-flight LAmax grid, draw the 60 / 65 / 70 dB contours (WGS84) and read the residents inside each
     contour (WorldPop grid of the noise model) and the level at the OpenStreetMap places of Map 1.

Outputs (static, loaded by Map 2):
  map-2/scenarios/index.json                       one record per combination
  map-2/scenarios/<runway>_<SID>_<aircraft>.geojson the three LAmax contours
Every number is modelled. One method per output, no alternatives.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from functools import reduce
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "map-2" / "scenarios"
WORK = Path(__file__).resolve().parent / ".work"
FT, KT, NM = 0.3048, 0.514444, 1852.0
RUNWAYS = ("34C", "34L")
# aircraft: OpenAP type and engine (fuel), and the identity record the noise model maps to an ANP aircraft
AIRCRAFT = {
    "A320": {"name": "Airbus A320", "engine": "CFM56-5B4", "model": "Airbus A320-214", "noise_engine": "CFM56-5B4/3"},
    "A20N": {"name": "Airbus A320neo", "engine": "LEAP-1A26", "model": "Airbus A320-251N", "noise_engine": "LEAP-1A26"},
    "B77W": {"name": "Boeing 777-300ER", "engine": "GE90-115B", "model": "Boeing 777-368ER", "noise_engine": "GE90-115B"},
}
LEVELS = (60, 65, 70)
TOP_FT = 12000            # the simulated climb stops here (as in the reference); results are read at 10,000 ft
CO2_PER_KG_FUEL = 3.16
T0_UTC = "2026-10-01T09:00Z"   # 12:00 local: the "day" period of the noise model
GRID_HALF_WIDTH_M = 60000.0
ASSUMPTIONS = [
    "Simulated flights, not recorded ones. The aircraft follows the published SID exactly and keeps to its published "
    "altitude and speed limits (AIP AMDT 10/26).",
    "Fuel comes from OpenAP: take-off mass 80% of the maximum take-off mass, the standard OpenAP (WRAP) climb, "
    "250 kt below 10,000 ft and no wind.",
    "Fuel, CO2, time and distance cover only the climb from brake release to 10,000 ft. CO2 = fuel x 3.16.",
    "Noise is the loudest moment of one departure (LAmax), from ECAC Doc 29 through the noise model of the "
    "oejn-noise-population repo: daytime, still air, 33 °C, 250 m grid.",
    "Residents are WorldPop 2025 people (100 m grid) inside each contour. Place names are OpenStreetMap points, "
    "not boundaries.",
    "Daily and yearly totals multiply one departure by the departures per day and by 365 days.",
]


def load_noise(repo: Path):
    for p in (repo / "scripts", repo / "src", repo):
        sys.path.insert(0, str(p))
    import make_synthetic_noise_inputs as syn            # noqa: E402  (noise repo, read only)
    from noise.run import main as noise_main             # noqa: E402
    return syn, noise_main


# ------------------------------------------------------------------------------------------------ 1. trajectory + fuel
def sid_legs(a1: pd.DataFrame, runway: str, sid: str):
    from pyproj import Transformer
    to_utm = Transformer.from_crs(4326, 32637, always_xy=True)
    legs = a1[(a1.procedure_name == sid) & (a1.departure_runway == runway)].sort_values("sequence_number")
    wps = []
    for r in legs.itertuples():
        e, n = to_utm.transform(r.waypoint_longitude_deg, r.waypoint_latitude_deg)
        spd = r.speed_limit_kt if r.speed_operator in ("at_or_below", "at") and pd.notna(r.speed_limit_kt) else None
        wps.append({"id": r.waypoint_id, "e": e, "n": n, "op": r.altitude_operator if pd.notna(r.altitude_operator) else None,
                    "raw": r.altitude_raw if r.altitude_raw not in ("-", None) and pd.notna(r.altitude_raw) else None,
                    "max_ft": r.altitude_max_ft if pd.notna(r.altitude_max_ft) else None,
                    "min_ft": r.altitude_min_ft if pd.notna(r.altitude_min_ft) else None, "max_kt": spd})
    first = legs.iloc[0]
    thr = (first.departure_threshold_latitude_deg, first.departure_threshold_longitude_deg,
           first.opposite_threshold_latitude_deg, first.opposite_threshold_longitude_deg,
           float(first.departure_threshold_elevation_ft_amsl), float(first.geoid_undulation_ft))
    return wps, thr, float(first.minimum_climb_ft_per_nm)


def simulate(a1, runway, sid, ac, step=2.0):
    """Reference model (masar-reference/reference_trajectory_fuel.py), generalised from the single
    "6,000 ft until JN276" level-off to every published altitude limit of the SID:
      * "at" and "at or below" limits are a ceiling until their fix is passed;
      * "at or above" limits are checked when the fix is passed (flag when not met);
      * a published "at or below" speed (e.g. 210 kt to JN272) caps the speed until its fix is passed.
    After the last SID fix the aircraft keeps its course until TOP_FT."""
    from openap import FuelFlow, WRAP, aero, prop
    from pyproj import Transformer
    to_utm = Transformer.from_crs(4326, 32637, always_xy=True)
    to_ll = Transformer.from_crs(32637, 4326, always_xy=True)
    wps, (la1, lo1, la2, lo2, elev, geoid), min_grad = sid_legs(a1, runway, sid)
    e1, n1 = to_utm.transform(lo1, la1)
    e2, n2 = to_utm.transform(lo2, la2)
    h = np.arctan2(e2 - e1, n2 - n1)
    w = WRAP(ac=ac)
    v_lof = w.takeoff_speed()["default"]
    d_to = w.takeoff_distance()["default"] * 1000
    vs_ic = w.initclimb_vs()["default"]
    vs_cl = w.climb_vs_pre_concas()["default"]
    acp = prop.aircraft(ac)
    mass = 0.8 * acp["mtow"]
    ff = FuelFlow(ac=ac, eng=AIRCRAFT[ac]["engine"])
    a = v_lof ** 2 / (2 * d_to)
    e, n, z, t, dist, fuel, cas = e1, n1, 0.0, 0.0, 0.0, 0.0, 0.0
    k, rows, f10, flags, passed, held = 0, [], None, [], [], {}
    while z < TOP_FT * FT - elev * FT and t < 1500:
        zmsl = z + elev * FT
        if z <= 0 and cas < v_lof:
            cas = min(cas + a * step, v_lof)
            vs, og = 0.0, True
            tas = aero.cas2tas(cas, zmsl)
            fflow = ff.takeoff(tas=tas / KT, alt=zmsl / FT, throttle=1)
        else:
            og = False
            caps = [x["max_kt"] for x in wps[k:k + 1] if x["max_kt"]]
            vmax = min([250.0] + caps) * KT
            if z < 1500 * FT:
                vs = vs_ic
            elif cas < vmax - 0.1:
                vs = 0.6 * vs_cl
                cas = min(cas + 0.5 * step, vmax)
            else:
                vs = vs_cl
                cas = min(cas, vmax)
            lim = [x for x in wps[k:] if x["max_ft"] and x["op"] in ("at", "at_or_below")]
            ceiling = min([x["max_ft"] for x in lim] + [1e9])
            if zmsl >= ceiling * FT - 1:
                vs = 0.0
                fix = next(x["id"] for x in lim if x["max_ft"] == ceiling)
                held.setdefault((ceiling, fix), [dist, dist])[1] = dist
            tas = aero.cas2tas(cas, zmsl)
            fflow = ff.enroute(mass=mass, tas=tas / KT, alt=zmsl / FT, vs=vs / FT * 60)
            if k < len(wps):
                wp = wps[k]
                brg = np.arctan2(wp["e"] - e, wp["n"] - n)
                d = ((brg - h + np.pi) % (2 * np.pi)) - np.pi
                if z > 400 * FT:
                    h += np.clip(d, -np.radians(3) * step, np.radians(3) * step)
                if np.hypot(wp["e"] - e, wp["n"] - n) < max(1500.0, tas * 12):
                    alt_ft = zmsl / FT
                    if wp["min_ft"] and alt_ft < wp["min_ft"] - 50:
                        flags.append(f"{wp['id']} reached at {alt_ft:.0f} ft, below the published {wp['raw']}")
                    passed.append({"id": wp["id"], "dist_nm": round(dist / NM, 2), "alt_ft": round(alt_ft),
                                   "constraint": wp["raw"]})
                    k += 1
        fflow = float(np.atleast_1d(fflow)[0])
        e += tas * np.sin(h) * step
        n += tas * np.cos(h) * step
        dist += tas * step
        z = max(0.0, z + vs * step)
        t += step
        fuel += fflow * step
        mass -= fflow * step
        if f10 is None and z + elev * FT >= 10000 * FT:
            f10 = {"fuel_kg": fuel, "time_s": t, "distance_nm": dist / NM, "fixes_passed": k}
        lon, lat = to_ll.transform(e, n)
        rows.append({"t": t, "lat": lat, "lon": lon, "e": e, "n": n, "z_afe_ft": z / FT, "alt_msl_ft": z / FT + elev,
                     "cas_kt": cas / KT, "tas_kt": tas / KT, "vs_fpm": vs / FT * 60, "on_ground": og,
                     "trk": np.degrees(h) % 360, "dist_nm": dist / NM})
    if f10 is None:
        raise RuntimeError(f"{runway} {sid} {ac}: 10,000 ft not reached within 1500 s")
    if f10["fixes_passed"] >= len(wps):
        flags.append("10,000 ft reached after the last SID fix (course held after the last fix)")
    df = pd.DataFrame(rows)
    # level-offs below 10,000 ft forced by a published altitude limit (shown in the UI as plain notes)
    notes = [f"Held at {c:,.0f} ft for {(b - a) / NM:.1f} NM until {fix} (published limit)."
             for (c, fix), (a, b) in held.items() if c < 10000 and (b - a) / NM >= 0.5]
    air = df[~df.on_ground & (df.alt_msl_ft <= 10000)]
    grad = np.diff(air.alt_msl_ft) / np.maximum(np.diff(air.dist_nm), 1e-9)
    info = {"elev_ft": elev, "geoid_ft": geoid, "mtow_kg": float(acp["mtow"]), "mass_kg": 0.8 * float(acp["mtow"]),
            "to10k": f10, "fixes": passed, "flags": flags, "notes": notes, "min_climb_ft_per_nm": min_grad,
            "lowest_gradient_ft_per_nm": float(np.percentile(grad[grad > 0], 1)) if (grad > 0).any() else None}
    return df, info


# ------------------------------------------------------------------------------------------------ 2. noise
def noise_inputs(syn, out: Path, jobs):
    """Noise-model inputs for all jobs in one run (same weather, distinct aircraft ids)."""
    syn.main(out, 1)                                     # schema-exact METAR + identity templates
    met = pd.read_csv(out / "ext_metar_oejn.csv")
    met["sknt"], met["drct"] = 0, np.nan                 # still air
    met["metar"] = met.metar.str.replace("33008KT", "00000KT")
    met.to_csv(out / "ext_metar_oejn.csv", index=False)
    t0 = int(pd.Timestamp(T0_UTC).value // 1e6)
    obs, fl, ident = [], [], []
    for i, j in enumerate(jobs):
        df, info = j["traj"], j["info"]
        icao = f"7a{i:04x}"
        fid = f"OEJN-2026-10-01-{icao}-{t0}"
        j["flight_id"] = fid
        elev = info["elev_ft"]
        o = pd.DataFrame({
            "flight_id": fid, "icao24": icao, "callsign": f"SCN{i:03d}", "timestamp_ms": (t0 + df.t * 1000).astype("int64"),
            "latitude_deg": df.lat, "longitude_deg": df.lon, "easting_m": df.e, "northing_m": df.n,
            "barometric_altitude_ft": [None if g else int(round(syn.press_alt(zz, elev) / 25) * 25) for zz, g in zip(df.z_afe_ft, df.on_ground)],
            "geometric_altitude_ft": [None if g else float(round(a + info["geoid_ft"])) for a, g in zip(df.alt_msl_ft, df.on_ground)],
            "ground_speed_kt": df.tas_kt.round(1), "indicated_airspeed_kt": None, "track_deg": df.trk.round(1),
            "on_ground": df.on_ground, "quality_flags": "", "observation_id": [f"scn{i}_{k}" for k in range(len(df))]})
        obs.append(o)
        fl.append({"flight_id": fid, "icao24": icao, "start_ms": int(o.timestamp_ms.min()), "end_ms": int(o.timestamp_ms.max()),
                   "anchor_ms": int(o[~o.on_ground].timestamp_ms.min()), "runway": j["runway"],
                   "runway_status": "accepted_departure_candidate", "match_status": "unmatched", "procedure": None})
        a = AIRCRAFT[j["ac"]]
        ident.append({"icao24": icao, "registration": f"HZ-SC{i:02d}", "icao_type": j["ac"], "model": a["model"],
                      "engine_type": a["noise_engine"], "operator_icao": "SCN", "operator": "SCENARIO", "source": "scenario",
                      "source_url": "", "lookup_date": "2026-11-25"})
    pd.concat(obs).to_parquet(out / "a2" / "a2_noise_departures.parquet", index=False)
    pd.DataFrame(fl).to_csv(out / "a2" / "a2_noise_flights.csv", index=False)
    pd.DataFrame(ident).to_csv(out / "aircraft_identity.csv", index=False)


def run_noise(noise_main, repo: Path, work: Path, workers: int):
    cfg = yaml.safe_load((repo / "config" / "noise.yaml").read_text())
    cfg["run"]["save_flight_grids"] = True
    cfg["run"]["workers"] = workers
    # The repo's 40 km grid cuts the B77W 60 dB footprint north of 34C; 60 km keeps every footprint whole.
    # Same 250 m spacing, so results inside the 40 km square are unchanged.
    cfg["grid"]["half_width_m"] = GRID_HALF_WIDTH_M
    (work / "noise.yaml").write_text(yaml.safe_dump(cfg))
    inp = work / "inp"
    os.environ.update(NOISE_A2_DIR=str(inp / "a2"), NOISE_METAR_CSV=str(inp / "ext_metar_oejn.csv"),
                      NOISE_IDENTITY_CSV=str(inp / "aircraft_identity.csv"), NOISE_OUT_ROOT=str(work / "out"))
    os.environ.pop("NOISE_IDENTITY_FILL_CSV", None)
    noise_main(work / "noise.yaml", work / "out")
    return work / "out" / "data" / "noise"


# ------------------------------------------------------------------------------------------------ 3. contours, places
def contour_polygons(X, Y, L, level):
    """Filled LAmax >= level area as a shapely geometry in UTM 37N (matplotlib contours, even-odd rings)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from shapely.geometry import Polygon
    fig, ax = plt.subplots()
    cs = ax.contourf(X, Y, L, levels=[level, 1e9])
    rings = [r for p in cs.get_paths() for r in p.to_polygons() if len(r) >= 4]
    plt.close(fig)
    polys = [Polygon(r).buffer(0) for r in rings]
    polys = [p for p in polys if not p.is_empty]
    if not polys:
        return None
    return reduce(lambda acc, p: acc.symmetric_difference(p), polys).buffer(0)


def places_table():
    import geopandas as gpd
    g = gpd.read_file(ROOT / "map-1" / "OEJN-ground.gpkg", layer="places").to_crs(32637)
    g = g[~g.name.str.startswith("King Abdulaziz")]                      # the airport itself
    g["name_ar"] = [json.loads(n).get("name:ar") if isinstance(n, str) else None for n in g.note]
    return g


def git_head(p: Path):
    try:
        return subprocess.run(["git", "-C", str(p), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def slug(runway, sid, ac):
    return f"{runway}_{sid.replace(' ', '')}_{ac}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--noise-repo", type=Path, default=Path(os.environ.get("NOISE_REPO", ROOT.parent / "oejn-noise-population")))
    ap.add_argument("--only", help='one combination, e.g. "34C/ISLAM 2W/A320" (check run; nothing is written to map-2)')
    ap.add_argument("--work", type=Path, default=WORK)
    ap.add_argument("--workers", type=int, default=1,
                    help="noise-model worker processes (keep 1 on Windows: the noise model's process pool fails there)")
    args = ap.parse_args()
    from pyproj import Transformer
    from scipy.interpolate import RegularGridInterpolator
    from shapely.geometry import LineString, Point, mapping
    from shapely.ops import transform as shp_transform
    import openap

    syn, noise_main = load_noise(args.noise_repo.resolve())
    a1 = pd.read_csv(ROOT / "data" / "A1_Procedures.csv")
    combos = [(rw, sid, ac) for rw in RUNWAYS for sid in sorted(a1[a1.departure_runway == rw].procedure_name.unique())
              for ac in AIRCRAFT]
    if args.only:
        combos = [tuple(args.only.split("/"))]
    work = args.work.resolve()
    (work / "inp" / "a2").mkdir(parents=True, exist_ok=True)

    jobs = []
    for rw, sid, ac in combos:
        df, info = simulate(a1, rw, sid, ac)
        jobs.append({"runway": rw, "sid": sid, "ac": ac, "traj": df, "info": info})
        f = info["to10k"]
        print(f"{rw} {sid:9s} {ac}: fuel {f['fuel_kg']:6.1f} kg  {f['time_s']:4.0f} s  {f['distance_nm']:5.1f} NM  "
              f"{' '.join(info['notes'] + info['flags'])}")
    noise_inputs(syn, work / "inp", jobs)
    nd = run_noise(noise_main, args.noise_repo.resolve(), work, args.workers)

    res = pd.read_csv(nd / "processed" / "flight_results.csv").set_index("flight_id")
    grid = pd.read_parquet(nd / "processed" / "noise_grid.parquet", columns=["x_utm37n_m", "y_utm37n_m"])
    n = int(round(np.sqrt(len(grid))))
    X = grid.x_utm37n_m.to_numpy().reshape(n, n)
    Y = grid.y_utm37n_m.to_numpy().reshape(n, n)
    to_ll = Transformer.from_crs(32637, 4326, always_xy=True)
    places = places_table()
    records = []
    if not args.only:
        OUT.mkdir(parents=True, exist_ok=True)
    for j in jobs:
        fid, info, df = j["flight_id"], j["info"], j["traj"]
        r = res.loc[fid]
        if r.path_status != "OK":
            raise RuntimeError(f"noise model failed for {fid}: {r.get('error')}")
        L = np.load(nd / "interim" / f"{fid}.npz")["lmax"].astype(float).reshape(n, n)
        L = np.where(np.isfinite(L), L, 0.0)
        sid_id = slug(j["runway"], j["sid"], j["ac"])
        feats, areas = [], {}
        for lev in LEVELS:
            geom = contour_polygons(X, Y, L, lev)
            if geom is None:
                areas[str(lev)] = 0.0
                continue
            areas[str(lev)] = round(geom.area / 1e6, 2)
            g = shp_transform(lambda x, y, z=None: to_ll.transform(x, y), geom.simplify(15))
            gj = json.loads(json.dumps(mapping(g)), parse_float=lambda s: round(float(s), 5))
            feats.append({"type": "Feature", "properties": {"lamax_db": lev, "residents": round(float(r[f"pop_lamax_ge_{lev}"])),
                                                              "area_km2": areas[str(lev)]}, "geometry": gj})
        # places: level and distance to the ground track below 10,000 ft
        interp = RegularGridInterpolator((Y[:, 0], X[0, :]), L, bounds_error=False, fill_value=0.0)
        low = df[df.alt_msl_ft <= 10000]
        track = LineString(np.c_[low.e, low.n])
        pl = []
        for p in places.itertuples():
            plon, plat = to_ll.transform(p.geometry.x, p.geometry.y)
            pl.append({"name": p.name, "name_ar": p.name_ar, "lon": round(plon, 5), "lat": round(plat, 5),
                       "lamax_db": round(float(interp([[p.geometry.y, p.geometry.x]])[0]), 1),
                       "km_from_track": round(track.distance(Point(p.geometry.x, p.geometry.y)) / 1000, 1)})
        pl.sort(key=lambda d: d["km_from_track"])
        # profile: every 10 s plus the 10,000 ft point, whole simulated climb
        i10 = int(np.argmax(df.alt_msl_ft.to_numpy() >= 10000))
        keep = sorted(set(range(0, len(df), 5)) | {i10, len(df) - 1})
        prof = [[round(df.dist_nm[i], 2), round(df.alt_msl_ft[i]), round(df.lon[i], 5), round(df.lat[i], 5)] for i in keep]
        f10 = info["to10k"]
        rec = {"id": sid_id, "runway": j["runway"], "sid": j["sid"], "aircraft": j["ac"], "geojson": f"{sid_id}.geojson",
               "to10k": {"fuel_kg": round(f10["fuel_kg"], 1), "co2_kg": round(f10["fuel_kg"] * CO2_PER_KG_FUEL, 1),
                         "time_s": round(f10["time_s"]), "distance_nm": round(f10["distance_nm"], 1)},
               "residents": {str(lev): round(float(r[f"pop_lamax_ge_{lev}"])) for lev in LEVELS},
               "contour_area_km2": areas, "noise_aircraft": r.anp_acft_id,
               "profile": prof, "fixes": info["fixes"], "places": pl, "notes": info["notes"], "flags": info["flags"],
               "lowest_climb_gradient_ft_per_nm": round(info["lowest_gradient_ft_per_nm"] or 0)}
        records.append(rec)
        if not args.only:
            (OUT / rec["geojson"]).write_text(json.dumps({"type": "FeatureCollection", "name": sid_id, "features": feats},
                                                         separators=(",", ":")) + "\n")
        print(f"{sid_id:22s} residents >=60/65/70: {rec['residents']['60']:>7,} / {rec['residents']['65']:>7,} / "
              f"{rec['residents']['70']:>6,}  ANP {r.anp_acft_id}")
    if args.only:
        print(json.dumps({k: v for k, v in records[0].items() if k not in ("profile", "places")}, indent=1))
        return
    index = {
        "schema_version": 1,
        "title": "Masar Map 2 scenarios: simulated departures, OEJN runways 34C and 34L",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "generator": "tools/scenarios/generate_scenarios.py",
        "sources": {"procedures": "data/A1_Procedures.csv (SANS AIP AIRAC AMDT 10/26)",
                    "fuel_model": f"OpenAP {getattr(openap, '__version__', '')}".strip(),
                    "noise_model": "github.com/M40aha/oejn-noise-population (ECAC Doc 29 5th ed., EASA ANP 2.3)",
                    "noise_model_commit": git_head(args.noise_repo),
                    "population": "WorldPop R2025A 100 m, via oejn-noise-population",
                    "places": "OpenStreetMap contributors (ODbL), via map-1/OEJN-ground.gpkg"},
        "levels_db": list(LEVELS), "co2_per_kg_fuel": CO2_PER_KG_FUEL, "assumptions": ASSUMPTIONS,
        "aircraft": {k: {"name": v["name"], "engine": v["engine"]} for k, v in AIRCRAFT.items()},
        "scenarios": records,
    }
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {len(records)} scenarios to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
