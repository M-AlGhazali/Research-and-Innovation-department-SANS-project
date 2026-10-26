"""Build the OEJN ground atlas from retained OSM and SANS source records using PyQGIS."""
from pathlib import Path
import json, math, html, collections
from qgis.core import *
from qgis.PyQt.QtCore import QVariant, Qt
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'map-1'
OUT.mkdir(exist_ok=True)
app=QgsApplication([],False); app.initQgis()
for fontfile in ['segoeui.ttf','segoeuib.ttf','arial.ttf','arialbd.ttf']:
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+fontfile)
project=QgsProject.instance()
project.setTitle('OEJN | Jeddah Airport Ground Atlas')
crs=QgsCoordinateReferenceSystem('EPSG:32637')
project.setCrs(crs)
project.setBackgroundColor(QColor('#f8f7f2'))
project.setFilePathStorage(Qgis.FilePathType.Relative)
transform=QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'),crs,project)
source=json.loads((ROOT/'sources/osm.json').read_text(encoding='utf-8'))
STAMP=source.get('osm3s',{}).get('timestamp_osm_base','unknown')
layers={}
schema=[('name',QVariant.String),('kind',QVariant.String),('reference',QVariant.String),('source',QVariant.String),('source_id',QVariant.String),('source_date',QVariant.String),('note',QVariant.String)]
def layer(key,kind):
    if key not in layers:
        l=QgsVectorLayer(kind+'?crs=EPSG:32637',key,'memory')
        l.dataProvider().addAttributes([QgsField(n,t) for n,t in schema]); l.updateFields(); layers[key]=l
    return layers[key]
def add(key,kind,g,name,typ,ref='',sid='',note='',src='OpenStreetMap contributors / ODbL',date=STAMP,geo=True):
    if g.isEmpty(): return
    if geo: g.transform(transform)
    l=layer(key,kind); f=QgsFeature(l.fields()); f.setGeometry(g)
    f.setAttributes([name,typ,ref,src,str(sid),date,note]); l.dataProvider().addFeatures([f])
def points(geo): return [QgsPointXY(p['lon'],p['lat']) for p in geo if 'lon' in p]
def stitch(seqs):
    result=[]
    while seqs:
        ring=seqs.pop()[:]
        while ring[0]!=ring[-1]:
            found=False
            for i,s in enumerate(seqs):
                if ring[-1]==s[0]: ring+=s[1:]
                elif ring[-1]==s[-1]: ring+=s[-2::-1]
                elif ring[0]==s[-1]: ring=s[:-1]+ring
                elif ring[0]==s[0]: ring=s[:0:-1]+ring
                else: continue
                seqs.pop(i); found=True; break
            if not found: break
        if len(ring)>3 and ring[0]==ring[-1]: result.append(ring)
    return result
def geometry(e,polygon):
    if e['type']=='node': return QgsGeometry.fromPointXY(QgsPointXY(e['lon'],e['lat']))
    if e['type']=='way':
        p=points(e.get('geometry',[]))
        if len(p)<2:return None
        if polygon and len(p)>3 and p[0]==p[-1]: return QgsGeometry.fromPolygonXY([p])
        return QgsGeometry.fromPolylineXY(p)
    outer=stitch([points(m['geometry']) for m in e.get('members',[]) if m.get('role') in ('outer','') and m.get('geometry')])
    inner=stitch([points(m['geometry']) for m in e.get('members',[]) if m.get('role')=='inner' and m.get('geometry')])
    polys=[]
    for r in outer:
        pg=QgsGeometry.fromPolygonXY([r]); polys.append([r]+[i for i in inner if pg.contains(QgsGeometry.fromPointXY(i[0]))])
    return QgsGeometry.fromMultiPolygonXY(polys) if polys else None

# Multipolygon member ways are represented by their parent, preventing duplicate airport boundaries.
member_ids={m['ref'] for e in source['elements'] if e['type']=='relation' and e.get('tags',{}).get('type')=='multipolygon' for m in e.get('members',[]) if m['type']=='way'}
for e in source['elements']:
    t=e.get('tags',{}); a=t.get('aeroway',''); key=None; poly=False
    if a=='runway': continue  # All runway displays derive from the versioned AIP thresholds below.
    if a=='aerodrome': key='Airport boundary'; poly=True
    elif a=='taxiway': key='Taxiways'
    elif a in ('apron','stopway'): key='Aprons and stopways'; poly=True
    elif a in ('terminal','hangar') or t.get('building') in ('terminal','hangar'): key='Terminals and hangars'; poly=True
    elif a in ('parking_position','gate','tower','windsock','helipad','jet_bridge'): key='Airfield facilities'
    elif 'building' in t: key='Buildings'; poly=True
    elif 'highway' in t: key='Roads'
    elif 'railway' in t: key='Railway'
    elif t.get('natural') in ('water','wetland') or t.get('landuse') in ('reservoir','basin'): key='Water'; poly=True
    elif t.get('natural')=='coastline': key='Coastline'
    elif t.get('leisure') in ('park','garden','golf_course','pitch') or t.get('landuse') in ('grass','forest','recreation_ground','meadow') or t.get('natural') in ('scrub','wood'): key='Green spaces'; poly=True
    elif 'landuse' in t: key='Land use'; poly=True
    elif 'place' in t: key='Places'
    if not key: continue
    if e['type']=='way' and e['id'] in member_ids and key=='Airport boundary': continue
    g=geometry(e,poly)
    if g is None: continue
    gt=QgsWkbTypes.geometryType(g.wkbType())
    kind=['Point','LineString','Polygon'][int(gt)] if int(gt)<3 else None
    if not kind:continue
    if key in ('Airfield facilities','Aprons and stopways','Airport boundary'):
        if kind=='Point' and key=='Airport boundary':key='Airport reference points'
        elif key=='Airfield facilities':key+=' '+kind
    if key in layers and QgsWkbTypes.geometryType(layers[key].wkbType())!=gt: key+=' '+kind
    typ=a or t.get('building') or t.get('highway') or t.get('railway') or t.get('landuse') or t.get('natural') or t.get('leisure') or t.get('place','')
    name=t.get('name:en') or t.get('name') or t.get('ref') or typ.replace('_',' ').title()
    add(key,kind,g,name,typ,t.get('ref',''),e['type']+'/'+str(e['id']),json.dumps(t,ensure_ascii=False))

AIP='SANS eAIP AD 2.12 / AIRAC AMDT 10/26'
ends={'34C':(21.661181,39.164919,28.60),'16C':(21.695072,39.151547,21.10),'34L':(21.670561,39.139594,15.50),'16R':(21.702758,39.126883,15.49),'34R':(21+39/60+59.57/3600,39+10/60+49.79/3600,49.60),'16L':(21+42/60+1.59/3600,39+10/60+1.67/3600,30.60)}
colors={'34C / 16C':'#008c95','34L / 16R':'#d45883','34R / 16L':'#b58329'}
for start,end,length in [('34C','16C',4000),('34L','16R',3800),('34R','16L',4000)]:
    name=start+' / '+end
    ps=[transform.transform(QgsPointXY(ends[k][1],ends[k][0])) for k in (start,end)]
    line=QgsGeometry.fromPolylineXY(ps)
    # Flat-ended 30 m half-width buffer is a cartographic approximation, not surveyed pavement.
    surf=line.buffer(30,8,Qgis.EndCapStyle.Flat,Qgis.JoinStyle.Miter,2)
    note=f'{length} x 60 m published dimensions. Threshold-derived 30 m half-width buffer; not surveyed pavement. '+('Study focus.' if start!='34R' else 'Airport context; outside initial 34C/34L study focus.')
    add('Runway surfaces','Polygon',surf,name,'runway',name,note=note,src=AIP,date='2026-10-01',geo=False)
    add('Runway centerlines','LineString',line,name,'centerline',name,note=note,src=AIP,date='2026-10-01',geo=False)
    for k,p in zip((start,end),ps):
        lat,lon,elev=ends[k]
        add('Runway ends','Point',QgsGeometry.fromPointXY(p),k,'threshold',name,note=f'{lat:.8f} N, {lon:.8f} E; threshold elevation {elev:.2f} ft AMSL.',src=AIP,date='2026-10-01',geo=False)

palette={'Airport boundary':('#eeeade','#c7c0af'),'Aprons and stopways':('#dcdcd4','#bdbdb4'),'Terminals and hangars':('#888a94','#626573'),'Buildings':('#e0dcd3','#d0ccc3'),'Water':('#c6e3ed','#a8cedc'),'Green spaces':('#dce6bd','#c3d49b'),'Land use':('#efede4','#e7e3d7')}
order=['Runway ends','Runway centerlines','Runway surfaces','Airfield facilities Point','Airfield facilities LineString','Airfield facilities Polygon','Terminals and hangars','Taxiways','Aprons and stopways','Railway','Roads','Places','Buildings','Green spaces','Water','Coastline','Airport boundary','Land use']
def label(l,field,size,color,buffer=True):
    settings=QgsPalLayerSettings(); settings.fieldName=field
    fmt=QgsTextFormat(); fmt.setFont(QFont('Segoe UI',size)); fmt.setSize(size); fmt.setColor(QColor(color))
    if buffer:
        buf=QgsTextBufferSettings();buf.setEnabled(True);buf.setSize(.8);buf.setColor(QColor('#faf9f4'));fmt.setBuffer(buf)
    settings.setFormat(fmt)
    if l.geometryType()==Qgis.GeometryType.Point: settings.placement=Qgis.LabelPlacement.OrderedPositionsAroundPoint;settings.dist=2
    l.setLabeling(QgsVectorLayerSimpleLabeling(settings));l.setLabelsEnabled(True)

gpkg=OUT/'OEJN-ground.gpkg'
if gpkg.exists(): raise RuntimeError('Output exists: archive map-1 before regenerating to preserve edits.')
saved={}
for i,(key,l) in enumerate(layers.items()):
    opt=QgsVectorFileWriter.SaveVectorOptions();opt.driverName='GPKG';opt.layerName=key.lower().replace(' ','_');opt.fileEncoding='UTF-8'
    opt.actionOnExistingFile=QgsVectorFileWriter.CreateOrOverwriteFile if i==0 else QgsVectorFileWriter.CreateOrOverwriteLayer
    if l.geometryType()==Qgis.GeometryType.Polygon: opt.forceMulti=True
    result=QgsVectorFileWriter.writeAsVectorFormatV3(l,str(gpkg),project.transformContext(),opt)
    if result[0]!=QgsVectorFileWriter.NoError:raise RuntimeError(str(result))
    v=QgsVectorLayer(str(gpkg)+'|layername='+opt.layerName,key,'ogr');assert v.isValid()
    if key=='Runway surfaces':
        cats=[QgsRendererCategory(n,QgsFillSymbol.createSimple({'color':c,'outline_color':c,'outline_width':'0.15'}),n) for n,c in colors.items()]
        v.setRenderer(QgsCategorizedSymbolRenderer('name',cats))
    elif key=='Runway ends':
        cats=[QgsRendererCategory(n,QgsMarkerSymbol.createSimple({'name':'circle','color':c,'outline_color':'#ffffff','size':'2.3','outline_width':'.35'}),n) for n,c in colors.items()]
        v.setRenderer(QgsCategorizedSymbolRenderer('reference',cats));label(v,'name',11,'#263c47')
    elif v.geometryType()==Qgis.GeometryType.Polygon:
        fill,stroke=palette.get(key,('#e2dfd6','#bdb9af'));v.renderer().setSymbol(QgsFillSymbol.createSimple({'color':fill,'outline_color':stroke,'outline_width':'.15'}))
    elif v.geometryType()==Qgis.GeometryType.Line:
        color,width={'Taxiways':('#b3b6ae',.65),'Roads':('#d1cbbc',.35),'Railway':('#9b8f84',.4),'Coastline':('#8bbac9',.4),'Runway centerlines':('#ffffff',.2)}.get(key,('#aaa79d',.3))
        v.renderer().setSymbol(QgsLineSymbol.createSimple({'line_color':color,'line_width':str(width),'line_style':'dash' if key in ('Runway centerlines','Railway') else 'solid'}))
    else:v.renderer().setSymbol(QgsMarkerSymbol.createSimple({'name':'circle','color':'#8c8195','size':'1.4','outline_style':'no'}))
    if key=='Terminals and hangars':label(v,'name',7,'#4a4d5a')
    if key=='Places':label(v,'name',8,'#90887a')
    if key=='Taxiways':
        label(v,'reference',7,'#70786e');v.labeling().settings()
        v.setLabelsEnabled(False) # Can be enabled for detailed inspection without cluttering overview.
    v.setDisplayExpression('"name"')
    v.setMapTipTemplate('<div style="font-family:Segoe UI;padding:10px;min-width:230px"><h3>[% "name" %]</h3><p>[% "kind" %] &middot; [% "reference" %]</p><p>[% "source" %]<br>[% "source_date" %]</p><p>[% "note" %]</p></div>')
    meta=v.metadata();meta.setTitle(key);meta.setAbstract('OEJN ground context. OSM geometry is community mapped, not a certified airport survey. AIP-derived runway surfaces are approximate buffers.');meta.setRights(['OpenStreetMap contributors: ODbL 1.0' if not key.startswith('Runway') else 'SANS AIP: source attribution retained']);v.setMetadata(meta)
    saved[key]=v
for key in reversed(order+[k for k in saved if k not in order]):
    if key in saved:project.addMapLayer(saved[key])
visible=[saved[k] for k in order if k in saved]+[saved[k] for k in saved if k not in order]
extent=QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'),crs,project).transformBoundingBox(QgsRectangle(39.095,21.625,39.205,21.735))
project.viewSettings().setDefaultViewExtent(QgsReferencedRectangle(extent,crs))
project.setFileName(str(OUT/'OEJN-ground-atlas.qgz'))
project.writeEntry('Gui','MapTips',True)

layout=QgsPrintLayout(project);layout.initializeDefaults();layout.setName('Ground atlas | A3 landscape')
layout.pageCollection().pages()[0].setPageSize('A3',QgsLayoutItemPage.Landscape)
def text(x,y,w,h,value,size=10,color='#253d46',bold=False):
    item=QgsLayoutItemLabel(layout);item.setText(value);f=QFont('Segoe UI',size);f.setBold(bold);item.setFont(f);item.setFontColor(QColor(color));layout.addLayoutItem(item);item.attemptMove(QgsLayoutPoint(x,y));item.attemptResize(QgsLayoutSize(w,h));return item
text(12,8,120,8,'SANS  /  RESEARCH & INNOVATION',10,'#72858a',True)
text(12,21,380,17,'Jeddah Airport | Ground atlas',27,'#203943',True)
text(12,39,380,10,'KING ABDULAZIZ INTERNATIONAL  /  OEJN     •     MAP 01',10,'#6d8086')
mapitem=QgsLayoutItemMap(layout);layout.addLayoutItem(mapitem);mapitem.attemptMove(QgsLayoutPoint(105,55));mapitem.attemptResize(QgsLayoutSize(302,222));mapitem.setCrs(crs);mapitem.setLayers(visible);mapitem.setKeepLayerSet(True);mapitem.zoomToExtent(extent);mapitem.setBackgroundColor(QColor('#f8f7f2'))
text(12,58,85,10,'THE AIRFIELD',15,'#263e47',True)
text(12,73,86,23,'Three physical runways.\nSix named runway ends.\nGround context in editable layers.',10,'#62777d')
y=108
for name,c in colors.items():
    text(12,y,85,9,'━  '+name,15,c,True);y+=11
    text(12,y,85,8,('4,000' if '34L' not in name else '3,800')+' × 60 m · published dimensions',8,'#718185');y+=17
text(12,198,85,9,'GROUND LAYERS',10,'#263e47',True)
text(12,210,87,42,'Taxiways / aprons / terminals\nBuildings / roads / railway\nGreen spaces / water / land use\nAirfield facilities / airport boundary',9,'#62777d')
text(12,255,87,24,'34C and 34L: initial study focus.\n34R: supporting airport context.\nN ↑   WGS 84 / UTM zone 37N',8,'#718185')
scale=QgsLayoutItemScaleBar(layout);scale.setStyle('Single Box');scale.setLinkedMap(mapitem);scale.applyDefaultSize();scale.setUnits(Qgis.DistanceUnit.Kilometers);scale.setUnitsPerSegment(1);scale.setNumberOfSegments(2);scale.setNumberOfSegmentsLeft(0);scale.setUnitLabel('km');scale.setFont(QFont('Segoe UI',8));layout.addLayoutItem(scale);scale.attemptMove(QgsLayoutPoint(110,265))
text(12,282,400,9,'© OpenStreetMap contributors · ODbL  |  SANS AIP AD 2.12 · effective 01 Oct 2026  |  Runway widths: derived approximation; ground features: community mapping.',7,'#76868a')
project.layoutManager().addLayout(layout)
assert project.write()
exporter=QgsLayoutExporter(layout);settings=QgsLayoutExporter.ImageExportSettings();settings.dpi=180
assert exporter.exportToImage(str(OUT/'OEJN-ground-atlas.png'),settings)==QgsLayoutExporter.Success

# Independent browser companion: actual projected ground geometry, with hover on every feature.
# No imagery, remote libraries, tile requests or schematic airport shapes.
bounds=mapitem.extent(); w,h=1600,1200
sx=w/bounds.width();sy=h/bounds.height()
def coord(p):return ((p.x()-bounds.xMinimum())*sx,(bounds.yMaximum()-p.y())*sy)
def path(g):
    if g.isMultipart(): geometries=g.asGeometryCollection()
    else:geometries=[g]
    parts=[]
    for gg in geometries:
        if gg.type()==Qgis.GeometryType.Polygon:
            rings=gg.asPolygon()
            for ring in rings:
                q=[coord(p) for p in ring];parts.append('M'+'L'.join(f'{x:.1f},{y:.1f}' for x,y in q)+'Z')
        elif gg.type()==Qgis.GeometryType.Line:
            q=[coord(p) for p in gg.asPolyline()];parts.append('M'+'L'.join(f'{x:.1f},{y:.1f}' for x,y in q))
    return ''.join(parts)
elements=[]; counts={}
for l in reversed(visible):
    key=l.name();counts[key]=l.featureCount(); shapes=[]
    for f in l.getFeatures():
        g=f.geometry()
        if not g.boundingBox().intersects(bounds): continue
        props={k:str(f[k]) for k in ['name','kind','reference','source','source_date','note']}
        attrs=html.escape(json.dumps(props,ensure_ascii=False),quote=True)
        fill,stroke=palette.get(key,('#b1a6bc','#8c8195'));width=.7
        if key=='Runway surfaces':fill=stroke=colors[f['name']]
        elif key=='Runway centerlines':fill='none';stroke='#ffffff';width=1
        elif g.type()==Qgis.GeometryType.Line:fill='none';stroke={'Taxiways':'#afb3a9','Roads':'#d2cabc','Railway':'#958979','Coastline':'#8bbac9'}.get(key,'#a8a49a');width=2 if key=='Taxiways' else .8
        if g.type()==Qgis.GeometryType.Point:
            p=coord(g.asPoint());fill=colors.get(str(f['reference']),'#95859e');r=5 if key=='Runway ends' else 2
            shapes.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{r}" fill="{fill}" stroke="white" data-info="{attrs}"/>')
            if key=='Runway ends':shapes.append(f'<text x="{p[0]+10:.1f}" y="{p[1]-10:.1f}" class="end-label">{html.escape(f["name"])}</text>')
            if key=='Places' and str(f['kind'])=='neighbourhood':
                name=html.escape(str(f['name']))
                shapes.append(f'<text x="{p[0]+9:.1f}" y="{p[1]-7:.1f}" class="place-label">{name}</text>')
        else:shapes.append(f'<path d="{path(g)}" fill="{fill}" fill-rule="evenodd" stroke="{stroke}" stroke-width="{width}" data-info="{attrs}"/>')
    elements.append('<g data-layer="'+html.escape(key)+'">'+''.join(shapes)+'</g>')
svg='<svg id="map" viewBox="0 0 1600 1200" xmlns="http://www.w3.org/2000/svg">'+''.join(elements)+'</svg>'
template=(ROOT/'viewer-template.html').read_text(encoding='utf-8')
(OUT/'Open-ground-map.html').write_text(template.replace('<!--MAP-->',svg).replace('<!--COUNTS-->',str(sum(counts.values()))),encoding='utf-8')
if (ROOT/'map-2/data.json').exists():
    from upgrade_map1 import main as upgrade_browser
    upgrade_browser()
report={'qgis_version':Qgis.QGIS_VERSION,'osm_snapshot':STAMP,'layers':counts,'total_features':sum(counts.values()),'crs':crs.authid(),'runway_ends':6,'runway_surfaces':3,'all_layers_valid':all(l.isValid() for l in saved.values()),'note':'Map tip templates are stored on every layer. Browser companion supports hover, click, wheel zoom, drag pan and layer toggles.'}
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
project.clear()
