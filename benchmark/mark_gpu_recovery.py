import json
from pathlib import Path
root=Path.home()/'cortex-benchmark/runs-base-only-v1'
(root/'recovery-required.json').write_text(json.dumps({'message':'GPU driver stalled during the 16K context case. 13 completed jobs are saved. Evaluator termination is pending in the driver; recovery is required before continuing.','pid':669075}))
