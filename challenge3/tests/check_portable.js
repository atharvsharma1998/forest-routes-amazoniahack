const fs=require('fs'),assert=require('assert');
const {ForestRouter}=require('../src/forest_routes/router.js');
const dir=process.argv[2]||'challenge3/private/reviewed';const g=JSON.parse(fs.readFileSync(dir+'/compact-graph.json'));
const t=performance.now(),engine=new ForestRouter(g),load_ms=performance.now()-t;
const expected=JSON.parse(fs.readFileSync(dir+'/routes.json'));const actual=[];
for(const p of g.terminals){const r=engine.route(p.origin,p.destination,1000),ref=expected.find(x=>x.pair_id===p.id);assert.strictEqual(r.candidate_connected,ref.candidate_connected,p.id+' connectivity');if(r.candidate_connected){assert(Math.abs(r.network_distance_km-ref.network_distance_km)<.002,p.id+' route distance');assert(Math.abs(r.final_walk_lower_bound_m-ref.final_walk_lower_bound_m)<.03,p.id+' access distance')}actual.push({pair_id:p.id,...r,segments:undefined})}
const result={runtime:process.version,platform:process.platform,load_ms,heap_used_mb:process.memoryUsage().heapUsed/1048576,array_buffers_mb:process.memoryUsage().arrayBuffers/1048576,matched_pairs:actual.length,queries:actual};fs.writeFileSync(dir+'/portable-validation.json',JSON.stringify(result,null,2));console.log(JSON.stringify({...result,queries:actual.map(r=>({pair_id:r.pair_id,candidate:r.candidate_connected,ms:r.query_ms}))},null,2));
