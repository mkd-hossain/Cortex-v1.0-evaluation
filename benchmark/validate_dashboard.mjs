import fs from 'node:fs';
import vm from 'node:vm';
new vm.Script(fs.readFileSync(new URL('./dashboard.js',import.meta.url),'utf8'));
const html=fs.readFileSync(new URL('./dashboard.html',import.meta.url),'utf8');
const script=fs.readFileSync(new URL('./dashboard.js',import.meta.url),'utf8');
const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
if(new Set(ids).size!==ids.length)throw Error('Duplicate HTML IDs');
for(const match of script.matchAll(/\$\('([^']+)'\)/g))if(!ids.includes(match[1]))throw Error('Missing HTML element '+match[1]);
console.log('JavaScript syntax and HTML bindings validated');
