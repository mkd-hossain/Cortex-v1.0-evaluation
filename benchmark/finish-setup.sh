#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/cortex-benchmark"
exec >> setup.log 2>&1
echo 'Waiting for isolated CUDA/PyTorch installation to finish.'
while systemctl --user is-active --quiet cortex-benchmark-setup.service; do sleep 10; done
echo 'Checking installed environment and tasks.'
.venv/bin/python verify-spark.py
.venv/bin/python -m unittest discover -p test_controller.py -v
mkdir -p provenance
uv pip freeze --python .venv/bin/python > provenance/pip-freeze.txt
nvidia-smi -q > provenance/nvidia-smi.txt
uname -a > provenance/uname.txt
sha256sum *.py plan.json pilot.json > provenance/source-sha256.txt
touch provenance/ready
echo 'Environment verified. Waiting for pinned model downloads.'
while systemctl --user is-active --quiet cortex-model-downloads.service; do sleep 10; done
grep -q MODEL_DOWNLOADS_COMPLETE downloads.log
echo 'Models downloaded. Starting the 20-example-per-task pilot.'
.venv/bin/python - <<'PY'
from urllib.request import Request, urlopen
import json
status = json.load(urlopen('http://127.0.0.1:8765/api/status'))
if status['status'] == 'ready':
    request = Request('http://127.0.0.1:8765/api/start', method='POST', headers={'X-Benchmark-Control': '1'})
    print(urlopen(request).read().decode())
else:
    print('Preserving existing controller state:', status['status'])
PY
