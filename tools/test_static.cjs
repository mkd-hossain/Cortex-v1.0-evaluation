const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),site=path.join(root,'docs'),html=fs.readFileSync(path.join(site,'index.html'),'utf8');
class Element{constructor(tag){this.tag=tag;this.children=[];this.style={};this.attrs={};this.hidden=false;this.value='';this.scrollTop=0;this.events={};}append(...nodes){this.children.push(...nodes)}replaceChildren(...nodes){this.children=nodes;if(this.tag==='select'&&nodes.length)this.value=nodes[0].value}setAttribute(k,v){this.attrs[k]=v}addEventListener(k,f){this.events[k]=f}scrollIntoView(){}focus(){}}
const ids={};for(const match of html.matchAll(/<([\w-]+)[^>]*\bid="([^"]+)"/g)){assert.ok(!ids[match[2]],'duplicate ID');ids[match[2]]=new Element(match[1]);}
ids['graph-paired'].checked=true;ids['graph-excluded'].checked=false;ids['graph-score'].value='primary';ids['graph-order'].value='original';
const context=vm.createContext({document:{getElementById:id=>{assert.ok(ids[id],'missing ID '+id);return ids[id]},createElement:tag=>new Element(tag)},window:{location:{hash:'#graphs'}}});
for(const file of ['data/results.js','data/logs.js','site.js'])vm.runInContext(fs.readFileSync(path.join(site,file),'utf8'),context,{filename:file});
assert.equal(context.window.BENCHMARK_DATA.completed,39);assert.equal(context.window.BENCHMARK_LOGS.length,39);assert.equal(ids.comparison.children.length,context.window.BENCHMARK_DATA.comparisons.completion.length);assert.ok(ids['log-text'].textContent.length>0);assert.ok(ids['graph-chart'].children.length>100);
assert.equal(vm.runInContext("graphRows(state.data,{paired:true,score:'primary'}).some(r=>r.task.startsWith('Tool-result grounding'))",context),false);
assert.equal(vm.runInContext("graphRows(state.data,{paired:true,score:'primary',excluded:true}).some(r=>r.task.startsWith('Tool-result grounding'))",context),true);
ids['graph-score'].value='semantic';ids['graph-score'].events.change();assert.ok(ids['graph-chart'].children.length>0);
for(const m of html.matchAll(/(?:src|href)="([^"]+)"/g)){const link=m[1];if(link.startsWith('#'))assert.ok(ids[link.slice(1)],'bad anchor '+link);else if(!/^https?:/.test(link))assert.ok(fs.existsSync(path.resolve(site,link)),'missing asset '+link);}
const js=fs.readFileSync(path.join(site,'site.js'),'utf8');assert.ok(!/fetch\(|XMLHttpRequest|WebSocket|setInterval|\/api\//.test(js));
console.log('PASS: final results, 39 logs, comparison rendering, graph filtering, semantic view, local assets and offline-only loading.');
