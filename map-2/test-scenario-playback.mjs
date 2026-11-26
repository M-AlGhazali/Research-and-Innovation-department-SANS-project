// Scenario playback: for all 48 scenarios the counters start at zero and end exactly on the saved totals at 10,000 ft.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {playbackAt} from './scenario-playback.mjs';
const index=JSON.parse(fs.readFileSync(new URL('./scenarios/index.json',import.meta.url),'utf8'));
assert.equal(index.scenarios.length,48);
for(const r of index.scenarios){
 const T=r.to10k.time_s,start=playbackAt(r,0),end=playbackAt(r,T),after=playbackAt(r,T+999);
 assert.equal(start.fuel,0,r.id);assert.equal(start.d,0,r.id);assert(start.alt<100,r.id);
 assert.equal(end.fuel,r.to10k.fuel_kg,r.id);assert.equal(end.co2,r.to10k.co2_kg,r.id);assert.equal(end.d,r.to10k.distance_nm,r.id);assert(end.done,r.id);
 assert(Math.abs(end.alt-10000)<150,`${r.id} ends at ${end.alt} ft`);
 assert.deepEqual(after,end,r.id);
 let prev=start;for(let i=1;i<=50;i++){const s=playbackAt(r,T*i/50);assert(s.fuel>=prev.fuel&&s.d>=prev.d,r.id);prev=s}
}
console.log('scenario playback: 48 scenarios OK');
