"""A3 weather sampling and A4 departure fuel estimation (Hala Al-Ali).

Ported from github.com/Hala-Alali/OEJN_Aircraft_Fuel_Weather (OEJN_A3_A4.ipynb).
Reads A2 outputs (flights.json, observations.parquet), samples ERA5 surface and
pressure-level weather at each observation, corrects ground speed to true
airspeed with the along-track wind, and estimates fuel flow with OpenAP
FuelFlow.enroute(). Results are model estimates, not measured fuel.

Optional dependencies (pip install -e '.[fuel]'): openap, xarray, netCDF4, scipy.
They are imported lazily so the core A2 pipeline and its tests do not need them.
"""
from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd
from .common import connect, dump, load, digest
from .extensions import PerformanceLink

MODEL_ID = "a3a4-0.1.0"
MS_TO_KT = 1.94384
FT_TO_M = 0.3048

# ISA troposphere constants (pressure altitude -> static pressure)
T0, P0, LAPSE, R_AIR, G0 = 288.15, 1013.25, 0.0065, 287.05, 9.80665


def isa_pressure_hpa(altitude_ft):
    """Static pressure (hPa) for a barometric (pressure) altitude in feet."""
    h = np.asarray(altitude_ft, dtype=float) * FT_TO_M
    return P0 * (1 - LAPSE * h / T0) ** (G0 / (R_AIR * LAPSE))


def true_airspeed_kt(ground_speed_kt, track_deg, wind_u_mps, wind_v_mps):
    """TAS ≈ GS minus the wind component along the track (crosswind ignored)."""
    theta = np.deg2rad(np.asarray(track_deg, dtype=float))
    along = np.asarray(wind_u_mps, dtype=float) * np.sin(theta) + np.asarray(wind_v_mps, dtype=float) * np.cos(theta)
    return np.asarray(ground_speed_kt, dtype=float) - along * MS_TO_KT


def integrate_fuel_kg(timestamp_ms, fuel_flow_kg_s):
    """Trapezoidal integral of fuel flow over time."""
    t = (np.asarray(timestamp_ms, dtype=float) - float(timestamp_ms[0])) / 1000
    return float(np.trapezoid(np.asarray(fuel_flow_kg_s, dtype=float), x=t))


def _path(c, key):
    value = c.get(key)
    if not value: raise ValueError(f"Config key '{key}' is required for the fuel stage")
    path = (Path(c["config_path"]).parent / value).resolve()
    if not path.exists(): raise FileNotFoundError(f"{key}: {path} not found")
    return path


def _open_weather(c):
    import xarray as xr
    surface = xr.open_dataset(_path(c, "era5_surface")).sortby("latitude")
    pressure = xr.open_dataset(_path(c, "era5_pressure")).rename({"u": "u_wind", "v": "v_wind", "t": "temperature", "z": "geopotential"}).sortby("latitude")
    if "time" not in surface.dims and "valid_time" in surface.dims: surface = surface.rename({"valid_time": "time"})
    if "u10" in surface: surface = surface.rename({"u10": "10m_u_component_of_wind", "v10": "10m_v_component_of_wind", "t2m": "2m_temperature", "sp": "surface_pressure"})
    return surface, pressure


def sample_weather(obs, surface, pressure):
    """Linear interpolation of ERA5 at each observation; NaN outside coverage."""
    import xarray as xr
    obs = obs.copy()
    times = pd.to_datetime(obs["timestamp_ms"], unit="ms").to_numpy()
    lat, lon = obs["latitude_deg"].to_numpy(), obs["longitude_deg"].to_numpy()
    obs["estimated_pressure_hPa"] = isa_pressure_hpa(obs["barometric_altitude_ft"])

    s = surface[["10m_u_component_of_wind", "10m_v_component_of_wind", "2m_temperature", "surface_pressure"]].interp(
        time=xr.DataArray(times, dims="obs"), latitude=xr.DataArray(lat, dims="obs"), longitude=xr.DataArray(lon, dims="obs"), method="linear")
    obs["wind_u_10m"] = s["10m_u_component_of_wind"].values
    obs["wind_v_10m"] = s["10m_v_component_of_wind"].values
    obs["wind_speed_10m"] = np.hypot(obs["wind_u_10m"], obs["wind_v_10m"])
    obs["temperature_2m_C"] = s["2m_temperature"].values - 273.15
    obs["surface_pressure_hPa"] = s["surface_pressure"].values / 100

    levels = pressure["pressure_level"].values
    inside = obs["estimated_pressure_hPa"].between(levels.min(), levels.max()).to_numpy()
    for col in ("wind_u_pressure", "wind_v_pressure", "temperature_pressure_C", "geopotential_height_m"): obs[col] = np.nan
    if inside.any():
        p = pressure[["u_wind", "v_wind", "temperature", "geopotential"]].interp(
            valid_time=xr.DataArray(times[inside], dims="obs"), pressure_level=xr.DataArray(obs["estimated_pressure_hPa"].to_numpy()[inside], dims="obs"),
            latitude=xr.DataArray(lat[inside], dims="obs"), longitude=xr.DataArray(lon[inside], dims="obs"), method="linear")
        idx = obs.index[inside]
        obs.loc[idx, "wind_u_pressure"] = p["u_wind"].values
        obs.loc[idx, "wind_v_pressure"] = p["v_wind"].values
        obs.loc[idx, "temperature_pressure_C"] = p["temperature"].values - 273.15
        obs.loc[idx, "geopotential_height_m"] = p["geopotential"].values / G0

    obs["wind_source"] = np.where(obs["wind_u_pressure"].notna(), "era5_pressure_level", np.where(obs["wind_u_10m"].notna(), "era5_surface_10m", "none"))
    obs["wind_u_used"] = obs["wind_u_pressure"].fillna(obs["wind_u_10m"])
    obs["wind_v_used"] = obs["wind_v_pressure"].fillna(obs["wind_v_10m"])
    return obs


def resolve_aircraft(c, icao24s):
    """ICAO24 -> type code from the aircraft registry, then OpenAP MTOW."""
    from openap import prop
    with sqlite3.connect(_path(c, "aircraft_db")) as db:
        registry = pd.read_sql_query("SELECT aircraft_icao_address, aircraft_type_code FROM aircrafts", db)
    registry["icao24"] = registry["aircraft_icao_address"].astype(str).str.strip().str.lower()
    types = registry.drop_duplicates("icao24").set_index("icao24")["aircraft_type_code"]
    resolved = {}
    for icao in icao24s:
        typecode = types.get(icao)
        entry = {"aircraft_type": typecode if isinstance(typecode, str) else None, "mtow_kg": None, "openap_aircraft_id": None}
        if entry["aircraft_type"]:
            try:
                spec = prop.aircraft(entry["aircraft_type"], use_synonym=True)
                entry["mtow_kg"] = float(spec["mtow"])
                entry["openap_aircraft_id"] = str(spec.get("aircraft") or entry["aircraft_type"])
            except Exception:
                pass
        resolved[icao] = entry
    return resolved


def flight_fuel(flight, obs, aircraft, c):
    """Fuel for one departure from anchor to fuel_max_altitude_ft. Returns (summary, per-observation frame)."""
    from openap import FuelFlow
    max_alt = c.get("fuel_max_altitude_ft", 10000)
    obs = obs[(obs["timestamp_ms"] >= flight["anchor_ms"]) & (obs["barometric_altitude_ft"] <= max_alt)].sort_values("timestamp_ms").copy()
    if len(obs) < 2: raise ValueError("insufficient_departure_observations")
    obs["TAS_kt"] = true_airspeed_kt(obs["ground_speed_kt"], obs["track_deg"], obs["wind_u_used"], obs["wind_v_used"])
    obs = obs.dropna(subset=["barometric_altitude_ft", "barometric_rate_fpm", "TAS_kt"])
    obs = obs[obs["TAS_kt"] > 0].copy()
    if len(obs) < 2: raise ValueError("insufficient_valid_observations")
    mass = aircraft["mtow_kg"] * c.get("fuel_mass_fraction_of_mtow", 0.8)
    model = FuelFlow(ac=aircraft["aircraft_type"], use_synonym=True)
    obs["fuel_flow_kg_s"] = np.asarray(model.enroute(mass=mass, tas=obs["TAS_kt"].to_numpy(), alt=obs["barometric_altitude_ft"].to_numpy(), vs=obs["barometric_rate_fpm"].to_numpy()), dtype=float)
    summary = {
        "mass_kg": float(mass),
        "departure_points": len(obs),
        "duration_s": float(obs["timestamp_ms"].iloc[-1] - obs["timestamp_ms"].iloc[0]) / 1000,
        "total_fuel_kg": round(integrate_fuel_kg(obs["timestamp_ms"].to_numpy(), obs["fuel_flow_kg_s"].to_numpy()), 3),
        "wind_sources": {str(k): int(v) for k, v in obs["wind_source"].value_counts().items()},
    }
    if not np.isfinite(summary["total_fuel_kg"]): raise ValueError("non_finite_fuel_flow")
    # Same identifying columns as the original Weather_FuelFlow_Dataset
    obs["flight_id"] = flight["flight_id"]
    obs["aircraft_type"] = aircraft["aircraft_type"]
    obs["estimated_mass_kg"] = float(mass)
    obs["total_departure_fuel_kg"] = summary["total_fuel_kg"]
    return summary, obs


def run_fuel(c):
    import openap
    out = Path(c["output_dir"])
    flights = [f for f in load(out / "flights.json") if f["runway_status"] == "accepted_departure_candidate"]
    con = connect(c)
    ids = sorted({f["icao24"] for f in flights})
    con.register("wanted", pd.DataFrame({"icao24": ids}))
    obs_all = con.execute("SELECT o.icao24,o.observation_id,o.timestamp_utc,o.timestamp_ms,o.latitude_deg,o.longitude_deg,o.barometric_altitude_ft,o.barometric_rate_fpm,o.ground_speed_kt,o.track_deg FROM read_parquet(?) o JOIN wanted w USING(icao24) ORDER BY o.icao24,o.timestamp_ms", [str(out / "observations.parquet")]).df()
    surface, pressure = _open_weather(c)
    aircraft = resolve_aircraft(c, ids)
    by_aircraft = dict(tuple(obs_all.groupby("icao24")))
    assumptions = (f"mass = {c.get('fuel_mass_fraction_of_mtow', 0.8):.0%} of OpenAP MTOW (actual mass unknown)",
                   "TAS = ground speed minus along-track ERA5 wind; pressure-level wind, 10 m wind fallback",
                   f"departure segment: anchor to {c.get('fuel_max_altitude_ft', 10000)} ft barometric altitude",
                   "OpenAP synonyms used for unsupported types (e.g. A21N, B77L)")
    results, frames, statuses = [], [], {}
    for f in flights:
        ac = aircraft.get(f["icao24"], {})
        link = dict(flight_id=f["flight_id"], aircraft_type=ac.get("aircraft_type"), openap_aircraft_id=ac.get("openap_aircraft_id"),
                    operating_assumptions=assumptions, model_version=f"{MODEL_ID}; openap {getattr(openap, '__version__', 'unknown')}",
                    uncertainty_note="Model estimate, not measured fuel; mass assumption dominates uncertainty",
                    result_artifact="fuel-observations.parquet")
        extra = {}
        if not ac.get("mtow_kg"):
            status = "unsupported_aircraft" if ac.get("aircraft_type") else "unresolved_aircraft_type"
        else:
            obs = by_aircraft.get(f["icao24"])
            obs = obs[(obs["timestamp_ms"] >= f["start_ms"]) & (obs["timestamp_ms"] <= f["end_ms"])] if obs is not None else pd.DataFrame()
            try:
                if obs.empty: raise ValueError("insufficient_departure_observations")
                summary, frame = flight_fuel(f, sample_weather(obs, surface, pressure), ac, c)
                link["mass_kg"] = summary.pop("mass_kg")
                extra = summary
                frames.append(frame)
                status = "calculated"
            except ValueError as e:
                status = str(e)
        statuses[status] = statuses.get(status, 0) + 1
        results.append({**asdict(PerformanceLink(**link, status=status)), **extra})
    dump(out / "fuel-results.json", results)
    # Columns of the original Weather_FuelFlow_Dataset (same names and order), then extras
    keep = ["flight_id", "icao24", "aircraft_type", "timestamp_utc", "timestamp_ms", "estimated_mass_kg", "barometric_altitude_ft", "barometric_rate_fpm",
            "ground_speed_kt", "track_deg", "TAS_kt", "wind_u_pressure", "wind_v_pressure", "wind_u_10m", "wind_v_10m", "temperature_2m_C", "wind_speed_10m",
            "surface_pressure_hPa", "fuel_flow_kg_s", "total_departure_fuel_kg",
            "observation_id", "latitude_deg", "longitude_deg", "estimated_pressure_hPa", "temperature_pressure_C", "geopotential_height_m", "wind_source"]
    per_obs = pd.concat(frames)[keep] if frames else pd.DataFrame(columns=keep)
    con.register("per_obs", per_obs)
    target = str(out / "fuel-observations.parquet").replace("'", "''")
    con.execute(f"COPY (SELECT * FROM per_obs) TO '{target}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    con.close()
    calculated = [r["total_fuel_kg"] for r in results if r["status"] == "calculated"]
    report = {"departure_candidates": len(flights), "statuses": statuses, "total_fuel_kg_sum": round(sum(calculated), 1),
              "mean_fuel_kg": round(sum(calculated) / len(calculated), 1) if calculated else None, "content_sha256": digest(results)}
    dump(out / "fuel-report.json", report)
    return report
