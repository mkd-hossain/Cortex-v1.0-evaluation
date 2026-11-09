import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root=Path(__file__).resolve().parent
old=json.loads((root/'archives/2026-11-09-cortex-v1-vs-qwen3-8b-instruct/qwen3-8b-instruct-results.json').read_text(encoding='utf-8'))
new=json.loads((root/'base-only-completed.json').read_text(encoding='utf-8-sig'))
models=['mkd-hossain/Keural-Cortex-8B-v1.0','Qwen/Qwen3-8B']
def metric(data,model,category):
    job=next(j for j in data['jobs'] if j['model']==model and j.get('suite')=='assistant')
    return next(m for m in job['metrics'] if m['task']==category)
def context(data,model):
    metrics=[j['metrics'][0] for j in data['jobs'] if j['model']==model and j.get('suite')=='long-context' and j['context']<=32768]
    return sum(m['passed'] for m in metrics),sum(m['n'] for m in metrics)

colors=['#087f78','#5575cb','#3ab7a8','#a2b5e8']
labels=['Pilot 1 · Cortex (native)','Pilot 1 · Qwen3-8B Instruct','Pilot 2 · Cortex (plain)','Pilot 2 · Qwen3-8B-Base']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
fig=plt.figure(figsize=(15,10),dpi=180,facecolor='#f7fafc')
gs=fig.add_gridspec(2,3,height_ratios=[1.15,1],left=.065,right=.97,top=.81,bottom=.16,hspace=.42,wspace=.28)
fig.text(.045,.955,'Two completed pilots: category-by-category comparison',fontsize=21,fontweight='bold',color='#14233d')
fig.text(.045,.922,'Pilot 1: native assistant formatting, Cortex vs Qwen Instruct   |   Pilot 2: shared plain transcript, Cortex vs Qwen Base',fontsize=10.5,color='#53667d')
handles=[plt.Rectangle((0,0),1,1,color=c) for c in colors]
fig.legend(handles,labels,ncol=2,loc='upper left',bbox_to_anchor=(.04,.9),frameon=False,fontsize=10)

for col,(category,title) in enumerate([('Chat','Chat constraints'),('Math reasoning','Thinking math'),('Tool calling','Tool calling')]):
    ax=fig.add_subplot(gs[0,col],facecolor='#f7fafc')
    values=[metric(old,models[0],category),metric(old,models[1],category),metric(new,models[0],category),metric(new,'Qwen/Qwen3-8B-Base',category)]
    x=np.array([0,1,2.6,3.6]);scores=[m['value']*100 for m in values]
    ax.bar(x,scores,width=.72,color=colors,zorder=3)
    for pos,score,m in zip(x,scores,values):
        ax.text(pos,score+3,f'{score:.1f}%\n({m["passed"]}/{m["n"]})',ha='center',va='bottom',fontsize=9,color='#263c55')
    ax.set_ylim(0,118);ax.set_yticks([0,25,50,75,100]);ax.set_ylabel('Pass rate (%)' if col==0 else '')
    ax.set_xticks([.5,3.1],['Pilot 1','Pilot 2']);ax.set_title(title,fontweight='bold',loc='left',pad=13,color='#14233d')
    ax.grid(axis='y',color='#dce5ed',zorder=0);ax.spines[['top','right','left']].set_visible(False);ax.spines['bottom'].set_color('#c9d5e0');ax.tick_params(axis='y',length=0)
    ax.axvline(1.8,color='#d9e1eb',linewidth=1)

ax=fig.add_subplot(gs[1,:2],facecolor='#f7fafc')
position=ax.get_position();ax.set_position([.245,position.y0,.40,position.height])
totals=[context(old,models[0]),context(old,models[1]),context(new,models[0]),context(new,'Qwen/Qwen3-8B-Base')]
scores=[p/n*100 for p,n in totals]
ax.barh(np.arange(4),scores,height=.55,color=colors,zorder=3)
for i,(score,(p,n)) in enumerate(zip(scores,totals)):
    ax.text(score+2,i,f'{score:.0f}% ({p}/{n})',va='center',fontsize=10)
ax.set_yticks(range(4),labels);ax.invert_yaxis();ax.set_xlim(0,118);ax.set_xticks([0,25,50,75,100]);ax.set_xlabel('All-constraints pass rate (%)')
ax.set_title('Shared long-context probes: 4K, 16K, 32K',loc='left',fontweight='bold',pad=14,color='#14233d')
ax.grid(axis='x',color='#dce5ed',zorder=0);ax.spines[['top','right','left']].set_visible(False);ax.spines['bottom'].set_color('#c9d5e0');ax.tick_params(axis='y',length=0)
ax.text(0,-.32,'',transform=ax.transAxes)

ax=fig.add_subplot(gs[1,2]);ax.axis('off')
ax.text(0,1,'Standard knowledge tests',fontsize=13,fontweight='bold',color='#14233d',va='top')
ax.text(0,.82,'Cortex vs Qwen Base\nSame outcomes in both pilots',fontsize=11,color='#53667d',va='top',linespacing=1.6)
ax.text(0,.52,'4 Cortex wins\n6 Qwen Base wins\n8 ties',fontsize=13,fontweight='bold',color='#263c55',va='top',linespacing=1.4)
ax.text(0,-.10,'18 subtasks · 10 examples each\nGSM8K excluded: budget audit pending',fontsize=9,color='#53667d',va='bottom',linespacing=1.6)
fig.text(.045,.087,'Observed: Qwen Instruct led in Pilot 1; Qwen Base narrowly led the behavior tests in Pilot 2.',fontsize=12,fontweight='bold',color='#263c55')
fig.text(.045,.06,'These are different comparison conditions, not model improvements. One case separates each behavioral score in Pilot 2.',fontsize=10,color='#53667d')
fig.text(.045,.035,'Small synthetic samples; no overall composite score or statistical winner. Context scores require failure analysis. Cortex-only 64K is excluded here.',fontsize=9,color='#6c5f6b')
out=root/'output';out.mkdir(exist_ok=True)
fig.savefig(out/'two-pilot-comparison.png',facecolor=fig.get_facecolor())
fig.savefig(out/'two-pilot-comparison.svg',facecolor=fig.get_facecolor())
print('Saved two-pilot comparison chart')
