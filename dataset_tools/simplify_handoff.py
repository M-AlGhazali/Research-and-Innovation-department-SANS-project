"""Consolidate the reviewed Phase 1 export into two self-contained CSVs.
Does not reprocess or blend the A2-A6 observations/models into A1 reference rows.
"""
from pathlib import Path
import csv,json,collections,re,hashlib

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
ARCHIVE=Path(__file__).parent/'archive/expanded_phase1_2026-10-26'
INPUT=BASE/'A1-Phase1-Dataset'
if not (INPUT/'07_procedure_legs.csv').exists():INPUT=ARCHIVE
OUT=ROOT/'data';OUT.mkdir(exist_ok=True)
def load(name):
 with (INPUT/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def write(name,rows):
 cols=list(rows[0])
 with (OUT/name).open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
 return cols
sources={s['source_id']:s for s in load('12_sources.csv')}
procs={p['procedure_id']:p for p in load('06_procedures.csv')}
coords={p['waypoint_id']:p for p in load('04_waypoints.csv')}
routes={p['procedure_id']:p for p in load('10_routing_text.csv')}
rules=collections.defaultdict(dict)
for r in load('09_procedure_instructions.csv'):rules[r['departure_runway_end_id']][r['instruction_type']]=r
def page(source_id):return re.search(r'AD 2 OEJN \d+',sources[source_id]['source_locator'])[0]
all_legs=load('07_procedure_legs.csv');a1=[]
for leg in all_legs:
 pr=procs[leg['procedure_id']];wp=coords[leg['waypoint_id']];route=routes[leg['procedure_id']];common=rules[pr['departure_runway_end_id']]
 ls=sources[leg['source_id']];rs=sources[leg['routing_source_id']]
 # Retain the source serial and both raw and normalized leg values.
 row=dict(airport_icao=pr['airport_id'],airport_name='Jeddah / King Abdulaziz International',departure_runway=pr['departure_runway_end_id'].split('_')[-1],procedure_name=pr['procedure_name'],procedure_id=leg['procedure_id'],leg_id=leg['leg_id'])
 for k in ['sequence_number','serial_number_raw','path_descriptor_raw','waypoint_id','previous_waypoint_id','fly_over_raw','fly_over_marked','course_raw','magnetic_course_deg','true_course_deg','magnetic_variation_raw','magnetic_variation_deg','distance_raw','distance_nm','distance_m','turn_direction_raw','turn_direction_table','turn_to_waypoint_routing_text','altitude_raw','altitude_operator','altitude_value','altitude_unit','altitude_min_ft','altitude_max_ft','flight_level_min','flight_level_max','speed_raw','speed_operator','speed_limit_kt','navigation_specification_raw']:
  row[k]=leg[k]
 row.update(waypoint_latitude_dms_raw=wp['latitude_dms_raw'],waypoint_longitude_dms_raw=wp['longitude_dms_raw'],waypoint_latitude_deg=wp['latitude_deg'],waypoint_longitude_deg=wp['longitude_deg'],horizontal_crs=wp['horizontal_crs'],coordinate_source_pages=';'.join(page(s) for s in wp['coordinate_source_ids'].split(';')),coordinate_in_departure_runway_list=f'A1_{row["departure_runway"]}_2' in wp['coordinate_source_ids'].split(';'),routing_label_raw=route['route_label_raw'],routing_text_raw=route['routing_text_raw'],procedure_waypoint_sequence=route['waypoint_sequence'])
 for kind,col in [('atc_notification','instruction_atc_notification_raw'),('frequency','instruction_frequency_raw'),('minimum_climb_gradient','instruction_minimum_climb_raw'),('initial_climb','instruction_initial_climb_raw')]:row[col]=common[kind]['instruction_text_raw']
 gradient=common['minimum_climb_gradient'];initial=common['initial_climb']
 row.update(minimum_climb_ft_per_nm=gradient['numeric_value'],minimum_climb_percent=gradient['climb_gradient_percent'],minimum_climb_until_altitude_ft=gradient['until_altitude_ft'],initial_climb_altitude_ft=initial['numeric_value'],initial_climb_subject_to_atc=initial['atc_assignment_can_override'],sheet_date=leg['sheet_date'],amendment=pr['amendment'],leg_source_page=page(leg['source_id']),leg_source_pdf=ls['file_name'],leg_source_sha256=ls['sha256'],leg_source_locator=leg['source_locator'],routing_and_instructions_source_page=page(leg['routing_source_id']),routing_and_instructions_source_pdf=rs['file_name'],routing_and_instructions_source_sha256=rs['sha256'],base_amendment_note_raw=ls['base_amendment_note_raw'],leg_sheet_change_note_raw=ls['change_note_raw'],routing_sheet_change_note_raw=rs['change_note_raw'])
 notes=[]
 if not row['coordinate_in_departure_runway_list']:notes.append('JN274 omitted from 34L coordinate list; coordinate cross-referenced from supplied 34C A1 list.')
 if leg['magnetic_variation_raw']=='3.8':notes.append('Positive 3.8 retained exactly as printed; no sign correction inferred.')
 if pr['procedure_name']=='EGREP 2W' and leg['waypoint_id'] in ['JN520','EGREP']:notes.append('Direct A1 table and routing agree: 13000 ft ceiling applies at JN520, not EGREP; earlier map transcription corrected here.')
 if route['route_label_raw']=='ISLM2W':notes.append('Source routing label ISLM2W retained; canonical procedure is ISLAM 2W.')
 row['data_notes']=' '.join(notes)
 a1.append(row)

airport=load('01_airports.csv')[0];ends=load('03_runway_ends.csv');runways={r['runway_id']:r for r in load('02_runways.csv')}
distances=load('17_declared_distances.csv');partners=collections.defaultdict(list)
for p in load('19_parallel_departure_pairs.csv'):
 partners[p['runway_end_a_id']].append(p['runway_end_b_id'].split('_')[-1]);partners[p['runway_end_b_id']].append(p['runway_end_a_id'].split('_')[-1])
external=[]
for end in ends:
 rw=runways[end['runway_id']];other=next(e for e in ends if e['runway_id']==end['runway_id'] and e['runway_end_id']!=end['runway_end_id'])
 full=next(d for d in distances if d['runway_end_id']==end['runway_end_id'] and d['departure_point']=='FULL_LENGTH')
 intersections=[dict(taxiway=d['departure_point'],tora_m=int(d['tora_m']),toda_m=int(d['toda_m']),asda_m=int(d['asda_m'])) for d in distances if d['runway_end_id']==end['runway_end_id'] and d['departure_point']!='FULL_LENGTH']
 row=dict(airport_icao=airport['icao_code'],airport_name=airport['airport_name'],airport_arp_latitude_deg=airport['latitude_deg'],airport_arp_longitude_deg=airport['longitude_deg'],airport_elevation_ft_amsl=airport['elevation_ft_amsl'],airport_physical_runway_count=airport['physical_runway_count'],runway_id=end['runway_id'],runway_pair=rw['designator_pair'],runway_position=rw['position'],runway_end=end['designator'],opposite_runway_end=other['designator'],in_initial_study=rw['in_initial_study'],a1_departure_direction=end['study_departure_direction'],runway_length_m=end['published_length_m'],runway_width_m=end['published_width_m'],runway_surface=end['surface'],runway_true_bearing_deg=end['true_bearing_deg'],threshold_latitude_dms_raw=end['latitude_dms_raw'],threshold_longitude_dms_raw=end['longitude_dms_raw'],threshold_latitude_deg=end['latitude_deg'],threshold_longitude_deg=end['longitude_deg'],threshold_elevation_ft_amsl=end['threshold_elevation_ft_amsl'],highest_tdz_elevation_ft_amsl=end['highest_tdz_elevation_ft_amsl'],geoid_undulation_ft=end['geoid_undulation_ft'],opposite_threshold_latitude_deg=other['latitude_deg'],opposite_threshold_longitude_deg=other['longitude_deg'],opposite_threshold_elevation_ft_amsl=other['threshold_elevation_ft_amsl'],runway_slope_percent=end['slope_percent'],full_length_tora_m=full['tora_m'],full_length_toda_m=full['toda_m'],full_length_asda_m=full['asda_m'],full_length_lda_m=full['lda_m'],intersection_departures_json=json.dumps(intersections,separators=(',',':')),published_independent_departure_partners=';'.join(partners[end['runway_end_id']]),horizontal_crs='EPSG:4326',aip_effective_date=end['effective_date'],aip_amendment='AIRAC AIP AMDT 10/26',source_sections='AD 2.2; AD 2.12; AD 2.13; AD 2.22.2.6.1',source_url=sources['SRC_AIP']['source_url'],source_snapshot_sha256=sources['SRC_AIP']['sha256'])
 external.append(row)
external_fields=write('External_Airport_Runways.csv',external)
external_by_end={r['runway_end']:r for r in external}
geodesy=json.loads((Path(__file__).parent/'geodesy.json').read_text())
for row in a1:
 ref=external_by_end[row['departure_runway']]
 for key,value in ref.items():
  if key in ['airport_icao','airport_name','horizontal_crs']:continue
  new_key=('departure_'+key if key.startswith('threshold_') else
           'airport_runway_reference_'+key if key.startswith('source_') else
           'reference_runway_end' if key=='runway_end' else key)
  assert new_key not in row,new_key
  row[new_key]=value
 prev=coords.get(row['previous_waypoint_id'])
 spatial=geodesy.get(row['previous_waypoint_id']+'>'+row['waypoint_id'],{}) if prev else {}
 pr=procs[row['procedure_id']]
 row.update(previous_waypoint_latitude_deg=prev['latitude_deg'] if prev else '',previous_waypoint_longitude_deg=prev['longitude_deg'] if prev else '',reference_fix_distance_m=spatial.get('distance_m',''),reference_fix_initial_bearing_deg=spatial.get('bearing_deg',''),reference_geometry_method='WGS84 ellipsoid inverse between published fixes' if prev else 'First CF origin not supplied; no connector invented',procedure_leg_count=pr['leg_count'],procedure_known_published_distance_sum_nm=pr['known_published_distance_sum_nm'],procedure_missing_published_distance_count=pr['published_distance_missing_leg_count'],procedure_published_distance_total_nm=pr['published_distance_total_nm'],reference_data_note='Airport/runway facts: retained SANS eAIP. Fix distance/bearing: derived WGS84 reference, not published leg length or an observed trajectory.')
fields=write('A1_Procedures.csv',a1)

# Verify consolidation preserves every tabulated A1 leg and all related content.
assert len(a1)==105 and len({r['procedure_id'] for r in a1})==16
assert {r['waypoint_id'] for r in a1}==set(coords)
assert sum(r['distance_nm']=='' for r in a1)==8
assert sum(r['altitude_value']!='' for r in a1)==42
assert sum(r['speed_limit_kt']!='' for r in a1)==8
for old,new in zip(all_legs,a1):
 for k in old:
  if k in new:assert str(old[k])==str(new[k]),(k,old,new)
assert len(external)==6 and sum(r['a1_departure_direction']=='True' for r in external)==2
for r in external:
 assert int(r['runway_length_m']) in [3800,4000] and int(r['runway_width_m'])==60
for row in a1:
 assert row['departure_runway']==row['reference_runway_end']
 assert row['runway_length_m']==('4000' if row['departure_runway']=='34C' else '3800')
 assert row['runway_width_m']=='60'
 assert row['airport_arp_latitude_deg'] and row['departure_threshold_latitude_deg']
 assert row['airport_runway_reference_source_url'] and row['airport_runway_reference_source_snapshot_sha256']
 assert bool(row['reference_fix_distance_m'])==(int(row['sequence_number'])>1)
assert len({r['procedure_id']:r['routing_text_raw'] for r in a1})==16
for name,expected in [('A1_Procedures.csv',a1),('External_Airport_Runways.csv',external)]:
 with (OUT/name).open(encoding='utf-8',newline='') as f:
  actual=list(csv.DictReader(f));assert len(actual)==len(expected) and all(None not in r for r in actual)
print(json.dumps({'A1_rows':len(a1),'A1_columns':len(fields),'procedures':16,'waypoints':36,'external_rows':len(external),'external_columns':len(external_fields),'all_A1_leg_fields_and_related_text_preserved':True,'output':str(OUT)},indent=2),flush=True)
