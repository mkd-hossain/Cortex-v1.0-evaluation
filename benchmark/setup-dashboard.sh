#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/cortex-benchmark"
exec >> dashboard-setup.log 2>&1
uv venv --python python3 .dashboard-venv
uv pip install --python .dashboard-venv/bin/python 'reportlab>=4.4,<5'
uv pip freeze --python .dashboard-venv/bin/python > dashboard-requirements.lock
echo DASHBOARD_ENVIRONMENT_READY
