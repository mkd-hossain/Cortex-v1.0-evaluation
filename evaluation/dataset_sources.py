"""Extract source references from the frozen datasets' own recorded metadata."""
import json,re
from pathlib import Path
root=Path(__file__).parent/'frozen-standard';records={}
for path in root.rglob('dataset_info.json'):
    info=json.loads(path.read_text());urls=list(info.get('download_checksums',{}))
    records[path.relative_to(root).as_posix()]={'dataset_name':info.get('dataset_name'),'config_name':info.get('config_name'),'version':info.get('version'),'source_urls':urls,'immutable_revision_candidates':sorted(set(re.findall(r'(?:@|/resolve/)([a-f0-9]{40})(?:/|$)','\n'.join(urls)))),'license':info.get('license'),'note':'These are metadata recorded with the downloaded dataset; fingerprints and saved-byte hashes remain in manifest.json.'}
Path(__file__).with_name('dataset-source-references.json').write_text(json.dumps(records,indent=2));print('DATASET_SOURCE_REFERENCES',len(records),flush=True)
