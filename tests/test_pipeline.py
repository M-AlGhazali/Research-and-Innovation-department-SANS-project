"""Synthetic cases only. Nothing in these fixtures is a research observation."""
from copy import deepcopy
from pathlib import Path
from datetime import datetime, timezone
import json
import math
import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
import duckdb
import pytest
from pyproj import Transformer
from sans_a2.common import ROOT, config, load, TRANSFORM, file_hash, connect, rows
from sans_a2.reference import export_reference, runways
from sans_a2.ingest import ingest, inventory
from sans_a2.flights import extract, extract_aircraft, runway_evidence
from sans_a2.matching import match, match_flight, route_geometry, ordered_alignment
from sans_a2.export import export_viewer
from sans_a2.validation import validate
from sans_a2.server import handler_for

@pytest.fixture
def c(tmp_path):
    values = config(ROOT / "config/oejn-2026-10-01.json")
    values.update(input_glob=str(tmp_path / "hour-*.parquet"), output_dir=str(tmp_path / "output"), threads=1)
    return values

def synthetic_raw(c):
    refs = runways()
    start, end = refs[0]["start"], refs[0]["end"]
    length = math.dist(start, end)
    de, dn = (end[0]-start[0])/length, (end[1]-start[1])/length
    inverse = Transformer.from_crs(32637,4326,always_xy=True)
    stamp = int(datetime(2026,10,1,0,59,45,tzinfo=timezone.utc).timestamp()*1000)
    records=[]
    for i in range(15):
        lon,lat=inverse.transform(start[0]+de*(500+i*100),start[1]+dn*(500+i*100))
        records.append(('abc123', datetime.fromtimestamp((stamp+i*5000)/1000,timezone.utc),lat,lon,300+i*50,350+i*50,140.,340.,1000.,False,0.,8.,'SYNTH-A',None))
    records.append(records[3]) # deterministic duplicate
    bad=list(records[5]);bad[1]=datetime.fromtimestamp((stamp+77000)/1000,timezone.utc);bad[2]=None;records.append(tuple(bad))
    stale=list(records[5]);stale[1]=datetime.fromtimestamp((stamp+78000)/1000,timezone.utc);stale[10]=90.;records.append(tuple(stale))
    missing=list(records[5]);missing[1]=datetime.fromtimestamp((stamp+79000)/1000,timezone.utc);missing[4]=None;missing[5]=None;missing[6]=None;records.append(tuple(missing))
    con=duckdb.connect()
    con.execute('CREATE TABLE fixture(h VARCHAR,timestamp TIMESTAMPTZ,la DOUBLE,lo DOUBLE,ab INTEGER,ag INTEGER,gs DOUBLE,tr DOUBLE,br DOUBLE,og BOOLEAN,sp DOUBLE,np DOUBLE,f VARCHAR,t VARCHAR)')
    con.executemany('INSERT INTO fixture VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',records)
    folder=Path(c['input_glob']).parent
    for suffix,condition in [('00',"timestamp<'2026-10-01 01:00:00+00'"),('01',"timestamp>='2026-10-01 01:00:00+00'")]:
        con.execute('COPY (SELECT * FROM fixture WHERE '+condition+' ORDER BY timestamp DESC) TO ? (FORMAT PARQUET)',[str(folder/f'hour-{suffix}.parquet')])
    con.close()
    return records

def test_reference_idempotence_and_correction():
    result=export_reference()
    paths=[ROOT/'map-2/data.json',ROOT/'map-2/reference/study-procedures.json']
    before=[file_hash(p) for p in paths]
    export_reference()
    assert before==[file_hash(p) for p in paths]
    assert result['study_legs']==105 and result['study_fixes']==36 and result['viewer_procedures']==24
    study=load(paths[1]);route=next(r for r in study['routes'] if r['name']=='EGREP 2W')
    assert [(l['fix'],l['altitude']) for l in route['legs'] if l['altitude']=='-13000']==[('JN520','-13000')]
    assert sum(l['published_distance_nm'] is None for r in study['routes'] for l in r['legs'])==8
    assert any(l['altitude_unit']=='FL' for r in study['routes'] for l in r['legs'])

def test_projection_round_trip():
    lon,lat=39.1561111111,21.6811111111
    e,n=TRANSFORM.transform(lon,lat)
    actual=Transformer.from_crs(32637,4326,always_xy=True).transform(e,n)
    assert actual==pytest.approx((lon,lat),abs=1e-8)
    assert 510000<e<520000 and 2390000<n<2410000

def test_ingest_hours_duplicates_audit_cache_and_pipeline(c):
    synthetic_raw(c)
    report=ingest(c)
    assert report['audit_reasons']['duplicate_timestamp']==1
    assert report['audit_reasons']['invalid_position']==1
    assert report['audit_reasons']['stale_position']==1
    assert report['retained_reports']==16
    assert report['selected_reports']==report['retained_reports']+sum(report['audit_reasons'].values())
    assert ingest(c)['cache_hit']
    con=connect(c)
    observations=rows(con,'select * from read_parquet(?) order by timestamp_ms',[str(Path(c['output_dir'])/'observations.parquet')])
    assert observations[0]['timestamp_utc'].tzinfo is not None
    assert observations[0]['timestamp_ms']<observations[-1]['timestamp_ms']
    assert len({o['source_file'] for o in observations})==2
    assert any('missing_altitude' in o['quality_flags'] for o in observations)
    assert all(o['message_type'] is None for o in observations)
    before=report['cache_key'];c['tracking_duration_s']+=1
    assert inventory(c)['cache_key']!=before
    extract(c);match(c);export_viewer(c)
    assert validate(c)['schema_validation']
    con.close()

def observation(rw,ms,along=1000,cross=0,**extra):
    sx,sy=rw['start'];ex,ey=rw['end'];length=math.hypot(ex-sx,ey-sy);dx,dy=(ex-sx)/length,(ey-sy)/length
    value=dict(icao24='abc123',timestamp_ms=ms,easting_m=sx+dx*along-dy*cross,northing_m=sy+dy*along+dx*cross,barometric_altitude_ft=500,geometric_altitude_ft=550,ground_speed_kt=140,track_deg=rw['bearing_deg'],barometric_rate_fpm=1000,on_ground=False,callsign='SYNTH-A',quality_flags='')
    value.update(extra);return value

def test_repeated_events_callsign_change_and_both_runways(c):
    for rw in runways():
        obs=[observation(rw,i*5000,along=500+i*100) for i in range(10)]
        obs+= [observation(rw,3600000+i*5000,along=500+i*100,callsign='SYNTH-B') for i in range(10)]
        events=extract_aircraft(obs,runways(),c)
        assert len(events)==2 and len({e['flight_id'] for e in events})==2
        assert all(e['runway']==rw['id'] for e in events)
        assert events[1]['callsigns']==['SYNTH-B']

def test_runway_intersection_reverse_missing_and_ambiguity(c):
    rw=runways()[0]
    assert runway_evidence(observation(rw,0,along=3000),rw,c)
    assert runway_evidence(observation(rw,0,track_deg=(rw['bearing_deg']+180)%360),rw,c) is None
    assert runway_evidence(observation(rw,0,barometric_rate_fpm=None),rw,c) is None
    # Coincident references deliberately expose a tie; the classifier must preserve it.
    other={**rw,'id':'34L'}
    events=extract_aircraft([observation(rw,i*5000) for i in range(8)],[rw,other],c)
    assert events[0]['runway_status']=='ambiguous_runway' and events[0]['runway'] is None

def track_on_route(route,study,rw,leg_count=None):
    geometry=route_geometry(route,study['fixes'],rw)
    if leg_count is not None:geometry=geometry[:leg_count+1]
    obs=[]
    for a,b in zip(geometry,geometry[1:]):
        heading=math.degrees(math.atan2(b[0]-a[0],b[1]-a[1]))%360
        for i in range(1,21):
            p=a+(b-a)*i/20
            obs.append(dict(timestamp_ms=len(obs)*5000,easting_m=float(p[0]),northing_m=float(p[1]),track_deg=heading,on_ground=False,quality_flags=''))
    return obs

def test_shared_trunk_ambiguity_unique_continuation_and_unmatched(c):
    study=load(ROOT/'map-2/reference/study-procedures.json');rw=runways()[0]
    route=next(r for r in study['routes'] if r['name']=='BOMOX 2W')
    f=dict(flight_id='SYNTHETIC',anchor_ms=0,runway='34C',runway_candidates=[dict(runway='34C')])
    trunk=match_flight(f,track_on_route(route,study,rw,2),study,c)
    assert trunk['status']=='ambiguous' and trunk['best_candidate'] is None
    full=match_flight(f,track_on_route(route,study,rw),study,c)
    assert full['best_candidate']==route['procedure_id'] and full['status']=='geometry_consistent'
    remote=track_on_route(route,study,rw)
    for o in remote:o['easting_m']+=150000
    assert match_flight(f,remote,study,c)['status']=='unmatched'
    assert match_flight(f,remote[:2],study,c)['status']=='insufficient_data'

def test_server_allowlist(c):
    viewer=Path(c['output_dir'])/'viewer';viewer.mkdir(parents=True)
    (viewer/'manifest.json').write_text('{"synthetic":true}')
    server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(c));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        base=f'http://127.0.0.1:{server.server_port}'
        assert b'synthetic' in urllib.request.urlopen(base+'/observed-data/manifest.json').read()
        for path in ['/A2/raw.parquet','/.git/config','/observed-data/../../.git/config','/map-2/../data/A1_Procedures.csv']:
            with pytest.raises(urllib.error.HTTPError):urllib.request.urlopen(base+path)
    finally:server.shutdown();server.server_close();thread.join()

def test_isolated_jump_and_invalid_time_are_audited(c):
    synthetic_raw(c)
    path=Path(c['input_glob']).parent/'hour-00.parquet'
    con=duckdb.connect()
    con.execute('CREATE TABLE changed AS SELECT * FROM read_parquet(?)',[str(path)])
    con.execute("UPDATE changed SET la=22.3,lo=39.7 WHERE timestamp='2026-10-01 00:59:55+00'")
    con.execute("INSERT INTO changed SELECT h,NULL,la,lo,ab,ag,gs,tr,br,og,sp,np,f,t FROM changed LIMIT 1")
    con.execute('COPY changed TO ? (FORMAT PARQUET)',[str(path)]);con.close()
    report=ingest(c)
    assert report['audit_reasons']['isolated_position_jump']==1
    assert report['audit_reasons']['invalid_timestamp']==1
    original=report['observation_sha256']
    assert ingest(c,force=True)['observation_sha256']==original

def test_schema_drift_fails_explicitly(c):
    synthetic_raw(c)
    con=duckdb.connect();path=Path(c['input_glob']).parent/'hour-02.parquet'
    con.execute('COPY (SELECT \'abc123\' h,now() AS "timestamp",21.6 la,39.1 lo) TO ? (FORMAT PARQUET)',[str(path)]);con.close()
    with pytest.raises(ValueError,match='schema drift'):inventory(c)

def test_empty_observation_day_remains_valid(c):
    synthetic_raw(c)
    con=duckdb.connect()
    for path in sorted(Path(c['input_glob']).parent.glob('hour-*.parquet')):
        con.execute('CREATE OR REPLACE TABLE empty_source AS SELECT * FROM read_parquet(?) WHERE false',[str(path)])
        con.execute('COPY empty_source TO ? (FORMAT PARQUET)',[str(path)])
    con.close()
    assert ingest(c)['retained_reports']==0
    assert extract(c)['events']==0
    assert match(c)['flights']==0
    assert export_viewer(c)['flights_exported']==0
    assert validate(c)['flights']==0

def test_ordered_alignment_matches_brute_force_reference():
    import numpy as np
    cost=np.random.default_rng(17).random((40,8)).tolist()
    previous=[j*.5 for j in range(8)];backs=[]
    for report in cost:
        current=[];indices=[]
        for j in range(8):
            k=min(range(j+1),key=lambda k:previous[k]+max(j-k-1,0)*.4)
            current.append(previous[k]+max(j-k-1,0)*.4+report[j]);indices.append(k)
        previous=current;backs.append(indices)
    j=min(range(8),key=lambda j:previous[j]);expected=[]
    for indices in reversed(backs):expected.append(j);j=indices[j]
    assert ordered_alignment(cost).tolist()==expected[::-1]

def test_ground_speed_not_substituted_by_ias(c):
    rw=runways()[0]
    assert runway_evidence(observation(rw,0,ground_speed_kt=None,indicated_airspeed_kt=220),rw,c) is None
