"""User-authorized runtime extension; do not alter scoring, prompts or samples."""
import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
root=Path(__file__).parent;run=root.parent/'runs-full-budget-v1'
subprocess.run(['systemctl','--user','stop','cortex-benchmark.service','cortex-full-summary.service'],check=True)
state=json.loads((run/'state.json').read_text());plan=json.loads((root/'plan.json').read_text())
assert state['status'] in ('budget_exhausted','ready','paused')
done=[j for j in state['jobs'] if j['status']=='completed'];assert len(done)==22
stamp=str(time.time_ns());archive=run/'runtime-extensions'/stamp;archive.mkdir(parents=True)
for name,path in [('state-before.json',run/'state.json'),('plan-before.json',root/'plan.json'),('summary-before.json',run/'summary-final-or-partial.json'),('checksums-before.json',run/'SHA256SUMS.json')]:
    if path.exists():(archive/name).write_bytes(path.read_bytes())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
preserved={p.relative_to(run).as_posix():sha(p) for j in done for p in (run/j['id']).rglob('*') if p.is_file()}
core={name:sha(root/name) for name in ('standard.py','behavior.py','domain_cases.py','domain-cases.json','frozen-standard/manifest.json')}
event={'time_unix':time.time(),'authorization':'User: let\'s finished remaining task','previous_deadline_unix':plan['deadline_unix'],'deadline_disabled':True,'completed_jobs_preserved':len(done),'completed_files':preserved,'evaluation_protocol_files':core,'remaining_jobs':len(state['jobs'])-len(done),'note':'Only runtime policy changes. Existing worker reads a numeric deadline, so its compatibility field is set to year 9999; the controller disables the deadline and the dashboard displays no hard stop. Prompts, decoding, model revisions, selected samples and scoring remain unchanged.'}
plan['runtime_extensions']=plan.get('runtime_extensions',[])+[event]
plan['deadline_disabled']=True
plan['deadline_unix']=253402214400.0
plan['title']='Cortex v1 vs Qwen3-8B-Base — continued evaluation'
plan['note']=plan['note'].replace('Hard deadline stops safely and preserves partial results.','The original runtime budget was reached; the user authorized continuation to finish remaining work without a new hard stop. Completed work remains preserved.')
state['title']=plan['title'];state['note']=plan['note'];state['deadline_unix']=None
(root/'plan.json').write_text(json.dumps(plan,indent=2));(run/'state.json').write_text(json.dumps(state,indent=2))
(archive/'extension.json').write_text(json.dumps(event,indent=2))
# Retire current partial summary/checksum files into the immutable archive; they
# must not look like the final state of the now-resumed run.
for path in (run/'summary-final-or-partial.json',run/'SHA256SUMS.json'):
    if path.exists():path.rename(archive/('retired-'+path.name))
subprocess.run(['systemctl','--user','restart','cortex-benchmark.service','cortex-benchmark-public.service','cortex-dashboard-private.service'],check=True)
for attempt in range(20):
    try:
        request=urllib.request.Request('http://127.0.0.1:8765/api/resume',method='POST',headers={'X-Benchmark-Control':'1'})
        with urllib.request.urlopen(request,timeout=5) as response:assert response.status==200
        break
    except OSError:
        if attempt==19:raise
        time.sleep(1)
subprocess.run(['systemctl','--user','start','cortex-full-summary.service'],check=True)
assert all(sha(run/name)==digest for name,digest in preserved.items()),'Completed artifact changed'
assert all(sha(root/name)==digest for name,digest in core.items()),'Evaluation protocol changed'
print('RESUMED_TO_COMPLETION',len(done),'completed jobs preserved;',len(state['jobs'])-len(done),'unfinished jobs queued',flush=True)
