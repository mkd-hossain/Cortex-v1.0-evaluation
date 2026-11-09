"""Plot the completed, base-only matched-completion pilot; no new evaluation."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root=Path(__file__).resolve().parent
data=json.loads((root/'completed-dashboard.json').read_text(encoding='utf-8-sig'))
all_rows=data['comparisons']['completion']
rows=[r for r in all_rows if r['task']!='gsm8k']
labels={
 'kmmlu_computer_science':'KMMLU · Computer science','kmmlu_korean_history':'KMMLU · Korean history',
 'kmmlu_economics':'KMMLU · Economics','haerae_general_knowledge':'HAE-RAE · General knowledge',
 'haerae_history':'HAE-RAE · History','haerae_loan_word':'HAE-RAE · Loan words',
 'haerae_rare_word':'HAE-RAE · Rare words','haerae_standard_nomenclature':'HAE-RAE · Standard nomenclature',
 'kobest_boolq':'KoBEST · BoolQ','kobest_copa':'KoBEST · COPA','kobest_hellaswag':'KoBEST · HellaSwag',
 'kobest_sentineg':'KoBEST · SentiNeg','mmlu_computer_security':'MMLU · Computer security',
 'mmlu_world_religions':'MMLU · World religions','mmlu_high_school_geography':'MMLU · High-school geography',
 'hellaswag':'HellaSwag (English)','arc_challenge':'ARC-Challenge','winogrande':'WinoGrande'}
for row in rows:
    assert row['cortex']['n']==row['qwen']['n']==10
    assert row['cortex']['metric']==row['qwen']['metric']
c=np.array([r['cortex']['value']*100 for r in rows]);q=np.array([r['qwen']['value']*100 for r in rows]);y=np.arange(len(rows))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(figsize=(13,12.5),dpi=170)
fig.patch.set_facecolor('#f7fafc');ax.set_facecolor('#f7fafc')
ax.barh(y-.17,c,height=.30,color='#098b80',label='Keural Cortex v1.0',zorder=3)
ax.barh(y+.17,q,height=.30,color='#4268c6',label='Qwen3-8B-Base',zorder=3)
for i,(a,b) in enumerate(zip(c,q)):
    ax.text(a+1,i-.17,f'{a:.0f}%',va='center',fontsize=9,color='#086c63')
    ax.text(b+1,i+.17,f'{b:.0f}%',va='center',fontsize=9,color='#3457a7')
ax.set_yticks(y,[labels.get(r['task'],r['task']) for r in rows]);ax.invert_yaxis()
ax.set_xlim(0,109);ax.set_xticks(range(0,101,20));ax.set_xlabel('Score (%) · accuracy or normalized accuracy, matching the task metric',labelpad=12)
ax.grid(axis='x',color='#dbe3ec',linewidth=.65,zorder=0);ax.tick_params(axis='y',length=0,pad=12)
ax.spines['left'].set_visible(False);ax.spines['bottom'].set_color('#c7d2df')
for boundary in (2.5,7.5,11.5,14.5):ax.axhline(boundary,color='#cfdbe5',linewidth=.7)
ax.legend(loc='lower left',bbox_to_anchor=(-.005,1.015),ncol=2,frameon=False,fontsize=11)
fig.text(.045,.966,'Cortex v1.0 vs Qwen3-8B-Base',fontsize=22,fontweight='bold',color='#14233d')
fig.text(.045,.94,'Completed short pilot · matched completion prompts · BF16 · 10 examples per subtask',fontsize=11,color='#596b80')
fig.text(.045,.057,f'Subtask outcomes (excluding GSM8K): Cortex {int(sum(c>q))} wins  |  Qwen Base {int(sum(q>c))} wins  |  {int(sum(c==q))} ties',fontsize=11,fontweight='bold',color='#263e56')
fig.text(.045,.035,'GSM8K omitted from chart: generation-budget override requires review. Small samples do not establish an overall winner.',fontsize=9,color='#6b5961')
fig.text(.045,.019,'Only the requested base-model comparison is shown; Qwen assistant results are excluded. No new tests were run.',fontsize=9,color='#596b80')
fig.subplots_adjust(left=.335,right=.955,top=.88,bottom=.115)
out=root/'output';out.mkdir(exist_ok=True)
fig.savefig(out/'cortex-vs-qwen-base-pilot.png',facecolor=fig.get_facecolor())
fig.savefig(out/'cortex-vs-qwen-base-pilot.svg',facecolor=fig.get_facecolor())
print('Chart created:',len(rows),'paired subtasks')
