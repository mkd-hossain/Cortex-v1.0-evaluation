"""Publication-style descriptive snapshot from actual current-run saved metrics."""
import csv,json
from decimal import Decimal,ROUND_HALF_UP
from datetime import datetime
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT.parent/'audit/latest-results.json').read_text(encoding='utf-8'))
OUT=ROOT/'output';OUT.mkdir(exist_ok=True)
COLORS=['#087f78','#526ac4'];TEXT='#182b45';MUTED='#60728a'
MODELS=['mkd-hossain/Keural-Cortex-8B-v1.0','Qwen/Qwen3-8B-Base']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titleweight':'bold','axes.labelcolor':TEXT,'text.color':TEXT,'xtick.color':MUTED,'ytick.color':TEXT,'svg.fonttype':'none'})

def job(model,task):return next(j for j in data['jobs'] if j['model']==model and j['task']==task)
def score(model,task,semantic=False):
    j=job(model,task);metrics=j['metrics']
    if j['status']!='completed':return None
    if j['runner']=='standard-audited':
        assert metrics and all(m['n']==50 for m in metrics)
        return float(np.mean([m['value'] for m in metrics])*100)
    suffix=' (semantic)' if semantic else ' (strict)'
    return next(m['value']*100 for m in metrics if m['task'].endswith(suffix))

def bars(ax,labels,values,title,subtitle):
    y=np.arange(len(labels));height=.31
    for side,color in enumerate(COLORS):
        vals=[v[side] for v in values];offset=(-.18 if side==0 else .18)
        ax.barh(y+offset,vals,height,color=color,zorder=3)
        for yy,value in zip(y+offset,vals):ax.text(value+1.4,yy,str(Decimal(str(value)).quantize(Decimal('0.1'),rounding=ROUND_HALF_UP))+'%',va='center',fontsize=9,fontweight='bold',color=TEXT)
    ax.set_yticks(y,labels);ax.invert_yaxis();ax.set_xlim(0,117)
    ax.set_xticks([0,25,50,75,100]);ax.set_xticklabels(['0','25','50','75','100'])
    ax.grid(axis='x',color='#dde5ed',linewidth=.7,zorder=0)
    ax.spines[['top','right','left']].set_visible(False);ax.spines['bottom'].set_color('#cfdae5');ax.tick_params(axis='y',length=0,pad=9)
    ax.set_title(title,loc='left',fontsize=13,pad=33,color=TEXT)
    ax.text(0,1.025,subtitle,transform=ax.transAxes,fontsize=8.5,color=MUTED,va='bottom')
    ax.set_xlabel('Score (%)',fontsize=9)

standards=[('KMMLU · 45-subject mean','kmmlu'),('HAE-RAE · 5-subtask mean','haerae'),('KoBEST BoolQ','kobest_boolq'),('KoBEST COPA','kobest_copa'),('KoBEST HellaSwag','kobest_hellaswag'),('KoBEST SentiNeg','kobest_sentineg'),('MMLU · 57-subject mean','mmlu'),('HellaSwag','hellaswag'),('ARC-Challenge','arc_challenge'),('WinoGrande','winogrande'),('GSM8K','gsm8k')]
synthetics=[('Four-tool routing · n=480','Four-tool routing'),('Abstention / no-tool · n=240','Abstention and no-tool'),('Simple extraction* · n=240','Tool-result grounding'),('Supplied-history state · n=160','Multi-turn fixture state'),('Instruction constraints · n=160','Instruction constraints')]
fig=plt.figure(figsize=(18,13.5),dpi=180,facecolor='#f7fafc')
gs=fig.add_gridspec(2,2,left=.18,right=.965,top=.81,bottom=.20,height_ratios=[2.0,1],wspace=.82,hspace=.62)
fig.text(.045,.955,'Cortex v1.0 vs Qwen3-8B-Base',fontsize=26,fontweight='bold')
fig.text(.045,.923,'CURRENT EVALUATION SNAPSHOT  |  Standard tasks and synthetic fixtures shown separately',fontsize=12,color=MUTED)
timestamp=datetime.fromtimestamp(data['updated_at']).astimezone().isoformat(timespec='minutes')
remaining=next((j for j in data['jobs'] if j['status']!='completed'),None)
status=f"{data['completed']}/{len(data['jobs'])} jobs completed"
if remaining:status+=f"  |  Cortex-only 64K: {remaining.get('case_progress',{}).get('completed',0)}/40 cases saved; final score pending"
fig.text(.045,.894,status,fontsize=10,color=MUTED)
fig.legend([plt.Rectangle((0,0),1,1,color=c) for c in COLORS],['Cortex v1.0','Qwen3-8B-Base'],loc='upper left',bbox_to_anchor=(.04,.88),ncol=2,frameon=False,fontsize=11)
bars(fig.add_subplot(gs[0,0],facecolor='#f7fafc'),[l for l,t in standards],[[score(m,t) for m in MODELS] for l,t in standards],'A  Standard benchmark samples','Matched raw completion · 50 seeded questions per subtask')
bars(fig.add_subplot(gs[0,1],facecolor='#f7fafc'),[l for l,t in synthetics],[[score(m,t) for m in MODELS] for l,t in synthetics],'B  Synthetic deployment fixtures','Strict pass rate · native Cortex chat vs Base plain transcript')
contexts=['Context 4K','Context 16K','Context 32K']
bars(fig.add_subplot(gs[1,0],facecolor='#f7fafc'),contexts,[[score(m,t) for m in MODELS] for t in contexts],'C  Context: strict output contract','40 cases per model / length · formatting and content required')
bars(fig.add_subplot(gs[1,1],facecolor='#f7fafc'),contexts,[[score(m,t,True) for m in MODELS] for t in contexts],'D  Context: semantic JSON content','Same cases as C · JSON fences accepted; not extra evidence')
notes=[
 '* Simple extraction has answer leakage: allocation repeats the ticket ID; citations are supplied. Exclude it from tool-grounding claims.',
 'Synthetic cases are template-generated, not independent holdout. Supplied-history tests do not measure autonomous tool execution.',
 'Standard scores use task-declared accuracy / normalized accuracy; GSM8K uses exact match. Subject means are unweighted across equal-sized samples.',
 'Descriptive snapshot only: no overall ranking or statistical significance claimed. Samples are not full official test splits. BF16 on NVIDIA DGX Spark.',
 f'Run: {data["run_id"]}  |  Snapshot: {timestamp}  |  Full subject scores are in the companion chart and CSV.'
]
for i,note in enumerate(notes):fig.text(.045,.135-i*.023,note,fontsize=8.7,color=MUTED)
for ext in ('png','svg'):fig.savefig(OUT/f'cortex-current-benchmark.{ext}',facecolor=fig.get_facecolor())
plt.close(fig)

# Every sampled subject is included in the detailed chart; no cherry-picking.
fig=plt.figure(figsize=(23,24),dpi=160,facecolor='#f7fafc');gs=fig.add_gridspec(1,3,left=.15,right=.97,top=.91,bottom=.055,wspace=.52)
fig.text(.035,.966,'All completed standard subtasks',fontsize=26,fontweight='bold');fig.text(.035,.94,'50 seeded questions per subtask / model · shared completion prompts · descriptive scores, no significance claims',fontsize=12,color=MUTED)
fig.legend([plt.Rectangle((0,0),1,1,color=c) for c in COLORS],['Cortex v1.0','Qwen3-8B-Base'],loc='upper right',bbox_to_anchor=(.97,.963),ncol=2,frameon=False)
allrows=[]
for suite in [t for _,t in standards]:
    left=job(MODELS[0],suite);right=job(MODELS[1],suite);lookup={m['task']:m for m in right['metrics']}
    for metric in left['metrics']:
        other=lookup[metric['task']];assert metric['metric']==other['metric']
        label=metric['task'].replace('kmmlu_','').replace('mmlu_','').replace('haerae_','HAE-RAE / ').replace('_',' ')
        allrows.append({'suite':suite,'task':metric['task'],'label':label,'metric':metric['metric'],'n':metric['n'],'cortex':metric['value']*100,'base':other['value']*100})
ko=[r for r in allrows if r['suite']=='kmmlu'];en=[r for r in allrows if r['suite']=='mmlu'];rest=[r for r in allrows if r['suite'] not in ('kmmlu','mmlu')]
for col,(title,items) in enumerate([('KMMLU: all 45 subjects',ko),('MMLU: all 57 subjects',en),('Other standard subtasks',rest)]):
    ax=fig.add_subplot(gs[0,col],facecolor='#f7fafc');bars(ax,[r['label'] for r in items],[[r['cortex'],r['base']] for r in items],title,'Declared task metric · percentages');ax.tick_params(axis='y',labelsize=8)
    for text in list(ax.texts):
        if text.get_text()=='Declared task metric · percentages':text.remove()
    ax.set_title(title,loc='left',fontsize=13,pad=18,color=TEXT)
    for text in ax.texts:text.set_fontsize(7)
fig.text(.035,.022,'Differences across these sampled subjects are not an overall capability ranking. See the overview image for synthetic and context results.',fontsize=11,color=MUTED)
fig.savefig(OUT/'cortex-current-all-subtasks.png',facecolor=fig.get_facecolor());plt.close(fig)
with (OUT/'cortex-current-results.csv').open('w',newline='',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=['suite','task','label','metric','n','cortex','base']);writer.writeheader();writer.writerows(allrows)
summary={}
for label,task in standards:summary[task]={'cortex':score(MODELS[0],task),'base':score(MODELS[1],task)}
(OUT/'cortex-current-summary.json').write_text(json.dumps({'status':status,'snapshot':timestamp,'standard':summary,'limitations':notes},indent=2))
print(json.dumps(summary,indent=2));print('Wrote overview PNG/SVG, all-subtasks PNG and results CSV.')
