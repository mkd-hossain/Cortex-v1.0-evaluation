import json,hashlib
from pathlib import Path
from base_protocol import EXPECTED_MODELS
from smoke import cases,TOOLS
root=Path(__file__).parent
plan={'title':'Audited configuration and tool-contract development smoke','note':'24 development cases per model. Cortex native chat vs Qwen3-8B-Base plain transcript: same requests/tools/budget; different serialization. Not final holdout, not an overall ranking. Corrected RoPE adapter; strict and component scores preserved.','jobs':[]}
for i,(model,rev) in enumerate(EXPECTED_MODELS.items()):
    plan['jobs'].append(dict(id=f'smoke-{i}',model=model,revision=rev,runner='audited-smoke',task='Bilingual tool-contract development smoke',category='Development smoke',track='Native chat' if i==0 else 'Plain transcript (base model)',chat=False,fewshot=0,limit=24))
(root/'plan.json').write_text(json.dumps(plan,indent=2))
(root/'public-cases.json').write_text(json.dumps({'license':'CC0-1.0 for newly authored synthetic cases only','status':'Development cases; not independent final holdout','cases':cases(),'tools':TOOLS},ensure_ascii=False,indent=2),encoding='utf-8')
manifest={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in root.iterdir() if f.is_file() and f.name!='manifest.json'}
(root/'manifest.json').write_text(json.dumps(manifest,indent=2))
