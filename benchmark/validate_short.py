import json
from pathlib import Path
from transformers import AutoTokenizer
from lm_eval.tasks import TaskManager
from diagnostic_cases import chat_cases, math_cases, tool_cases, TOOLS
from run_diagnostics import long_cases

root=Path(__file__).resolve().parent
plan=json.loads((root/'short-all.json').read_text())
assert len(plan['jobs'])==len({j['id'] for j in plan['jobs']})
manager=TaskManager()
for job in plan['jobs']:
    if job.get('runner')!='diagnostics':
        for task in job['tasks'].split(','):
            assert task in manager.all_tasks,task
tok=AutoTokenizer.from_pretrained('mkd-hossain/Keural-Cortex-8B-v1.0',revision='a592a43fe940299b5a025e5b719459cda97ae1e6',local_files_only=True)
for case in chat_cases()+math_cases()+tool_cases():
    tok.apply_chat_template(case['messages'],tools=TOOLS if 'tool_rule' in case else None,tokenize=False,
                            add_generation_prompt=True,enable_thinking=case.get('thinking',False))
for budget in (4096,16384,32768,65536):
    for case in long_cases(tok,budget):
        tokens=tok.apply_chat_template(case['messages'],tokenize=True,add_generation_prompt=True,enable_thinking=False)
        assert len(tokens)+256<=budget,(budget,len(tokens))
        print('Context preflight',budget,'input',len(tokens),'output allowance',256)
print('SHORT_RUN_PREFLIGHT_PASSED',len(plan['jobs']),'jobs')
