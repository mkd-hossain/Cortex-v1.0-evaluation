import json
from pathlib import Path
import torch
import transformers
from lm_eval.tasks import TaskManager

assert torch.cuda.is_available(), 'CUDA unavailable'
print('PyTorch', torch.__version__, 'Transformers', transformers.__version__)
print('GPU', torch.cuda.get_device_name(0), 'capability', torch.cuda.get_device_capability(0))
x = torch.randn(512, 512, dtype=torch.bfloat16, device='cuda')
assert torch.isfinite(x @ x).all().item()
print('BF16 GPU matrix multiplication passed')
manager = TaskManager()
plan = json.loads(Path('plan.json').read_text())
for task in sorted({job['task'] for job in plan['jobs']}):
    assert task in manager.all_tasks, f'Task unavailable: {task}'
    print('Task found:', task)
