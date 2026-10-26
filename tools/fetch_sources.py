from pathlib import Path
import urllib.request, urllib.parse, json
root=Path(__file__).resolve().parents[1]
(root/'sources').mkdir(exist_ok=True)
query='''[out:json][timeout:180];(nwr["aeroway"](21.59,39.08,21.76,39.23);way["building"](21.59,39.08,21.76,39.23);way["highway"](21.59,39.08,21.76,39.23);way["railway"](21.59,39.08,21.76,39.23);way["landuse"](21.59,39.08,21.76,39.23);way["natural"](21.59,39.08,21.76,39.23);way["leisure"](21.59,39.08,21.76,39.23);node["place"](21.59,39.08,21.76,39.23););out body geom;'''
(root/'sources'/'overpass-query.txt').write_text(query)
if not (root/'sources'/'osm.json').exists():
    req=urllib.request.Request('https://overpass-api.de/api/interpreter', data=urllib.parse.urlencode({'data':query}).encode(),headers={'User-Agent':'OEJN-student-ground-map/1.0'})
    with urllib.request.urlopen(req,timeout=240) as response: data=response.read()
    obj=json.loads(data)
    if obj.get('remark'): raise RuntimeError(obj['remark'])
    (root/'sources'/'osm.json').write_bytes(data)
    print('OSM elements',len(obj['elements']),flush=True)
url='https://aimss.sans.com.sa/assets/FileManagerFiles/AIRAC%20AIP%20AMDT%2010_26_2026_10_01/eAIP/AD%202%20OEJN%20JEDDAH%20-%20KING%20ABDULAZIZ%20INTERNATIONAL-en-US.html'
if not (root/'sources'/'OEJN-AIP-2026-10-01.html').exists():
    with urllib.request.urlopen(url,timeout=60) as response: (root/'sources'/'OEJN-AIP-2026-10-01.html').write_bytes(response.read())
print('Sources retained',flush=True)
