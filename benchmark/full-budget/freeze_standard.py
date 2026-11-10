"""Freeze exact local dataset snapshots and seeded stratified selections."""
import hashlib,json,os,time
from pathlib import Path
from lm_eval.tasks import TaskManager
from lm_eval.utils import handle_non_serializable
import numpy as np
ROOT=Path(__file__).parent
SUITES=[('kmmlu',5,'Korean knowledge'),('haerae',5,'Korean knowledge'),('kobest_boolq',0,'Korean understanding'),('kobest_copa',0,'Korean understanding'),('kobest_hellaswag',0,'Korean understanding'),('kobest_sentineg',0,'Korean understanding'),('mmlu',5,'English knowledge/reasoning'),('hellaswag',0,'English knowledge/reasoning'),('arc_challenge',0,'English knowledge/reasoning'),('winogrande',0,'English knowledge/reasoning'),('gsm8k',5,'Math reasoning')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    directory=ROOT/'frozen-standard';directory.mkdir(exist_ok=True)
    manager=TaskManager();manifest={'seed':20261110,'selection':'Seeded random indices per leaf task; fixed before inference; up to 50 per leaf, all if smaller. Budgeted coverage, not every full official split.','suites':{},'datasets':{}}
    for suite,fewshot,category in SUITES:
        print('FREEZING',suite,flush=True)
        loaded=manager.load([suite]);entry={'fewshot':fewshot,'category':category,'tasks':{},'samples':{}}
        for name,task in loaded['tasks'].items():
            path=task.config.dataset_path;config=task.config.dataset_name
            key=json.dumps([path,config]);identity=hashlib.sha256(key.encode()).hexdigest()[:20]
            target=directory/identity
            if key not in manifest['datasets']:
                if not target.exists():task.dataset.save_to_disk(str(target))
                manifest['datasets'][key]={'directory':identity,'fingerprints':{split:ds._fingerprint for split,ds in task.dataset.items()},'rows':{split:len(ds) for split,ds in task.dataset.items()}}
            docs=task.eval_docs;size=len(docs)
            rng=np.random.default_rng(int(hashlib.sha256(name.encode()).hexdigest()[:8],16)^20261110)
            chosen=sorted(rng.choice(size,min(50,size),replace=False).tolist())
            entry['samples'][name]=chosen
            entry['tasks'][name]={'test_rows':size,'selected':len(chosen),'dataset_key':key,'config':task.dump_config()}
        manifest['suites'][suite]=entry
        (directory/'manifest-in-progress.json').write_text(json.dumps(manifest,indent=2,default=handle_non_serializable))
    manifest['files']={p.relative_to(directory).as_posix():sha(p) for p in directory.rglob('*') if p.is_file() and p.suffix in ('.arrow','.json') and not p.name.startswith('manifest')}
    text=json.dumps(manifest,indent=2,default=handle_non_serializable)
    (directory/'manifest.json').write_text(text);(directory/'manifest.sha256').write_text(hashlib.sha256(text.encode()).hexdigest())
    print('FROZEN_STANDARD_READY',sum(sum(len(x) for x in v['samples'].values()) for v in manifest['suites'].values()),flush=True)
if __name__=='__main__':main()
