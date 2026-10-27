"""Compatibility tokens generated from the canonical study CSV and isolated 34R context.
No study procedures are maintained manually here. Full viewer metadata is applied
by sans_a2.reference.export_reference after the optional QGIS ground rebuild.
"""
from pathlib import Path
import csv,json,math
ROOT=Path(__file__).resolve().parents[1]
with (ROOT/'data/A1_Procedures.csv').open(encoding='utf-8-sig',newline='') as f:
    rows=list(csv.DictReader(f))
context=json.loads((ROOT/'map-2/reference/context-34R.json').read_text(encoding='utf-8'))
positions={r['waypoint_id']:(float(r['waypoint_latitude_deg']),float(r['waypoint_longitude_deg'])) for r in rows}
positions.update({k:(v['lat'],v['lon']) for k,v in context['fixes'].items()})
def dms(value):
    total=round(value*3600);return total//3600,(total%3600)//60,total%60
COORDS='\n'.join(name+' '+' '.join(map(str,(*dms(lat),*dms(lon)))) for name,(lat,lon) in sorted(positions.items()))
ROUTES={'34C':{},'34L':{},'34R':{}}
for pid in sorted({r['procedure_id'] for r in rows}):
    group=sorted([r for r in rows if r['procedure_id']==pid],key=lambda r:int(r['sequence_number']))
    ROUTES[group[0]['departure_runway']][group[0]['procedure_name']]=' '.join(r['waypoint_id']+'|'+(r['altitude_raw'] if r['altitude_raw']!='-' else '')+'|'+(r['speed_raw'] if r['speed_raw']!='-' else '') for r in group)
for route in context['routes']:
    ROUTES['34R'][route['name']]=' '.join(l['fix']+'|'+l['altitude']+'|'+l['speed'] for l in route['legs'])
WARNINGS={'MIGDA 3X':'JN274 omitted from the 34L coordinate list; coordinate cross-referenced from 34C. Specialist reconciliation remains open.'}
