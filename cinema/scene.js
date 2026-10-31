import * as THREE from 'three';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {UnrealBloomPass} from 'three/addons/postprocessing/UnrealBloomPass.js';
import {ShaderPass} from 'three/addons/postprocessing/ShaderPass.js';
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js';
import {gsap} from 'gsap';
import {seeded,makeTerrain,activeStage,cameraShot,clamp,smooth} from './math.js';
import {waterVertex,waterFragment,cloudVertex,cloudFragment,skyVertex,skyFragment} from './shaders.js';

const v=p=>new THREE.Vector3(...p);
function terrainWorld(scene,config,updates){
 const random=seeded(config.seed),height=makeTerrain(config.seed);
 const geometry=new THREE.PlaneGeometry(70,64,210,190);geometry.rotateX(-Math.PI/2);
 const p=geometry.attributes.position,colors=new Float32Array(p.count*3),color=new THREE.Color();
 for(let i=0;i<p.count;i++){
  const x=p.getX(i),z=p.getZ(i),y=height(x,z);p.setY(i,y);
  const slope=Math.hypot(height(x+.15,z)-height(x-.15,z),height(x,z+.15)-height(x,z-.15))/.3;
  if(y>7.2+Math.sin(x*1.4+z)*.35)color.set('#dbe8e8');else if(slope>1.05||y>4.2)color.set('#697677');else if(y<.4)color.set('#bcb193');else color.set('#52734f');
  color.multiplyScalar(.86+random()*.22);color.toArray(colors,i*3);
 }
 geometry.setAttribute('color',new THREE.BufferAttribute(colors,3));geometry.computeVertexNormals();
 const terrain=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({vertexColors:true,roughness:.94}));terrain.receiveShadow=true;terrain.castShadow=true;scene.add(terrain);
 const waterGeo=new THREE.PlaneGeometry(110,100,180,160);waterGeo.rotateX(-Math.PI/2);
 const waterMat=new THREE.ShaderMaterial({vertexShader:waterVertex,fragmentShader:waterFragment,uniforms:{uTime:{value:0},uSun:{value:v([-1,1,-.7]).normalize()}}});
 const ocean=new THREE.Mesh(waterGeo,waterMat);ocean.position.y=-.21;scene.add(ocean);updates.push(t=>waterMat.uniforms.uTime.value=t);
 const count=420,trunks=new THREE.InstancedMesh(new THREE.CylinderGeometry(.045,.075,.65,5),new THREE.MeshStandardMaterial({color:'#665041',roughness:1}),count);
 const leaves=new THREE.InstancedMesh(new THREE.ConeGeometry(.42,.85,10),new THREE.MeshStandardMaterial({color:'#315a40',roughness:.92}),count*3);
 trunks.castShadow=true;leaves.castShadow=true;leaves.receiveShadow=true;
 const dummy=new THREE.Object3D();let found=0;
 for(let k=0;k<5000&&found<count;k++){
  const x=random()*27+1,z=random()*42-24,y=height(x,z);
  if(y<.45||y>3.8)continue;
  const scale=.6+random()*.75;
  dummy.position.set(x,y+scale*.3,z);dummy.scale.setScalar(scale);dummy.rotation.y=random()*Math.PI;dummy.updateMatrix();trunks.setMatrixAt(found,dummy.matrix);
  for(let tier=0;tier<3;tier++){dummy.position.y=y+scale*(.65+tier*.35);dummy.scale.setScalar(scale*(1-tier*.19));dummy.updateMatrix();leaves.setMatrixAt(found*3+tier,dummy.matrix);leaves.setColorAt(found*3+tier,new THREE.Color().setHSL(.3+random()*.05,.22+random()*.15,.5+random()*.13));}found++;
 }
 trunks.count=found;leaves.count=found*3;scene.add(trunks,leaves);
 const riverPoints=[];
 for(let i=0;i<=60;i++){const u=i/60,x=11*(1-u)+1.2,z=-11+u*18+Math.sin(u*Math.PI*3)*.7;riverPoints.push(new THREE.Vector3(x,height(x,z)+.065,z));}
 const riverCurve=new THREE.CatmullRomCurve3(riverPoints);const verts=[],indices=[];
 for(let i=0;i<=150;i++){
  const u=i/150,pos=riverCurve.getPoint(u),t=riverCurve.getTangent(u),side=new THREE.Vector3(-t.z,0,t.x).normalize().multiplyScalar(.09+u*.19);
  verts.push(pos.x+side.x,pos.y,pos.z+side.z,pos.x-side.x,pos.y,pos.z-side.z);
  if(i<150){let a=i*2;indices.push(a,a+1,a+2,a+1,a+3,a+2);}
 }
 const rg=new THREE.BufferGeometry();rg.setAttribute('position',new THREE.Float32BufferAttribute(verts,3));rg.setIndex(indices);rg.computeVertexNormals();
 const river=new THREE.Mesh(rg,new THREE.MeshPhysicalMaterial({color:'#69b8c1',metalness:.35,roughness:.17,side:THREE.DoubleSide}));scene.add(river);
 const cloudMeshes=[];
 for(let i=0;i<3;i++){
  const material=new THREE.ShaderMaterial({vertexShader:cloudVertex,fragmentShader:cloudFragment,side:THREE.BackSide,transparent:true,depthWrite:false,uniforms:{uCamera:{value:new THREE.Vector3()},uTime:{value:0},uFormation:{value:0}}});
  const cloud=new THREE.Mesh(new THREE.BoxGeometry(1,1,1),material);cloud.scale.set(7+i*.7,3.5,4.8);cloud.position.set(1+i*4,8.5+i*.25,-5-i*3);cloud.renderOrder=10+i;scene.add(cloud);cloudMeshes.push(cloud);
 }
 updates.push((t,camera)=>{
  const formation=(config.stages||[]).find(s=>s.process==='condensation');const amount=formation?smooth(formation.start,Math.min(formation.start+2,formation.end),t):.8;
  for(let i=0;i<cloudMeshes.length;i++){const c=cloudMeshes[i];c.position.x=1+i*4+t*.045;c.updateMatrixWorld(true);c.material.uniforms.uCamera.value.copy(camera.position);c.worldToLocal(c.material.uniforms.uCamera.value);c.material.uniforms.uFormation.value=amount;c.material.uniforms.uTime.value=t;}
 });
 const vaporN=300,vaporData=new Float32Array(vaporN*3),vaporSeed=Array.from({length:vaporN},()=>[random(),random(),random()]);
 const vg=new THREE.BufferGeometry();vg.setAttribute('position',new THREE.BufferAttribute(vaporData,3));
 const vm=new THREE.PointsMaterial({color:'#d5eff2',size:.045,transparent:true,opacity:0,depthWrite:false,sizeAttenuation:true});const vapor=new THREE.Points(vg,vm);scene.add(vapor);
 const rainN=1300,rainData=new Float32Array(rainN*6),rainSeed=Array.from({length:rainN},()=>[random(),random(),random()]);
 const rainGeo=new THREE.BufferGeometry();rainGeo.setAttribute('position',new THREE.BufferAttribute(rainData,3));const rainMat=new THREE.LineBasicMaterial({color:'#b3d9ed',transparent:true,opacity:0,depthWrite:false});scene.add(new THREE.LineSegments(rainGeo,rainMat));
 const runoffN=70,runoffData=new Float32Array(runoffN*3),runoffGeo=new THREE.BufferGeometry();runoffGeo.setAttribute('position',new THREE.BufferAttribute(runoffData,3));const runoffMat=new THREE.PointsMaterial({color:'#c4f2f2',size:.075,transparent:true,opacity:0});scene.add(new THREE.Points(runoffGeo,runoffMat));
 updates.push(t=>{
  vm.opacity=activeStage(config.stages,'evaporation',t)*.5;
  for(let i=0;i<vaporN;i++){const r=vaporSeed[i],u=(r[0]+t*.13)%1;vaporData[i*3]=-10+r[1]*9+Math.sin(u*8+r[2]*6)*.35+u*3;vaporData[i*3+1]=-.1+u*9;vaporData[i*3+2]=-3+r[2]*10;}
  vg.attributes.position.needsUpdate=true;
  rainMat.opacity=activeStage(config.stages,'rain',t)*.48;
  for(let i=0;i<rainN;i++){const r=rainSeed[i],x=2+r[0]*11,z=-10+r[1]*9,y=8.1-((r[2]+t*.6)%1)*8;const k=i*6;rainData.set([x,y,z,x-.04,y-.22,z],k);}
  rainGeo.attributes.position.needsUpdate=true;runoffMat.opacity=activeStage(config.stages,'runoff',t)*.7;
  for(let i=0;i<runoffN;i++){const point=riverCurve.getPoint((i/runoffN+t*.17)%1);runoffData.set([point.x,point.y+.06,point.z],i*3);}runoffGeo.attributes.position.needsUpdate=true;
 });
}

function genericWorld(scene,config,updates){
 const random=seeded(config.seed),objects=new Map();
 if(config.world==='space'){
  scene.background=new THREE.Color('#030812');scene.fog=null;
  const stars=new Float32Array(1500*3);for(let i=0;i<stars.length;i++)stars[i]=(random()-.5)*180;
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(stars,3));scene.add(new THREE.Points(g,new THREE.PointsMaterial({color:'#dfe9ff',size:.13,sizeAttenuation:true})));
 }else{
  const floor=new THREE.Mesh(new THREE.PlaneGeometry(500,500),new THREE.MeshStandardMaterial({color:'#182535',roughness:.48,metalness:.15}));floor.rotation.x=-Math.PI/2;floor.position.y=-2.5;floor.receiveShadow=true;scene.add(floor);
 }
 for(const spec of config.objects||[]){
  let geometry;
  switch(spec.shape){case'box':geometry=new THREE.BoxGeometry(1,1,1);break;case'cone':geometry=new THREE.ConeGeometry(.5,1,40);break;case'cylinder':geometry=new THREE.CylinderGeometry(.5,.5,1,40);break;case'torus':geometry=new THREE.TorusGeometry(.5,.15,20,70);break;case'plane':geometry=new THREE.PlaneGeometry(1,1);break;default:geometry=new THREE.SphereGeometry(.5,48,32);}
  const material=new THREE.MeshPhysicalMaterial({color:spec.color,roughness:spec.roughness,metalness:spec.metalness,transparent:spec.opacity<1,opacity:spec.opacity,clearcoat:.25});
  const mesh=new THREE.Mesh(geometry,material);mesh.position.fromArray(spec.position);mesh.scale.fromArray(spec.scale);mesh.castShadow=true;mesh.receiveShadow=true;scene.add(mesh);objects.set(spec.id,{mesh,base:mesh.position.clone(),scale:mesh.scale.clone()});
 }
 for(const motion of config.motions||[]){
  const obj=objects.get(motion.target);if(!obj)continue;
  const curve=motion.path.length>=2?new THREE.CatmullRomCurve3(motion.path.map(v)):null;
  updates.push(t=>{let u=clamp((t-motion.start)/(motion.end-motion.start));if(motion.repeats>1&&u<1)u=(u*motion.repeats)%1;
   if(motion.action==='move'&&curve)obj.mesh.position.copy(curve.getPoint(u));
   else if(motion.action==='rotate')obj.mesh.rotation.y=motion.amount*u;
   else if(motion.action==='pulse')obj.mesh.scale.copy(obj.scale).multiplyScalar(1+Math.sin(u*Math.PI*2)*motion.amount);
   else if(motion.action==='reveal'||motion.action==='hide'){obj.mesh.material.transparent=true;obj.mesh.material.opacity=motion.action==='hide'?1-u:u;obj.mesh.visible=obj.mesh.material.opacity>.01;}
  });
 }
}

export async function createFilm(plan,width=960,height=540){
 const config=plan.cinema;if(!config)throw new Error('Missing procedural 3D scene configuration.');
 const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true,powerPreference:'high-performance'});renderer.setPixelRatio(1);renderer.setSize(width,height);
 renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=.98;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
 renderer.info.autoReset=false;
 document.body.replaceChildren(renderer.domElement);document.body.style.cssText='margin:0;overflow:hidden;background:#000';
 const scene=new THREE.Scene();scene.background=new THREE.Color('#95b6c2');scene.fog=new THREE.FogExp2('#9fb7bc',.009);
 const camera=new THREE.PerspectiveCamera(45,width/height,.1,220);
 scene.add(new THREE.HemisphereLight('#d6edff','#546441',1.3));
 const sun=new THREE.DirectionalLight('#ffe4bc',3.2);sun.position.set(-18,23,-12);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);sun.shadow.camera.left=-35;sun.shadow.camera.right=35;sun.shadow.camera.top=35;sun.shadow.camera.bottom=-35;sun.shadow.normalBias=.04;sun.shadow.bias=-.00015;scene.add(sun);
 const sky=new THREE.Mesh(new THREE.SphereGeometry(150,32,24),new THREE.ShaderMaterial({vertexShader:skyVertex,fragmentShader:skyFragment,side:THREE.BackSide,uniforms:{uSun:{value:sun.position.clone().normalize()}}}));scene.add(sky);
 const solar=new THREE.Mesh(new THREE.SphereGeometry(2.3,24,20),new THREE.MeshBasicMaterial({color:new THREE.Color(5,3.8,2.1)}));solar.position.copy(sun.position).normalize().multiplyScalar(100);scene.add(solar);
 const updates=[];
 if(config.world==='landscape')terrainWorld(scene,config,updates);else{sky.visible=false;solar.visible=false;genericWorld(scene,config,updates);}
 const composer=new EffectComposer(renderer);composer.addPass(new RenderPass(scene,camera));composer.addPass(new UnrealBloomPass(new THREE.Vector2(width,height),.18,.3,1.05));
 composer.addPass(new ShaderPass({uniforms:{tDiffuse:{value:null}},vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',fragmentShader:'uniform sampler2D tDiffuse;varying vec2 vUv;void main(){vec3 c=texture2D(tDiffuse,vUv).rgb;float vig=smoothstep(.95,.18,distance(vUv,vec2(.5)));c*=.86+.14*vig;gl_FragColor=vec4(c,1.);}'}));composer.addPass(new OutputPass());
 const ease=gsap.parseEase('power1.inOut');
 function frame(t){
  const shot=cameraShot(config.shots,t);if(!shot)throw new Error('No camera shot.');
  const u=ease(clamp((t-shot.start)/(shot.end-shot.start)));camera.position.lerpVectors(v(shot.position),v(shot.end_position),u);camera.lookAt(v(shot.target).lerp(v(shot.end_target),u));camera.fov=shot.fov;camera.updateProjectionMatrix();
  for(const update of updates)update(t,camera);renderer.info.reset();composer.render();
 }
 frame(0);
 if(config.world==='landscape')renderer.shadowMap.autoUpdate=false;
 const gl=renderer.getContext(),debug=gl.getExtension('WEBGL_debug_renderer_info');
 return {frame,canvas:renderer.domElement,info:()=>({renderer:debug?gl.getParameter(debug.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER),drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles,three:THREE.REVISION})};
}
window.createFilm=createFilm;
