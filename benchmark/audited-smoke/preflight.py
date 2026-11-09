import json
from pathlib import Path
from smoke import load_config,SYSTEM,TOOLS
from base_protocol import EXPECTED_MODELS
from transformers import AutoTokenizer
from transformers.models.qwen3.modeling_qwen3 import Qwen3RotaryEmbedding
results=[]
for model,revision in EXPECTED_MODELS.items():
    config,before=load_config(model,revision)
    rotary=Qwen3RotaryEmbedding(config,device='cpu')
    expected='yarn' if model.startswith('mkd-hossain/') else 'default'
    assert config.rope_theta==1000000 and rotary.rope_type==expected
    tokenizer=AutoTokenizer.from_pretrained(model,revision=revision,local_files_only=True)
    result=dict(model=model,revision=revision,theta=config.rope_theta,rotary_type=rotary.rope_type,frequencies=rotary.inv_freq[:8].tolist())
    if expected=='yarn':
        prompt=tokenizer.apply_chat_template([{'role':'system','content':SYSTEM},{'role':'user','content':'Hello'}],tools=TOOLS,tokenize=False,add_generation_prompt=True,enable_thinking=False)
        result['native_prompt_repr']=repr(prompt)
        assert '\n' in prompt
    results.append(result)
Path('preflight.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
