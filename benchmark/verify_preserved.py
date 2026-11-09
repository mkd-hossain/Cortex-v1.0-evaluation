import hashlib
from pathlib import Path
import shutil

root=Path(__file__).resolve().parent/'archives'
archive=root/'2026-11-09-cortex-v1-vs-qwen3-8b-instruct'
lines=(archive/'SHA256SUMS.txt').read_text().splitlines()
for line in lines:
    expected,name=line.split('  ',1)
    assert hashlib.sha256((archive/name).read_bytes()).hexdigest()==expected,name
zip_path=shutil.make_archive(str(root/'qwen3-8b-instruct-pilot-preserved'),'zip',root_dir=root,base_dir=archive.name)
print('Verified',len(lines),'checksummed files. Archive:',zip_path)
