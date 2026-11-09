#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/cortex-benchmark"
test -f provenance/ready
cp -n "$HOME/.config/systemd/user/cortex-benchmark.service" cortex-benchmark-pilot-backup.service || true
cp cortex-benchmark-short.service "$HOME/.config/systemd/user/cortex-benchmark.service"
systemctl --user daemon-reload
systemctl --user restart cortex-benchmark.service
systemctl --user restart cortex-benchmark-public.service
.venv/bin/python - <<'PY'
import json,time
from urllib.request import urlopen,Request
for i in range(20):
    try:
        state=json.load(urlopen('http://127.0.0.1:8765/api/status',timeout=5))
        assert state['title']=='Seven-category short evaluation'
        assert len(state['jobs'])==53
        break
    except Exception:
        if i==19: raise
        time.sleep(.5)
request=Request('http://127.0.0.1:8765/api/start',method='POST',headers={'X-Benchmark-Control':'1'})
print(urlopen(request).read().decode())
print('SHORT_EVALUATION_STARTED',len(state['jobs']),'jobs')
PY
