import json
from pathlib import Path
from huggingface_hub import snapshot_download

root = Path(__file__).resolve().parent
metadata = json.loads((root / 'qwen-assistant-metadata.json').read_text())
print('Downloading assistant comparator', metadata['id'], metadata['sha'], flush=True)
snapshot_download(metadata['id'], revision=metadata['sha'], max_workers=4,
                  allow_patterns=['*.json','*.safetensors','*.jinja','*.txt','*.model'])
print('ASSISTANT_DOWNLOAD_COMPLETE', flush=True)
