"""Readable, one-panel model-card figures, designed for ~750 px rendered width."""
import json
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parent.parent
DATA=json.loads((ROOT/'results/dashboard-data.json').read_text(encoding='utf-8'))
assert DATA['status']=='completed' and DATA['completed']==39
OUT=ROOT/'assets/model-card';OUT.mkdir(parents=True,exist_ok=True)
MODELS=['mkd-hossain/Keural-Cortex-8B-v1.0','Qwen/Qwen3-8B-Base']
COLORS=['#087f78','#526ac4'];INK='#182b45';MUTED='#55667c'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':14,'svg.fonttype':'none'})
def pct(value,places=1):
    return str(Decimal(str(round(value,10))).quantize(Decimal('0.'+'0'*(places-1)+'1'),rounding=ROUND_HALF_UP))
def metric(model,task,kind=None):
    job=next(j for j in DATA['jobs'] if j['model']==model and j['task']==task)
    assert job['status']=='completed'
    if kind:return next(m['value']*100 for m in job['metrics'] if m['task'].endswith(' ('+kind+')'))
    return np.mean([m['value'] for m in job['metrics']])*100
def draw(filename,title,subtitle,labels,values,caption):
    height=2.9+len(labels)*.7
    fig=plt.figure(figsize=(10,height),dpi=180,facecolor='#f7fafc')
    ax=fig.add_axes([.30,1.2/height,.65,(height-3.2)/height],facecolor='#f7fafc')
    fig.text(.045,1-.40/height,title,fontsize=23,fontweight='bold',color=INK)
    fig.text(.045,1-.79/height,subtitle,fontsize=13,color=MUTED)
    fig.legend([plt.Rectangle((0,0),1,1,color=c) for c in COLORS],['Cortex v1.0','Qwen3-8B-Base'],loc='upper left',bbox_to_anchor=(.035,1-1.01/height),ncol=2,frameon=False,fontsize=14,handlelength=1.6)
    y=np.arange(len(labels))
    for side,color in enumerate(COLORS):
        offset=-.18 if side==0 else .18
        for i,row in enumerate(values):
            value=row[side]
            if value is None:
                ax.text(2,i+offset,'Not evaluated',va='center',fontsize=13,color=MUTED)
                continue
            assert 0<=value<=100
            ax.barh(i+offset,value,.30,color=color,zorder=3)
            ax.text(value+1.6,i+offset,pct(value)+'%',va='center',fontsize=14,color=INK,fontweight='bold')
    ax.set_yticks(y,labels,fontsize=14,color=INK);ax.set_ylim(len(labels)-.4,-.6);ax.set_xlim(0,117)
    ax.set_xticks([0,25,50,75,100]);ax.tick_params(axis='x',labelsize=12,colors=MUTED);ax.tick_params(axis='y',length=0,pad=12)
    ax.grid(axis='x',color='#dce5ed',linewidth=.8,zorder=0)
    ax.spines[['top','right','left']].set_visible(False);ax.spines['bottom'].set_color('#cbd7e2')
    ax.set_xlabel('Score (%)',fontsize=13,labelpad=9,color=MUTED)
    fig.text(.045,.29/height,caption,fontsize=12,color=MUTED,va='bottom')
    for ext in ('png','svg'):fig.savefig(OUT/(filename+'.'+ext),facecolor=fig.get_facecolor())
    qa=ROOT/'dashboard-qa';qa.mkdir(exist_ok=True)
    fig.savefig(qa/('model-card-'+filename+'.png'),dpi=75,facecolor=fig.get_facecolor())
    plt.close(fig)
    return {'file':filename+'.png','title':title,'labels':labels,'values':values,'caption':caption,'rendered_width_target':750,'label_font_pt':14}

figures=[]
tasks=['kmmlu','haerae','kobest_boolq','kobest_copa','kobest_hellaswag','kobest_sentineg']
figures.append(draw('korean-benchmarks','Korean benchmark samples','Matched completion · 50 seeded questions per subtask',['KMMLU\n45-subject mean','HAE-RAE\n5-subtask mean','KoBEST BoolQ','KoBEST COPA','KoBEST HellaSwag','KoBEST SentiNeg'],[[metric(m,t) for m in MODELS] for t in tasks],'Sampled scores, not full test splits. Subject means use equal-sized samples.'))
tasks=['mmlu','hellaswag','arc_challenge','winogrande','gsm8k']
figures.append(draw('english-math-benchmarks','English and math samples','Matched completion · task-declared metrics',['MMLU\n57-subject mean','HellaSwag','ARC-Challenge','WinoGrande','GSM8K'],[[metric(m,t) for m in MODELS] for t in tasks],'50 questions per subtask. GSM8K: exact match, greedy decoding, 512-token cap.'))
tasks=['Four-tool routing','Abstention and no-tool','Multi-turn fixture state','Instruction constraints']
figures.append(draw('application-diagnostics','Application diagnostics','Synthetic fixtures · different deployment serialization',['Four-tool routing\n480 cases','Abstention / no-tool\n240 cases','Supplied-history state\n160 cases','Exact-output constraints\n160 cases'],[[metric(m,t,'strict') for m in MODELS] for t in tasks],'Native Cortex chat vs Base plain transcript. Leaky extraction test excluded.'))
tasks=['Context 4K','Context 16K','Context 32K','Context 64K']
for kind,title,caption in [('strict','Context: strict output contract','Correct content and requested format required. 64K is Cortex-only.'),('semantic','Context: semantic JSON content','Same cases as strict scoring; JSON fences accepted. 64K is unpaired.')]:
    values=[[metric(MODELS[0],t,kind),None if t=='Context 64K' else metric(MODELS[1],t,kind)] for t in tasks]
    figures.append(draw('context-'+kind,title,'40 synthetic cases per model and input budget',['4K','16K','32K','64K\nCortex only'],values,caption))
(OUT/'figure-data.json').write_text(json.dumps({'run_id':DATA['run_id'],'completed_jobs':39,'figures':figures},indent=2))
print('Created five readable PNG/SVG figure pairs and exact figure-data.json.')
