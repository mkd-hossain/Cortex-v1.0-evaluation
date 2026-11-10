'use strict';
const $=id=>document.getElementById(id);
const privateMode=document.documentElement.dataset.mode==='private';
const state={data:null,track:'completion',log:'evaluation',logs:null,busy:false};
const categories=['Korean knowledge','Korean understanding','English knowledge/reasoning','Math reasoning','Long context','Chat','Tool calling'];
const titles={'Chat':'Chat constraints','Math reasoning':'Thinking math','Tool calling':'Tool calling'};
const fmt=value=>Number.isFinite(value)?(value*100).toFixed(1)+'%':null;
const human=value=>({kobest_boolq:'KoBEST BoolQ',kobest_copa:'KoBEST COPA',kobest_hellaswag:'KoBEST HellaSwag',kobest_sentineg:'KoBEST SentiNeg',arc_challenge:'ARC-Challenge',gsm8k:'GSM8K',hellaswag:'HellaSwag',winogrande:'WinoGrande','Chat':'Chat constraints · synthetic','Math reasoning':'Thinking math · synthetic','Tool calling':'Tool calling · synthetic'}[value]||String(value).replace(/^haerae_/,'HAE-RAE / ').replace(/^kmmlu_/,'KMMLU / ').replace(/^mmlu_/,'MMLU / ').replaceAll('_',' '));
function element(tag,text,className){const item=document.createElement(tag);if(text!==undefined)item.textContent=text;if(className)item.className=className;return item}
function pill(status){return element('span',status==='not-applicable'?'Not in matched test':status,'state-pill state-'+status)}
function selectTrack(track){state.track=track;document.querySelectorAll('[data-track]').forEach(button=>button.setAttribute('aria-selected',String(button.dataset.track===track)));if(state.data)renderComparison(state.data)}
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
  const tr=element('tr');const label=element('td');label.append(element('strong',human(row.task)));
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
function renderAssistant(data){
 const jobs=data.jobs.filter(j=>j.suite==='assistant');
 $('assistant-cards').replaceChildren(...['Chat','Math reasoning','Tool calling'].map(category=>{
  const card=element('article',undefined,'diagnostic-card');card.append(element('h3',titles[category]));const values=element('div',undefined,'diagnostic-values');
  for(const [name,prefix] of [['Cortex','mkd-hossain/'],['Qwen','Qwen/']]){const job=jobs.find(j=>j.model.startsWith(prefix));const metric=job?.metrics.find(m=>m.task===category);const block=element('div');block.append(element('small',name));block.append(element('strong',fmt(metric?.value)||'Pending',metric?'':'pending'));if(metric)block.append(element('small',`${metric.passed} / ${metric.n} checks`));values.append(block)}
  card.append(values);return card;
 }));
}
function elapsed(data){const starts=data.jobs.map(j=>j.started).filter(Number.isFinite);if(!starts.length)return 'Not started';const ends=data.jobs.map(j=>j.ended).filter(Number.isFinite);const stop=['completed','budget_exhausted'].includes(data.status)?Math.max(...ends):Date.now()/1000;const seconds=Math.max(0,Math.floor(stop-Math.min(...starts)));return `${Math.floor(seconds/3600)}h ${Math.floor(seconds%3600/60)}m`}
function render(data){
 const total=data.jobs.length,count=data.completed,percent=total?Math.round(count/total*100):0;
 $('job-count').textContent=`${count} / ${total}`;$('progress').value=percent;$('percentage').textContent=percent+'%';
 const active=data.jobs.find(j=>j.status==='running'),failed=data.jobs.find(j=>j.status==='failed');
 $('status').textContent=({budget_exhausted:'Runtime budget reached ? partial coverage saved',blocked:'GPU recovery required',running:'Evaluation in progress',paused:'Evaluation paused',completed:'Evaluation complete',ready:'Ready to evaluate',failed:'Evaluation needs attention',preparing:'Preparing environment'})[data.status]||data.status;
 if(data.status==='ready'&&data.completed>0)$('status').textContent='Ready to resume';
 document.body.classList.toggle('is-idle',data.status!=='running');
 const dot=document.querySelector('.status-line .dot');dot.classList.toggle('failed-dot',data.status==='failed');dot.classList.toggle('paused-dot',data.status==='paused');
 let activeText=active?`${active.model.split('/').pop()} · ${active.task}`:failed?`Needs attention: ${failed.task}`:data.status==='completed'?'All evaluation jobs have finished. Completion report is available.':'No evaluator is currently active.';
 if(active?.case_progress)activeText+=` · ${active.case_progress.completed}/${active.case_progress.total} cases saved`;
 $('active').textContent=activeText;
 if(data.incident)$('active').textContent=data.incident.message;
 const gpu=String(data.gpu||'').split(',').map(x=>x.trim());$('gpu').textContent=gpu[1]||'Unavailable';$('temperature').textContent=(gpu[0]||'NVIDIA GB10')+(gpu.length>4?' · '+gpu.at(-1)+'°C':'');$('memory').textContent=String(data.memory||'Unavailable').replace('System memory: ','').replace(' used','');
 $('elapsed').textContent=elapsed(data);$('last-update').textContent='Updated '+new Date(data.updated_at*1000).toLocaleTimeString();
 $('subtitle').textContent=(data.title||'Seven-category short evaluation')+' · NVIDIA DGX Spark · BF16';$('protocol').textContent=data.note+(data.deadline_unix?' Hard stop: '+new Date(data.deadline_unix*1000).toLocaleString():'');
 $('cortex-revision').textContent='Revision '+(data.jobs.find(j=>j.model.startsWith('mkd-hossain/'))?.revision?.slice(0,9)||'pinned');
 $('export').disabled=!data.report_ready;$('export-note').textContent=data.report_ready?(data.status==='budget_exhausted'?'Download partial-coverage report':'Download the completion report'):'Available when all jobs complete';$('report-state').textContent=data.report_ready?'Report ready':'Waiting for completion';
 $('warnings').hidden=!data.incident&&!data.warnings?.length;$('warnings').textContent=data.incident?data.incident.message:data.warnings?.length?data.warnings.join(' '):'';
 $('categories').replaceChildren(...categories.map(category=>{const jobs=data.jobs.filter(j=>(j.category||'').includes(category));const chip=element('span',category.replace('/reasoning',''),'category');chip.append(element('em',jobs.filter(j=>j.status==='completed').length+'/'+jobs.length));return chip}));
 $('activity-description').textContent=active?active.task:'Most recent evaluation activity';
 const recent=data.jobs.filter(j=>j.ended).slice(-2);const items=recent.map(j=>({time:j.ended,text:`Completed ${j.model.split('/').pop()} · ${j.task}`}));if(active)items.push({time:active.started,text:`Running ${active.model.split('/').pop()} · ${active.task}`});
 $('activity-lines').replaceChildren(...items.map(item=>{const line=element('div',undefined,'activity-line');line.append(element('span',undefined,'dot'),element('time',new Date(item.time*1000).toLocaleTimeString()),element('span',item.text));return line}));
 $('queue').replaceChildren(...data.jobs.map(job=>{const row=element('tr');const model=element('td');model.append(element('strong',job.model.split('/').pop()),element('small',job.track));const title=element('td',job.task);const status=element('td');status.append(pill(job.status));const settings=element('td');settings.textContent=job.runner==='standard-audited'?`${job.sample_count} seeded samples; ${job.fewshot}-shot; BF16`:job.runner==='behavior-full'?`${job.sample_count} fixtures; ${job.track}; 128-token cap`:job.runner==='diagnostics'?(job.suite==='assistant'?'24 bilingual development cases':`2 cases; ${job.context/1024}K context budget`):`${job.limit} per subtask; ${job.fewshot}-shot; BF16`;if(job.warnings?.length)settings.append(element('small',job.warnings.join(' ')));row.append(model,title,status,settings);return row}));
 if(privateMode){$('controls').hidden=false;$('start').disabled=data.status!=='ready'||data.completed>0||!data.environment_ready;$('pause').disabled=data.status!=='running';$('resume').disabled=!['paused','ready','failed','blocked','interrupted'].includes(data.status)||data.completed===data.jobs.length||!data.environment_ready;}
 renderComparison(data);
}
function showLog(){if(!state.logs)return;const key=state.log==='evaluation'?'log':state.log==='environment'?'setup_log':'downloads_log';$('log-text').textContent=(state.logs[key]||'No output yet.')+(state.log==='downloads'?'\n\n'+(state.logs['assistant-download_log']||''):'')}
async function refreshLogs(){if($('log-panel').hidden)return;const response=await fetch('/api/details');if(!response.ok)throw Error('Live logs temporarily unavailable');state.logs=await response.json();showLog()}
async function refresh(){if(state.busy)return;state.busy=true;try{const response=await fetch('/api/status');if(!response.ok)throw Error('Live status temporarily unavailable');state.data=await response.json();render(state.data);await refreshLogs();$('connection').hidden=true;}catch(error){$('connection').hidden=false;$('connection').textContent='Connection interrupted. The benchmark runs independently on Spark. '+error.message;if(privateMode)['start','pause','resume'].forEach(id=>$(id).disabled=true)}finally{state.busy=false}}
async function control(action){try{const response=await fetch('/api/'+action,{method:'POST',headers:{'X-Benchmark-Control':'1'}});const data=await response.json();if(!response.ok)throw Error(data.error||'Control unavailable');await refresh()}catch(error){$('connection').hidden=false;$('connection').textContent=error.message}}
document.querySelectorAll('[data-track]').forEach(button=>button.addEventListener('click',()=>selectTrack(button.dataset.track)));
document.querySelectorAll('[data-log]').forEach(button=>button.addEventListener('click',()=>{state.log=button.dataset.log;document.querySelectorAll('[data-log]').forEach(b=>b.setAttribute('aria-selected',String(b===button)));showLog()}));

$('toggle-logs').addEventListener('click',async()=>{$('log-panel').hidden=!$('log-panel').hidden;const expanded=!$('log-panel').hidden;$('toggle-logs').setAttribute('aria-expanded',String(expanded));$('toggle-logs').textContent=expanded?'Hide details':'Show details';try{await refreshLogs()}catch(error){$('log-text').textContent=error.message}});
$('export').addEventListener('click',()=>{if(state.data?.report_ready)window.location.assign('/api/report.pdf')});
if(privateMode){$('mode').textContent='Private · Operator';$('footer-mode').textContent='Private operator dashboard';['start','pause','resume'].forEach(action=>$(action).addEventListener('click',()=>control(action)))}
refresh();setInterval(refresh,5000);
