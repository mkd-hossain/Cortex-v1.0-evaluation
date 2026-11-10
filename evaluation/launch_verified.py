"""Wait for frozen data/calibration, validate actual harness paths, then launch."""
import json,subprocess,sys,time,urllib.request
from pathlib import Path
from base_protocol import EXPECTED_MODELS
root=Path(__file__).parent
def run(*args):subprocess.run([sys.executable,'-u',*map(str,args)],check=True,cwd=root)
while not (root/'frozen-standard/manifest.json').exists():
    if subprocess.run(['systemctl','--user','is-active','--quiet','cortex-freeze-full.service']).returncode:
        raise SystemExit('Dataset freezing failed: inspect journal; no scored inference launched')
    print('WAITING_FOR_DATASET_FREEZE',flush=True);time.sleep(10)
while not all((root/'calibration-v2'/str(i)/'results-behavior.json').exists() for i in (0,1)):
    if subprocess.run(['systemctl','--user','is-active','--quiet','cortex-calibrate-full-v2.service']).returncode:
        raise SystemExit('Calibration did not complete; no scored inference launched')
    print('WAITING_FOR_CALIBRATION',flush=True);time.sleep(10)
summary={}
for i,model in enumerate(EXPECTED_MODELS):
    rows=[json.loads(x) for x in (root/'calibration-v2'/str(i)/'samples.jsonl').read_text().splitlines()]
    assert any(r['terminated'] for r in rows),'No valid stopping boundary observed'
    summary[model]={'cases':len(rows),'terminated':sum(r['terminated'] for r in rows),'truncated':sum(r['truncated'] for r in rows),'seconds':sum(r['seconds'] for r in rows),'output_tokens':sum(r['output_tokens'] for r in rows)}
(root/'calibration-summary.json').write_text(json.dumps(summary,indent=2))
run(root/'size_budget.py')
run(root/'prepare_full.py')
for i,(model,revision) in enumerate(EXPECTED_MODELS.items()):
    output=root/'harness-preflight'/str(i)
    if not (output/'results-standard.json').exists():
        run(root/'standard.py','--model',model,'--revision',revision,'--suite','kobest_boolq','--preflight','--output',output)
# Verify the generation-cap path on an actual math request before queueing scored work.
model,revision=next(iter(EXPECTED_MODELS.items()))
if not (root/'math-preflight-v3/results-standard.json').exists():
    run(root/'standard.py','--model',model,'--revision',revision,'--suite','gsm8k','--preflight','--output',root/'math-preflight-v3')
run(root/'test_full.py')
run(root/'deploy_full.py')
for attempt in range(20):
    try:
        request=urllib.request.Request('http://127.0.0.1:8765/api/start',method='POST',headers={'X-Benchmark-Control':'1'})
        with urllib.request.urlopen(request,timeout=5) as response:print('FULL_RUN_STARTED',response.read().decode(),flush=True)
        break
    except OSError:
        if attempt==19:raise
        time.sleep(1)
(root/'STARTED').write_text(str(time.time()))
