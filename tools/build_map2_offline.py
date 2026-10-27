"""Build a directly openable Map 2 with embedded modules, data, CSS and logo."""
from pathlib import Path
import base64
import json
import re

ROOT = Path(__file__).resolve().parents[1] / 'map-2'

def data_url(text, mime='text/javascript'):
    return f'data:{mime};base64,' + base64.b64encode(text.encode('utf-8')).decode('ascii')

def build():
    read = lambda name: (ROOT / name).read_text(encoding='utf-8')
    modules = {
        'three-core': read('vendor/three.core.js'),
        'three': read('vendor/three.module.js').replace("'./three.core.js'", "'three-core'"),
        'orbit-controls': read('vendor/OrbitControls.js'),
        'flight-model': read('flight-model.mjs'),
        'observed-model': read('observed-model.mjs'),
        'observed-layer': read('observed-layer.mjs').replace("'./observed-model.mjs'", "'observed-model'"),
    }
    imports = {name: data_url(source) for name, source in modules.items()}
    html = read('index.html').replace('<link rel="stylesheet" href="observed.css">', '<style>' + read('observed.css') + '</style>')
    html = re.sub(r'<link rel="stylesheet" href="studio\.css[^\"]*">',
                  lambda _: '<style>' + read('studio.css') + '</style>', html)
    html = re.sub(r'<script type="importmap">.*?</script>',
                  lambda _: '<script type="importmap">' + json.dumps({'imports': imports}) + '</script>', html)
    html = html.replace('src="sans-logo-light.svg"', 'src="' + data_url(read('sans-logo-light.svg'), 'image/svg+xml') + '"')
    studio = read('studio.js').replace("'./vendor/OrbitControls.js'", "'orbit-controls'").replace("'./flight-model.mjs'", "'flight-model'").replace("'./observed-layer.mjs'", "'observed-layer'")
    old = "const response=await fetch('./data.json');if(!response.ok)throw new Error('Map dataset could not be loaded');data=await response.json();"
    assert old in studio, 'Dataset loader changed; update the offline build.'
    studio = studio.replace(old, "data=JSON.parse(document.getElementById('embedded-map-data').textContent);")
    studio = studio.replace('Use “Start Map 2.cmd” and a browser with WebGL enabled.', 'Open this file in Chrome or Edge with WebGL enabled.')
    dataset = json.dumps(json.loads(read('data.json')), separators=(',', ':')).replace('<', '\\u003c')
    scripts = '<script type="application/json" id="embedded-map-data">' + dataset + '</script><script type="module">' + studio.replace('</script', '<\\/script') + '</script>'
    html = re.sub(r'<script type="module" src="studio\.js[^\"]*"></script>', lambda _: scripts, html)
    assert '<script type="module" src=' not in html
    assert "fetch('./data.json')" not in html
    output = ROOT / 'Open Map 2.html'
    output.write_text(html, encoding='utf-8')
    print(f'Built: {output} ({output.stat().st_size:,} bytes)')

if __name__ == '__main__':
    build()

