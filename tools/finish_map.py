from pathlib import Path
import json, math
from qgis.core import *
from qgis.PyQt.QtGui import QFontDatabase
root=Path(__file__).resolve().parents[1]; out=root/'map-1'
app=QgsApplication([],False);app.initQgis()
for n in ['segoeui.ttf','segoeuib.ttf','arial.ttf','arialbd.ttf']:QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+n)
p=QgsProject.instance();assert p.read(str(out/'OEJN-ground-atlas.qgz'))
tree=p.layerTreeRoot()
groups=[tree.findGroup(n) or tree.addGroup(n) for n in ['01  Runway reference','02  Airfield infrastructure','03  Jeddah ground context']]
(out/'styles').mkdir(exist_ok=True)
report=json.loads((out/'validation.json').read_text())
report['reopened_project']=True;report['geometry_issues']={};report['runway_centerline_lengths_m']={}
rank=['Runway ends','Runway centerlines','Runway surfaces','Airfield facilities Point','Airfield facilities LineString','Airfield facilities Polygon','Terminals and hangars','Taxiways','Aprons and stopways','Aprons and stopways LineString','Airport boundary','Railway','Roads','Places','Buildings','Green spaces','Water','Coastline','Land use']
for layer in sorted(p.mapLayers().values(),key=lambda l:rank.index(l.name()) if l.name() in rank else 99):
    assert layer.isValid(),layer.name()
    assert layer.mapTipTemplate(),layer.name()
    node=tree.findLayer(layer.id());clone=node.clone()
    group=groups[0] if layer.name().startswith('Runway') else groups[1] if layer.name().startswith(('Airfield','Airport','Apron','Terminal','Taxiway')) else groups[2]
    group.addChildNode(clone);node.parent().removeChildNode(node)
    layer.saveNamedStyle(str(out/'styles'/(layer.name().lower().replace(' ','_')+'.qml')))
    issues=[]
    for f in layer.getFeatures():
        if not f.geometry().isGeosValid():issues.append(str(f['source_id']))
        if layer.name()=='Runway centerlines':
            length=f.geometry().length();report['runway_centerline_lengths_m'][f['name']]=round(length,2)
            expected=3800 if f['name']=='34L / 16R' else 4000
            assert abs(length-expected)<15,(f['name'],length)
    if issues:report['geometry_issues'][layer.name()]=issues
for layout in p.layoutManager().layouts():
    for item in layout.items():
        if isinstance(item,QgsLayoutItemMap):
            tree.setHasCustomLayerOrder(True);tree.setCustomLayerOrder(item.layers())
        if isinstance(item,QgsLayoutItemLabel) and item.text().startswith('━'):item.setText(item.text().replace('━  ',''))
    settings=QgsLayoutExporter.ImageExportSettings();settings.dpi=180
    assert QgsLayoutExporter(layout).exportToImage(str(out/'OEJN-ground-atlas.png'),settings)==QgsLayoutExporter.Success
assert p.write()
report['native_project_layers']=len(p.mapLayers());report['map_tip_templates']=len(p.mapLayers())
(out/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
p.clear()
