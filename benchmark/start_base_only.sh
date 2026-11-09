#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/cortex-benchmark"
.venv/bin/python - <<'PY'
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path('prepared-base-only').resolve()))
from base_protocol import validate_plan
plan=json.loads(Path('prepared-base-only/plan.json').read_text())
validate_plan(plan)
assert len(plan['jobs'])==31
print('Validated exact Cortex v1 and Qwen3-8B-Base revisions; 31 jobs')
PY
cp prepared-base-only/PREPARED-NOT-INSTALLED.service "$HOME/.config/systemd/user/cortex-benchmark.service"
python3 - <<'PY'
from pathlib import Path
root=Path.home()/'cortex-benchmark'
config=Path.home()/'.config/systemd/user'
for unit,port,flag in [('cortex-benchmark-public',8766,''),('cortex-dashboard-private',8767,' --private')]:
    (config/(unit+'.service')).write_text(f'''[Unit]
Description=Benchmark Evaluation Lab - Cortex vs Qwen3-8B-Base
After=cortex-benchmark.service
[Service]
WorkingDirectory={root}/prepared-base-only
ExecStart={root}/.dashboard-venv/bin/python -u dashboard_web.py --port {port}{flag}
Restart=on-failure
RestartSec=3
[Install]
WantedBy=default.target
''')
    dropin=config/(unit+'.service.d')/'base-only-view.conf'
    if dropin.exists():dropin.write_text('[Service]\nUnsetEnvironment=BENCHMARK_PREPARED_PLAN\n')
PY
systemctl --user daemon-reload
systemctl --user restart cortex-benchmark.service
systemctl --user restart cortex-benchmark-public.service cortex-dashboard-private.service
.venv/bin/python - <<'PY'
import json,time
from urllib.request import urlopen,Request
for i in range(30):
    try:
        state=json.load(urlopen('http://127.0.0.1:8765/api/status',timeout=5))
        assert len(state['jobs'])==31
        assert {j['model'] for j in state['jobs']}=={'Qwen/Qwen3-8B-Base','mkd-hossain/Keural-Cortex-8B-v1.0'}
        break
    except Exception:
        if i==29:raise
        time.sleep(.5)
request=Request('http://127.0.0.1:8765/api/start',method='POST',headers={'X-Benchmark-Control':'1'})
print(urlopen(request).read().decode())
print('BASE_ONLY_RUN_STARTED')
PY
