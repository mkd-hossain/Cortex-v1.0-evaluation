import json
from pathlib import Path
import shutil
import subprocess
import time

root=Path.home()/'cortex-benchmark'
run=root/'runs-base-only-v1'
state=json.loads((run/'state.json').read_text())
assert state['status']!='running','An evaluator is active; do not restart the controller.'
completed=[j['id'] for j in state['jobs'] if j['status']=='completed']
assert len(completed)==13
shutil.copy2(run/'state.json',run/'state-before-resume-fix.json')
check=subprocess.run(['nvidia-smi','--query-gpu=name','--format=csv,noheader'],capture_output=True,text=True,timeout=5)
assert check.returncode==0,'GPU is not ready'
marker=run/'recovery-required.json'
if marker.exists():marker.rename(run/f'recovery-resolved-after-reboot-{time.time_ns()}.json')
unit=Path.home()/'.config/systemd/user/cortex-gpu-telemetry.service'
unit.write_text(f'''[Unit]
Description=Isolated GPU telemetry sampler
[Service]
ExecStart=/usr/bin/python3 {root}/gpu_sampler.py
Restart=on-failure
RestartSec=5
[Install]
WantedBy=default.target
''')
subprocess.run(['systemctl','--user','daemon-reload'],check=True)
subprocess.run(['systemctl','--user','enable','--now','cortex-gpu-telemetry'],check=True)
subprocess.run(['systemctl','--user','restart','cortex-benchmark','cortex-benchmark-public','cortex-dashboard-private'],check=True)
after=json.loads((run/'state.json').read_text())
assert [j['id'] for j in after['jobs'] if j['status']=='completed']==completed
print('RESUME_FIX_INSTALLED; all 13 completed jobs preserved; awaiting Resume')
