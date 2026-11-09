"""Prepare, validate, and freeze a base-only pilot. Never launch evaluation."""
import hashlib
import json
from pathlib import Path

from base_protocol import validate_plan

root=Path(__file__).resolve().parent
out=root/'prepared-base-only';out.mkdir(exist_ok=True)
old=json.loads((root/'short-all.json').read_text(encoding='utf-8'))
jobs=[]
for model,tag in [('mkd-hossain/Keural-Cortex-8B-v1.0','cortex'),('Qwen/Qwen3-8B-Base','qwen-base')]:
    template=next(j for j in old['jobs'] if j['model']==model)
    for job in old['jobs']:
        if job['model']==model and job.get('runner')!='diagnostics' and not job.get('chat'):
            copy=dict(job)
            copy.update(id=tag+'-completion-'+job['id'].rsplit('-',1)[-1],chat=False,
                        batch_size=8 if job.get('generation') else 'auto',max_batch_size=32,
                        track='Identical completion prompts; Base-only comparison')
            jobs.append(copy)
    jobs.append(dict(id=tag+'-capabilities',model=model,revision=template['revision'],task='Chat / tools / reasoning',
                     category='Chat / Tool calling / Math reasoning',runner='diagnostics',suite='assistant',
                     track='Identical plain transcript; no native chat template',context=4096,chat=False))
    for context in (4096,16384,32768):
        jobs.append(dict(id=f'{tag}-context-{context}',model=model,revision=template['revision'],task=f'Long context {context//1024}K',
                         category='Long context',runner='diagnostics',suite='long-context',context=context,chat=False,
                         track='Identical documents and plain transcript'))
jobs.append(dict(id='cortex-context-65536',model='mkd-hossain/Keural-Cortex-8B-v1.0',
                 revision='a592a43fe940299b5a025e5b719459cda97ae1e6',task='Long context 64K',
                 category='Long context',runner='diagnostics',suite='long-context',context=65536,chat=False,
                 track='Cortex-only extension; no matched Base score'))
plan={'title':'Keural Cortex v1 vs Qwen3-8B-Base - seven-category pilot',
      'comparison_mode':'single-table','comparator':'Qwen/Qwen3-8B-Base','status':'prepared-not-started',
      'note':'Only Cortex v1 and Qwen3-8B-Base. All seven categories in one table. Standard completion prompts and custom plain-transcript prompts are identical across models; no Instruct weights or native assistant template. 64K is labeled Cortex-only. First 10 examples per sampled standard subtask; small synthetic custom tests. No overall winner or contamination clearance implied.',
      'categories':old['categories'],'jobs':jobs}
validate_plan(plan)
assert len(jobs)==31
(out/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')


def replace_once(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new,1)


controller=(root/'controller.py').read_text(encoding='utf-8')
controller=replace_once(controller,'ROOT = Path(__file__).resolve().parent','ROOT = Path(__file__).resolve().parent\nfrom base_protocol import validate_plan, EXPECTED_MODELS')
controller=replace_once(controller,'def build_command(job, out):','def build_command(job, out):\n    if EXPECTED_MODELS.get(job["model"]) != job["revision"]:\n        raise ValueError("Rejected non-Base comparator or unpinned checkpoint")')
controller=replace_once(controller,"'max_gen_toks=512,do_sample=False'","'max_gen_toks=512,max_new_tokens=512,do_sample=False'")
controller=replace_once(controller,"    if job.get('limit'):\n","    if job.get('max_batch_size'):\n        command += ['--max_batch_size',str(job['max_batch_size'])]\n    if job.get('limit'):\n")
controller=replace_once(controller,"    plan = json.loads(Path(args.plan).read_text())","    plan = json.loads(Path(args.plan).read_text())\n    validate_plan(plan)")
(out/'controller.py').write_text(controller,encoding='utf-8')

runner=(root/'run_diagnostics.py').read_text(encoding='utf-8')
runner=replace_once(runner,"from diagnostic_cases import chat_cases, math_cases, tool_cases, grade_text, grade_tool, parse_calls, TOOLS", "from diagnostic_cases import chat_cases, math_cases, tool_cases, grade_text, grade_tool, parse_calls, TOOLS\nfrom base_protocol import render_shared_prompt, EXPECTED_MODELS")
runner=replace_once(runner,"    if not tokenizer.chat_template:\n        raise RuntimeError('Assistant diagnostics require a native chat template.')", "    if EXPECTED_MODELS.get(args.model) != args.revision:\n        raise RuntimeError('Only the pinned Cortex and Qwen3-8B-Base checkpoints may run.')")
runner=replace_once(runner,"'template_sha256':hashlib.sha256(tokenizer.chat_template.encode()).hexdigest(),", "'prompt_format':'shared-plain-transcript-v1',\n                'renderer_sha256':hashlib.sha256((Path(__file__).parent/'base_protocol.py').read_bytes()).hexdigest(),\n                'scorer_sha256':hashlib.sha256((Path(__file__).parent/'diagnostic_cases.py').read_bytes()).hexdigest(),")
runner=replace_once(runner,"    def generate(messages, thinking=False, tools=False, seed=20261109, budget=256):\n        prompt = tokenizer.apply_chat_template(messages, tools=TOOLS if tools else None,\n                    tokenize=False, add_generation_prompt=True, enable_thinking=thinking)","    def generate(messages, thinking=False, tools=False, seed=20261109, budget=256):\n        prompt = render_shared_prompt(messages, TOOLS if tools else None)")
runner=replace_once(runner,"        started = time.time()", "        settings.update(stop_strings=['\\n\\nUSER:', '\\n\\nSYSTEM:', '\\n\\nTOOL:'],tokenizer=tokenizer)\n        started = time.time()")
runner=replace_once(runner,"        raw = tokenizer.decode(new_tokens, skip_special_tokens=True)","        raw = tokenizer.decode(new_tokens, skip_special_tokens=True)\n        for marker in ('\\n\\nUSER:', '\\n\\nSYSTEM:', '\\n\\nTOOL:'):\n            raw = raw.split(marker,1)[0].strip()")
runner=runner.replace('BF16 native-template diagnostics','BF16 shared-transcript Base-only diagnostics').replace('native chat template.','identical plain transcript.')
runner=replace_once(runner,'    args = parser.parse_args()','    args = parser.parse_args()\n    if EXPECTED_MODELS.get(args.model) != args.revision:\n        raise RuntimeError("Rejected unapproved checkpoint before loading tokenizer or weights")')
(out/'run_diagnostics.py').write_text(runner,encoding='utf-8')
for name in ('base_protocol.py','diagnostic_cases.py'):
    (out/name).write_bytes((root/name).read_bytes())

# Stage the single-table dashboard without changing the active completed dashboard.
adapter=(root/'dashboard_data.py').read_text(encoding='utf-8')
adapter=replace_once(adapter,"RUN = ROOT / os.environ.get('BENCHMARK_RUN', 'runs-short-all-v1')","RUN = ROOT.parent / os.environ.get('BENCHMARK_RUN', 'runs-base-only-v1')")
adapter=replace_once(adapter,"            if caps:","            if caps and any(cap != '512' for cap in caps):")
start=adapter.index('def comparison_rows(data, track):')
adapter=adapter[:start]+'''def comparison_rows(data, track):
    rows={}
    for job in data['jobs']:
        side='cortex' if job['model']=='mkd-hossain/Keural-Cortex-8B-v1.0' else 'qwen'
        if job['model'] not in ('mkd-hossain/Keural-Cortex-8B-v1.0','Qwen/Qwen3-8B-Base'):
            raise ValueError('Rejected non-Base comparator from new-run results')
        for metric in job['metrics'] or [{'task':job['task'],'metric':'','value':None,'n':None}]:
            key=(job['task'],metric['task'])
            row=rows.setdefault(key,{'benchmark':job['task'],'task':metric['task'],'category':job['category'],'extension':job.get('context')==65536})
            row[side]={'status':job['status'],'warnings':job['warnings'],**metric}
    for key,row in list(rows.items()):
        if row['task']==row['benchmark'] and any(k[0]==key[0] and k!=key for k in rows):rows.pop(key)
    for row in rows.values():
        for side,model in [('cortex','mkd-hossain/Keural-Cortex-8B-v1.0'),('qwen','Qwen/Qwen3-8B-Base')]:
            if side not in row:
                match=next((j for j in data['jobs'] if j['model']==model and j['task']==row['benchmark']),None)
                row[side]={'status':match['status'] if match else 'not-applicable','value':None,'n':None,'metric':''}
    return list(rows.values())
'''
(out/'dashboard_data.py').write_text(adapter,encoding='utf-8')
html=(root/'dashboard.html').read_text(encoding='utf-8')
start=html.index('<div class="track-panel glass">');end=html.index('<div class="model-pair">',start)
html=html[:start]+'<div class="track-panel glass"><div><h2>All seven categories · Base-only comparison</h2><p id="track-description">Same questions, scoring and prompt format on both models.</p></div></div>\n'+html[end:]
start=html.index('<section class="glass assistant-summary">');end=html.index('<section class="glass coverage">',start)
html=html[:start]+'</section>\n'+html[end:]
html=html.replace('Native assistant','Common-format behavior').replace('Cortex vs Qwen3-8B. Each uses its own chat template. Thinking is off for standard and operational tasks; enabled for the separate six-case math diagnostic.','Only Cortex v1 and Qwen3-8B-Base. Custom behavior probes use an identical plain transcript, tool instructions, output budget and scoring. No Instruct checkpoint is used.')
html=html.replace('64K is a Cortex-only extension. Shared context budgets are tested with the same source documents. Actual input lengths reserve output space; these are synthetic probes, not RULER or LongBench scores.','Standard tasks use matching completion prompts. Chat, tools and context use the same plain transcript on both models. Actual input lengths reserve output space. 64K is a Cortex-only extension, not a paired win. Synthetic probes are not standardized capability certifications.')
(out/'dashboard.html').write_text(html,encoding='utf-8')
js=(root/'dashboard.js').read_text(encoding='utf-8')
js=js.replace('renderComparison(data);renderAssistant(data);','renderComparison(data);')
js=js.replace("$('context-note').hidden=state.track!=='context';","$('context-note').hidden=false;")
js=js.replace("$('assistant-link').addEventListener('click',()=>{selectTrack('assistant');$('results').scrollIntoView({behavior:'smooth'})});",'')
js=js.replace("Identical completion prompts and scoring · first 10 test examples per subtask","One table: standard completion tasks and shared-format behavioral/context probes")
(out/'dashboard.js').write_text(js,encoding='utf-8')
for name in ('dashboard.css','dashboard_web.py','public_server.py'):
    (out/name).write_bytes((root/name).read_bytes())
report=(root/'dashboard_report.py').read_text(encoding='utf-8')
report=replace_once(report,"for track,title,comparator in [('completion','Matched completion','Qwen3-8B-Base'),('assistant','Native assistant','Qwen3-8B'),('context','Long context','Qwen3-8B')]:","for track,title,comparator in [('completion','All seven categories','Qwen3-8B-Base')]:")
report=report.replace('Raw-completion results and native-assistant results are separate comparison tracks.','Only Qwen3-8B-Base and Cortex v1 are compared. All categories are in one table; brief prompt-format notes distinguish knowledge tasks from behavior probes.')
report=report.replace('Native assistant compares Cortex to Qwen3-8B using their respective chat templates, with thinking disabled for standard and operational cases.','Custom behavior probes compare Cortex to Qwen3-8B-Base using an identical plain transcript and tool instructions, with matched generation budgets and sampling.')
report=report.replace('for both assistants','for both checkpoints')
(out/'dashboard_report.py').write_text(report,encoding='utf-8')
service='''[Unit]
Description=PREPARED Cortex v1 versus Qwen3-8B-Base pilot
After=network-online.target

[Service]
WorkingDirectory=%h/cortex-benchmark/prepared-base-only
ExecStart=%h/cortex-benchmark/.venv/bin/python -u controller.py --plan plan.json --data %h/cortex-benchmark/runs-base-only-v1 --ready-file %h/cortex-benchmark/provenance/ready
Environment=PYTHONUNBUFFERED=1
Environment=TOKENIZERS_PARALLELISM=false
Environment=HF_DATASETS_TRUST_REMOTE_CODE=1
Environment=OMP_NUM_THREADS=8
Restart=on-failure
KillMode=control-group
TimeoutStopSec=30

[Install]
WantedBy=default.target
'''
(out/'PREPARED-NOT-INSTALLED.service').write_text(service,encoding='utf-8')
(out/'README.md').write_text('''# Cortex v1 versus Qwen3-8B-Base - prepared, not started

Only these pinned model IDs are allowed; the runner rejects every other checkpoint:
- mkd-hossain/Keural-Cortex-8B-v1.0
- Qwen/Qwen3-8B-Base

31 jobs cover all seven categories. All results will appear in one comparison table
with Cortex, Qwen3-8B-Base, difference, sample count and a short protocol note.
No new model download is required. No Qwen Instruct checkpoint is referenced.

Standard tasks use identical completion prompts and a corrected explicit 512-token
generation cap on both models. Custom chat/tools/reasoning and long-context probes
use the same plain role transcript and tool instructions on both models. This avoids
requiring a chat template that the Base checkpoint may not have. It measures behavior
under this common format; it does not claim to measure Cortex at its optimal native
serving configuration. Thinking-math sampling and output budgets remain matched.

The 64K Cortex result is included in the same table, clearly marked as an unmatched
extension, rather than counted as a win over the Base model's 32K configuration.

Resource policy: adaptive standard-task batches, maximum 32; generation batches 8.
Custom diagnostics remain single-stream; long-context jobs run alone to avoid memory
exhaustion. Runtime tuning may be adjusted only without changing questions or scores.
More allocated memory alone is not a speed optimization.

This service file is staged only. It is not installed, enabled or started. Activating
the new run and single-table dashboard requires the user's next instruction. Original
completed artifacts and dashboard remain available throughout preparation.
''',encoding='utf-8')
hashes=[hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt']
(out/'SHA256SUMS.txt').write_text('\n'.join(hashes)+'\n',encoding='utf-8')
print('PREPARED_NOT_STARTED',len(jobs),'jobs;',sorted({j['model'] for j in jobs}))
