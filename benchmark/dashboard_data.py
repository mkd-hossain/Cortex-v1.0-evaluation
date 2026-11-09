"""Read-only results adapter; never writes evaluation state or controls jobs."""
import json
import os
from pathlib import Path
import re
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
RUN = ROOT / os.environ.get('BENCHMARK_RUN', 'runs-short-all-v1')
_CACHE = {}
METRICS = ('pass_rate','acc_norm,none','acc,none','exact_match,strict-match','exact_match,flexible-extract')


def read_result(path):
    stamp = (path.stat().st_mtime_ns,path.stat().st_size)
    previous = _CACHE.get(str(path))
    if previous and previous[0] == stamp:
        return previous[1]
    data = json.loads(path.read_text(encoding='utf-8'))
    _CACHE[str(path)] = stamp,data
    return data


def enrich(snapshot, run=RUN):
    data = {key:snapshot.get(key,'') for key in ('status','title','note','environment_ready','gpu','memory')}
    data.update(updated_at=time.time(),run_id=run.name,jobs=[],warnings=[])
    for source in snapshot['jobs']:
        job = {key:source.get(key) for key in ('id','model','revision','task','tasks','category','track','status',
                    'started','ended','limit','fewshot','chat','runner','suite','context','batch_size','generation')}
        job['metrics'] = []
        job['warnings'] = []
        directory = run / source['id']
        if source['status'] == 'completed':
            files = sorted((directory/'results').rglob('results*.json'))
            if files:
                try:
                    result = read_result(files[-1])
                    samples = result.get('n-samples',{})
                    group_tasks = result.get('group_subtasks',{})
                    for name,metrics in result.get('results',{}).items():
                        if group_tasks.get(name):
                            continue
                        for metric in METRICS:
                            if isinstance(metrics.get(metric),(int,float)):
                                job['metrics'].append({'task':name,'metric':metric,'value':metrics[metric],
                                    'n':metrics.get('total',samples.get(name,{}).get('effective',metrics.get('sample_len'))),
                                    'passed':metrics.get('passed'),
                                    'stderr':metrics.get(metric.replace(',','_stderr,',1))})
                                break
                    config = result.get('config',{})
                    job['runtime'] = {key:result.get(key) for key in ('lm_eval_version','transformers_version','model_dtype','model_revision','chat_template_sha','task_hashes')}
                    job['runtime']['generation_kwargs'] = config.get('gen_kwargs',{})
                    job['runtime']['actual_batch_sizes'] = config.get('batch_sizes',[])
                except (OSError,ValueError,TypeError):
                    job['warnings'].append('Result file could not be parsed; inspect evaluation artifacts.')
        progress = directory/'results'/'progress.json'
        if progress.exists():
            try:
                job['case_progress'] = json.loads(progress.read_text())
            except (OSError,ValueError):
                pass
        log = directory/'run.log'
        if source.get('generation') and log.exists():
            # The requested harness budget can be overridden by model generation_config.
            with log.open('rb') as stream:
                stream.seek(max(0,log.stat().st_size-30000))
                tail=stream.read().decode('utf-8',errors='replace')
            caps = sorted(set(re.findall(r'max_new_tokens`?\s*\(=(\d+)\)',tail)))
            if caps:
                job['warnings'].append('Generation override observed: max_new_tokens='+','.join(caps)+'. Requested harness cap was 512; generation-budget comparability needs review.')
        if job['warnings']:
            data['warnings'].extend(f"{job['model'].split('/')[-1]} / {job['task']}: {warning}" for warning in job['warnings'])
        data['jobs'].append(job)
    data['completed'] = sum(j['status']=='completed' for j in data['jobs'])
    data['report_ready'] = bool(data['jobs']) and data['completed']==len(data['jobs']) and data['status']=='completed'
    return data


def get_snapshot():
    with urlopen('http://127.0.0.1:8765/api/status',timeout=8) as response:
        snapshot=json.load(response)
    prepared=os.environ.get('BENCHMARK_PREPARED_PLAN')
    if prepared:
        plan=json.loads((ROOT/prepared).read_text(encoding='utf-8'))
        allowed={'mkd-hossain/Keural-Cortex-8B-v1.0','Qwen/Qwen3-8B-Base'}
        assert {j['model'] for j in plan['jobs']}==allowed
        snapshot.update(status='ready',title=plan['title']+' — prepared, not started',note=plan['note'],
                        jobs=[dict(j,status='pending') for j in plan['jobs']])
    data=enrich(snapshot)
    if prepared:data['run_id']='runs-base-only-v1'
    data['controls_enabled']=not bool(prepared)
    data['comparisons']={track:comparison_rows(data,track) for track in ('completion','assistant','context')}
    return data


def comparison_rows(data, track):
    base_only=bool(os.environ.get('BENCHMARK_PREPARED_PLAN'))
    comparator='Qwen/Qwen3-8B-Base' if track=='completion' or base_only else 'Qwen/Qwen3-8B'
    rows={}
    def selected_job(job):
        if base_only:return True
        if track=='completion':
            return job.get('runner')!='diagnostics' and not job.get('chat')
        elif track=='assistant':
            return (job.get('runner')!='diagnostics' and job.get('chat')) or job.get('suite')=='assistant'
        return job.get('suite')=='long-context'
    for job in data['jobs']:
        if not selected_job(job):
            continue
        side='cortex' if job['model'].startswith('mkd-hossain/') else 'qwen'
        if side=='qwen' and job['model']!=comparator:
            continue
        metrics=job['metrics'] or [{'task':job['task'],'metric':'','value':None,'n':None}]
        for metric in metrics:
            # Standard rows align by task; pending multi-domain jobs remain explicit.
            key=(job['task'],metric['task'])
            row=rows.setdefault(key,{'benchmark':job['task'],'task':metric['task'],'category':job['category'],
                                    'extension':job.get('context')==65536})
            row[side]={'status':job['status'],'warnings':job['warnings'],**metric}
    # Remove pending parent rows when the other side already has domain-level rows.
    for key,row in list(rows.items()):
        if row['task']==row['benchmark'] and any(k[0]==key[0] and k!=key for k in rows):
            rows.pop(key)
    # Add the pending model's state to domain rows whose artifacts are not ready yet.
    for row in rows.values():
        for side,model in [('cortex','mkd-hossain/Keural-Cortex-8B-v1.0'),('qwen',comparator)]:
            if side not in row:
                match=next((j for j in data['jobs'] if j['model']==model and j['task']==row['benchmark'] and selected_job(j)),None)
                row[side]={'status':match['status'] if match else 'not-applicable','value':None,'n':None,'metric':''}
    return list(rows.values())
