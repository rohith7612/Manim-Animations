import {createNoise2D} from 'simplex-noise';
export const clamp=(x,a=0,b=1)=>Math.min(b,Math.max(a,x));
export const smooth=(a,b,x)=>{const t=clamp((x-a)/(b-a));return t*t*(3-2*t);};
export function seeded(seed=42){let n=seed>>>0;return()=>{n=(1664525*n+1013904223)>>>0;return n/4294967296;};}
export function makeTerrain(seed=42){
 const noise=createNoise2D(seeded(seed));
 return(x,z)=>{
  const coast=smooth(-2,3,x+Math.sin(z*.12)*1.8);
  const peaks=11*Math.exp(-((x-11)**2/40+(z+10)**2/55))+8*Math.exp(-((x-22)**2/65+(z+18)**2/45))+5.5*Math.exp(-((x-2)**2/60+(z+27)**2/35));
  const ridge=Math.abs(noise(x*.2,z*.2))*.28+noise(x*.55,z*.55)*.07;
  return -1.6+coast*(1.95+peaks*(.82+ridge)+noise(x*.13,z*.13)*.22);
 };
}
export function activeStage(stages,name,t){
 let value=0;
 for(const s of stages||[])if(s.process===name){const enter=smooth(s.start,s.start+Math.min(.9,(s.end-s.start)*.2),t),exit=1-smooth(s.end-.5,s.end,t);value=Math.max(value,enter*exit*s.intensity);}
 return value;
}
export function cameraShot(shots,t){return shots.find(s=>t>=s.start&&t<s.end)||shots.at(-1);}
