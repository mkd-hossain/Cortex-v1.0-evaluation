"""Install isolated development run; retain old run and service definitions."""
from pathlib import Path
import shutil,subprocess,time,json
root=Path.home()/'cortex-benchmark'; here=root/'audited-smoke'; units=Path.home()/'.config/systemd/user'
backup=root/'archives'/('before-audited-smoke-'+str(int(time.time())));backup.mkdir(parents=True)
state=json.loads((root/'runs-base-only-v1/state.json').read_text())
assert all(j['status']=='completed' for j in state['jobs']), 'Do not interrupt unfinished old run'
for name in ('cortex-benchmark.service','cortex-benchmark-public.service','cortex-dashboard-private.service'):
    shutil.copy2(units/name,backup/name)
for name in ('cortex-benchmark.service','cortex-benchmark-public.service','cortex-dashboard-private.service'):
    old=(units/name).read_text();new=old.replace('prepared-base-only','audited-smoke').replace('runs-base-only-v1','runs-audited-smoke-v1')
    new=new.replace('PREPARED Cortex v1 versus Qwen3-8B-Base pilot','Audited bilingual development smoke')
    if name!='cortex-benchmark.service':new=new.replace('[Service]','[Service]\nEnvironment=BENCHMARK_RUN=runs-audited-smoke-v1')
    (units/name).write_text(new)
subprocess.run(['systemctl','--user','daemon-reload'],check=True)
subprocess.run(['systemctl','--user','restart','cortex-benchmark.service','cortex-benchmark-public.service','cortex-dashboard-private.service'],check=True)
print('Installed isolated smoke dashboard; previous run preserved at',root/'runs-base-only-v1')
