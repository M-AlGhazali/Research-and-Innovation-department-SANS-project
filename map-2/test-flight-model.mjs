import assert from 'node:assert/strict';
import fs from 'node:fs';
import {buildFlight,sampleFlight,advance,altitudeValue} from './flight-model.mjs';
const data=JSON.parse(fs.readFileSync(new URL('./data.json',import.meta.url),'utf8'));
let testedPoints=0;
assert.equal(data.routes.length,24);assert.equal(data.runways.length,3);
for(const route of data.routes){
 const runway=data.runways.find(r=>r.id===route.runway),f=buildFlight(route,runway,data.fixes);
 assert.equal(f.points.length,route.legs.length+3);
 const start=sampleFlight(f,0);assert.equal(start.x,runway.start[0]);assert.equal(start.z,runway.start[1]);assert.equal(start.altFt,0);
 for(let i=0;i<f.segments.length;i++){
  const segment=f.segments[i],s=sampleFlight(f,segment.end);
  assert(Math.abs(s.x-segment.b.xz[0])<1e-7,route.name+' misses '+segment.b.name);
  assert(Math.abs(s.z-segment.b.xz[1])<1e-7);assert(Math.abs(s.altFt-segment.b.altFt)<1e-7);testedPoints++;
  const raw=segment.b.altitude;if(raw){const limit=altitudeValue(raw);assert(raw[0]==='@'?s.altFt===limit:raw[0]==='+'?s.altFt>=limit:s.altFt<=limit)}
 }
 const last=sampleFlight(f,f.duration);assert.equal(last.next,route.legs.at(-1).fix);assert(last.complete);
 const state={flight:f,elapsed:0,playing:true,loop:true,loops:0};advance(state,f.duration+2);assert.equal(state.loops,1);assert.equal(state.elapsed,0);assert.equal(sampleFlight(f,state.elapsed).altFt,0);
 state.playing=false;advance(state,100);assert.equal(state.elapsed,0);
 state.playing=true;state.loop=false;advance(state,f.duration+10);assert.equal(state.playing,false);assert.equal(state.elapsed,f.duration);
}
const report={routesTested:24,runways:3,segmentEndpointsTested:testedPoints,checks:['Ground start','Every published fix reached exactly','Demo endpoint heights satisfy transcribed numeric restrictions','Final destination reached','Loop returns to start','Pause freezes time','Loop-off stops at destination'],result:'passed'};
fs.writeFileSync(new URL('./playback-validation.json',import.meta.url),JSON.stringify(report,null,2));console.log(report);
