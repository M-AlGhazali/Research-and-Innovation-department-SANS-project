"""Build the A1-only procedure reference and retained mapping context as flat CSVs.
Uses only explicitly whitelisted files. Never opens A2-A6 datasets.
The four image-only PDFs are parsed using the reviewed a1_transcription module.
"""
from pathlib import Path
import sys,csv,json,re,hashlib,math,zipfile,collections
from urllib.parse import urljoin,quote
from lxml import html,etree
from pypdf import PdfReader
from a1_transcription import ROWS,COORDS,C_LIST,L_LIST,TEXT
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
OUT=Path(__file__).parent/'archive/expanded_phase1_2026-10-26';OUT.mkdir(parents=True,exist_ok=True)
VERSION='2026-10-26_v1';EFFECTIVE='2026-10-01';SHEET_DATE='2026-09-17'
AIP_URL='https://aimss.sans.com.sa/assets/FileManagerFiles/AIRAC%20AIP%20AMDT%2010_26_2026_10_01/eAIP/AD%202%20OEJN%20JEDDAH%20-%20KING%20ABDULAZIZ%20INTERNATIONAL-en-US.html'
tables={};descriptions={};sources=[];issues=[]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sid(runway,name):return 'OEJN_'+runway+'_'+name.replace(' ','')+'_20261001'
def rid(end):return 'OEJN_'+('34C_16C' if end in ['34C','16C'] else '34L_16R' if end in ['34L','16R'] else '34R_16L')
def write(name,rows,description,pk,foreign_keys='',cols=None):
 rows=list(rows);fields=cols or list(dict.fromkeys(k for r in rows for k in r))
 assert fields,name
 with (OUT/name).open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 tables[name]=(rows,fields);descriptions[name]=(description,pk,foreign_keys)
 return rows
def issue(code,scope,record,field,severity,detail,resolution,source,locator,status='documented'):
 issues.append(dict(issue_id=code,table_name=scope,record_id=record,field_name=field,severity=severity,description=detail,resolution=resolution,status=status,source_id=source,source_locator=locator))
def source(source_id,p,role,cls,locator='',date='',effective='',url='',method='file_read'):
 assert p.exists(),p
 assert not any(x in p.parts for x in ['A2','A3','A4','A5','A6']),p
 row=dict(source_id=source_id,relative_path=p.relative_to(BASE).as_posix(),file_name=p.name,source_role=role,data_class=cls,source_locator=locator,sheet_date=date if p.suffix.lower()=='.pdf' else None,source_snapshot_date=date if p.suffix.lower()!='.pdf' else None,effective_date=effective,source_url=url,sha256=sha(p),bytes=p.stat().st_size,extraction_method=method)
 if p.suffix.lower()=='.pdf':
  reader=PdfReader(str(p));row.update(pdf_page_count=len(reader.pages),pdf_text_layer_char_count=len(reader.pages[0].extract_text()),amendment='AIP AMDT 10/26',visual_table_review=True)
  row['base_amendment_note_raw']='Amdt: 10 AUG 23'
  row['change_note_raw']={'A1_34C_1':'CHANGE: JN274/BOMOX distance revised.','A1_34C_2':'CHANGE: Table updated.','A1_34L_1':'CHANGE: JN743 renamed to ORSOD.','A1_34L_2':'CHANGE: JN743 renamed to ORSOD.'}.get(source_id)
 sources.append(row)
 return row

for p in sorted((BASE/'OEJN-Noise-Fuel-Capacity/A1').glob('*.pdf')):
 runway=re.search(r'RWY (34\w)',p.name)[1];n=re.search(r'tabulation (\d)',p.name)[1]
 page={('34C','1'):114,('34C','2'):115,('34L','1'):110,('34L','2'):111}[(runway,n)]
 source(f'A1_{runway}_{n}',p,'primary_procedure_pdf','published_reference',f'PDF page 1; AD 2 OEJN {page}',SHEET_DATE,EFFECTIVE,method='image_assisted_cell_transcription_visually_checked')
 assert sha(p)==sha(ROOT/'sources/map-2'/f'{runway}-table-{n}.pdf')
source('SRC_AIP',ROOT/'sources/OEJN-AIP-2026-10-01.html','official_airport_reference','published_reference','OEJN AD 2',effective=EFFECTIVE,url=AIP_URL,method='retained_html_table_parsing')
source('SRC_OSM',ROOT/'sources/osm.json','upstream_ground_context','community_mapped_context',date='2026-10-25',url='https://www.openstreetmap.org/copyright',method='retained_overpass_json')
source('SRC_QUERY',ROOT/'sources/overpass-query.txt','ground_extraction_query','provenance')
source('SRC_GPKG',ROOT/'map-1/OEJN-ground.gpkg','map1_full_vector_geometry','mixed_published_derived_and_community_context',method='read_only_pyqgis_export')
source('SRC_MAPPING_BRIEF',BASE/'OEJN A1 mapping data sources and visual evidence.docx','project_context_and_crosscheck','authored_research_context',method='docx_ooxml_text_extraction')
source('SRC_SEED',BASE/'The initial seed of the initiative SANS project.docx','project_vision_and_historical_context','authored_research_context',method='docx_ooxml_text_extraction')
source('SRC_MAP_BUILD',ROOT/'build_map.py','mapping_transformations_and_assumptions','implementation_provenance')
source('SRC_MAP2',ROOT/'map-2/data.json','existing_map_transcription_comparison_only','derived_visualization_dataset',method='filter_34C_34L_before_comparison')
source('SRC_REPORT_BUILD',ROOT/'upgrade_map1.py','report_massing_display_parameters','implementation_provenance')
source('SRC_FLIGHT_MODEL',ROOT/'map-2/flight-model.mjs','illustrative_animation_controls','implementation_provenance')
for s in sources:
 s['license_name']='ODbL 1.0' if s['source_id'] in ['SRC_OSM','SRC_GPKG'] else 'Not asserted; retain provider/source terms'
 s['attribution']='© OpenStreetMap contributors' if s['source_id'] in ['SRC_OSM','SRC_GPKG'] else 'SANS eAIP / GACA' if s['source_id'].startswith('A1_') or s['source_id']=='SRC_AIP' else 'User-supplied project context / local implementation'
 if s['source_id']=='SRC_OSM':s['snapshot_timestamp_utc']=json.loads((ROOT/'sources/osm.json').read_text(encoding='utf-8'))['osm3s']['timestamp_osm_base']
write('12_sources.csv',sources,'One row per input file actually used; no A2-A6 directories.','source_id')

dom=html.fromstring((ROOT/'sources/OEJN-AIP-2026-10-01.html').read_bytes())
for s in sources:
 if s['source_id'].startswith('A1_'):
  _,runway,n=s['source_id'].split('_')
  found=[a.get('href') for a in dom.xpath('//a[@href]') if 'SID RNAV RWY '+runway in a.get('href','') and 'tabulation '+n+')' in a.get('href','')]
  if found:s['source_url']=quote(urljoin(AIP_URL,found[0]),safe=':/%')
write('12_sources.csv',sources,'One row per input file actually used; no A2-A6 directories.','source_id')
leaf_tables=dom.xpath('//table[not(.//table)]')
def cells(tr):return [' '.join(c.text_content().split()) for c in tr.xpath('./td|./th')]
def dms_packed(raw,lat):
 digits=raw[:-1];n=2 if lat else 3;deg=float(digits[:n]);minutes=float(digits[n:n+2]);seconds=float(digits[n+2:]);v=deg+minutes/60+seconds/3600
 assert minutes<60 and seconds<60,raw
 return round(v*(-1 if raw[-1] in 'SW' else 1),10)

airports=[dict(airport_id='OEJN',icao_code='OEJN',airport_name='Jeddah / King Abdulaziz International',country='Saudi Arabia',city='Jeddah',arp_latitude_raw='N214052',arp_longitude_raw='E0390922',latitude_deg=dms_packed('214052N',True),longitude_deg=dms_packed('0390922E',False),horizontal_crs='EPSG:4326',elevation_ft_amsl=50,elevation_m_amsl=15.24,reference_temperature_c=37.9,geoid_undulation_ft=15,magnetic_variation_raw='4° E (2025) / 0.01 increasing',operator='Jeddah Airports Company (JEDCO)',traffic_permitted='IFR/VFR',operation_type='Civil/Military',ats_hours='H24',fire_category='CAT 10',physical_runway_count=3,study_runway_count=2,study_departure_directions='34C;34L',data_class='published_reference',source_id='SRC_AIP',source_locator='AD 2.1; 2.2; 2.3; 2.6; 2.12',effective_date=EFFECTIVE)]
airports[0].update(arp_site_relative_to_tower_raw='920 M / 063° from TWR',airport_location_reference_raw='13 NM (24 KM) North of Jeddah Islamic Harbour')
write('01_airports.csv',airports,'One row per airport. ARP is distinct from map scene origin.','airport_id','source_id -> sources')

end_rows=[];runway_rows=[]
for t in leaf_tables:
 for tr in t.xpath('./tbody/tr|./tr'):
  c=cells(tr)
  if len(c)!=6 or c[0] not in ['16C','34C','16L','34R','16R','34L'] or 'GUND' not in c[4]:continue
  end=c[0];lat,lon=re.findall(r'\d{6,7}\.\d+[NE]',c[4]);length,width=map(int,re.findall(r'\d+',c[2]));elev,tdz=re.findall(r'(?:THR|TDZ) ([\d.]+) FT',c[5]);geoid=re.search(r'GUND: ([\d.]+)',c[4])[1]
  end_rows.append(dict(runway_end_id='OEJN_'+end,airport_id='OEJN',runway_id=rid(end),designator=end,study_departure_direction=end in ['34C','34L'],latitude_dms_raw=lat,longitude_dms_raw=lon,latitude_deg=dms_packed(lat,True),longitude_deg=dms_packed(lon,False),horizontal_crs='EPSG:4326',true_bearing_deg=float(c[1]),threshold_elevation_ft_amsl=float(elev),threshold_elevation_m_amsl=round(float(elev)*.3048,6),highest_tdz_elevation_ft_amsl=float(tdz),geoid_undulation_ft=float(geoid),published_length_m=length,published_width_m=width,pavement_rating_raw=c[3],surface='Asphalt',data_class='published_reference',source_id='SRC_AIP',source_locator='AD 2.12 / '+end,effective_date=EFFECTIVE))
assert len(end_rows)==6
for t in leaf_tables:
 for tr in t.xpath('./tbody/tr|./tr'):
  c=cells(tr)
  if len(c)!=7 or not c[0].startswith('For Rwy '):continue
  match=re.fullmatch(r'For Rwy (16[CLR]|34[CLR]): ([+-][\d.]+)%',c[0])
  if not match:continue
  e=next(r for r in end_rows if r['designator']==match[1]);strip=list(map(int,c[3].split(' x ')));resa=list(map(int,c[4].split(' x ')))
  e.update(slope_percent=float(match[2]),slope_raw=c[0],stopway_dimensions_raw=c[1],clearway_dimensions_raw=c[2],strip_length_m=strip[0],strip_width_m=strip[1],resa_length_m=resa[0],resa_width_m=resa[1],arresting_system_raw=c[5],obstacle_free_zone_raw=c[6])
for key,other,position in [('34C','16C','central'),('34L','16R','western'),('34R','16L','eastern')]:
 e=next(r for r in end_rows if r['designator']==key);o=next(r for r in end_rows if r['designator']==other)
 wkt=f'LINESTRING ({e["longitude_deg"]} {e["latitude_deg"]}, {o["longitude_deg"]} {o["latitude_deg"]})'
 runway_rows.append(dict(runway_id=rid(key),airport_id='OEJN',end_a_id=e['runway_end_id'],end_b_id=o['runway_end_id'],designator_pair=key+'/'+other,position=position,in_initial_study=key!='34R',published_length_m=e['published_length_m'],published_width_m=e['published_width_m'],surface='Asphalt',center_latitude_deg=round((e['latitude_deg']+o['latitude_deg'])/2,10),center_longitude_deg=round((e['longitude_deg']+o['longitude_deg'])/2,10),centerline_wgs84_wkt=wkt,geometry_data_class='derived_connector_of_published_thresholds',visual_buffer_half_width_m=30,source_id='SRC_AIP',source_locator='AD 2.12',effective_date=EFFECTIVE))
write('02_runways.csv',runway_rows,'One physical runway; third runway is context, never an extra A1 procedure family.','runway_id','airport_id -> airports; end_a_id/end_b_id -> runway_ends')
write('03_runway_ends.csv',end_rows,'One published threshold/end, with exact DMS converted independently of rounded map coordinates.','runway_end_id','runway_id -> runways; source_id -> sources')

waypoints=[];evidence=[];coord={}
for line in COORDS.strip().splitlines():
 name,ld,lm,ls,od,om,os=line.split();lat=f'{ld}{lm}{ls}N';lon=f'{od}{om}{os}E';coord[name]=(dms_packed(lat,True),dms_packed(lon,False))
 ids=[f'A1_{r}_2' for r,names in [('34C',C_LIST),('34L',L_LIST)] if name in names]
 waypoints.append(dict(waypoint_id=name,latitude_dms_raw=f'{ld}°{lm}\'{ls}" N',longitude_dms_raw=f'{od}°{om}\'{os}" E',latitude_deg=coord[name][0],longitude_deg=coord[name][1],horizontal_crs='EPSG:4326',published_coordinate_precision_arcsec=1,coordinate_source_ids=';'.join(ids),coordinate_source_locator='Waypoint list',data_class='published_reference',intrinsic_altitude_ft=None,effective_date=EFFECTIVE))
 for source_id in ids:evidence.append(dict(coordinate_evidence_id=source_id+'_'+name,waypoint_id=name,source_id=source_id,source_locator='PDF page 1 / Waypoint list',latitude_dms_raw=waypoints[-1]['latitude_dms_raw'],longitude_dms_raw=waypoints[-1]['longitude_dms_raw'],latitude_deg=coord[name][0],longitude_deg=coord[name][1],sheet_date=SHEET_DATE,effective_date=EFFECTIVE))
write('04_waypoints.csv',waypoints,'One unique navigation position. Altitude is not an intrinsic waypoint property.','waypoint_id')
write('05_coordinate_evidence.csv',evidence,'One published coordinate occurrence per waypoint list, retaining overlapping evidence.','coordinate_evidence_id','waypoint_id -> waypoints; source_id -> sources')
assert len(waypoints)==36 and len(evidence)==49

legs=[];constraints=[];procedures=[];routes=[];rules=[];flat=[];features=[]
geo_path=Path(__file__).parent/'geodesy.json'
geodesy=json.loads(geo_path.read_text()) if geo_path.exists() else {}
for (runway,name),block in ROWS.items():
 proc=sid(runway,name);family=name.split()[1];table_n=2 if name=='KAROX 2W' else 1;src=f'A1_{runway}_{table_n}';page=115 if table_n==2 else 114 if runway=='34C' else 110;rows=block.strip().splitlines();texts=TEXT[name]
 turns=dict((fix,'L' if direction=='left' else 'R') for direction,fix in re.findall(r'turn (left|right) to ([A-Z]+\d*|JN\d+)',texts))
 names=[];known_distance=0;missing_distance=0;first=None;last=None
 for i,line in enumerate(rows,1):
  fix,pd,mag,true,var,dist,turn,alt,speed,fly=line.split();names.append(fix);leg_id=proc+f'_{i:03}';prev=names[-2] if i>1 else None;known_distance+=float(dist) if dist!='-' else 0;missing_distance+=dist=='-'
  alt_op={'@':'at','+':'at_or_above','-':'at_or_below'}.get(alt[:1]) if alt!='-' else None;alt_unit='FL' if 'FL' in alt else 'ft' if alt!='-' else None;alt_val=int(re.sub(r'[^0-9]','',alt)) if alt!='-' else None
  speed_op={'-':'at_or_below','+':'at_or_above','@':'at'}.get(speed[:1]) if speed!='-' else None;speed_val=int(re.sub(r'[^0-9]','',speed)) if speed!='-' else None
  row=dict(leg_id=leg_id,procedure_id=proc,sequence_number=i,serial_number_raw=f'{i*10:03}',path_descriptor_raw=pd,waypoint_id=fix,previous_waypoint_id=prev,fly_over_raw=fly,fly_over_marked=fly=='Y',course_raw=f'{mag} ({true})',magnetic_course_deg=float(mag),true_course_deg=float(true),magnetic_variation_raw=var,magnetic_variation_deg=float(var) if var!='-' else None,distance_raw=dist,distance_nm=float(dist) if dist!='-' else None,distance_m=round(float(dist)*1852,3) if dist!='-' else None,turn_direction_raw=turn,turn_direction_table=turn if turn!='-' else None,turn_to_waypoint_routing_text=turns.get(fix),altitude_raw=alt,altitude_operator=alt_op,altitude_value=alt_val,altitude_unit=alt_unit,altitude_min_ft=alt_val if alt_unit=='ft' and alt_op in ['at','at_or_above'] else None,altitude_max_ft=alt_val if alt_unit=='ft' and alt_op in ['at','at_or_below'] else None,flight_level_min=alt_val if alt_unit=='FL' and alt_op in ['at','at_or_above'] else None,flight_level_max=alt_val if alt_unit=='FL' and alt_op in ['at','at_or_below'] else None,speed_raw=speed,speed_operator=speed_op,speed_limit_kt=speed_val,navigation_specification_raw='RNAV 1',data_class='published_reference',source_id=src,source_locator=f'PDF page 1 / AD 2 OEJN {page} / {name.replace(" ","")} / {i*10:03}',routing_source_id=f'A1_{runway}_2',sheet_date=SHEET_DATE,effective_date=EFFECTIVE,quality_flag='coordinate_cross_reference_34C_list' if runway=='34L' and fix=='JN274' else 'source_magvar_sign_retained' if var=='3.8' else '')
  legs.append(row)
  for typ,raw,op,val,unit in [('altitude',alt,alt_op,alt_val,alt_unit),('speed',speed,speed_op,speed_val,'kt')]:
   if raw!='-':constraints.append(dict(constraint_id=leg_id+'_'+typ,procedure_id=proc,leg_id=leg_id,waypoint_id=fix,constraint_type=typ,operator=op,value=val,unit=unit,raw_value=raw,reference='standard_pressure_flight_level' if unit=='FL' else 'published_altitude_in_feet' if typ=='altitude' else 'published_speed_in_knots',source_id=src,source_locator=row['source_locator'],effective_date=EFFECTIVE))
  ll=coord[fix];pl=coord[prev] if prev else None
  geo=geodesy.get(prev+'>'+fix,{}) if prev else {}
  ft=dict(row);ft.update(airport_id='OEJN',runway_id=rid(runway),departure_runway_end_id='OEJN_'+runway,procedure_name=name,waypoint_latitude_deg=ll[0],waypoint_longitude_deg=ll[1],previous_latitude_deg=pl[0] if pl else None,previous_longitude_deg=pl[1] if pl else None,reference_geometry_wgs84_wkt=f'LINESTRING ({pl[1]} {pl[0]}, {ll[1]} {ll[0]})' if pl else None,reference_fix_distance_m=geo.get('distance_m'),reference_fix_initial_bearing_deg=geo.get('bearing_deg'),reference_geometry_method='WGS84_ellipsoid_inverse_between_fixes' if pl else 'first_CF_start_geometry_not_supplied',runway_length_m=4000 if runway=='34C' else 3800,runway_width_m=60,coordinate_source_ids=next(w['coordinate_source_ids'] for w in waypoints if w['waypoint_id']==fix),actual_flight_id=None,observation_time_utc=None,observed_altitude_ft=None,observed_speed_kt=None,measured_noise_db=None,observed_fuel_kg=None,target_label=None)
  flat.append(ft)
 routes.append(dict(procedure_id=proc,procedure_name=name,route_label_raw='ISLM2W' if name=='ISLAM 2W' else name.replace(' ',''),routing_text_raw=texts,text_normalization='PDF line wraps collapsed to spaces; visible typos retained; image-assisted transcription',waypoint_sequence='>'.join(names),source_id=f'A1_{runway}_2',source_locator=f'PDF page 1 / Routing / {name}',sheet_date=SHEET_DATE,effective_date=EFFECTIVE))
 procedures.append(dict(procedure_id=proc,airport_id='OEJN',runway_id=rid(runway),departure_runway_end_id='OEJN_'+runway,procedure_name=name,procedure_name_raw=name.replace(' ',''),destination_waypoint_id=names[-1],procedure_type='SID',navigation_specification='RNAV 1',procedure_suffix=family,leg_count=len(rows),in_initial_study=True,amendment='AIP AMDT 10/26',sheet_date=SHEET_DATE,effective_date=EFFECTIVE,effective_date_source_id='SRC_AIP',leg_source_id=src,routing_source_id=f'A1_{runway}_2',known_published_distance_sum_nm=round(known_distance,3),published_distance_missing_leg_count=missing_distance,published_distance_total_nm=round(known_distance,3) if missing_distance==0 else None,distance_summary_note='Sum of published cells; not a measured flight length. Missing CF distance is not imputed.',requires_source_reconciliation=name=='MIGDA 3X',data_class='published_reference_with_derived_counts'))

for runway in ['34C','34L']:
 for n,kind,text,value,unit,until in [
  (1,'atc_notification','Advise ATC prior to take-off if unable to comply with SID.',None,None,None),
  (2,'frequency','After take-off, remain TWR FREQ.',None,None,None),
  (3,'minimum_climb_gradient','Minimum rate of climb is 320 FT per nautical mile. (5.27% CG) until 10000 FT.',320,'ft_per_nm',10000),
  (4,'initial_climb','Climb to 6000 FT or as assigned by ATC.',6000,'ft',None)]:
  rules.append(dict(rule_id=f'RULE_{runway}_{n}',airport_id='OEJN',departure_runway_end_id='OEJN_'+runway,applies_to='all_A1_SIDs_for_this_departure_runway',instruction_number=n,instruction_type=kind,instruction_text_raw=text,numeric_value=value,unit=unit,climb_gradient_percent=5.27 if n==3 else None,until_altitude_ft=until,atc_assignment_can_override=n==4,source_id=f'A1_{runway}_2',source_locator='PDF page 1 / common procedure instructions',effective_date=EFFECTIVE))
write('06_procedures.csv',procedures,'One runway-specific SID version. Sixteen procedures, not sixteen recorded flights.','procedure_id','runway_id -> runways; departure_runway_end_id -> runway_ends')
write('07_procedure_legs.csv',legs,'One published ordered leg; original symbols remain beside normalized numeric fields.','leg_id','procedure_id -> procedures; waypoint_id -> waypoints')
write('08_constraints.csv',constraints,'One explicit altitude or speed constraint attached to a procedure leg.','constraint_id','leg_id -> procedure_legs')
write('09_procedure_instructions.csv',rules,'One common instruction per study departure direction.','rule_id','departure_runway_end_id -> runway_ends')
write('10_routing_text.csv',routes,'One source narrative per procedure, retaining turns missing from tabular cells.','procedure_id','procedure_id -> procedures')
assert len(legs)==105 and len(procedures)==16

# Retain the full native mapping export, including exact geometry and mapped tags.
ground_path=OUT/'11_ground_features.csv';assert ground_path.exists(),'Run export_ground.py first.'
with ground_path.open(encoding='utf-8',newline='') as f:
 reader=csv.DictReader(f);ground_cols=reader.fieldnames;ground=list(reader)
for g in ground:
 for col in ['centroid_longitude_deg','centroid_latitude_deg','area_projected_m2','length_projected_m']:
  g[col]=float(g[col]) if g[col] else None
 g['geometry_valid']=g['geometry_valid']=='True'
tables['11_ground_features.csv']=(ground,ground_cols);descriptions['11_ground_features.csv']=('One Map 1 vector feature, all 18 layers. WKT coordinates and actual OSM tags; no fabricated building heights.','ground_feature_id','source_id/upstream_source_id -> sources')
assert len(ground)==20008

# Published runway distances: full-length and all retained intersection departures.
distances=[]
for t in leaf_tables:
 cr=[cells(tr) for tr in t.xpath('./tbody/tr|./tr')]
 for c in cr:
  if len(c)==6 and c[0] in [r['designator'] for r in end_rows] and all(re.fullmatch(r'\d+',x) for x in c[1:5]):
   distances.append(dict(distance_record_id='DIST_'+c[0]+'_FULL',runway_end_id='OEJN_'+c[0],departure_point='FULL_LENGTH',tora_m=int(c[1]),toda_m=int(c[2]),asda_m=int(c[3]),lda_m=int(c[4]),remarks_raw=c[5],source_id='SRC_AIP',source_locator='AD 2.13 / '+c[0],effective_date=EFFECTIVE))
 if cr and len(cr[0])==1 and re.fullmatch(r'RWY (16[CLR]|34[CLR])',cr[0][0]):
  end=cr[0][0].split()[-1]
  for c in cr[2:]:
   if len(c)!=4 or not c[0].startswith('TWY'):continue
   distances.append(dict(distance_record_id='DIST_'+end+'_'+c[0].replace(' ','_'),runway_end_id='OEJN_'+end,departure_point=c[0],tora_m=int(c[1]),toda_m=int(c[2]),asda_m=int(c[3]),lda_m=None,remarks_raw=None,source_id='SRC_AIP',source_locator='AD 2.13 / intersection departures / '+end,effective_date=EFFECTIVE))
write('17_declared_distances.csv',distances,'One full-length or intersection departure distance record; blank intersection LDA was not supplied.','distance_record_id','runway_end_id -> runway_ends')

# Archive relevant source context as section text without turning it into synthetic observations.
plain=' '.join(dom.text_content().split())
excerpts=[]
for sec in ['2.2','2.3','2.6','2.8','2.9','2.12','2.13','2.14','2.15','2.22']:
 match=re.search(r'OEJN AD '+re.escape(sec)+r'\s',plain)
 if not match:continue
 rem=plain[match.start():];next_section=re.search(r'OEJN AD 2\.\d+\s',rem[15:]);stop=next_section.start()+15 if next_section else len(rem)
 excerpts.append(dict(excerpt_id='AIP_AD_'+sec.replace('.','_'),source_id='SRC_AIP',source_locator='OEJN AD '+sec,text_raw_whitespace_normalized=rem[:stop].strip(),data_class='published_context',effective_date=EFFECTIVE))
for source_id,filename in [('SRC_MAPPING_BRIEF','OEJN A1 mapping data sources and visual evidence.docx'),('SRC_SEED','The initial seed of the initiative SANS project.docx')]:
 with zipfile.ZipFile(BASE/filename) as z:
  xml=etree.fromstring(z.read('word/document.xml'));ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
  paras=[''.join(p.xpath('.//w:t/text()',namespaces=ns)) for p in xml.xpath('//w:body/w:p',namespaces=ns)]
  selected=[p for p in paras if ('Develop an analytical review layer' in p or 'This brief reviews' in p or 'Use machine learning only' in p or 'With only four procedure PDFs' in p or 'All four sheets carry' in p or 'All four supplied PDFs' in p)]
  for i,text in enumerate(selected,1):excerpts.append(dict(excerpt_id=source_id+f'_{i}',source_id=source_id,source_locator='Document paragraph beginning: '+text[:65],text_raw_whitespace_normalized=text,data_class='authored_project_context',effective_date=None))
write('18_source_context.csv',excerpts,'One retained relevant AIP section or brief excerpt; supplementary source text, not measured data.','excerpt_id','source_id -> sources')

# Published parallel pairs are directional operational context, not a capacity label.
pairs=[]
for a,b in [('34R','34C'),('34R','34L'),('16R','16L')]:pairs.append(dict(operation_pair_id='PAIR_'+a+'_'+b,airport_id='OEJN',runway_end_a_id='OEJN_'+a,runway_end_b_id='OEJN_'+b,operation_type='simultaneous_independent_parallel_departure',publication_status='listed_in_fixed_AIP_snapshot',actual_active_status=None,source_id='SRC_AIP',source_locator='AD 2.22.2.6.1',effective_date=EFFECTIVE))
write('19_parallel_departure_pairs.csv',pairs,'One pair explicitly listed by the retained AIP; not a live clearance or throughput measurement.','operation_pair_id','runway_end_a_id/runway_end_b_id -> runway_ends')

# Explicit gaps are future collection needs drawn from the project vision, not fake training rows.
gaps=[]
for n,subject,fields,purpose in [
 (1,'actual_trajectories','flight_id;timestamp_utc;latitude;longitude;altitude;speed;quality','Observed-versus-published comparisons and flight-level validation'),
 (2,'assignments_and_clearances','flight_id;assigned_runway;assigned_SID;clearance_amendment;vector_event;timestamp_utc','Distinguish authorized vectors from unexplained track differences'),
 (3,'aircraft_and_weather','aircraft_type;engine;mass;wind;temperature;pressure;observation_time','Explain operational and performance variation'),
 (4,'noise','monitor_id;location;calibrated_event_reading;timestamp;weather;flight_match','Measured noise labels or validated environmental analysis'),
 (5,'fuel_and_emissions','flight_id;fuel_kg;CO2_kg;calculation_method;model_version;uncertainty','Use existing SANS/airline outputs as appropriate supervised targets'),
 (6,'terrain_obstacles_and_survey','surveyed_building_height;terrain_elevation;obstacle_id;datum;survey_date','Validated 3D physical context'),
 (7,'reviewed_labels','flight_id;event_id;review_outcome;reviewer;reference_version','Evaluate matching and anomaly ranking using independent reviewed cases')]:
 gaps.append(dict(gap_id=f'GAP_{n:02}',data_domain=subject,current_availability='not_in_this_A1_phase',future_fields_needed=fields,analytical_purpose=purpose,source_id='SRC_SEED',source_locator='Ground/air separation; MVP; machine learning discussion',training_target_available=False))
write('20_data_gaps.csv',gaps,'One future evidence need; no records from A2-A6 and no fabricated observations.','gap_id')

assumptions=[]
for n,key,value,unit,why in [(1,'building_height',12,'m','Default building massing only'),(2,'terminal_height',20,'m','Default terminal massing only'),(3,'vertical_emphasis_report',4,'ratio','Report display exaggeration only'),(4,'runway_surface_half_width',30,'m','Flat-ended visualization buffer, not surveyed pavement'),(5,'map2_ground_roll_fraction',.60,'runway_length_fraction','Animation control, not aircraft take-off performance'),(6,'map2_liftoff_fraction',.94,'runway_length_fraction','Animation control, not aircraft take-off performance')]:
 assumptions.append(dict(assumption_id=f'VIS_{n:02}',parameter=key,illustrative_value=value,unit=unit,usage=why,data_class='visualization_assumption',use_as_observed_ML_feature=False,source_id='SRC_MAP_BUILD' if n==4 else 'SRC_FLIGHT_MODEL' if n in [5,6] else 'SRC_REPORT_BUILD',source_locator='Map implementation / visualization notes'))
write('21_visualization_assumptions.csv',assumptions,'One existing display assumption, quarantined from published reference and training observations.','assumption_id')

issue('Q001','06_procedures.csv','ALL','edition','warning','The seed document discusses AMDT 09/25 / September 2025 sheets; supplied A1 binaries are AMDT 10/26 / 17 Sep 2026.','Use supplied A1 2026 sheets; preserve seed only as vision/history.','SRC_SEED','What the four procedure files represent')
issue('Q002','04_waypoints.csv','JN274','coordinate_source_ids','warning','JN274 is used by MIGDA 3X but omitted from the 34L coordinate list.','Cross-reference its published coordinate from the supplied 34C A1 waypoint list; specialist reconciliation remains open.','A1_34L_2','Waypoint list','open_source_omission')
issue('Q003','07_procedure_legs.csv',sid('34C','EGREP 2W'),'altitude_raw','warning','Existing Map 2 transcription put the at/below 13000 ft restriction at EGREP. Direct A1 leg-table and routing review both put it at JN520. The old claimed source disagreement is incorrect.','Canonical CSV attaches restriction to JN520. Existing map files were not edited by this dataset task.','A1_34C_1','AD 2 OEJN 114 / EGREP2W / 050','corrected_in_dataset_map_update_pending')
for l in legs:
 if l['magnetic_variation_raw']=='3.8':issue('Q_MAG_'+l['leg_id'],'07_procedure_legs.csv',l['leg_id'],'magnetic_variation_raw','review','Source prints unsigned positive 3.8 in a column otherwise predominantly -3.8.','Retained exactly as printed; no sign correction inferred. Published courses are separate fields.',l['source_id'],l['source_locator'],'retained_as_published')
 if l['distance_raw']=='-':issue('Q_DIST_'+l['leg_id'],'07_procedure_legs.csv',l['leg_id'],'distance_nm','information','Second CF leg has a dash in the published distance cell.','Numeric distance remains blank. A separately named fix-to-fix distance is derived; it is not substituted for the published CF distance.',l['source_id'],l['source_locator'],'missing_as_published')
issue('Q004','10_routing_text.csv',sid('34C','ISLAM 2W'),'route_label_raw','information','Routing row is labeled ISLM2W; leg/header labels identify ISLAM2W.','Canonical procedure name is ISLAM 2W; raw routing label retained.','A1_34C_2','Routing / ISLM2W','normalized_with_raw_retained')
issue('Q005','03_runway_ends.csv','STUDY_FOUR_ENDS','latitude_deg;longitude_deg','information','Existing map uses six-decimal threshold coordinates from the brief.','This reference CSV converts original published DMS, preserving more decimal precision; map-export geometry remains its original version.','SRC_MAPPING_BRIEF','Runway reference table','documented_precision_difference')
issue('Q006','11_ground_features.csv','ALL','geometry_wkt','information','OSM context and threshold buffers are not a certified surveyed airport inventory.','Keep geometry class and upstream source fields; assumed 12/20 m display heights are isolated.','SRC_GPKG','All layers')
issue('Q007','07_procedure_legs.csv','ALL','turn_direction_table','information','Narrative turns often exist where the tabular turn cell is a dash.','Keep both fields with distinct provenance; do not overwrite table cells using routing text.','A1_34C_2','Routing; corresponding leg tables')
old_routes=[r for r in json.loads((ROOT/'map-2/data.json').read_text(encoding='utf-8'))['routes'] if r['runway'] in ['34C','34L']]
assert len(old_routes)==16
map_diffs=[]
for pr in procedures:
 old=next(r for r in old_routes if r['name']==pr['procedure_name'])
 group=[l for l in legs if l['procedure_id']==pr['procedure_id']]
 assert [l['waypoint_id'] for l in group]==[l['fix'] for l in old['legs']],pr['procedure_name']
 for new,previous in zip(group,old['legs']):
  old_alt=previous['altitude'] or '-'
  if old_alt!=new['altitude_raw']:
   map_diffs.append(dict(leg_id=new['leg_id'],old=old_alt,new=new['altitude_raw']))
   issue('Q_MAP_'+new['leg_id'],'07_procedure_legs.csv',new['leg_id'],'altitude_raw','warning',f'Existing map altitude token {old_alt}; directly reviewed A1 token {new["altitude_raw"]}.','Use A1 token in CSV. Map implementation is unchanged by this export.','SRC_MAP2',new['source_locator'],'corrected_in_dataset_map_update_pending')
write('13_quality_issues.csv',issues,'One identified source, transcription, missing-data or interpretation issue.','issue_id','source_id -> sources')
write('16_analysis_legs.csv',flat,'Convenience join: one A1 leg with coordinates/runway/context. Reference features only; target and observed fields intentionally blank.','leg_id','leg_id -> procedure_legs')
for pr in procedures:
 group=[l for l in legs if l['procedure_id']==pr['procedure_id']];pts=[coord[l['waypoint_id']] for l in group]
 features.append(dict(procedure_id=pr['procedure_id'],procedure_name=pr['procedure_name'],airport_id='OEJN',runway_id=pr['runway_id'],leg_count=len(group),cf_leg_count=sum(l['path_descriptor_raw']=='CF' for l in group),tf_leg_count=sum(l['path_descriptor_raw']=='TF' for l in group),fly_over_marked_count=sum(l['fly_over_marked'] for l in group),tabular_turn_mark_count=sum(l['turn_direction_table'] is not None for l in group),narrative_turn_to_fix_count=sum(l['turn_to_waypoint_routing_text'] is not None for l in group),altitude_constraint_count=sum(l['altitude_value'] is not None for l in group),speed_constraint_count=sum(l['speed_limit_kt'] is not None for l in group),known_published_distance_sum_nm=pr['known_published_distance_sum_nm'],published_distance_missing_leg_count=pr['published_distance_missing_leg_count'],published_distance_total_nm=pr['published_distance_total_nm'],first_waypoint_id=group[0]['waypoint_id'],destination_waypoint_id=group[-1]['waypoint_id'],min_latitude_deg=min(p[0] for p in pts),max_latitude_deg=max(p[0] for p in pts),min_longitude_deg=min(p[1] for p in pts),max_longitude_deg=max(p[1] for p in pts),data_class='derived_procedure_reference_features',feature_method='Counts and coordinate bounding box derived from A1 records; not actual flights',effective_date=EFFECTIVE))
write('15_procedure_features.csv',features,'One deterministic reference feature summary per SID. No actual trajectories or supervised labels.','procedure_id','procedure_id -> procedures')

# Catalog and typed schema make CSV nulls, units and join grains explicit.
def dtype(values,key):
 if key in ['serial_number_raw'] or key.endswith('_id') or key.endswith('_ids'):return 'string'
 vals=[v for v in values if v is not None and v!='']
 if not vals:return 'number' if any(k in key for k in ['altitude','speed','noise','fuel','latitude','longitude']) else 'string'
 if all(isinstance(v,bool) or v in ['True','False'] for v in vals):return 'boolean'
 if all(isinstance(v,(int,float)) and not isinstance(v,bool) for v in vals):return 'integer' if all(float(v).is_integer() for v in vals) else 'number'
 if key.endswith('_date') or key=='sheet_date':return 'date'
 return 'string'
def unit_for(k):
 for suffix,u in [('_deg','degree'),('_arcsec','arcsecond'),('_m2','square_metre'),('_nm','nautical_mile'),('_kt','knot'),('_ft','foot'),('_ft_amsl','foot_AMSL'),('_m_amsl','metre_AMSL'),('_m','metre'),('_kg','kilogram'),('_db','decibel')]:
  if k.endswith(suffix):return u
 return 'flight_level_hundreds_of_feet_standard_pressure' if k.startswith('flight_level') else 'percent' if k.endswith('_percent') else ''
specific={
 'serial_number_raw':'Source serial preserved as text, e.g. 010; import as text in Excel.',
 'latitude_deg':'Latitude in WGS84 decimal degrees; positive north. Derived by exact DMS conversion.',
 'longitude_deg':'Longitude in WGS84 decimal degrees; positive east. WKT uses longitude then latitude.',
 'intrinsic_altitude_ft':'Always blank: altitude restrictions belong to a leg within a procedure, not to a waypoint globally.',
 'true_course_deg':'Published true course, not a bearing recalculated from map connectors.',
 'magnetic_variation_deg':'Literal signed numeric source cell; source signs are not harmonized.',
 'distance_nm':'Published leg distance. Blank for a printed dash; never imputed from coordinates.',
 'turn_to_waypoint_routing_text':'Turn direction into this named fix parsed from the separate narrative, L or R. Not a replacement for the table cell.',
 'reference_fix_distance_m':'Derived WGS84 ellipsoidal distance between preceding and current fix, not a flown-path measurement or reconstructed CF path.',
 'reference_fix_initial_bearing_deg':'Derived WGS84 ellipsoid initial bearing between fixes; do not substitute for published course.',
 'reference_geometry_wgs84_wkt':'Straight fix connector for TF/CF visualization only; first leg blank because CF origin geometry was not supplied.',
 'geometry_wkt':'Full retained native geometry in EPSG:32637 (metres), not the simplified browser mesh.',
 'geometry_wgs84_wkt':'Native geometry transformed to EPSG:4326; coordinate tuple order longitude latitude.',
 'centroid_latitude_deg':'Geometric centroid, not an airport ARP, building entrance or surveyed reference.',
 'centroid_longitude_deg':'Geometric centroid, not an airport ARP, building entrance or surveyed reference.',
 'mapped_height_raw':'Original OSM height tag when present; no default visualization heights inserted.',
 'raw_osm_tags_json':'Original mapped tags as a JSON object inside a properly quoted CSV field.',
 'target_label':'Intentionally blank: no reviewed flight-level target labels in A1.',
 'observed_altitude_ft':'Intentionally blank: A1 contains no observed flight trajectories.',
 'measured_noise_db':'Intentionally blank: no measured noise events included.',
 'observed_fuel_kg':'Intentionally blank: no observed flight fuel included.',
 'data_class':'Semantic evidence class. Published reference, derived geometry, community context, and illustration must remain distinguishable.',
 'effective_date':'Fixed 2026-10-01 package effective date; not the 2026-09-17 sheet publication date.',
 'source_id':'Foreign key to 12_sources.csv; provenance IDs in lists are separated by semicolon.',
 'source_locator':'Printed sheet, section, row or table location for reproducing the record.',
 'course_raw':'Exact magnetic and parenthesized true course text, with original leading zeros.',
 'altitude_value':'Magnitude from altitude_raw; interpreted only together with altitude_operator and altitude_unit.',
 'published_distance_total_nm':'Sum only when every published leg distance is present; otherwise blank.',
 'known_published_distance_sum_nm':'Sum of available published cells, explicitly excluding missing cells; not full length when any are absent.',
 'fly_over_marked':'True only where source fly-over cell is Y. False means not marked, not a reconstructed fly-by instruction.',
 'altitude_unit':'ft or FL. Flight levels use standard pressure and are not converted into surveyed AMSL altitude.',
 'departure_point':'FULL_LENGTH or published taxiway intersection; intersection records do not supply LDA.',
 'actual_active_status':'Intentionally blank: published availability is not live operational status.'
}
specific.update({
 'tora_m':'Published take-off run available in metres for the stated departure point.',
 'toda_m':'Published take-off distance available in metres for the stated departure point.',
 'asda_m':'Published accelerate-stop distance available in metres for the stated departure point.',
 'lda_m':'Published landing distance available in metres; blank for intersection departure rows because it was not supplied there.',
 'threshold_elevation_ft_amsl':'Published threshold elevation in feet above mean sea level; not geoid undulation.',
 'highest_tdz_elevation_ft_amsl':'Highest published touchdown-zone elevation, separate from threshold elevation.',
 'geoid_undulation_ft':'Published geoid undulation in feet. Do not substitute it for threshold or terrain elevation.',
 'slope_percent':'Published signed runway slope for this direction. Retained independently of slope estimated from threshold elevations.',
 'stopway_dimensions_raw':'Published stopway dimensions text; NIL means none stated, not an unknown numeric length.',
 'clearway_dimensions_raw':'Published clearway dimensions text; NIL means none stated, not an unknown numeric length.',
 'arresting_system_raw':'Published arresting-system/EMAS text, including NIL.',
 'obstacle_free_zone_raw':'Published OFZ field text, including NIL.',
 'source_snapshot_date':'Snapshot date for non-PDF sources; distinct from a printed procedure sheet date.',
 'base_amendment_note_raw':'Older base-amendment note printed on the sheet; not the current sheet issue date.',
 'change_note_raw':'Visible PDF change note, retained to support edition reconciliation.',
 'altitude_min_ft':'Lower bound for a published feet-valued constraint; blank for flight-level-valued constraints.',
 'altitude_max_ft':'Upper bound for a published feet-valued constraint; blank for flight-level-valued constraints.',
 'area_projected_m2':'Area of the native mapped polygon in EPSG:32637; not a surveyed area.',
 'length_projected_m':'Length of the native mapped line in EPSG:32637; not a surveyed or flown distance.'
})
dictionary=[];schema={}
for file,(rows,cols) in sorted(tables.items()):
 schema[file]={'description':descriptions[file][0],'primary_key':descriptions[file][1],'foreign_keys':descriptions[file][2],'columns':{}}
 for k in cols:
  vals=[r.get(k) for r in rows];typ=dtype(vals,k);nullable=any(v is None or v=='' for v in vals)
  meaning=specific.get(k, ('Literal source value; dash and source spelling are preserved.' if k.endswith('_raw') else 'Stable relational identifier.' if k.endswith('_id') else 'Source identifiers separated by semicolon.' if k.endswith('_ids') else k.replace('_',' ').capitalize()+'.'))
  row=dict(table_name=file,column_name=k,data_type=typ,unit=unit_for(k),nullable=nullable,null_encoding='empty_field',description=meaning)
  dictionary.append(row);schema[file]['columns'][k]={'type':typ,'unit':row['unit'],'nullable':nullable,'description':meaning}
write('14_data_dictionary.csv',dictionary,'One definition per data column; refer to this before numeric/boolean imports.','table_name + column_name')
catalog=[]
for file,(rows,cols) in sorted(tables.items()):
 description,pk,fks=descriptions[file];catalog.append(dict(table_name=file,row_count=len(rows),column_count=len(cols),row_grain=description,primary_key=pk,foreign_keys=fks,encoding='UTF-8',delimiter='comma',null_encoding='empty_field'))
write('00_dataset_catalog.csv',catalog,'One CSV inventory entry per data table.','table_name')
(OUT/'schema.json').write_text(json.dumps(schema,indent=2,ensure_ascii=False),encoding='utf-8')

# Integrity checks independent of the rendering and previous map transcription.
for table,(records,cols) in tables.items():
 pk=descriptions[table][1]
 if pk in cols:assert len({r[pk] for r in records})==len(records),(table,'duplicate key')
for l in legs:
 assert l['waypoint_id'] in coord and l['procedure_id'] in {p['procedure_id'] for p in procedures}
 assert l['path_descriptor_raw'] in ['CF','TF']
 assert 0<=l['magnetic_course_deg']<360 and 0<=l['true_course_deg']<360
 assert l['altitude_unit']!='FL' or (l['altitude_min_ft'] is None and l['altitude_max_ft'] is None)
key_sets={'airport_id':{r['airport_id'] for r in airports},'runway_id':{r['runway_id'] for r in runway_rows},'procedure_id':{r['procedure_id'] for r in procedures},'leg_id':{r['leg_id'] for r in legs}}
end_keys={r['runway_end_id'] for r in end_rows};source_keys={r['source_id'] for r in sources}
for key in ['runway_end_id','departure_runway_end_id','end_a_id','end_b_id','runway_end_a_id','runway_end_b_id']:key_sets[key]=end_keys
for key in ['waypoint_id','previous_waypoint_id','first_waypoint_id','destination_waypoint_id']:key_sets[key]=set(coord)
for key in ['source_id','upstream_source_id','routing_source_id','leg_source_id','effective_date_source_id']:key_sets[key]=source_keys
for table,(records,cols) in tables.items():
 for record in records:
  for key,allowed in key_sets.items():
   if key in record and record[key] not in [None,'']:assert record[key] in allowed,(table,key,record[key])
  for key in ['coordinate_source_ids']:
   if record.get(key):assert set(record[key].split(';'))<=source_keys
for p in procedures:
 group=[r for r in legs if r['procedure_id']==p['procedure_id']]
 assert [r['sequence_number'] for r in group]==list(range(1,len(group)+1))
 assert group[-1]['waypoint_id']==p['destination_waypoint_id']
assert not any(p['procedure_suffix']=='3V' for p in procedures)
assert [r['waypoint_id'] for r in legs if r['procedure_id']==sid('34C','EGREP 2W') and r['altitude_raw']=='-13000']==['JN520']
assert len([r for r in legs if r['distance_nm'] is None])==8
assert len([r for r in legs if r['fly_over_marked']])==8
assert len(geodesy)>0,'Run export_ground.py with geodesy generation before build.'
for f,(records,cols) in tables.items():
 with (OUT/f).open(encoding='utf-8',newline='') as stream:
  rr=list(csv.DictReader(stream));assert len(rr)==len(records)
  assert all(None not in r for r in rr),f
manifest=[dict(file_name=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(OUT.glob('*.csv'))]
(OUT/'file_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
summary=dict(dataset_version=VERSION,scope='Four supplied A1 PDFs plus previously retained map sources; no A2-A6 dataset files opened',airport_count=1,physical_runways=3,study_runways=2,procedures=16,legs=len(legs),unique_waypoints=len(waypoints),coordinate_evidence_rows=len(evidence),constraints=len(constraints),ground_features=len(ground),ground_layers=len({g['layer_name'] for g in ground}),primary_pdf_pages=4,csv_files=len(list(OUT.glob('*.csv'))),missing_published_distance_cells=8,unresolved_source_omissions=['JN274 absent from 34L waypoint list; coordinate cross-referenced from supplied 34C A1'],map_transcription_corrections=map_diffs,all_foreign_keys_checked=True,source_pdfs_copy_hash_match=True,actual_flight_training_samples=0,ml_target_labels=0)
(OUT/'validation.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2),flush=True)
