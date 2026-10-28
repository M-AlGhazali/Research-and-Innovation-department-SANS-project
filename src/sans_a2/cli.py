import argparse
import importlib.metadata
from pathlib import Path
import threading
import time
import platform
import psutil
from .common import config, dump, load, ALGORITHM_VERSION, digest
from .reference import export_reference
from .ingest import inventory, ingest
from .flights import extract
from .matching import match
from .export import export_viewer
from .validation import validate
from .server import serve

def measured(name, fn, c):
    start = time.perf_counter()
    process = psutil.Process()
    peak = [process.memory_info().rss]
    stopped = threading.Event()
    def sample():
        while not stopped.wait(.05): peak[0] = max(peak[0], process.memory_info().rss)
    thread = threading.Thread(target=sample, daemon=True)
    thread.start()
    try: result = fn()
    finally: stopped.set(); thread.join()
    record = {"stage": name, "elapsed_s": round(time.perf_counter()-start, 3), "peak_process_rss_bytes": max(peak[0], process.memory_info().rss), "result": result}
    manifest_path = Path(c["output_dir"]) / "run-manifest.json"
    manifest = load(manifest_path) if manifest_path.exists() else {"schema_version": 1, "stages": {}}
    manifest.update({"algorithm": ALGORITHM_VERSION, "config": c, "config_sha256": digest(c), "python": platform.python_version(), "dependencies": {k: importlib.metadata.version(k) for k in ("duckdb", "pyproj", "numpy", "pandas", "pytz", "psutil", "jsonschema")}, "interpretation": "Local observational feasibility; heuristic geometric labels, no operational or environmental claims"})
    manifest["stages"][name] = record
    dump(manifest_path, manifest)
    print(f"{name}: {result} ({record['elapsed_s']:.1f}s; peak RSS {record['peak_process_rss_bytes']/1024**2:.1f} MiB)", flush=True)
    return result

def main():
    parser = argparse.ArgumentParser(description="Reproducible local OEJN A2 pipeline")
    parser.add_argument("command", choices=["reference", "preflight", "ingest", "flights", "match", "export", "validate", "run", "serve"])
    parser.add_argument("--config", default=str(Path(__file__).resolve().parents[2] / "config/oejn-2026-10-01.json"))
    parser.add_argument("--force", action="store_true", help="Rebuild observation cache")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    c = config(args.config)
    if args.command == "serve": return serve(c, args.port)
    if args.command == "run":
        dump(Path(c["output_dir"]) / "run-manifest.json", {"schema_version": 1, "stages": {}})
    operations = {"reference": export_reference, "preflight": lambda: inventory(c), "ingest": lambda: ingest(c, args.force), "flights": lambda: extract(c), "match": lambda: match(c), "export": lambda: export_viewer(c), "validate": lambda: validate(c)}
    for command in (["reference", "ingest", "flights", "match", "export", "validate"] if args.command == "run" else [args.command]):
        if command in {"flights", "match", "export", "validate"}:
            out = Path(c["output_dir"])
            if not (out / "ingest-report.json").exists() or load(out / "ingest-report.json")["cache_key"] != inventory(c)["cache_key"]:
                raise ValueError("Observation inputs/configuration/implementation changed; run ingest or run before this stage")
            from .common import file_hash
            if file_hash(out / "observations.parquet") != load(out / "ingest-report.json")["observation_sha256"]:
                raise ValueError("Observation output changed; rebuild with ingest --force")
        if command in {"match", "export", "validate"}:
            if digest(load(out / "flights.json")) != load(out / "flight-report.json")["content_sha256"]:
                raise ValueError("Flight output changed; rerun flights")
        if command in {"export", "validate"}:
            if digest(load(out / "matches.json")) != load(out / "match-report.json")["content_sha256"]:
                raise ValueError("Match output changed; rerun match")
        measured(command, operations[command], c)
