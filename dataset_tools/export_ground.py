"""Read-only export of the retained Map 1 GeoPackage, never the A2-A6 folders."""
from pathlib import Path
import csv,json,hashlib,math
from qgis.core import *
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(__file__).parent/'archive/expanded_phase1_2026-10-26'
OUT.mkdir(parents=True,exist_ok=True)
app=QgsApplication([],False);app.initQgis()
p=QgsProject.instance();src=QgsCoordinateReferenceSystem('EPSG:32637');dst=QgsCoordinateReferenceSystem('EPSG:4326')
tr=QgsCoordinateTransform(src,dst,p)
cols=['ground_feature_id','layer_name','source_feature_id','name','kind','reference','source_id','upstream_source_id','source_date','data_class','geometry_type','geometry_crs','geometry_wkt','geometry_wgs84_wkt','centroid_longitude_deg','centroid_latitude_deg','area_projected_m2','length_projected_m','geometry_valid','mapped_height_raw','mapped_levels_raw','raw_osm_tags_json','source_note']
counts={}
with (OUT/'11_ground_features.csv').open('w',encoding='utf-8',newline='') as stream:
 w=csv.DictWriter(stream,fieldnames=cols);w.writeheader()
 import sqlite3
 db=sqlite3.connect(f'file:{(ROOT/"map-1/OEJN-ground.gpkg").as_posix()}?mode=ro',uri=True)
 tables=[r[0] for r in db.execute('select table_name from gpkg_contents where data_type="features" order by table_name')];db.close()
 for table in tables:
  layer=QgsVectorLayer(str(ROOT/'map-1/OEJN-ground.gpkg')+'|layername='+table,table,'ogr');assert layer.isValid()
  counts[table]=0
  for f in layer.getFeatures():
   g=f.geometry();geo=QgsGeometry(g);geo.transform(tr);c=geo.centroid().asPoint()
   attrs={k:str(f[k]) if f[k] is not None else '' for k in ['name','kind','reference','source_id','source_date','note']}
   tags={}
   try:tags=json.loads(attrs['note'])
   except (ValueError,TypeError):pass
   official=table.startswith('runway_');derived=official and table!='runway_ends'
   row=dict(ground_feature_id=f'G_{table}_{f.id()}',layer_name=table,source_feature_id=attrs['source_id'],name=attrs['name'],kind=attrs['kind'],reference=attrs['reference'],source_id='SRC_GPKG',upstream_source_id='SRC_AIP' if official else 'SRC_OSM',source_date=attrs['source_date'],data_class='derived_runway_reference' if derived else 'published_threshold_reference' if official else 'community_mapped_context',geometry_type=QgsWkbTypes.displayString(g.wkbType()),geometry_crs='EPSG:32637',geometry_wkt=g.asWkt(8),geometry_wgs84_wkt=geo.asWkt(10),centroid_longitude_deg=round(c.x(),10),centroid_latitude_deg=round(c.y(),10),area_projected_m2=round(g.area(),3) if layer.geometryType()==Qgis.GeometryType.Polygon else '',length_projected_m=round(g.length(),3) if layer.geometryType()==Qgis.GeometryType.Line else '',geometry_valid=g.isGeosValid(),mapped_height_raw=tags.get('height',''),mapped_levels_raw=tags.get('building:levels',''),raw_osm_tags_json=json.dumps(tags,ensure_ascii=False,separators=(',',':')) if tags else '',source_note='' if tags else attrs['note'])
   w.writerow(row);counts[table]+=1
print(json.dumps(counts),flush=True)
assert sum(counts.values())==20008
from a1_transcription import COORDS,ROWS
positions={}
for line in COORDS.strip().splitlines():
 name,*v=line.split();v=list(map(float,v));positions[name]=QgsPointXY(v[3]+v[4]/60+v[5]/3600,v[0]+v[1]/60+v[2]/3600)
d=QgsDistanceArea();d.setSourceCrs(dst,p.transformContext());d.setEllipsoid('WGS84')
geodesy={}
for block in ROWS.values():
 fixes=[line.split()[0] for line in block.strip().splitlines()]
 for a,b in zip(fixes,fixes[1:]):
  geodesy[a+'>'+b]={'distance_m':round(d.measureLine(positions[a],positions[b]),6),'bearing_deg':round(math.degrees(d.bearing(positions[a],positions[b]))%360,8)}
(Path(__file__).parent/'geodesy.json').write_text(json.dumps(geodesy,indent=2))
p.clear()
