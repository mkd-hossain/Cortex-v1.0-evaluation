const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(__dirname+'/dashboard.js','utf8').split("document.querySelectorAll('[data-track]')")[0];
// Use the declarations before event registration, without running network polling.
const declarations=fs.readFileSync(__dirname+'/dashboard.js','utf8').split("\ndocument.querySelectorAll('[data-track]')")[0];
class Node{constructor(tag){this.tag=tag;this.children=[];this.style={};this.attrs={};this.hidden=false;this.value='';this.scrollTop=0;}append(...nodes){this.children.push(...nodes)}replaceChildren(...nodes){this.children=nodes}setAttribute(k,v){this.attrs[k]=v}}
const ids={};for(const id of ['graphs','graph-category','graph-search','graph-score','graph-order','graph-paired','graph-summary','graph-updated','graph-empty','graph-chart'])ids[id]=new Node('div');
ids['graph-paired'].checked=true;ids['graph-score'].value='primary';ids['graph-order'].value='original';
const context=vm.createContext({document:{documentElement:{dataset:{mode:'public'}},getElementById:id=>ids[id],createElement:tag=>new Node(tag)}});
vm.runInContext(declarations,context);
const entry=(value,status='completed',metric='acc,none')=>({value,status,metric,n:50});
const row=(task,c,q,extra={})=>({task,benchmark:task,category:'Korean knowledge',cortex:entry(c),qwen:entry(q),...extra});
const rows=[row('a',.8,.7),row('tie',.6,.6),row('base',.5,.9),row('zero',0,.1),row('pending',.5,null,{qwen:entry(null,'pending')}),row('extension',.7,null,{extension:true}),row('Fixture (semantic)',.9,.8),row('mismatched',.9,.8,{qwen:entry(.8,'completed','acc_norm,none')}),row('warn',.9,.8,{cortex:{...entry(.9),warnings:['Review']}})];
context.data={comparisons:{completion:rows},updated_at:Date.now()/1000};
assert.equal(vm.runInContext("graphRows(data,{paired:true,score:'primary'}).length",context),4);
assert.equal(vm.runInContext("graphRows(data,{paired:true,score:'semantic'}).length",context),1);
assert.equal(vm.runInContext("graphRows(data,{paired:true,search:'zero'}).length",context),1);
assert.equal(vm.runInContext("graphRows(data,{paired:true,category:'Long context'}).length",context),0);
assert.equal(vm.runInContext("graphRows(data,{paired:true,order:'qwen'})[0].task",context),'base');
assert.equal(vm.runInContext("graphRows(data,{paired:true,order:'cortex'})[0].task",context),'a');
vm.runInContext('renderGraphs(data)',context);assert.equal(ids['graph-chart'].children.length,4);assert.equal(ids['graph-summary'].children[1].children[1].textContent,'1');
const zero=ids['graph-chart'].children.find(n=>n.children[0].children[0].children[0].textContent==='zero');assert.equal(zero.children[2].children[1].children[0].style.width,'0%');
ids['graph-paired'].checked=false;vm.runInContext('renderGraphs(data)',context);assert.equal(ids['graph-chart'].children.length,8);
const pending=ids['graph-chart'].children.find(n=>n.children[0].children[0].children[0].textContent==='pending');assert.equal(pending.children[3].children[2].textContent,'—');assert.equal(pending.children[3].children[1].children[0].tag,'small');
context.data=JSON.parse(fs.readFileSync(__dirname+'/graph-test-snapshot.json','utf8'));ids['graph-paired'].checked=true;vm.runInContext('renderGraphs(data)',context);assert.ok(ids['graph-chart'].children.length>0);
console.log('Graph filtering, zero/pending handling, comparability, sorting, DOM rendering and live-data tests passed.');
