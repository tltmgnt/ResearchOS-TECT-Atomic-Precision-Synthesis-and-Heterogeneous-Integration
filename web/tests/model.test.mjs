import assert from 'node:assert/strict';
import{analyze,validate,csv,demo}from'../model.mjs';
const r=demo(),result=analyze(r);
assert.equal(result.total_thickness_nm,10);
assert.deepEqual(result.interfaces.map(i=>i.depth_nm),[0,4]);
assert.ok(Math.abs(result.interfaces[0].nominal_mismatch_percent-2)<1e-12);
assert.deepEqual(result.target_checks.map(c=>c.status),['met','no-data']);
assert.equal(result.target_checks[0].basis,'synthetic');
for(const mutation of [r=>r.id='../escape',r=>r.layers=[],r=>r.layers[0].thickness_nm=0,r=>r.layers[0].lattice_constant_A=Infinity,r=>r.layers[0].thickness_nm=true,r=>r.layers.push({...r.layers[0]}),r=>r.measurements[0].uncertainty=-1,r=>r.measurements[0].evidence_ids=['missing'],r=>r.data_kind='experimental']){let bad=structuredClone(r);mutation(bad);assert.throws(()=>validate(bad))}
let unmet=demo();unmet.measurements[0].value=.9;assert.equal(analyze(unmet).target_checks[0].status,'unmet');unmet.targets[0].operator='>=';assert.equal(analyze(unmet).target_checks[0].status,'met');
let experimental=demo();experimental.data_kind='experimental';experimental.evidence=[{id:'raw',path:'raw.csv',sha256:'a'.repeat(64),description:'Test only'}];experimental.measurements[0].evidence_ids=['raw'];validate(experimental);
for(const path of ['../escape','/absolute','C:\\absolute']){let bad=structuredClone(experimental);bad.evidence[0].path=path;assert.throws(()=>validate(bad))}
let overflow=demo();overflow.layers[0].thickness_nm=1.7e308;overflow.layers[1].thickness_nm=1.7e308;assert.throws(()=>analyze(overflow));
let quoted=demo();quoted.substrate.material='Material,"quoted"';assert.ok(csv(analyze(quoted)).includes('"Material,""quoted"""'));
assert.equal(JSON.stringify(analyze(r)),JSON.stringify(analyze(r)));
console.log('Web record validation, geometry, target checks, path restrictions, overflow and CSV tests passed.');
