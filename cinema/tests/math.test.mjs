import test from 'node:test';
import assert from 'node:assert/strict';
import {seeded,makeTerrain,activeStage,cameraShot} from '../math.js';
test('terrain and procedural randomness are deterministic',()=>{
 const a=seeded(42),b=seeded(42);for(let i=0;i<30;i++)assert.equal(a(),b());
 const terrain=makeTerrain(42);assert.equal(terrain(4,2),makeTerrain(42)(4,2));assert.ok(terrain(11,-10)>terrain(-15,0));
});
test('physical effects follow stage timing',()=>{
 const stages=[{process:'rain',start:3,end:8,intensity:1}];assert.equal(activeStage(stages,'rain',1),0);assert.ok(activeStage(stages,'rain',5)>.9);assert.equal(activeStage(stages,'rain',9),0);
});
test('camera cuts select the appropriate shot',()=>{const shots=[{start:0,end:4},{start:4,end:8}];assert.equal(cameraShot(shots,4),shots[1]);});
