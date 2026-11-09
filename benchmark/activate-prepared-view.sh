#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/cortex-benchmark"
mkdir -p archived-dashboard-before-base-only
cp --update=none dashboard.html dashboard.js archived-dashboard-before-base-only/
cp prepared-base-only/dashboard.html dashboard.html
cp prepared-base-only/dashboard.js dashboard.js
python3 - <<'PY'
from pathlib import Path
p=Path('dashboard.js')
s=p.read_text()
s=s.replace("if(privateMode){$('controls').hidden=false;", "if(privateMode){$('controls').hidden=!state.data.controls_enabled;")
p.write_text(s)
for unit in ('cortex-benchmark-public','cortex-dashboard-private'):
    folder=Path.home()/'.config/systemd/user'/f'{unit}.service.d'
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'base-only-view.conf').write_text('[Service]\nEnvironment=BENCHMARK_PREPARED_PLAN=prepared-base-only/plan.json\n')
PY
systemctl --user daemon-reload
systemctl --user restart cortex-benchmark-public cortex-dashboard-private
echo BASE_ONLY_VIEW_READY_NO_EVALUATION_STARTED
