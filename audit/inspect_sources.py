"""Read-only audit inventory and bounded HF data inspection; no model inference."""
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'evidence';OUT.mkdir(exist_ok=True)
source=ROOT/'training-source'
records=[]
for path in source.rglob('*'):
    if path.is_file() and '.git' not in path.parts:
        records.append({'path':path.relative_to(source).as_posix(),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(OUT/'source-inventory.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
builder=source/'audit/keural_agent_20260923/build_dataset.py'
spec=importlib.util.spec_from_file_location('read_only_agent_builder',builder)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
families=collections.defaultdict(collections.Counter)
for index in range(120):
    row=module.row(index,False)
    question=next(m['content'] for m in row['messages'] if m['role']=='user')
    language='ko' if any('\uac00'<=c<='\ud7a3' for c in question) else 'en'
    families[row['family']][language]+=1
(OUT/'agent-generator-language-coverage.json').write_text(json.dumps(families,indent=2),encoding='utf-8')

dataset=json.loads((ROOT/'hf-dataset-metadata.json').read_text())
sha=dataset['sha'];repo=dataset['id']
for name in ('README.md','MANIFEST.json'):
    url=f'https://huggingface.co/datasets/{repo}/resolve/{sha}/{name}'
    try:
        body=urllib.request.urlopen(url,timeout=30).read()
        (OUT/('hf-sft-'+name)).write_bytes(body)
    except Exception as error:
        (OUT/('hf-sft-'+name+'.error.txt')).write_text(type(error).__name__,encoding='utf-8')
(OUT/'dataset-identity.json').write_text(json.dumps({'id':repo,'revision':sha,'files':[x['rfilename'] for x in dataset['siblings']]},indent=2),encoding='utf-8')

summary=[]
for run,label in [(ROOT/'base-only-run','plain-base-only'),(ROOT.parent/'benchmark/archives/2026-11-09-cortex-v1-vs-qwen3-8b-instruct/original-mixed-run','native-mixed')]:
    for path in run.rglob('samples.jsonl'):
        for line in path.read_text(encoding='utf-8').splitlines():
            row=json.loads(line)
            response=row.get('response',{})
            summary.append({'run':label,'job':path.parent.parent.name,'id':row['id'],'passed':row['passed'],
                            'reason':row['reason'],'expected':row['expected'],'truncated':response.get('truncated'),
                            'input_tokens':response.get('input_tokens'),'output_tokens':response.get('output_tokens'),
                            'raw_excerpt':response.get('raw','')[:800], 'final_excerpt':response.get('final','')[:500]})
(OUT/'pilot-response-audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print('Inventoried',len(records),'source files; inspected generator coverage; summarized',len(summary),'saved diagnostic responses')
for row in summary:
    if 'context' in row['job']:
        print(row['run'],row['job'],row['id'],'pass',row['passed'],'truncated',row['truncated'],repr(row['final_excerpt'][:160]))
