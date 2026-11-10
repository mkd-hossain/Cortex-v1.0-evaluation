"""Read-only hashes of the exact model snapshots and installed harness source."""
import hashlib,json,subprocess,sys
from pathlib import Path
from huggingface_hub import snapshot_download
from base_protocol import EXPECTED_MODELS
import lm_eval,transformers,torch
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()
out={'torch':torch.__version__,'transformers':transformers.__version__,'models':{},'harness':{}}
for model,revision in EXPECTED_MODELS.items():
    root=Path(snapshot_download(model,revision=revision,local_files_only=True))
    files={p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p)} for p in root.rglob('*') if p.is_file() and p.suffix in ('.safetensors','.json','.jinja')}
    out['models'][model]={'revision':revision,'files':files}
root=Path(lm_eval.__file__).parent
out['harness']={p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file() and p.suffix in ('.py','.yaml','.yml')}
out['hardware']=subprocess.check_output(['nvidia-smi','--query-gpu=name,driver_version','--format=csv,noheader'],text=True).strip()
Path(__file__).with_name('environment-provenance.json').write_text(json.dumps(out,indent=2))
Path(__file__).with_name('requirements-recorded.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
print('PROVENANCE_COMPLETE',flush=True)
