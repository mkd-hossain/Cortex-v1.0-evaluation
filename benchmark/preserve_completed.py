"""Preserve the completed mixed run and separately label its Instruct comparison."""
import hashlib
import json
from pathlib import Path
import shutil
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'runs-short-all-v1'
DEST=ROOT/'archives'/'2026-11-09-cortex-v1-vs-qwen3-8b-instruct'
state=json.loads((RUN/'state.json').read_text())
assert state['status']=='completed' and all(j['status']=='completed' for j in state['jobs'])
DEST.mkdir(parents=True,exist_ok=True)
if not (DEST/'original-mixed-run').exists():
    shutil.copytree(RUN,DEST/'original-mixed-run')
for path in RUN.rglob('*'):
    if path.is_file():
        target=DEST/'original-mixed-run'/path.relative_to(RUN)
        assert hashlib.sha256(path.read_bytes()).digest()==hashlib.sha256(target.read_bytes()).digest(),str(path)
source_dir=DEST/'original-source';source_dir.mkdir(exist_ok=True)
for name in ('controller.py','run_diagnostics.py','diagnostic_cases.py','short-all.json','SHORT_PROTOCOL.md',
             'cortex-metadata.json','qwen-metadata.json','qwen-assistant-metadata.json'):
    target=source_dir/name
    if not target.exists():shutil.copy2(ROOT/name,target)
if (ROOT/'provenance').exists() and not (DEST/'provenance').exists():
    shutil.copytree(ROOT/'provenance',DEST/'provenance')
with urlopen('http://127.0.0.1:8765/api/status') as response:
    snapshot=json.load(response)
from dashboard_data import enrich,comparison_rows
data=enrich(snapshot)
instruct_jobs=[j for j in data['jobs'] if j['model']=='Qwen/Qwen3-8B' or
               (j['model']=='mkd-hossain/Keural-Cortex-8B-v1.0' and (j.get('chat') or j.get('runner')=='diagnostics'))]
assert len(instruct_jobs)==31
summary={'label':'Keural Cortex v1.0 vs Qwen3-8B Instruct - preserved completed pilot',
         'model_labels':{'Qwen/Qwen3-8B':'Qwen3-8B Instruct','mkd-hossain/Keural-Cortex-8B-v1.0':'Keural Cortex v1.0'},
         'note':'Instruct is the display name for Qwen/Qwen3-8B. Qwen3-8B-Base records remain correctly labeled in original-mixed-run and are not relabeled as Instruct.',
         'jobs':instruct_jobs,'assistant_comparison':comparison_rows(data,'assistant'),
         'context_comparison':comparison_rows(data,'context'),'warnings':data['warnings']}
(DEST/'qwen3-8b-instruct-results.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
with urlopen('http://127.0.0.1:8766/api/report.pdf',timeout=60) as response:
    (DEST/'original-completed-mixed-report.pdf').write_bytes(response.read())
(DEST/'README.txt').write_text(
    'PRESERVED COMPLETED PILOT\n\nDisplay name: Qwen3-8B Instruct\nExact Hugging Face ID: Qwen/Qwen3-8B\n'
    'Frozen revision: b968826d9c46dd6066d109eabc6255188de91218\n\n'
    'qwen3-8b-instruct-results.json isolates the 31 native-chat/context jobs.\n'
    'original-mixed-run preserves all 53 original jobs bit for bit, including the 22 actual Base-completion jobs.\n'
    'The original completed PDF describes the mixed run, not an Instruct-only evaluation.\n'
    'Generation-budget override warnings are retained. Small samples do not establish an overall winner.\n',encoding='utf-8')
manifest=[]
for path in sorted(DEST.rglob('*')):
    if path.is_file() and path.name!='SHA256SUMS.txt':
        manifest.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.relative_to(DEST).as_posix())
(DEST/'SHA256SUMS.txt').write_text('\n'.join(manifest)+'\n',encoding='utf-8')
print('PRESERVED',DEST,'original jobs',len(state['jobs']),'Instruct comparison jobs',len(instruct_jobs),'verified files',len(manifest))
