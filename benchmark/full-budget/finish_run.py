"""Persist honest final/partial coverage and paired descriptive summaries."""
import collections,hashlib,json,random,time
from pathlib import Path
root=Path(__file__).parent;run=root.parent/'runs-full-budget-v1'
while True:
    try:state=json.loads((run/'state.json').read_text())
    except (OSError,ValueError):time.sleep(10);continue
    if state['status'] in ('completed','budget_exhausted'):break
    time.sleep(10)
summary={'status':state['status'],'deadline_unix':state.get('deadline_unix'),'completed_jobs':sum(j['status']=='completed' for j in state['jobs']),'total_jobs':len(state['jobs']),'limitations':'Descriptive results only; synthetic fixtures are not independent holdout. No overall winner. Missing or interrupted work is not scored zero. Standard-task normalization differs across tasks.','jobs':state['jobs'],'paired_fixtures':{}}
groups=collections.defaultdict(dict)
for job in state['jobs']:
    if job.get('runner')!='behavior-full':continue
    path=run/job['id']/'results/samples.jsonl'
    if not path.exists():continue
    for line in path.read_text(encoding='utf-8').splitlines():
        try:r=json.loads(line)
        except ValueError:continue
        key=(job['domain_category'],r['language']);groups[key].setdefault(job['model'],{})[r['id']]=r
rng=random.Random(20261110)
for (category,language),models in groups.items():
    if len(models)!=2:continue
    cortex=models.get('mkd-hossain/Keural-Cortex-8B-v1.0',{});base=models.get('Qwen/Qwen3-8B-Base',{})
    ids=sorted(set(cortex)&set(base))
    if not ids:continue
    differences=[int(cortex[i]['passed'])-int(base[i]['passed']) for i in ids];n=len(ids)
    draws=sorted(sum(rng.choice(differences) for _ in ids)/n for _ in range(2000))
    summary['paired_fixtures'][category+'/'+language]={'paired_cases':n,'cortex_passed':sum(cortex[i]['passed'] for i in ids),'base_passed':sum(base[i]['passed'] for i in ids),'difference':sum(differences)/n,'paired_bootstrap_95_percentile':[draws[49],draws[1949]],'confidence_interval_scope':'Within these synthetic fixtures; does not account for template dependence or task selection.'}
(run/'summary-final-or-partial.json').write_text(json.dumps(summary,indent=2))
files={p.relative_to(run).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in run.rglob('*') if p.is_file() and p.suffix not in ('.db','.lock') and p.name!='SHA256SUMS.json'}
(run/'SHA256SUMS.json').write_text(json.dumps(files,indent=2));print('FINAL_OR_PARTIAL_AUDIT_SAVED',state['status'],flush=True)
