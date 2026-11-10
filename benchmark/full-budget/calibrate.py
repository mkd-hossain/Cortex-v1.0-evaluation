import json,subprocess,sys,time
from pathlib import Path
from base_protocol import EXPECTED_MODELS
root=Path(__file__).parent
if not (root/'plan.json').exists():(root/'plan.json').write_text(json.dumps({'deadline_unix':time.time()+14*3600}))
for i,(model,revision) in enumerate(EXPECTED_MODELS.items()):
    out=root/'calibration-v2'/str(i)
    subprocess.run([sys.executable,'-u',str(root/'behavior.py'),'--model',model,'--revision',revision,'--category','Calibration','--calibrate','--output',str(out)],check=True)
    rows=[json.loads(x) for x in (out/'samples.jsonl').read_text().splitlines()]
    assert any(r['terminated'] for r in rows),'No valid output termination: do not launch full run'
print('CALIBRATION_COMPLETE',flush=True)
