import puppeteer from 'puppeteer-core';
import {readFile,writeFile,mkdir,access} from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import {once} from 'node:events';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const [planPath,outputDir,widthArg='960',heightArg='540',fpsArg='24',progressArg]=process.argv.slice(2);
if(!planPath||!outputDir)throw new Error('Usage: node cinema/render.mjs plan.json output width height fps [progress.json]');
const width=Number(widthArg),height=Number(heightArg),fps=Number(fpsArg);
if(!Number.isInteger(width)||width<128||width>1920||!Number.isInteger(height)||height<128||height>1920||!Number.isInteger(fps)||fps<1||fps>30)throw new Error('Invalid export dimensions or frame rate.');
const plan=JSON.parse(await readFile(planPath,'utf8'));if(!(plan.duration>0&&plan.duration<=180))throw new Error('Invalid film duration.');
const output=path.resolve(outputDir);await mkdir(output,{recursive:true});
const bundle=await readFile(path.join(root,'dist/cinema/scene.js'));
const server=http.createServer((req,res)=>{
 if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end('<!doctype html><html><head><meta charset="utf-8"></head><body><script type="module" src="/scene.js"></script></body></html>');}
 else if(req.url==='/scene.js'){res.setHeader('Content-Type','application/javascript');res.end(bundle);}else if(req.url==='/favicon.ico'){res.statusCode=204;res.end();}else{res.statusCode=404;res.end();}
});server.listen(0,'127.0.0.1');await once(server,'listening');
const origin=`http://127.0.0.1:${server.address().port}`;
let executable=process.env.FRAMECRAFT_BROWSER;
if(!executable){for(const p of ['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe','/usr/bin/chromium','/usr/bin/google-chrome']){try{await access(p);executable=p;break;}catch{}}}
if(!executable)throw new Error('Chrome/Edge was not found. Set FRAMECRAFT_BROWSER.');
let browser;const started=Date.now()/1000;
try{
 browser=await puppeteer.launch({executablePath:executable,headless:true,userDataDir:path.join(output,'browser-profile'),args:['--enable-gpu','--use-angle=d3d11','--hide-scrollbars','--mute-audio'],defaultViewport:{width,height,deviceScaleFactor:1}});
 const page=await browser.newPage();page.setDefaultTimeout(120000);let errors=[];
 page.on('pageerror',error=>errors.push(error.message));page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
 await page.setRequestInterception(true);page.on('request',request=>{if(request.url().startsWith(origin+'/')||request.url()==='about:blank')request.continue();else request.abort();});
 await page.goto(origin,{waitUntil:'load'});await page.waitForFunction('typeof window.createFilm === "function"');
 const info=await page.evaluate(async(p,w,h)=>{window.film=await window.createFilm(p,w,h);return window.film.info();},plan,width,height);
 console.log(JSON.stringify({stage:'ready',...info}));
 const total=Math.ceil(plan.duration*fps);
 for(let i=0;i<total;i++){
  const t=i/fps;
  const data=await page.evaluate(t=>{window.film.frame(t);return window.film.canvas.toDataURL('image/jpeg',.96);},t);
  await writeFile(path.join(output,`${String(i).padStart(6,'0')}.jpg`),Buffer.from(data.split(',')[1],'base64'));
  if(i%Math.max(1,Math.round(fps/2))===0||i===total-1){
   const now=Date.now()/1000,payload={started_at:started,updated_at:now,rendered_seconds:(i+1)/fps,wall_elapsed:now-started,frame:i+1,total_frames:total,engine:'threejs'};
   if(progressArg){const temp=progressArg+'.partial';await writeFile(temp,JSON.stringify(payload));await (await import('node:fs/promises')).rename(temp,progressArg);}
   console.log(JSON.stringify(payload));
  }
  if(errors.length)throw new Error('3D shader/render error: '+errors.slice(0,3).join('; '));
 }
 await writeFile(path.join(output,'render-info.json'),JSON.stringify({...info,width,height,fps,frames:total,duration:total/fps,procedural:true,externalAssets:0},null,2));
}finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
