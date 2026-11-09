"""Read-only results adapter; never writes evaluation state or controls jobs."""
import json
import os
from pathlib import Path
import re
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
RUN = ROOT.parent / os.environ.get('BENCHMARK_RUN', 'runs-base-only-v1')
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
            if caps and any(cap != '512' for cap in caps):
                job['warnings'].append('Generation override observed: max_new_tokens='+','.join(caps)+'. Requested harness cap was 512; generation-budget comparability needs review.')
        if job['warnings']:
            data['warnings'].extend(f"{job['model'].split('/')[-1]} / {job['task']}: {warning}" for warning in job['warnings'])
        data['jobs'].append(job)
    data['completed'] = sum(j['status']=='completed' for j in data['jobs'])
    data['report_ready'] = bool(data['jobs']) and data['completed']==len(data['jobs']) and data['status']=='completed'
    return data


def get_snapshot():
    # Status must not wait on a GPU driver query or the controller's HTTP handler.
    snapshot=json.loads((RUN/'state.json').read_text(encoding='utf-8'))
    snapshot['environment_ready']=True
    snapshot['gpu']='NVIDIA GB10, unavailable, [N/A], [N/A], unavailable'
    telemetry=ROOT.parent/'prepared-base-only'/'gpu-telemetry.json'
    if telemetry.exists():
        try:
            reading=json.loads(telemetry.read_text())
            if time.time()-reading['time']<20:snapshot['gpu']=reading['gpu']
        except (ValueError,OSError,KeyError):pass
    info=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
    total=int(info['MemTotal'].split()[0]);available=int(info['MemAvailable'].split()[0])
    snapshot['memory']=f'System memory: {(total-available)/1048576:.1f} / {total/1048576:.1f} GiB used'
    data=enrich(snapshot)
    incident=RUN/'recovery-required.json'
    if incident.exists():
        data['incident']=json.loads(incident.read_text())
        data['status']='blocked'
        data['controls_enabled']=False
    data['comparisons']={track:comparison_rows(data,track) for track in ('completion','assistant','context')}
    return data


def comparison_rows(data, track):
    rows={}
    for job in data['jobs']:
        side='cortex' if job['model']=='mkd-hossain/Keural-Cortex-8B-v1.0' else 'qwen'
        if job['model'] not in ('mkd-hossain/Keural-Cortex-8B-v1.0','Qwen/Qwen3-8B-Base'):
            raise ValueError('Rejected non-Base comparator from new-run results')
        for metric in job['metrics'] or [{'task':job['task'],'metric':'','value':None,'n':None}]:
            key=(job['task'],metric['task'])
            row=rows.setdefault(key,{'benchmark':job['task'],'task':metric['task'],'category':job['category'],'extension':job.get('context')==65536})
            row[side]={'status':job['status'],'warnings':job['warnings'],**metric}
    for key,row in list(rows.items()):
        if row['task']==row['benchmark'] and any(k[0]==key[0] and k!=key for k in rows):rows.pop(key)
    for row in rows.values():
        for side,model in [('cortex','mkd-hossain/Keural-Cortex-8B-v1.0'),('qwen','Qwen/Qwen3-8B-Base')]:
            if side not in row:
                match=next((j for j in data['jobs'] if j['model']==model and j['task']==row['benchmark']),None)
                row[side]={'status':match['status'] if match else 'not-applicable','value':None,'n':None,'metric':''}
    return list(rows.values())
