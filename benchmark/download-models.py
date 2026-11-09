"""Download exact model snapshots, independently of the evaluation queue."""
import json
from pathlib import Path
from huggingface_hub import snapshot_download

root = Path(__file__).resolve().parent
plan = json.loads((root / 'plan.json').read_text())
models = {job['model']: job['revision'] for job in plan['jobs']}
for model, revision in models.items():
    print('Downloading', model, revision, flush=True)
    path = snapshot_download(model, revision=revision, max_workers=4,
                             allow_patterns=['*.json', '*.safetensors', '*.jinja', '*.txt', '*.model'])
    print('Snapshot ready', path, flush=True)
print('MODEL_DOWNLOADS_COMPLETE', flush=True)
