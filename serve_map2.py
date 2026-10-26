"""Serve only Map 2 on this computer. No ingest, backend or external connection."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
import sys,threading,webbrowser
root=Path(__file__).parent;url='http://127.0.0.1:8765/map-2/'
class Handler(SimpleHTTPRequestHandler):
    extensions_map={**SimpleHTTPRequestHandler.extensions_map,'.mjs':'text/javascript','.js':'text/javascript'}
server=ThreadingHTTPServer(('127.0.0.1',8765),partial(Handler,directory=str(root)))
if '--open' in sys.argv:threading.Timer(1,lambda:webbrowser.open(url)).start()
print('Map 2: '+url+'  |  Ctrl+C to stop.',flush=True)
try:server.serve_forever()
except KeyboardInterrupt:server.server_close()
