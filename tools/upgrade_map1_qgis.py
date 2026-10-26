from pathlib import Path
import json
from qgis.core import *
from qgis.PyQt.QtGui import QColor,QFont,QFontDatabase
from qgis.PyQt.QtSvg import QSvgRenderer
from qgis.PyQt.QtCore import QByteArray
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'map-1'
app=QgsApplication([],False);app.initQgis()
for n in ['segoeui.ttf','segoeuib.ttf','arial.ttf','arialbd.ttf']:QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+n)
p=QgsProject.instance();assert p.read(str(out/'OEJN-ground-atlas.qgz'))
assert all(l.isValid() for l in p.mapLayers().values())
navy='#222b55';blue='#387aff';mint='#65ffa0'
layout=next(l for l in p.layoutManager().layouts() if l.name().startswith('Ground atlas'))
for item in list(layout.items()):
    if isinstance(item,QgsLayoutItem) and item.id().startswith('sans-'):
        layout.removeLayoutItem(item);continue
    if isinstance(item,QgsLayoutItemLabel):
        t=item.text()
        if t.startswith('SANS  /') or t.startswith('Jeddah Airport') or t.startswith('KING ABDULAZIZ'):
            layout.removeLayoutItem(item)
        elif t.startswith('Three physical'):
            item.setText('3 physical runways / 6 ends.\n2 runways in the initial study.\n34R / 16L: airport context.')
        elif t.startswith('34C and 34L:'):
            item.setText('34C + 34L: initial study focus.\nAsphalt / each 60 m wide.\nN ↑  WGS 84 / UTM zone 37N')
    elif isinstance(item,QgsLayoutItemShape) and item.id().startswith('sans-'):
        layout.removeLayoutItem(item)
# Header is placed above the map; map geometry and native layer styling remain editable.
def shape(x,y,w,h,color):
    i=QgsLayoutItemShape(layout);i.setId('sans-header');i.setShapeType(QgsLayoutItemShape.Rectangle);i.setSymbol(QgsFillSymbol.createSimple({'color':color,'outline_style':'no'}));layout.addLayoutItem(i);i.attemptMove(QgsLayoutPoint(x,y));i.attemptResize(QgsLayoutSize(w,h));return i
def label(x,y,w,h,t,size,color):
    i=QgsLayoutItemLabel(layout);i.setId('sans-label');i.setText(t);i.setFont(QFont('Segoe UI',size));i.setFontColor(QColor(color));layout.addLayoutItem(i);i.attemptMove(QgsLayoutPoint(x,y));i.attemptResize(QgsLayoutSize(w,h));return i
shape(0,0,420,51,navy);shape(0,51,210,1.4,blue);shape(210,51,210,1.4,mint)
logo=QgsLayoutItemPicture(layout);logo.setId('sans-logo');layout.addLayoutItem(logo);logo.attemptMove(QgsLayoutPoint(12,10));logo.attemptResize(QgsLayoutSize(48,24));logo.setPicturePath(str(out/'sans-logo.svg'))
label(72,7,320,9,'RESEARCH & INNOVATION / AIRFIELD ATLAS',9,'#b0c2dc')
label(72,18,335,16,'Jeddah Airport / Ground atlas',24,'#ffffff')
label(72,36,320,9,'KING ABDULAZIZ INTERNATIONAL / OEJN / MAP 01',9,mint)
# Supplemental operations note in available left-hand space.
for i in layout.items():
    if isinstance(i,QgsLayoutItemLabel) and i.text().startswith('Taxiways /'):
        i.setText('Taxiways / aprons / terminals\nBuildings / roads / railway\nATC applies movement separation.\nWidth does not imply aircraft capacity.')
for num,name in enumerate(['airport-overview','runway-34C','runway-34L'],1):
    title=f'Report {num:02} | '+name
    old=p.layoutManager().layoutByName(title)
    if old:p.layoutManager().removeLayout(old)
    report=QgsPrintLayout(p);report.initializeDefaults();report.setName(title);report.pageCollection().pages()[0].setPageSize('A3',QgsLayoutItemPage.Landscape)
    picture=QgsLayoutItemPicture(report);report.addLayoutItem(picture);picture.attemptMove(QgsLayoutPoint(0,0));picture.attemptResize(QgsLayoutSize(420,297));picture.setPicturePath(str(out/'report-assets'/(name+'.svg')))
    p.layoutManager().addLayout(report)
    settings=QgsLayoutExporter.ImageExportSettings();settings.dpi=110
    assert QgsLayoutExporter(report).exportToImage(str(out/'report-assets'/(name+'.png')),settings)==QgsLayoutExporter.Success
settings=QgsLayoutExporter.ImageExportSettings();settings.dpi=150
assert QgsLayoutExporter(layout).exportToImage(str(out/'OEJN-ground-atlas.png'),settings)==QgsLayoutExporter.Success
p.setFilePathStorage(Qgis.FilePathType.Relative);assert p.write()
assert p.read(str(out/'OEJN-ground-atlas.qgz'))
result={'layers_valid':all(l.isValid() for l in p.mapLayers().values()),'layers':len(p.mapLayers()),'layouts':[l.name() for l in p.layoutManager().layouts()],'report_plates':3,'geometry_modified':False}
(out/'branding-validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
p.clear()
