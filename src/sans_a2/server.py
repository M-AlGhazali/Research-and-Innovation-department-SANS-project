"""Local allowlisted viewer assets and explicit traffic exports; no raw-input serving."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlsplit
from .common import ROOT

def handler_for(c):
    viewer = (Path(c["output_dir"]) / "viewer").resolve()
    class Handler(SimpleHTTPRequestHandler):
        extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".mjs": "text/javascript", ".js": "text/javascript"}
        def translate_path(self, request):
            path = unquote(urlsplit(request).path)
            if path.startswith("/observed-data/"):
                base, rel = viewer, path[len("/observed-data/"):]
                target = (base / rel).resolve()
                if not target.is_relative_to(base) or target.suffix != ".json": return str(viewer / "__not_found__")
                return str(target)
            if path in ("/", "/map-2", "/map-2/"): path = "/map-2/index.html"
            base = ROOT / "map-2"
            if not path.startswith("/map-2/"): return str(viewer / "__not_found__")
            target = (ROOT / path.lstrip("/")).resolve()
            if not target.is_relative_to(base) or target.suffix.lower() not in {".html", ".js", ".mjs", ".css", ".json", ".svg", ".jpg"}: return str(viewer / "__not_found__")
            return str(target)
        def list_directory(self, path):
            self.send_error(404)
            return None
        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()
    return Handler

def serve(c, port=8765):
    server = ThreadingHTTPServer(("127.0.0.1", port), handler_for(c))
    print(f"Local viewer: http://127.0.0.1:{port}/map-2/ | Ctrl+C stops the server", flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
