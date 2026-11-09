#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/cortex-benchmark"
exec >> setup.log 2>&1
export UV_LINK_MODE=copy
uv venv --python python3 .venv
uv pip install --python .venv/bin/python 'torch==2.11.0' --index-url https://download.pytorch.org/whl/cu130
uv pip install --python .venv/bin/python 'lm_eval==0.4.12' 'transformers==4.57.6' 'datasets==3.6.0' 'accelerate==1.12.0' sentencepiece
.venv/bin/python verify-spark.py
.venv/bin/python -m unittest discover -p test_controller.py -v
mkdir -p provenance
.venv/bin/python -m pip freeze > provenance/pip-freeze.txt 2>/dev/null || uv pip freeze --python .venv/bin/python > provenance/pip-freeze.txt
nvidia-smi -q > provenance/nvidia-smi.txt
uname -a > provenance/uname.txt
sha256sum *.py *.json > provenance/source-sha256.txt
touch provenance/ready
echo SETUP_COMPLETE
