import collections,hashlib,json,time
from pathlib import Path
from base_protocol import EXPECTED_MODELS
from domain_cases import build
root=Path(__file__).parent;manifest=json.loads((root/'frozen-standard/manifest.json').read_text())
deadline=json.loads((root/'plan.json').read_text())['deadline_unix']
plan={'title':'Cortex v1 vs Qwen3-8B-Base — 15-hour budgeted evaluation','deadline_unix':deadline,'note':'Time-budgeted coverage of all requested categories, not all official full test splits. Seeded up to 50 examples per standard leaf task; 1,280 bilingual synthetic domain cases per model; 120 paired context cases per model plus 40 Cortex-only 64K cases. Standard tasks use matched completion; deployment fixtures use Cortex native chat vs Base plain transcript with identical demonstrations, schema and 128-token cap. Synthetic cases are parameter-held-out, not independently authored. No overall winner. Hard deadline stops safely and preserves partial results.','jobs':[]}
models=list(EXPECTED_MODELS.items())
for suite in ('kobest_boolq','arc_challenge','kobest_copa','kobest_hellaswag','kobest_sentineg','haerae','kmmlu','mmlu','hellaswag','winogrande','gsm8k'):
    metadata=manifest['suites'][suite];n=sum(len(v) for v in metadata['samples'].values())
    for i,(model,revision) in enumerate(models):plan['jobs'].append(dict(id=f'standard-{suite}-{i}',model=model,revision=revision,task=suite,category=metadata['category'],runner='standard-audited',suite=suite,fewshot=metadata['fewshot'],limit=None,sample_count=n,batch_size=1 if suite=='gsm8k' else 'auto:16',chat=False,track='Matched raw completion; frozen stratified sample',generation=suite=='gsm8k'))
for category in ('Four-tool routing','Abstention and no-tool','Tool-result grounding','Multi-turn fixture state','Instruction constraints'):
    n=sum(c['category']==category for c in build())
    for i,(model,revision) in enumerate(models):plan['jobs'].append(dict(id=f'domain-{category.lower().replace(" ","-")}-{i}',model=model,revision=revision,task=category,category='Tool calling' if 'tool routing' in category else 'Chat',runner='behavior-full',suite='domain',domain_category=category,sample_count=n,chat=False,fewshot=0,track='Native chat + fixed examples' if i==0 else 'Plain transcript + same fixed examples'))
for context in (4096,16384,32768,65536):
    for i,(model,revision) in enumerate(models[:1] if context==65536 else models):plan['jobs'].append(dict(id=f'context-{context}-{i}',model=model,revision=revision,task=f'Context {context//1024}K',category='Long context',runner='behavior-full',suite='context',domain_category=f'Context {context//1024}K',context=context,sample_count=40,chat=False,fewshot=0,track=('Cortex-only extension' if context==65536 else 'Paired source text; deployment serialization differs')))
(root/'plan.json').write_text(json.dumps(plan,indent=2))
(root/'domain-cases.json').write_text(json.dumps({'seed':20261110,'limitations':'Synthetic parameter-held-out fixtures, not independent holdout; mult-turn tasks provide history rather than executing live tools.','cases':build()},ensure_ascii=False,indent=2),encoding='utf-8')
(root/'READY').write_text('Frozen datasets, plan and calibration completed.')
files={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in root.iterdir() if f.is_file() and f.name!='code-manifest.json'}
(root/'code-manifest.json').write_text(json.dumps(files,indent=2))
print('PLAN_READY',len(plan['jobs']),'jobs',sum(j['sample_count'] for j in plan['jobs']),'scenarios',flush=True)
