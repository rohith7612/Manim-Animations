import {build} from 'esbuild';
import {mkdir} from 'node:fs/promises';
await mkdir('dist/cinema',{recursive:true});
await build({entryPoints:['cinema/scene.js'],outfile:'dist/cinema/scene.js',bundle:true,format:'esm',target:'es2022',minify:true,legalComments:'eof'});
console.log('Procedural renderer bundled.');
