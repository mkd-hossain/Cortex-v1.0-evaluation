"""Freeze downloaded model revisions into separate pilot and full run plans."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
models = [json.loads((root / name).read_text()) for name in
          ('cortex-metadata.json', 'qwen-metadata.json')]
tasks = [('kmmlu', 5), ('haerae', 5), ('kobest_boolq', 0), ('kobest_copa', 0),
         ('kobest_hellaswag', 0), ('kobest_sentineg', 0), ('mmlu', 5),
         ('hellaswag', 0), ('arc_challenge', 0), ('winogrande', 0), ('gsm8k', 5)]
for pilot in (True, False):
    jobs = []
    for index, model in enumerate(models):
        for task, fewshot in (tasks[2:3] + tasks[8:9] if pilot else tasks):
            jobs.append(dict(id=f'm{index}-{task}', model=model['id'], revision=model['sha'],
                             task=task, fewshot=fewshot, **({'limit': 20} if pilot else {})))
    (root / ('pilot.json' if pilot else 'plan.json')).write_text(
        json.dumps({'track': 'completion', 'precision': 'bfloat16', 'jobs': jobs}, indent=2))

