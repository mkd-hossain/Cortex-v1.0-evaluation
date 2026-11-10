"""Archive previous code manifest before recording a runtime-policy update."""
import hashlib,json
from pathlib import Path
root=Path(__file__).parent;run=root.parent/'runs-full-budget-v1'
archives=sorted((run/'runtime-extensions').iterdir());assert archives
manifest=root/'code-manifest.json';backup=archives[-1]/'code-manifest-before.json'
if manifest.exists() and not backup.exists():backup.write_bytes(manifest.read_bytes())
files={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in root.iterdir() if f.is_file() and f.suffix in ('.py','.html','.js','.css','.json','.md','.txt') and f.name!='code-manifest.json'}
manifest.write_text(json.dumps(files,indent=2));print('RUNTIME_MANIFEST_REFRESHED',flush=True)
