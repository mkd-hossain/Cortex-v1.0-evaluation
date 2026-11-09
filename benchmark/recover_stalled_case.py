"""Stop only the verified stalled evaluator; never reset GPU or touch other apps."""
import json
import os
from pathlib import Path
import signal
import time

root=Path.home()/'cortex-benchmark'
state_path=root/'runs-base-only-v1/state.json'
state=json.loads(state_path.read_text())
job=next(j for j in state['jobs'] if j['status']=='running')
assert job['id']=='cortex-context-16384'
pid=job['pid']
command=Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\x00',b' ')
assert b'prepared-base-only/run_diagnostics.py' in command and b'cortex-context-16384' in command
assert os.getpgid(pid)==pid
os.killpg(pid,signal.SIGTERM)
for _ in range(10):
    time.sleep(.5)
    if not Path(f'/proc/{pid}').exists():break
else:
    os.killpg(pid,signal.SIGKILL)
print('Termination requested for stalled evaluator only:',pid)
