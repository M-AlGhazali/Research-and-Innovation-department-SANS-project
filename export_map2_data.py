from pathlib import Path
import json,hashlib
from qgis.core import *
from map2_procedures import COORDS,ROUTES,WARNINGS
ROOT=Path(__file__).parent;OUT=ROOT/'map-2';OUT.mkdir(exist_ok=True)
app=QgsApplication([],False);app.initQgis();project=QgsProject.instance()
crs=QgsCoordinateReferenceSystem('EPSG:32637');tr=QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'),crs,project)
origin=tr.transform(QgsPointXY(39.154,21.68))
def world(p):return [round((p.x()-origin.x())/1000,6),round(-(p.y()-origin.y())/1000,6)]
fixes={}
for row in COORDS.strip().splitlines():
    name,*raw=row.split();v=list(map(int,raw));lat=v[0]+v[1]/60+v[2]/3600;lon=v[3]+v[4]/60+v[5]/3600
    fixes[name]={'lat':lat,'lon':lon,'rawDms':raw,'xz':world(tr.transform(QgsPointXY(lon,lat)))}
pages={'34C':[114,115],'34L':[110,111],'34R':[118,119]}
routes=[]
for runway,records in ROUTES.items():
    for name,spec in records.items():
        legs=[]
        for i,token in enumerate(spec.split()):
            parts=token.split('|');fix=parts[0];assert fix in fixes
            legs.append({'fix':fix,'altitude':parts[1] if len(parts)>1 else '', 'speed':parts[2] if len(parts)>2 else '', 'path':'CF' if i==0 or (runway!='34C' and i==1) else 'TF','flyOver':i==0 and runway!='34C'})
        routes.append({'id':name.replace(' ','-'),'name':name,'runway':runway,'legs':legs,'pages':pages[runway],'sheetDate':'2026-09-17','amendment':'AIP AMDT 10/26','warning':WARNINGS.get(name,'')})
ground=[];runways=[]
for key in ['airport_boundary','land_use','water','green_spaces','buildings','roads','railway','taxiways','aprons_and_stopways','terminals_and_hangars','coastline','runway_surfaces','runway_centerlines','runway_ends']:
    l=QgsVectorLayer(str(ROOT/'map-1/OEJN-ground.gpkg')+'|layername='+key,key,'ogr');assert l.isValid()
    for f in l.getFeatures():
        g=f.geometry()
        if key=='runway_centerlines':
            coords=g.asPolyline();start,end=f['name'].split(' / ')
            runways.append({'id':start,'end':end,'start':world(coords[0]),'finish':world(coords[-1]),'lengthKm':g.length()/1000,'color':{'34C':'#50e1df','34L':'#f78fb5','34R':'#efbd64'}[start]})
            continue
        if key=='runway_ends':continue
        # Simplification is confined to display geometry. Map 1 retains the original editable data.
        g=g.simplify(3 if key in ('roads','buildings') else 1)
        parts=g.asGeometryCollection() if g.isMultipart() else [g]
        for part in parts:
            if part.type()==Qgis.GeometryType.Polygon:coords=[[world(p) for p in ring] for ring in part.asPolygon()];kind='polygon'
            elif part.type()==Qgis.GeometryType.Line:coords=[world(p) for p in part.asPolyline()];kind='line'
            else:continue
            ground.append({'layer':key,'name':str(f['name']),'kind':kind,'coords':coords})
data={'origin':{'lat':21.68,'lon':39.154,'utm':[origin.x(),origin.y()]},'crs':'EPSG:32637','units':'kilometres','fixes':fixes,'routes':routes,'runways':runways,'ground':ground,'notes':{'animation':'Illustrative timing, take-off position and climb profile. Exact published fix positions; straight connectors do not reconstruct CF/TF turn geometry.','heights':'Flat ground; building footprints have illustrative 12 m/20 m massing. No surveyed terrain or building heights.','flightLevels':'FL values retain their original labels; nominal hundreds of feet used only for the illustrative animation, without a QNH conversion.'}}
(OUT/'data.json').write_text(json.dumps(data,separators=(',',':'),ensure_ascii=False),encoding='utf-8')
(OUT/'reference').mkdir(exist_ok=True)
manifest=[]
for p in (ROOT/'sources/map-2').glob('*.pdf'):
    manifest.append({'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(OUT/'reference/manifest.json').write_text(json.dumps(manifest,indent=2))
assert len(routes)==24 and len(runways)==3
print(json.dumps({'routes':len(routes),'runways':len(runways),'fixes':len(fixes),'groundParts':len(ground),'sourceWarnings':WARNINGS},indent=2),flush=True)
