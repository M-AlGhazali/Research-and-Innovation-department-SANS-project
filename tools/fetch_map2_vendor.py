from pathlib import Path
import urllib.request
root=Path(__file__).resolve().parents[1]/'map-2'/'vendor';root.mkdir(parents=True,exist_ok=True)
files={'three.module.js':'build/three.module.js','three.core.js':'build/three.core.js','OrbitControls.js':'examples/jsm/controls/OrbitControls.js','LICENSE.txt':'LICENSE'}
for dst,src in files.items():
    url='https://cdn.jsdelivr.net/npm/three@0.180.0/'+src
    with urllib.request.urlopen(url,timeout=60) as response:(root/dst).write_bytes(response.read())
    print(dst,flush=True)
