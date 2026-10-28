"""Two selective disk-backed passes; the full global day is never fetched into Python."""
from pathlib import Path
import glob
from .common import connect, rows, dump, load, digest, file_hash, ROOT, TRANSFORM, ALGORITHM_VERSION
from .reference import runways
from .provider import REQUIRED, MAPPING, QUALITY

def inventory(c):
    files = sorted(Path(p).resolve() for p in glob.glob(c["input_glob"]))
    if not files: raise FileNotFoundError(f"No observations match {c['input_glob']}")
    con = connect(c)
    reference = None
    items = []
    for p in files:
        schema = rows(con, "SELECT name,type,converted_type,logical_type FROM parquet_schema(?)", [str(p)])
        names = {r["name"] for r in schema}
        if REQUIRED - names: raise ValueError(f"Missing provider columns in {p.name}: {REQUIRED-names}")
        timestamp = next(r for r in schema if r["name"] == "timestamp")
        if "isAdjustedToUTC=1" not in (timestamp["logical_type"] or ""): raise ValueError("Timestamp must be UTC-adjusted")
        if reference is not None and schema != reference: raise ValueError("Hourly schema drift")
        reference = schema
        meta = con.execute("SELECT num_rows FROM parquet_file_metadata(?)", [str(p)]).fetchone()
        stat = p.stat()
        items.append({"file": str(p), "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "rows": meta[0]})
    con.close()
    implementation = {name: file_hash(Path(__file__).parent / name) for name in ("ingest.py", "provider.py", "common.py", "reference.py")}
    key = digest({"config": c, "inputs": items, "algorithm": ALGORITHM_VERSION, "implementation": implementation, "reference": file_hash(ROOT / "data/A1_Procedures.csv")})
    report = {"schema_version": 1, "inputs": items, "total_rows_from_footers": sum(x["rows"] for x in items), "schema": reference, "mapping": MAPPING, "quality_fields": QUALITY, "cache_key": key, "identity_method": "file path/size/mtime plus reference SHA-256; raw input content not fully hashed", "publication": "Local evaluation; distribution permission not established"}
    dump(Path(c["output_dir"]) / "preflight.json", report)
    return report

def ingest(c, force=False):
    out = Path(c["output_dir"])
    pre = inventory(c)
    report_path = out / "ingest-report.json"
    if not force and report_path.exists() and (out / "observations.parquet").exists() and load(report_path)["cache_key"] == pre["cache_key"]:
        return {**load(report_path), "cache_hit": True}
    # A persistent work database permits spilling without retaining Python dataframes.
    con = connect(c, out / "ingest-work.duckdb")
    files = [x["file"] for x in pre["inputs"]]
    con.execute("SET VARIABLE input_files=?", [files])
    con.execute("CREATE OR REPLACE VIEW raw AS SELECT * FROM read_parquet(getvariable('input_files'), filename=true, file_row_number=true)")
    names = {x["name"] for x in pre["schema"]}
    optional = {"ab": "INTEGER", "ag": "INTEGER", "gs": "DOUBLE", "i": "DOUBLE", "tr": "DOUBLE", "th": "DOUBLE", "mh": "DOUBLE", "br": "DOUBLE", "gr": "DOUBLE", "og": "BOOLEAN", "sp": "DOUBLE", "f": "VARCHAR", "t": "VARCHAR"}
    optional.update({k: "DOUBLE" for k in QUALITY})
    select = ",".join(f'try_cast("{k}" AS {typ}) AS "{k}"' if k in names else f'NULL::{typ} AS "{k}"' for k, typ in optional.items())
    con.execute(f"CREATE OR REPLACE VIEW provider AS SELECT lower(trim(h)) icao24, timestamp::TIMESTAMPTZ timestamp_utc, la::DOUBLE latitude_deg, lo::DOUBLE longitude_deg, filename source_file, file_row_number source_row, {select} FROM raw")
    runway = runways()[0]
    lat, lon = runway["airport_lat"], runway["airport_lon"]
    radius = c["discovery_radius_m"]
    print("ingest: discovering airport-area aircraft", flush=True)
    # WGS84 spherical discovery boundary reproduces the earlier documented 40 km scope.
    radius_sql = f"6371000*2*asin(sqrt(least(1.0,pow(sin(radians(latitude_deg-{lat})/2),2)+cos(radians({lat}))*cos(radians(latitude_deg))*pow(sin(radians(longitude_deg-{lon})/2),2))))"
    con.execute(f"CREATE OR REPLACE TABLE discovery AS SELECT *, {radius_sql} discovery_distance_m FROM provider WHERE latitude_deg BETWEEN ? AND ? AND longitude_deg BETWEEN ? AND ? AND timestamp_utc >= ?::DATE AND timestamp_utc < ?::DATE+INTERVAL 1 DAY", [lat-radius/110000, lat+radius/110000, lon-radius/100000, lon+radius/100000, c["date"], c["date"]])
    con.execute("DELETE FROM discovery WHERE discovery_distance_m> ?", [radius])
    discovery_count, discovery_aircraft = con.execute("SELECT count(*),count(DISTINCT icao24) FROM discovery").fetchone()
    print(f"ingest: {discovery_count} discovery reports / {discovery_aircraft} aircraft; retrieving wider tracks", flush=True)
    # Per-aircraft windows cover all local encounters, including repeat flights.
    # Flight extraction later enforces per-departure maximum duration.
    con.execute("CREATE OR REPLACE TABLE candidates AS SELECT icao24,min(timestamp_utc)-?*INTERVAL 1 SECOND start_time,max(timestamp_utc)+?*INTERVAL 1 SECOND end_time FROM discovery WHERE icao24 IS NOT NULL GROUP BY icao24", [c["pre_roll_s"], c["tracking_duration_s"]])
    con.execute("CREATE OR REPLACE TABLE selected AS SELECT p.* FROM provider p JOIN candidates c ON p.icao24=c.icao24 WHERE (p.timestamp_utc BETWEEN c.start_time AND c.end_time OR p.timestamp_utc IS NULL)")
    print("ingest: wider tracks selected; applying quality and duplicate rules", flush=True)
    extent = c["tracking_radius_m"]
    reject = f"""CASE WHEN timestamp_utc IS NULL THEN 'invalid_timestamp'
      WHEN NOT regexp_full_match(icao24,'[0-9a-f]{{6}}') THEN 'invalid_icao24'
      WHEN latitude_deg IS NULL OR longitude_deg IS NULL OR NOT isfinite(latitude_deg) OR NOT isfinite(longitude_deg) OR abs(latitude_deg)>90 OR abs(longitude_deg)>180 THEN 'invalid_position'
      WHEN {radius_sql}>{extent} THEN 'outside_tracking_envelope'
      WHEN sp>{float(c['max_position_age_s'])} THEN 'stale_position'
      ELSE NULL END"""
    con.execute(f"CREATE OR REPLACE TABLE checked AS SELECT *, {reject} rejection_reason FROM selected")
    con.execute("CREATE OR REPLACE TABLE ranked AS SELECT *,row_number() OVER(PARTITION BY icao24,timestamp_utc ORDER BY np DESC NULLS LAST,sp ASC NULLS LAST,(ag IS NOT NULL) DESC,source_file,source_row) duplicate_rank,first_value(source_file||':'||source_row) OVER(PARTITION BY icao24,timestamp_utc ORDER BY np DESC NULLS LAST,sp ASC NULLS LAST,(ag IS NOT NULL) DESC,source_file,source_row) retained_source FROM checked WHERE rejection_reason IS NULL")
    # No PROJ callbacks from DuckDB threads: transform bounded vectors in Python.
    # pandas is only the small-batch interchange bridge, never the global dataset.
    import pandas as pd
    con.execute("CREATE OR REPLACE TABLE projection_coords(source_file VARCHAR,source_row BIGINT,easting_m DOUBLE,northing_m DOUBLE)")
    reader = con.cursor()
    reader.execute("SELECT source_file,source_row,longitude_deg,latitude_deg FROM ranked WHERE duplicate_rank=1 ORDER BY source_file,source_row")
    projected_count = 0
    while batch := reader.fetchmany(25000):
        frame = pd.DataFrame(batch, columns=["source_file", "source_row", "longitude_deg", "latitude_deg"])
        frame["easting_m"], frame["northing_m"] = TRANSFORM.transform(frame["longitude_deg"].to_numpy(), frame["latitude_deg"].to_numpy())
        con.register("projection_batch", frame[["source_file", "source_row", "easting_m", "northing_m"]])
        con.execute("INSERT INTO projection_coords SELECT * FROM projection_batch")
        con.unregister("projection_batch")
        projected_count += len(batch)
    reader.close()
    con.execute("CREATE OR REPLACE TABLE projected AS SELECT r.*,p.easting_m,p.northing_m FROM ranked r JOIN projection_coords p USING(source_file,source_row) WHERE duplicate_rank=1")
    print("ingest: projection complete; evaluating isolated jumps", flush=True)
    con.execute("""CREATE OR REPLACE TABLE edges AS SELECT *,
      lag(easting_m) OVER w prev_e,lag(northing_m) OVER w prev_n,lag(epoch_ms(timestamp_utc)) OVER w prev_t,
      lead(easting_m) OVER w next_e,lead(northing_m) OVER w next_n,lead(epoch_ms(timestamp_utc)) OVER w next_t
      FROM projected WINDOW w AS(PARTITION BY icao24 ORDER BY timestamp_utc)""")
    threshold = c["max_jump_speed_kt"] * 0.514444
    con.execute(f"""CREATE OR REPLACE TABLE movement AS SELECT *,
      CASE WHEN prev_t IS NOT NULL AND next_t IS NOT NULL AND next_t>prev_t AND
        hypot(easting_m-prev_e,northing_m-prev_n)/greatest((epoch_ms(timestamp_utc)-prev_t)/1000.0,0.001)>{threshold} AND
        hypot(next_e-easting_m,next_n-northing_m)/greatest((next_t-epoch_ms(timestamp_utc))/1000.0,0.001)>{threshold} AND
        hypot(next_e-prev_e,next_n-prev_n)/((next_t-prev_t)/1000.0)<{threshold}
      THEN true ELSE false END isolated_jump FROM edges""")
    audit_sql = """SELECT source_file,source_row,icao24,timestamp_utc,rejection_reason,NULL::VARCHAR retained_source FROM checked WHERE rejection_reason IS NOT NULL
      UNION ALL SELECT source_file,source_row,icao24,timestamp_utc,'duplicate_timestamp',retained_source FROM ranked WHERE duplicate_rank>1
      UNION ALL SELECT source_file,source_row,icao24,timestamp_utc,'isolated_position_jump',NULL FROM movement WHERE isolated_jump"""
    con.execute("COPY (" + audit_sql + " ORDER BY source_file,source_row) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)", [str(out / "observation-audit.parquet")])
    quality_cols = ",".join(f'{k} AS quality_{k}' for k in QUALITY)
    con.execute(f"""COPY (SELECT 1 schema_version,sha256(source_file||':'||source_row) observation_id,
      source_file,source_row,'Wingbits evaluation sample' AS "source",icao24,timestamp_utc,epoch_ms(timestamp_utc) timestamp_ms,
      latitude_deg,longitude_deg,easting_m,northing_m,f callsign_raw,nullif(trim(f),'') callsign,
      ab barometric_altitude_ft,ag geometric_altitude_ft,gs ground_speed_kt,i indicated_airspeed_kt,
      tr track_deg,th true_heading_deg,mh magnetic_heading_deg,br barometric_rate_fpm,gr geometric_rate_fpm,
      og on_ground,sp position_age_s,t message_type,{quality_cols},
      concat_ws(';',CASE WHEN ab IS NULL AND ag IS NULL THEN 'missing_altitude' END,
      CASE WHEN gs IS NULL THEN 'missing_ground_speed' END,
      CASE WHEN ab < -2000 OR ab>70000 THEN 'altitude_out_of_range' END,
      CASE WHEN prev_t IS NOT NULL AND hypot(easting_m-prev_e,northing_m-prev_n)/greatest((epoch_ms(timestamp_utc)-prev_t)/1000.0,0.001)>{threshold} THEN 'implausible_movement' END) quality_flags
      FROM movement WHERE NOT isolated_jump ORDER BY icao24,timestamp_utc,source_file,source_row)
      TO ? (FORMAT PARQUET, COMPRESSION ZSTD)""", [str(out / "observations.parquet")])
    reasons = dict(con.execute("SELECT rejection_reason,count(*) FROM (" + audit_sql + ") GROUP BY rejection_reason ORDER BY rejection_reason").fetchall())
    selected_count = con.execute("SELECT count(*) FROM selected").fetchone()[0]
    retained = con.execute("SELECT count(*) FROM read_parquet(?)", [str(out / "observations.parquet")]).fetchone()[0]
    if retained + sum(reasons.values()) != selected_count: raise AssertionError("Observation accounting mismatch")
    report = {"schema_version": 1, "cache_key": pre["cache_key"], "cache_hit": False, "global_rows_from_footers": pre["total_rows_from_footers"], "discovery_reports": discovery_count, "discovery_aircraft": discovery_aircraft, "selected_reports": selected_count, "retained_reports": retained, "audit_reasons": reasons, "audit_scope": "Selected aircraft/time windows, before tracking-envelope and quality filters; not a global invalid-record audit", "observation_sha256": file_hash(out / "observations.parquet"), "mapping_semantics": "Wingbits identities; readsb convention units; provider-semantic assumption documented"}
    con.close()
    dump(report_path, report)
    return report
