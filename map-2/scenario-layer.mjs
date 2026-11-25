import * as THREE from 'three';
import {playbackAt} from './scenario-playback.mjs';

const colors={'34C':'#168d9b','34L':'#bb4b76'};
const levelColors={60:'#12B5EA',65:'#1738F5',70:'#03072E'},levelOpacity={60:.28,65:.3,70:.34},levelHeight={60:.02,65:.022,70:.024};
const FT_KM=.0003048,LINKS={maha:'https://github.com/M40aha/oejn-noise-population',hala:'https://github.com/Hala-Alali/OEJN_Aircraft_Fuel_Weather',openap:'https://github.com/TUDelft-CNS-ATM/openap'};
const element=(tag,text,className)=>{const e=document.createElement(tag);if(text!==undefined&&text!==null)e.textContent=text;if(className)e.className=className;return e};
const num=(v,digits=0)=>Number(v).toLocaleString('en-US',{minimumFractionDigits:digits,maximumFractionDigits:digits});
const tons=kg=>{const t=kg/1000;return num(t,t>=100?0:1)};
const clock=s=>{s=Math.round(s);return Math.floor(s/60)+':'+String(s%60).padStart(2,'0')};

// WGS84 transverse Mercator (Krüger series) for UTM zone 37N: k0 .9996, central meridian 39°E, false easting 500000.
export function toUtm37(lat,lon){
 const a=6378137,f=1/298.257223563,n=f/(2-f),k0=.9996,rad=Math.PI/180;
 const A=a/(1+n)*(1+n*n/4+n**4/64+n**6/256);
 const al=[n/2-2*n*n/3+5*n**3/16+41*n**4/180,13*n*n/48-3*n**3/5+557*n**4/1440,61*n**3/240-103*n**4/140,49561*n**4/161280];
 const phi=lat*rad,lam=(lon-39)*rad,c=2*Math.sqrt(n)/(1+n);
 const t=Math.sinh(Math.atanh(Math.sin(phi))-c*Math.atanh(c*Math.sin(phi)));
 const xi0=Math.atan2(t,Math.cos(lam)),eta0=Math.atanh(Math.sin(lam)/Math.sqrt(1+t*t));
 let xi=xi0,eta=eta0;
 al.forEach((v,i)=>{const j=2*(i+1);xi+=v*Math.sin(j*xi0)*Math.cosh(j*eta0);eta+=v*Math.cos(j*xi0)*Math.sinh(j*eta0)});
 return [500000+k0*A*eta,k0*A*xi];
}

export const SCENARIO_DEFAULT={runway:'34C',sid:'ISLAM 2W',aircraft:'A320'};
export const departuresSentence=n=>`People inside the 65 dB area hear about ${n} ${n===1?'departure':'departures'} like this a day (${n}×365 = ${num(n*365)} a year).`;

export function mountScenario({scene,data,host,viewport,camera,controls,vertical,onMode,aircraft,base='./scenarios/'}){
 const baseUrl=new URL(base,import.meta.url);
 const state={enabled:false,...SCENARIO_DEFAULT,perDay:10,index:null,record:null,error:null};
 const play={t:0,playing:false,speed:30,dirty:true};
 const geoCache=new Map();let token=0,indexPromise=null,lastVertical=vertical(),plane=null,chart=null;
 const project=(lat,lon)=>{const [e,n]=toUtm37(lat,lon);return [(e-data.origin.utm[0])/1000,-(n-data.origin.utm[1])/1000]};
 // Self-check the projection against the published fixes.
 let worst=0;for(const [id,fix] of Object.entries(data.fixes)){const [x,z]=project(fix.lat,fix.lon),err=Math.hypot(x-fix.xz[0],z-fix.xz[1]);worst=Math.max(worst,err);if(err>.002)console.warn(`Scenario projection check: fix ${id} is off by ${err.toFixed(4)} km`)}

 const group=new THREE.Group();group.visible=false;scene.add(group);
 let contours=null,track=null;
 const labels=element('div',undefined,'scenario-labels');labels.hidden=true;host.append(labels);
 let placeLabels=[];

 // Mode select lives in observed-layer; this layer only reacts to it.
 const panel=element('section',undefined,'scenario-panel');panel.hidden=true;panel.setAttribute('aria-label','Scenario controls');
 panel.append(element('h2','Scenario (what-if)'),element('p','A simulated departure on a published SID. Every number is modelled, not measured.','scenario-intro'));
 const notice=element('p','Loading the scenarios…','scenario-notice');notice.setAttribute('role','status');panel.append(notice);
 const field=(label,child)=>{const w=element('div',undefined,'scenario-field');w.append(element('span',label,'scenario-label'),child);panel.append(w);return w};
 const runwayBox=element('div',undefined,'scenario-runways');runwayBox.setAttribute('role','tablist');runwayBox.setAttribute('aria-label','Runway');
 const runwayButtons={};
 for(const id of ['34C','34L']){const b=element('button',id,'runway-tab');b.type='button';b.style.setProperty('--runway',colors[id]);b.setAttribute('role','tab');b.onclick=()=>choose({runway:id});runwayButtons[id]=b;runwayBox.append(b)}
 field('Runway',runwayBox);
 const sidSelect=element('select');sidSelect.setAttribute('aria-label','SID');sidSelect.onchange=()=>choose({sid:sidSelect.value});field('SID',sidSelect);
 const aircraftBox=element('div',undefined,'scenario-seg');aircraftBox.setAttribute('role','group');aircraftBox.setAttribute('aria-label','Aircraft');
 const aircraftButtons={};
 for(const id of ['A320','A20N','B77W']){const b=element('button',id);b.type='button';b.onclick=()=>choose({aircraft:id});aircraftButtons[id]=b;aircraftBox.append(b)}
 field('Aircraft',aircraftBox);
 const perDayLabel=element('span','Departures per day','scenario-label'),perDayValue=element('b','10');perDayLabel.append(' ',perDayValue);
 const perDayInput=element('input');perDayInput.type='range';perDayInput.min='1';perDayInput.max='50';perDayInput.step='1';perDayInput.value='10';perDayInput.setAttribute('aria-label','Departures per day');
 perDayInput.oninput=()=>{state.perDay=Number(perDayInput.value);perDayValue.textContent=state.perDay;renderResults()};
 const perDayField=element('div',undefined,'scenario-field');perDayField.append(perDayLabel,perDayInput);panel.append(perDayField);
 const results=element('div',undefined,'scenario-results');panel.append(results);
 document.querySelector('.sidebar').append(panel);

 // Scene overlays: legend and climb profile card.
 const legend=element('div',undefined,'scenario-legend');legend.hidden=true;
 legend.append(element('small','NOISE · LAMAX, ONE DEPARTURE · MODELLED'));
 for(const level of [60,65,70]){const row=element('span');const sw=element('i');sw.style.background=levelColors[level];row.append(sw,document.createTextNode('≥'+level+' dB'));legend.append(row)}
 const card=element('div',undefined,'scenario-card');card.hidden=true;
 const cardHead=element('div',undefined,'card-heading');const cardTitle=element('span','CLIMB PROFILE'),cardTag=element('b','MODELLED');
 const collapse=element('button','–','scenario-collapse');collapse.type='button';
 const setCollapsed=on=>{card.classList.toggle('collapsed',on);collapse.textContent=on?'+':'–';collapse.setAttribute('aria-expanded',String(!on));collapse.setAttribute('aria-label',on?'Show climb chart':'Hide climb chart')};
 collapse.onclick=()=>setCollapsed(!card.classList.contains('collapsed'));
 cardHead.append(cardTitle,cardTag,collapse);
 const cardSub=element('p',undefined,'scenario-card-sub'),svgNS='http://www.w3.org/2000/svg';
 // live counters and transport for the playback
 const live=element('div',undefined,'scenario-live');
 const liveCell=caption=>{const c=element('div');const v=element('b','—');c.append(element('small',caption),v);live.append(c);return v};
 const liveTime=liveCell('TIME'),liveAlt=liveCell('ALTITUDE'),liveFuel=liveCell('FUEL SO FAR'),liveCo2=liveCell('CO₂ SO FAR');
 const transport=element('div',undefined,'scenario-transport');
 const playBtn=element('button','▶ Play','primary');playBtn.type='button';playBtn.setAttribute('aria-label','Play or pause the scenario departure');
 const restartBtn=element('button','↺');restartBtn.type='button';restartBtn.setAttribute('aria-label','Restart the scenario departure');
 const speedSelect=element('select');speedSelect.setAttribute('aria-label','Scenario playback speed');
 for(const n of [10,30,60]){const o=element('option',n+'× speed');o.value=n;if(n===play.speed)o.selected=true;speedSelect.append(o)}
 playBtn.onclick=()=>{if(!state.record)return;if(play.t>=state.record.to10k.time_s)play.t=0;play.playing=!play.playing;play.dirty=true};
 restartBtn.onclick=()=>{play.t=0;play.playing=false;play.dirty=true};
 speedSelect.onchange=()=>play.speed=Number(speedSelect.value);
 transport.append(playBtn,restartBtn,speedSelect);
 const svg=document.createElementNS(svgNS,'svg');svg.setAttribute('viewBox','0 0 320 150');svg.setAttribute('role','img');svg.setAttribute('aria-label','Modelled altitude profile');svg.classList.add('scenario-profile');
 const cardFoot=element('div',undefined,'card-foot');cardFoot.append(element('span','Altitude (ft, MSL) against distance flown (NM)'));
 card.append(cardHead,cardSub,live,svg,transport,cardFoot);
 setCollapsed(matchMedia('(max-width:600px)').matches);
 viewport.append(legend,card);

 const setNotice=(text,error)=>{notice.textContent=text;notice.classList.toggle('error',Boolean(error));notice.hidden=!text};
 function loadIndex(){
  indexPromise??=(async()=>{
   try{
    const response=await fetch(new URL('index.json',baseUrl));if(!response.ok)throw Error('The scenario data is not available yet (scenarios/index.json is missing).');
    const index=await response.json();if(index.schema_version!==1||!Array.isArray(index.scenarios)||!index.scenarios.length)throw Error('Unsupported scenario index.');
    state.index=index;setNotice('');return index;
   }catch(e){state.error=e.message;setNotice(e.message,true);indexPromise=null;throw e}
  })();
  return indexPromise;
 }
 const sidsFor=runway=>[...new Set(state.index.scenarios.filter(s=>s.runway===runway).map(s=>s.sid))];
 const findRecord=()=>state.index.scenarios.find(s=>s.runway===state.runway&&s.sid===state.sid&&s.aircraft===state.aircraft);

 async function choose(change){
  try{await loadIndex()}catch{return}
  Object.assign(state,change);
  const sids=sidsFor(state.runway);if(!sids.includes(state.sid))state.sid=sids[0];
  syncInputs();
  await refresh();
 }
 function syncInputs(){
  for(const [id,b] of Object.entries(runwayButtons)){b.classList.toggle('active',id===state.runway);b.setAttribute('aria-selected',String(id===state.runway))}
  if(sidSelect.dataset.runway!==state.runway||!sidSelect.options.length){sidSelect.replaceChildren();for(const sid of sidsFor(state.runway)){const o=element('option',sid);o.value=sid;sidSelect.append(o)}sidSelect.dataset.runway=state.runway}
  sidSelect.value=state.sid;
  for(const [id,b] of Object.entries(aircraftButtons)){const info=state.index.aircraft?.[id];b.title=info?`${info.name} · ${info.engine}`:id;b.classList.toggle('active',id===state.aircraft);b.setAttribute('aria-pressed',String(id===state.aircraft))}
  perDayInput.value=state.perDay;perDayValue.textContent=state.perDay;
 }

 async function loadGeo(record){
  if(!geoCache.has(record.id)){
   geoCache.set(record.id,fetch(new URL(record.geojson,baseUrl)).then(r=>{if(!r.ok)throw Error('Noise contours for this scenario could not be loaded.');return r.json()}).catch(e=>{geoCache.delete(record.id);throw e}));
  }
  return geoCache.get(record.id);
 }
 function dispose(object){if(!object)return;object.traverse(o=>{o.geometry?.dispose();for(const m of [].concat(o.material||[]))m.dispose?.()});group.remove(object)}
 const polygonsOf=geometry=>geometry?.type==='Polygon'?[geometry.coordinates]:geometry?.type==='MultiPolygon'?geometry.coordinates:[];
 function ringPoints(ring){const pts=ring.map(([lon,lat])=>{const [x,z]=project(lat,lon);return new THREE.Vector2(x,z)});if(pts.length>1&&pts[0].distanceTo(pts.at(-1))<1e-9)pts.pop();return pts}
 function buildContours(geo){
  const result=new THREE.Group(),bounds=new THREE.Box3();
  for(const feature of geo.features){
   const level=Math.round(feature.properties.lamax_db),color=levelColors[level]||'#1738F5',height=levelHeight[level]||.022,rank=[60,65,70].indexOf(level)+1;
   const positions=[];
   for(const polygon of polygonsOf(feature.geometry)){
    const rings=polygon.map(ringPoints).filter(r=>r.length>2);if(!rings.length)continue;
    const vertices=rings.flat(),triangles=THREE.ShapeUtils.triangulateShape(rings[0],rings.slice(1));
    for(const tri of triangles)for(const idx of tri){const p=vertices[idx];positions.push(p.x,height,p.y)}
    for(const [i,ring] of rings.entries()){
     const line=new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(ring.map(p=>new THREE.Vector3(p.x,height+.001,p.y))),new THREE.LineBasicMaterial({color,transparent:true,opacity:.9,depthWrite:false}));line.renderOrder=10+rank;result.add(line);
     if(level===60&&i===0)for(const p of ring)bounds.expandByPoint(new THREE.Vector3(p.x,0,p.y));
    }
   }
   if(positions.length){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));const mesh=new THREE.Mesh(g,new THREE.MeshBasicMaterial({color,transparent:true,opacity:levelOpacity[level]??.3,side:THREE.DoubleSide,depthWrite:false}));mesh.renderOrder=rank;result.add(mesh)}
  }
  result.userData.bounds=bounds;return result;
 }
 function buildTrack(record){
  const v=vertical(),color=colors[record.runway],result=new THREE.Group();
  const pts=record.profile.map(p=>{const [x,z]=project(p[3],p[2]);return new THREE.Vector3(x,p[1]*FT_KM*v,z)});
  result.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),new THREE.LineBasicMaterial({color})));
  result.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts.map(p=>new THREE.Vector3(p.x,.03,p.z))),new THREE.LineBasicMaterial({color,transparent:true,opacity:.32})));
  const k=record.profile.findIndex(p=>p[1]>=10000);
  if(k>0){const a=record.profile[k-1],b=record.profile[k],t=(10000-a[1])/Math.max(1,b[1]-a[1]),at=project(a[3]+(b[3]-a[3])*t,a[2]+(b[2]-a[2])*t);
   const marker=new THREE.Mesh(new THREE.OctahedronGeometry(.22),new THREE.MeshBasicMaterial({color}));marker.position.set(at[0],10000*FT_KM*v,at[1]);result.add(marker);
   result.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(at[0],.03,at[1]),marker.position.clone()]),new THREE.LineBasicMaterial({color,transparent:true,opacity:.25})))}
  result.userData.below10k=pts.filter((p,i)=>record.profile[i][1]<=10000);
  // the rest of the published SID after the modelled climb: thin dashed line through the remaining fixes
  const fixes=routeFixes(record),lastModelled=record.fixes.at(-1)?.id,after=fixes.slice(fixes.indexOf(lastModelled)+1).map(id=>data.fixes[id]).filter(Boolean);
  if(after.length){const top=pts.at(-1),dashed=new THREE.Line(new THREE.BufferGeometry().setFromPoints([top,...after.map(f=>new THREE.Vector3(f.xz[0],top.y,f.xz[1]))]),new THREE.LineDashedMaterial({color,dashSize:.6,gapSize:.4,transparent:true,opacity:.75}));dashed.computeLineDistances();result.add(dashed)}
  group.add(result);return result;
 }
 const routeFixes=r=>data.routes.find(x=>x.runway===r.runway&&x.name===r.sid)?.legs.map(l=>l.fix)||[];
 // Other SIDs of the same runway and aircraft with the same footprint (same residents in every band), and where this route splits from them.
 function sharedFootprint(r){
  const same=state.index.scenarios.filter(s=>s.runway===r.runway&&s.aircraft===r.aircraft&&s.sid!==r.sid&&[60,65,70].every(l=>s.residents[l]===r.residents[l]));
  if(!same.length)return '';
  const seqs=[r,...same].map(routeFixes);let n=0;while(seqs.every(s=>s[n]&&s[n]===seqs[0][n]))n++;
  if(!n)return '';
  const who=same.length===sidsFor(r.runway).length-1?`the other ${r.runway} routes`:same.map(s=>s.sid).join(', ');
  return `Same footprint as ${who} up to 10,000 ft; this route splits after ${seqs[0][n-1]}.`;
 }
 // A long level hold (for example 9,000 ft for 64 NM) makes fuel and time to 10,000 ft much larger while the footprint stays the same.
 function holdNote(r){
  const m=(r.notes||[]).map(n=>/Held at ([\d,]+) ft for ([\d.]+) NM/.exec(n)).find(m=>m&&Number(m[2])>=30);
  if(!m||!sharedFootprint(r))return '';
  return `Held at or below ${m[1]} ft for ${m[2]} NM, so fuel and time to 10,000 ft are about double the other ${r.runway} routes, while the noise near the city is the same.`;
 }
 function buildPlaceLabels(record){
  for(const l of placeLabels)l.el.remove();placeLabels=[];
  for(const p of record.places.slice(0,5)){
   if(!Number.isFinite(p.lat)||!Number.isFinite(p.lon))continue;
   const [x,z]=project(p.lat,p.lon),el=element('span',`${p.name} · ${num(p.lamax_db,1)} dB`,'scenario-place-label');labels.append(el);placeLabels.push({el,position:new THREE.Vector3(x,.05,z)});
  }
 }
 // Frame the 60 dB footprint on the ground from a steep, slightly tilted top view (the footprint is the subject).
 function fitCamera(){
  const box=new THREE.Box3();if(contours?.userData.bounds&&!contours.userData.bounds.isEmpty())box.union(contours.userData.bounds);
  if(box.isEmpty()){const low=track?.userData.below10k||[];low.forEach(p=>box.expandByPoint(new THREE.Vector3(p.x,0,p.z)))}
  if(box.isEmpty())return;
  const center=box.getCenter(new THREE.Vector3()),size=box.getSize(new THREE.Vector3()),half=Math.tan(THREE.MathUtils.degToRad(camera.fov/2));
  // keep the footprint in the free area left of the climb card on wide screens
  const hostRect=host.getBoundingClientRect(),cardRect=card.getBoundingClientRect(),w=hostRect.width||1,h=hostRect.height||1;
  const free=!card.hidden&&w>900&&cardRect.width?Math.max(w*.5,cardRect.left-hostRect.left):w;
  const dist=Math.min(300,Math.max(6,1.45*Math.max(size.z/2/half,size.x/2/(half*free/h))));
  const shift=(w-free)/2*(2*dist*half*(w/h))/w;
  const tilt=THREE.MathUtils.degToRad(28);center.y=0;center.x+=shift;
  controls.target.copy(center);camera.position.set(center.x,dist*Math.cos(tilt),center.z+dist*Math.sin(tilt));controls.update();
 }

 async function refresh(){
  const mine=++token,record=findRecord();
  if(!record){setNotice('No scenario for this combination.',true);return}
  let geo;
  try{geo=await loadGeo(record)}catch(e){if(mine===token)setNotice(e.message,true);return}
  if(mine!==token)return;
  setNotice('');state.record=record;
  dispose(contours);dispose(track);contours=buildContours(geo);group.add(contours);track=buildTrack(record);lastVertical=vertical();
  dispose(plane);plane=aircraft?aircraft(colors[record.runway]):null;if(plane)group.add(plane);
  play.t=0;play.playing=false;play.dirty=true;
  buildPlaceLabels(record);renderResults();renderCard();if(state.enabled)fitCamera();
 }

 function tile(caption,value,unit){const t=element('div',undefined,'scenario-tile');t.append(element('small',caption+' · MODELLED'));const s=element('strong',value);if(unit)s.append(' ',element('em',unit));t.append(s);return t}
 function section(title){const s=element('div',undefined,'scenario-block');s.append(element('h3',title));return s}
 function renderResults(){
  results.replaceChildren();const r=state.record,idx=state.index;if(!r||!idx)return;
  const n=state.perDay,t=r.to10k;
  const one=section('One departure');const grid=element('div',undefined,'scenario-tiles');
  grid.append(tile('FUEL TO 10,000 FT',num(t.fuel_kg),'kg'),tile('CO₂',num(t.co2_kg),'kg'),tile('TIME TO 10,000 FT',clock(t.time_s),'min'),tile('DISTANCE TO 10,000 FT',num(t.distance_nm,1),'NM'));one.append(grid);
  const hold=holdNote(r);if(hold)one.append(element('p',hold,'scenario-explain'));results.append(one);
  const noise=section('Noise footprint (LAmax, one departure)');
  for(const level of idx.levels_db||[60,65,70]){
   const row=element('div',undefined,'scenario-noise'),sw=element('i');sw.style.background=levelColors[level];
   const text=element('span');text.append(element('b',num(r.residents?.[level]??0)),' residents inside · '+num(r.contour_area_km2?.[level]??0,1)+' km²');
   row.append(sw,element('em','≥'+level+' dB'),text,element('small','modelled'));noise.append(row);
  }
  const shared=sharedFootprint(r);if(shared)noise.append(element('p',shared,'scenario-explain'));
  results.append(noise);
  const near=section('Nearest named places');const list=element('ol',undefined,'scenario-places');
  for(const p of r.places.slice(0,5)){
   const li=element('li'),name=element('span',undefined,'scenario-place-name');name.append(element('b',p.name));
   if(p.name_ar){const ar=element('bdi',p.name_ar);ar.dir='rtl';ar.lang='ar';ar.className='scenario-ar';name.append(' ',ar)}
   li.append(name,element('small',`${num(p.lamax_db,1)} dB LAmax · ${num(p.km_from_track,1)} km from the track · modelled`));list.append(li);
  }
  near.append(list);results.append(near);
  const day=section(`Per day and per year · ${n} ${n===1?'departure':'departures'} a day`);const dg=element('div',undefined,'scenario-tiles');
  dg.append(tile('FUEL PER DAY',tons(t.fuel_kg*n),'t'),tile('CO₂ PER DAY',tons(t.co2_kg*n),'t'),tile('FUEL PER YEAR',tons(t.fuel_kg*n*365),'t'),tile('CO₂ PER YEAR',tons(t.co2_kg*n*365),'t'));day.append(dg);
  day.append(element('p',departuresSentence(n),'scenario-intro'));results.append(day);
  const notes=[...(r.notes||[]),...(r.flags||[])];
  if(notes.length){const nb=element('div',undefined,'scenario-notes');for(const text of notes)nb.append(element('p',String(text)));results.append(nb)}
  const det=element('details',undefined,'scenario-assumptions');det.append(element('summary','Assumptions'));const ul=element('ul');for(const a of idx.assumptions||[])ul.append(element('li',a));det.append(ul);
  const credit=element('p',undefined,'scenario-credit'),a=(href,text)=>{const l=element('a',text);l.href=href;l.target='_blank';l.rel='noopener';return l};
  credit.append('Noise and population: Maha\'s ',a(LINKS.maha,'oejn-noise-population'),' (ECAC Doc 29, WorldPop). Fuel: ',a(LINKS.openap,'OpenAP'),', with Hala\'s ',a(LINKS.hala,'fuel and weather work'),' as a reference. Recorded-flight mode: Khalid\'s A2 pipeline. Procedures: A1 dataset (SANS AIP AMDT 10/26).');
  det.append(credit);results.append(det);
 }

 function renderCard(){
  const r=state.record;svg.replaceChildren();if(!r)return;
  const color=colors[r.runway],name=state.index.aircraft?.[r.aircraft]?.name||r.aircraft;
  cardSub.textContent=`${r.runway} · ${r.sid} · ${name}`;
  const W=320,H=150,L=40,R=12,T=10,B=24,prof=r.profile,maxD=Math.max(...prof.map(p=>p[0]),1),maxA=Math.max(12000,Math.ceil(Math.max(...prof.map(p=>p[1]))/4000)*4000);
  const X=d=>L+d/maxD*(W-L-R),Y=a=>H-B-a/maxA*(H-T-B);
  const mk=(tag,attrs,text)=>{const e=document.createElementNS(svgNS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;svg.append(e);return e};
  for(let a=0;a<=maxA;a+=4000){mk('line',{x1:L,x2:W-R,y1:Y(a),y2:Y(a),class:'grid'});mk('text',{x:L-5,y:Y(a)+3,'text-anchor':'end',class:'tick'},num(a))}
  const step=maxD>60?20:maxD>30?10:5;for(let d=0;d<=maxD+.01;d+=step){mk('line',{x1:X(d),x2:X(d),y1:H-B,y2:H-B+3,class:'axis'});mk('text',{x:X(d),y:H-B+12,'text-anchor':'middle',class:'tick'},String(d))}
  mk('text',{x:W-R,y:H-1,'text-anchor':'end',class:'tick'},'NM');
  mk('line',{x1:L,x2:L,y1:T,y2:H-B,class:'axis'});mk('line',{x1:L,x2:W-R,y1:H-B,y2:H-B,class:'axis'});
  const path='M'+prof.map(p=>X(p[0]).toFixed(1)+','+Y(p[1]).toFixed(1)).join('L');
  mk('path',{d:path+`L${X(prof.at(-1)[0]).toFixed(1)},${H-B}L${X(0)},${H-B}Z`,fill:color,opacity:.12});
  mk('line',{x1:L,x2:W-R,y1:Y(10000),y2:Y(10000),class:'limit'});
  mk('path',{d:path,fill:'none',stroke:color,'stroke-width':1.8});
  r.fixes.filter(f=>f.dist_nm<=maxD).forEach((f,i)=>{const x=X(f.dist_nm),y=Y(f.alt_ft);mk('circle',{cx:x,cy:y,r:2.2,fill:'#fff',stroke:color,'stroke-width':1.2});mk('text',{x,y:y+(i%2?11:-5),'text-anchor':'middle',class:'fixid'},f.id)});
  const d10=r.to10k.distance_nm,xm=Math.min(X(d10),W-R);mk('circle',{cx:xm,cy:Y(10000),r:3.6,fill:color,stroke:'#fff','stroke-width':1.2});
  const label=`10,000 ft · ${num(d10,1)} NM`,anchorEnd=xm>W*.6;mk('text',{x:anchorEnd?xm-6:xm+6,y:Y(10000)-6,'text-anchor':anchorEnd?'end':'start',class:'mark'},label);
  chart={X,Y,dot:mk('circle',{cx:X(0),cy:Y(0),r:4,class:'play-dot',fill:'#fff',stroke:color,'stroke-width':2.2})};play.dirty=true;
 }
 // Playback: move the aircraft along the track, the dot along the chart, and update the live counters.
 function updatePlayback(dt){
  const r=state.record;if(!r||!plane)return;
  if(play.playing){play.t+=dt*play.speed;if(play.t>=r.to10k.time_s){play.t=r.to10k.time_s;play.playing=false}play.dirty=true}
  plane.scale.setScalar(Math.min(4,Math.max(.25,camera.position.distanceTo(plane.position)*.032)));  // same on-screen size as the demo aircraft
  if(!play.dirty)return;play.dirty=false;
  const s=playbackAt(r,play.t),[x,z]=project(s.lat,s.lon),[ax,az]=project(s.from[3],s.from[2]),[bx,bz]=project(s.to[3],s.to[2]);
  plane.position.set(x,s.alt*FT_KM*vertical()+.035,z);if(bx!==ax||bz!==az)plane.rotation.y=Math.atan2(-(bx-ax),-(bz-az));
  if(chart){chart.dot.setAttribute('cx',chart.X(s.d).toFixed(1));chart.dot.setAttribute('cy',chart.Y(s.alt).toFixed(1))}
  liveTime.textContent=clock(s.t)+' min';liveAlt.textContent=num(s.done?10000:s.alt)+' ft';liveFuel.textContent=num(s.fuel)+' kg';liveCo2.textContent=num(s.co2)+' kg';
  playBtn.textContent=play.playing?'Ⅱ Pause':'▶ Play';
 }

 function setMode(enabled){
  if(enabled===state.enabled){if(enabled)onMode(true);return}  // re-selecting Scenario must hide the demo again
  state.enabled=enabled;group.visible=enabled;panel.hidden=!enabled;labels.hidden=!enabled;legend.hidden=!enabled;card.hidden=!enabled;
  document.body.classList.toggle('scenario-mode-active',enabled);
  if(enabled){onMode(true);start()}
 }
 async function start(){
  try{await loadIndex()}catch{return}
  if(!state.sid){const first=state.index.scenarios.find(s=>s.runway===state.runway)||state.index.scenarios[0];state.runway=first.runway;state.sid=first.sid;if(!state.index.aircraft?.[state.aircraft])state.aircraft=first.aircraft}
  syncInputs();
  if(state.record&&state.record===findRecord()){renderResults();renderCard();fitCamera()}else await refresh();
 }
 function update(dt=0){
  if(!state.enabled)return;
  if(track&&lastVertical!==vertical()){dispose(track);track=buildTrack(state.record);lastVertical=vertical();play.dirty=true}
  updatePlayback(dt);
  const w=host.clientWidth,h=host.clientHeight,v=new THREE.Vector3(),kept=[];
  // labels are in priority order (nearest first); hide a label that would overlap one already shown
  for(const l of placeLabels){
   v.copy(l.position).project(camera);let show=v.z>=-1&&v.z<=1&&Math.abs(v.x)<1.05&&Math.abs(v.y)<1.05;
   if(show){
    const x=(v.x*.5+.5)*w,y=(-v.y*.5+.5)*h;
    if(!l.w){l.el.style.display='';l.w=l.el.offsetWidth;l.h=l.el.offsetHeight}
    const box=[x-l.w/2-2,y-l.h-2,x+l.w/2+2,y+2];
    show=!kept.some(b=>box[0]<b[2]&&b[0]<box[2]&&box[1]<b[3]&&b[1]<box[3]);
    if(show){kept.push(box);l.el.style.left=x+'px';l.el.style.top=y+'px'}
   }
   l.el.style.display=show?'':'none';
  }
 }
 return {update,setMode,projectionError:worst,
  select:async(runway,sid,aircraft,perDay)=>{try{await loadIndex()}catch(e){throw e}await choose({runway,sid,aircraft,perDay:perDay??state.perDay});if(!state.record)throw Error(state.error||'No scenario for this combination.');return state.record.id},
  getState:()=>({enabled:state.enabled,runway:state.runway,sid:state.sid,aircraft:state.aircraft,perDay:state.perDay,recordId:state.record?.id||null,error:state.error,groupVisible:group.visible,contourMeshes:contours?.children.filter(o=>o.isMesh).length||0,trackVisible:Boolean(track),places:placeLabels.length,placesShown:placeLabels.filter(l=>l.el.style.display!=='none').length,
   playback:{t:play.t,playing:play.playing,time:liveTime.textContent,altitude:liveAlt.textContent,fuel:liveFuel.textContent,co2:liveCo2.textContent}})};
}
