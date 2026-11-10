"""Freeze a conservative sample count before scored inference; no scores consulted."""
import hashlib,json
from pathlib import Path
import numpy as np
p=Path(__file__).parent/'frozen-standard/manifest.json';manifest=json.loads(p.read_text())
manifest['selection']='Seeded random indices per leaf task; fixed before inference; up to 50 per leaf, all if smaller. Conservative 15-hour budget sizing; no model scores consulted.'
for suite in manifest['suites'].values():
    for name,meta in suite['tasks'].items():
        rng=np.random.default_rng(int(hashlib.sha256(name.encode()).hexdigest()[:8],16)^20261110)
        selected=sorted(rng.choice(meta['test_rows'],min(50,meta['test_rows']),replace=False).tolist())
        suite['samples'][name]=selected;meta['selected']=len(selected)
text=json.dumps(manifest,indent=2);p.write_text(text);p.with_name('manifest.sha256').write_text(hashlib.sha256(text.encode()).hexdigest())
print('FINAL_STANDARD_SAMPLES_PER_MODEL',sum(sum(len(v) for v in s['samples'].values()) for s in manifest['suites'].values()),flush=True)
