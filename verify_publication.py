"""Verify publication checksums without inference or network access."""
import hashlib,json
from pathlib import Path
root=Path(__file__).parent
manifest=json.loads((root/'SHA256SUMS.json').read_text())
for name,expected in manifest.items():
    path=root/name
    assert path.is_file(),name
    assert hashlib.sha256(path.read_bytes()).hexdigest()==expected,name
assert not (root/'audit/training-source').exists()
print(f'Verified {len(manifest)} published file checksums.')
