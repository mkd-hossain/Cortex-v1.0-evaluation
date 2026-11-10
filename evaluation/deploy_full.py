import json,shutil,subprocess,time,hashlib
from pathlib import Path
root=Path.home()/'cortex-benchmark';here=root/'full-budget';units=Path.home()/'.config/systemd/user'
assert (here/'READY').exists()
(here/'code-manifest.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in here.iterdir() if f.is_file() and f.name!='code-manifest.json'},indent=2))
old=json.loads((root/'runs-audited-smoke-v1/state.json').read_text());assert all(j['status']=='completed' for j in old['jobs']), 'Old run has unfinished work'
backup=root/'archives'/('before-full-budget-'+str(int(time.time())));backup.mkdir(parents=True)
for name in ('cortex-benchmark.service','cortex-benchmark-public.service','cortex-dashboard-private.service'):
    shutil.copy2(units/name,backup/name)
    text=(units/name).read_text().replace('audited-smoke','full-budget').replace('runs-full-budget-v1','runs-full-budget-v1')
    # The directory replacement changes runs-audited-smoke-v1 to runs-full-budget-v1 too.
    (units/name).write_text(text)
(units/'cortex-full-summary.service').write_text('''[Unit]
Description=Save completed or budget-limited evaluation audit summary
After=cortex-benchmark.service
[Service]
WorkingDirectory=%h/cortex-benchmark/full-budget
ExecStart=%h/cortex-benchmark/.venv/bin/python -u finish_run.py
Restart=on-failure
RestartSec=5
[Install]
WantedBy=default.target
''')
subprocess.run(['systemctl','--user','daemon-reload'],check=True)
subprocess.run(['systemctl','--user','restart','cortex-benchmark.service','cortex-benchmark-public.service','cortex-dashboard-private.service'],check=True)
subprocess.run(['systemctl','--user','enable','--now','cortex-full-summary.service'],check=True)
print('Full budgeted dashboard installed; old smoke preserved')
