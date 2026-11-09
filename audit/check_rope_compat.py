"""CPU-only configuration compatibility audit; does not load model weights."""
import inspect
import json
from pathlib import Path
from transformers import AutoConfig
from transformers.models.qwen3.modeling_qwen3 import Qwen3RotaryEmbedding
import transformers

config=AutoConfig.from_pretrained('mkd-hossain/Keural-Cortex-8B-v1.0',revision='a592a43fe940299b5a025e5b719459cda97ae1e6',local_files_only=True)
rotary=Qwen3RotaryEmbedding(config,device='cpu')
result={'transformers':transformers.__version__,'serialized_rope_parameters':getattr(config,'rope_parameters',None),
        'loaded_rope_scaling':getattr(config,'rope_scaling',None),'effective_rotary_type':getattr(rotary,'rope_type',None),
        'rotary_source':inspect.getsource(Qwen3RotaryEmbedding.__init__)}
print(json.dumps(result,indent=2))
Path.home().joinpath('cortex-benchmark/rope-compat-audit.json').write_text(json.dumps(result,indent=2))
