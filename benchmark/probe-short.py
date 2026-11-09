import json
from pathlib import Path
from transformers import AutoTokenizer
from lm_eval.tasks import TaskManager

root = Path(__file__).resolve().parent
metadata = json.loads((root / 'qwen-assistant-metadata.json').read_text())
print('Qwen assistant revision', metadata['sha'])
tok = AutoTokenizer.from_pretrained('mkd-hossain/Keural-Cortex-8B-v1.0', revision='a592a43fe940299b5a025e5b719459cda97ae1e6', local_files_only=True)
prompt = tok.apply_chat_template([{'role':'user','content':'Hello'}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
print('Cortex native prompt:', repr(prompt))
print('Literal backslash-n sequences:', prompt.count('\\n'), 'Actual newline characters:', prompt.count('\n'))
manager = TaskManager()
for name in ('kmmlu','haerae','mmlu','gsm8k'):
    print('Task available',name,name in manager.all_tasks)
print('Setup probe passed')
import inspect
from lm_eval.models.huggingface import HFLM
print(inspect.signature(HFLM.__init__))
print(inspect.getsource(HFLM.apply_chat_template))
for fragment in ('kmmlu_computer','kmmlu_korean','kmmlu_economics','mmlu_computer_security','mmlu_world_religions','mmlu_high_school_geography'):
    print('MATCH',fragment,[t for t in manager.all_tasks if fragment in t])
