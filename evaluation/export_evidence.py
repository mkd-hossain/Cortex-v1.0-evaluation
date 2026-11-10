"""Snapshot code/provenance and available run evidence; omit weights and datasets."""
import zipfile
from pathlib import Path
root=Path(__file__).parent;run=root.parent/'runs-full-budget-v1'
target=root/'publication-snapshot.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
    for name in ('plan.json','code-manifest.json','environment-provenance.json','requirements-recorded.txt','calibration-summary.json','dataset-source-references.json'):
        if (root/name).exists():archive.write(root/name,'benchmark/full-budget/'+name)
    if (root/'frozen-standard/manifest.json').exists():archive.write(root/'frozen-standard/manifest.json','benchmark/full-budget/frozen-standard-manifest.json')
    for directory in ('calibration-v2','harness-preflight','math-preflight-v2','math-preflight-v3'):
        for file in (root/directory).rglob('*'):
            if file.is_file() and file.suffix in ('.json','.jsonl','.txt','.log'):
                archive.write(file,'benchmark/full-budget/'+file.relative_to(root).as_posix())
    for file in run.rglob('*'):
        if file.is_file() and file.suffix in ('.json','.jsonl','.txt','.log'):
            archive.write(file,'audit/full-budget-run/'+file.relative_to(run).as_posix())
print(target,flush=True)
