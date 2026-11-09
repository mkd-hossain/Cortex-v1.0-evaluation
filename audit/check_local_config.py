import importlib.util
import json
from pathlib import Path
for name in ('transformers','torch'):
    print(name, bool(importlib.util.find_spec(name)))
try:
    from transformers import AutoConfig
    import transformers
    config=AutoConfig.from_pretrained(str(Path(__file__).parent/'evidence/hf-v1'),local_files_only=True)
    result={'runtime_version':transformers.__version__,'rope_theta':getattr(config,'rope_theta',None),
            'rope_scaling':getattr(config,'rope_scaling',None),'rope_parameters':getattr(config,'rope_parameters',None)}
    print(json.dumps(result,indent=2))
    (Path(__file__).parent/'evidence/local-config-check.json').write_text(json.dumps(result,indent=2))
except ImportError:
    print('No local Transformers runtime; use the isolated audit environment.')
