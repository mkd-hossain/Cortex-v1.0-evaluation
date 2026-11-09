"""One GPU query at a time, isolated from all dashboard HTTP requests."""
import json
from pathlib import Path
import subprocess
import time

root=Path(__file__).resolve().parent/'prepared-base-only'
while True:
    try:
        result=subprocess.run(['nvidia-smi','--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu','--format=csv,noheader'],capture_output=True,text=True,timeout=3)
        if result.returncode==0:
            target=root/'gpu-telemetry.json';temporary=target.with_suffix('.tmp')
            temporary.write_text(json.dumps({'time':time.time(),'gpu':result.stdout.strip()}));temporary.replace(target)
    except (OSError,subprocess.TimeoutExpired):
        pass
    time.sleep(5)
