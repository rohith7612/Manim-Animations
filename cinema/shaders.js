export const waterVertex=`
uniform float uTime; varying vec3 vWorld; varying vec3 vNormalW;
void main(){
 vec3 p=position;float a=.10*sin(p.x*.72+uTime*.85)+.07*sin(p.z*.98-uTime*.7)+.025*sin(p.x*2.8+p.z*1.8+uTime*1.9);
 p.y+=a;float dx=.072*cos(p.x*.72+uTime*.85)+.07*cos(p.x*2.8+p.z*1.8+uTime*1.9);
 float dz=.0686*cos(p.z*.98-uTime*.7)+.045*cos(p.x*2.8+p.z*1.8+uTime*1.9);
 vNormalW=normalize(vec3(-dx,1.,-dz));vWorld=(modelMatrix*vec4(p,1.)).xyz;gl_Position=projectionMatrix*viewMatrix*vec4(vWorld,1.);
}`;
export const waterFragment=`
uniform float uTime;uniform vec3 uSun;varying vec3 vWorld;varying vec3 vNormalW;
void main(){
 vec3 n=normalize(vNormalW),view=normalize(cameraPosition-vWorld),r=reflect(-view,n);
 float fresnel=pow(1.-max(dot(n,view),0.),3.);
 vec3 deep=vec3(.005,.065,.105),sky=mix(vec3(.27,.52,.65),vec3(.08,.24,.42),clamp(r.y,0.,1.));
 float glint=pow(max(dot(normalize(r),normalize(uSun)),0.),220.);
 float small=sin(vWorld.x*4.+uTime*2.)*sin(vWorld.z*3.-uTime)*.003;
 vec3 col=mix(deep,sky,.25+.7*fresnel)+glint*vec3(4.,2.9,1.5)+small;
 float coast=1.-smoothstep(.0,.7,abs(vWorld.x-1.+sin(vWorld.z*.12)*1.8));
 col+=coast*.12*(.5+.5*sin(vWorld.z*6.+uTime*2.));
 float fog=1.-exp(-length(cameraPosition-vWorld)*.004);col=mix(col,vec3(.57,.72,.76),fog);
 gl_FragColor=vec4(col,1.);
}`;
export const cloudVertex=`varying vec3 vLocal;void main(){vLocal=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`;
export const cloudFragment=`
precision highp float;varying vec3 vLocal;uniform vec3 uCamera;uniform float uTime;uniform float uFormation;
float hash(vec3 p){p=fract(p*.3183099+vec3(.1,.2,.3));p*=17.;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}
float noise(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(mix(hash(i),hash(i+vec3(1,0,0)),f.x),mix(hash(i+vec3(0,1,0)),hash(i+vec3(1,1,0)),f.x),f.y),mix(mix(hash(i+vec3(0,0,1)),hash(i+vec3(1,0,1)),f.x),mix(hash(i+vec3(0,1,1)),hash(i+vec3(1,1,1)),f.x),f.y),f.z);}
float density(vec3 p){float shape=1.-length(p*vec3(1.7,2.5,1.85));vec3 q=p*4.+vec3(uTime*.025,0,0);float f=noise(q)*.6+noise(q*2.1)*.26+noise(q*4.2)*.14;return max(0.,shape+f*.65-.3)*uFormation;}
void main(){
 vec3 ray=normalize(vLocal-uCamera);vec3 inv=1./ray;vec3 a=(-vec3(.5)-uCamera)*inv,b=(vec3(.5)-uCamera)*inv;
 vec3 lo=min(a,b),hi=max(a,b);float near=max(max(lo.x,lo.y),lo.z),far=min(min(hi.x,hi.y),hi.z);if(far<near)discard;
 near=max(near,0.);float stepSize=(far-near)/28.;vec4 sum=vec4(0.);
 for(int i=0;i<28;i++){vec3 p=uCamera+ray*(near+(float(i)+.5)*stepSize);float d=density(p);float light=clamp((d-density(p+vec3(-.06,.08,-.04)))*3.+.65,.3,1.);float alpha=1.-exp(-d*stepSize*16.);vec3 color=mix(vec3(.44,.56,.64),vec3(1.,.96,.88),light);sum.rgb+=(1.-sum.a)*alpha*color;sum.a+=(1.-sum.a)*alpha;if(sum.a>.98)break;}
 if(sum.a<.005)discard;gl_FragColor=vec4(sum.rgb/max(sum.a,.001),sum.a);
}`;
export const skyVertex=`varying vec3 vDir;void main(){vDir=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}`;
export const skyFragment=`varying vec3 vDir;uniform vec3 uSun;void main(){vec3 d=normalize(vDir);float h=clamp(d.y,0.,1.);vec3 sky=mix(vec3(.55,.72,.85),vec3(.06,.22,.45),pow(h,.5));float glow=pow(max(dot(d,normalize(uSun)),0.),20.);sky+=glow*vec3(.45,.22,.04);gl_FragColor=vec4(sky,1.);}`;
