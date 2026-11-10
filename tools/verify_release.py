"""Verify published artifact bytes. Run from any directory."""
from pathlib import Path
import hashlib
root=Path(__file__).resolve().parent.parent
count=0
for line in (root/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
    expected,relative=line.split('  ',1)
    target=(root/relative).resolve()
    assert target.is_relative_to(root),relative
    assert hashlib.sha256(target.read_bytes()).hexdigest()==expected,relative
    count+=1
print(f'Verified {count} artifact checksums.')
