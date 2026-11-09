"""Create a bounded seven-category evaluation; never overwrite pilot state."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
cortex = json.loads((root/'cortex-metadata.json').read_text())
base = json.loads((root/'qwen-metadata.json').read_text())
assistant = json.loads((root/'qwen-assistant-metadata.json').read_text())
suites = [
    ('KMMLU (3 domains)','kmmlu_computer_science,kmmlu_korean_history,kmmlu_economics','Korean knowledge',5),
    ('HAE-RAE','haerae','Korean knowledge',5),
    ('KoBEST BoolQ','kobest_boolq','Korean understanding',0),
    ('KoBEST COPA','kobest_copa','Korean understanding',0),
    ('KoBEST HellaSwag','kobest_hellaswag','Korean understanding',0),
    ('KoBEST SentiNeg','kobest_sentineg','Korean understanding',0),
    ('MMLU (3 domains)','mmlu_computer_security,mmlu_world_religions,mmlu_high_school_geography','English knowledge/reasoning',5),
    ('HellaSwag','hellaswag','English knowledge/reasoning',0),
    ('ARC-Challenge','arc_challenge','English knowledge/reasoning',0),
    ('WinoGrande','winogrande','English knowledge/reasoning',0),
    ('GSM8K','gsm8k','Math reasoning',5),
]
jobs = []


def diagnostic(model, tag, suite='assistant', context=4096):
    return {'id':f'{tag}-{suite}-{context}', 'model':model['id'],'revision':model['sha'],
            'task':'Chat + tools + thinking math' if suite=='assistant' else f'Long context {context//1024}K',
            'category':'Chat / Tool calling / Math reasoning' if suite=='assistant' else 'Long context',
            'track':'Native chat; mocked tools' if suite=='assistant' else ('Cortex-only extension' if context==65536 else 'Native chat; matched context budget'),
            'runner':'diagnostics','suite':suite,'context':context}


jobs.append(diagnostic(cortex,'cortex'))
for model, tag, chat in [(cortex,'cortex-completion',False),(base,'base-completion',False),
                         (cortex,'cortex-chat',True),(assistant,'qwen-chat',True)]:
    for index,(label,tasks,category,fewshot) in enumerate(suites):
        jobs.append({'id':f'{tag}-{index:02}', 'model':model['id'],'revision':model['sha'],
                     'task':label,'tasks':tasks,'category':category,'fewshot':fewshot,'limit':10,
                     'batch_size':4 if tasks=='gsm8k' else 8,'generation':tasks=='gsm8k',
                     'chat':chat,'track':'Native chat; thinking off' if chat else 'Matched raw completion'})
jobs.append(diagnostic(assistant,'qwen'))
for context in (4096,16384,32768):
    jobs.extend([diagnostic(cortex,'cortex','long-context',context),diagnostic(assistant,'qwen','long-context',context)])
jobs.append(diagnostic(cortex,'cortex','long-context',65536))
plan = {'title':'Seven-category short evaluation',
        'note':'Short exploratory evaluation, not a full benchmark. Standard tests: first 10 test examples per subtask; KMMLU/MMLU sample 3 domains. Chat/tools use new synthetic constraint-based diagnostics. 64K is Cortex-only. No training-overlap audit established.',
        'categories':['Korean knowledge','Korean understanding','English knowledge/reasoning','Math reasoning','Long context','Chat','Tool calling'],
        'jobs':jobs}
(root/'short-all.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
print(f'Prepared {len(jobs)} jobs across seven categories')
