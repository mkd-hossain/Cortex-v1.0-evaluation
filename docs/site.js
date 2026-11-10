'use strict';
const $=id=>document.getElementById(id);
const state={data:null,track:'completion'};
const fmt=value=>Number.isFinite(value)?(value*100).toFixed(1)+'%':null;
const human=value=>({kobest_boolq:'KoBEST BoolQ',kobest_copa:'KoBEST COPA',kobest_hellaswag:'KoBEST HellaSwag',kobest_sentineg:'KoBEST SentiNeg',arc_challenge:'ARC-Challenge',gsm8k:'GSM8K',hellaswag:'HellaSwag',winogrande:'WinoGrande','Chat':'Chat constraints · synthetic','Math reasoning':'Thinking math · synthetic','Tool calling':'Tool calling · synthetic'}[value]||String(value).replace(/^haerae_/,'HAE-RAE / ').replace(/^kmmlu_/,'KMMLU / ').replace(/^mmlu_/,'MMLU / ').replaceAll('_',' '));
function element(tag,text,className){const item=document.createElement(tag);if(text!==undefined)item.textContent=text;if(className)item.className=className;return item}
function pill(status){return element('span',status==='not-applicable'?'Not in matched test':status,'state-pill state-'+status)}
function scoreCell(entry,side){const td=element('td');const value=fmt(entry?.value);if(value){td.append(element('span',value,'score '+side+'-value'));if(entry.passed!==undefined&&entry.passed!==null)td.append(element('small',`${entry.passed} / ${entry.n} checks`));}else td.append(pill(entry?.status||'pending'));return td}
function renderComparison(data){
 const assistant=false;
 $('qwen-model').textContent=assistant?'Qwen3-8B':'Qwen3-8B-Base';
 $('qwen-description').textContent=assistant?'Instruction-tuned assistant · native chat template':'Original pretrained baseline';
 $('comparator-heading').textContent=assistant?'Qwen3-8B':'Qwen3-8B-Base';
 $('track-description').textContent=state.track==='completion'?'Matched standard completion and separately labeled deployment fixtures; frozen before inference':state.track==='assistant'?'Native templates · standard tasks plus separate synthetic assistant diagnostics':'Matched source documents · actual input tokens reserve output space';
 $('context-note').hidden=false;$('context-note').textContent=data.note;
 const comparator=assistant?'Qwen/Qwen3-8B':'Qwen/Qwen3-8B-Base';
 $('qwen-revision').textContent='Revision '+(data.jobs.find(j=>j.model===comparator)?.revision?.slice(0,9)||'pinned');
 const rows=data.comparisons?.[state.track]||[];
 $('comparison').replaceChildren(...rows.map(row=>{
  const tr=element('tr');const label=element('td');label.append(element('strong',human(row.task).replace('Tool-result grounding','Simple extraction [answer leakage]')));
  if(row.task!==row.benchmark)label.append(element('small',row.benchmark));
  if(row.extension)label.append(element('small','Cortex-only extension'));
  tr.append(label,scoreCell(row.cortex,'cortex'),scoreCell(row.qwen,'qwen'));
  const delta=element('td',undefined,'delta');
  const warning=[...(row.cortex?.warnings||[]),...(row.qwen?.warnings||[])].length>0;
  if(warning)delta.textContent='Review budget';
  else if(Number.isFinite(row.cortex?.value)&&Number.isFinite(row.qwen?.value)&&row.cortex.metric===row.qwen.metric){const difference=(row.cortex.value-row.qwen.value)*100;delta.textContent=(difference>0?'+':'')+difference.toFixed(1)+' pp';}
  else delta.textContent='—';tr.append(delta);
  const coverage=element('td');const c=row.cortex?.n,q=row.qwen?.n;
  coverage.append(element('span',c&&q?(c===q?c+' examples / model':c+' / '+q+' examples'):c?c+' Cortex examples':q?q+' Qwen examples':'Awaiting results'));
  const metric=row.cortex?.metric||row.qwen?.metric||'';
  coverage.append(element('small',metric==='pass_rate'?'Synthetic constraint pass rate':metric.startsWith('acc_norm')?'Normalized accuracy':metric.startsWith('acc,')?'Accuracy':metric.startsWith('exact_match')?'Exact match':row.category,'metric-badge'));
  tr.append(coverage);return tr;
 }));
}
function graphPair(row){return row.cortex?.status==='completed'&&row.qwen?.status==='completed'&&Number.isFinite(row.cortex.value)&&Number.isFinite(row.qwen.value)&&row.cortex.value>=0&&row.cortex.value<=1&&row.qwen.value>=0&&row.qwen.value<=1&&row.cortex.metric===row.qwen.metric&&!row.extension&&!(row.cortex.warnings?.length||row.qwen.warnings?.length)}
function graphRows(data,options={}){
 const query=(options.search||'').trim().toLowerCase();
 const rows=(data.comparisons?.completion||[]).filter(row=>{
  const semantic=String(row.task).endsWith(' (semantic)');
  if(!options.excluded&&String(row.task).startsWith('Tool-result grounding'))return false;
  if(options.score==='semantic'?!semantic:semantic)return false;
  if(options.category&&row.category!==options.category)return false;
  if(query&&!`${human(row.task).replace('Tool-result grounding','Simple extraction [answer leakage]')} ${row.benchmark} ${row.category}`.toLowerCase().includes(query))return false;
  return !options.paired||graphPair(row);
 });
 const delta=row=>graphPair(row)?row.cortex.value-row.qwen.value:null;
 if(options.order==='cortex'||options.order==='qwen')rows.sort((a,b)=>{const x=delta(a),y=delta(b);if(x===null)return y===null?0:1;if(y===null)return -1;return options.order==='cortex'?y-x:x-y});
 return rows;
}
function renderGraphs(data){
 if(!$('graphs')||$('graphs').hidden)return;
 const scrollTop=$('graph-chart').scrollTop;
 const rows=graphRows(data,{category:$('graph-category').value,search:$('graph-search').value,score:$('graph-score').value,order:$('graph-order').value,paired:$('graph-paired').checked,excluded:$('graph-excluded').checked});
 const pairs=rows.filter(graphPair);let cortex=0,qwen=0,ties=0;
 for(const row of pairs){const delta=row.cortex.value-row.qwen.value;if(Math.abs(delta)<1e-10)ties++;else if(delta>0)cortex++;else qwen++;}
 $('graph-summary').replaceChildren(...[['Displayed paired rows',pairs.length],['Cortex higher',cortex],['Qwen higher',qwen],['Tied',ties]].map(([label,value])=>{const card=element('div');card.append(element('small',label),element('strong',String(value)));return card}));
 $('graph-updated').textContent=`${rows.length} displayed rows · final saved results`;
 $('graph-empty').hidden=rows.length>0;
 $('graph-chart').replaceChildren(...rows.map(row=>{
  const item=element('article',undefined,'benchmark-graph');const header=element('div',undefined,'graph-row-heading');const label=element('div');label.append(element('strong',human(row.task).replace('Tool-result grounding','Simple extraction [answer leakage]')),element('small',row.category+(row.extension?' · Cortex-only extension':'')));header.append(label);
  if(graphPair(row)){const difference=(row.cortex.value-row.qwen.value)*100;header.append(element('span',(difference>0?'+':'')+difference.toFixed(1)+' pp','graph-difference'));}else header.append(element('span',row.extension?'Unpaired extension':'Pair not complete / comparable','graph-pending'));
  item.append(header);
  const axis=element('div',undefined,'graph-axis');axis.append(element('span',''),...['0%','25%','50%','75%','100%'].map(x=>element('span',x)));item.append(axis);
  for(const [side,name] of [['cortex','Cortex'],['qwen','Qwen Base']]){
   const entry=row[side],line=element('div',undefined,'graph-bar-line');line.append(element('span',name,'graph-model-label'));
   const track=element('div',undefined,'graph-bar-track');const known=entry?.status==='completed'&&Number.isFinite(entry.value)&&entry.value>=0&&entry.value<=1;
   if(known){const bar=element('div',undefined,'graph-bar '+side);bar.style.width=(entry.value*100)+'%';track.append(bar);track.setAttribute('role','img');track.setAttribute('aria-label',`${name}: ${(entry.value*100).toFixed(1)} percent`);}else track.append(element('small',entry?.status==='not-applicable'?'Not in matched test':entry?.status||'Pending','graph-pending'));
   line.append(track,element('strong',known?(entry.value*100).toFixed(1)+'%':'—','graph-value'));item.append(line);
  }
  const rawMetric=row.cortex?.metric||row.qwen?.metric||'';const metric=rawMetric.startsWith('acc_norm')?'Normalized accuracy':rawMetric.startsWith('acc,')?'Accuracy':rawMetric.startsWith('exact_match')?'Exact match':rawMetric==='pass_rate'?'Synthetic fixture pass rate':'Awaiting results';const c=row.cortex?.n,q=row.qwen?.n;
  item.append(element('small',`${metric} · samples Cortex ${c??'pending'} / Base ${row.extension?'not applicable':q??'pending'}${row.cortex?.warnings?.length||row.qwen?.warnings?.length?' · audit warning: inspect table and methodology':''}`,'graph-row-note'));return item;
 }));
 $('graph-chart').scrollTop=scrollTop;
}

function openGraphs(){ $('graphs').hidden=false;$('graph-nav').setAttribute('aria-expanded','true');renderGraphs(state.data);$('graphs').scrollIntoView({block:'start'}); }
function renderLog(){
 const record=window.BENCHMARK_LOGS.find(log=>log.id===$('log-job').value);
 $('log-text').textContent=record?.text||'No archived output available.';
 if(record)$('full-log-link').href='https://github.com/mkd-hossain/Cortex-v1.0-evaluation/blob/main/results/run/'+encodeURIComponent(record.id)+'/run.log';
}
function init(){
 const data=window.BENCHMARK_DATA;
 if(!data||data.status!=='completed'||data.completed!==39){$('data-error').hidden=false;$('data-error').textContent='The final results file could not be loaded. Please reload this page.';return;}
 state.data=data;renderComparison(data);
 $('graph-nav').addEventListener('click',event=>{event.preventDefault();openGraphs();});
 $('close-graphs').addEventListener('click',()=>{$('graphs').hidden=true;$('graph-nav').setAttribute('aria-expanded','false');$('graph-nav').focus();});
 for(const id of ['graph-category','graph-score','graph-order','graph-paired','graph-excluded'])$(id).addEventListener('change',()=>{ $('graph-chart').scrollTop=0;renderGraphs(data);});
 $('graph-search').addEventListener('input',()=>{$('graph-chart').scrollTop=0;renderGraphs(data);});
 $('log-job').replaceChildren(...window.BENCHMARK_LOGS.map(log=>{const option=element('option',log.model+' · '+log.task);option.value=log.id;return option;}));
 $('log-job').addEventListener('change',renderLog);renderLog();
 if(window.location.hash==='#graphs')openGraphs();
}
init();
