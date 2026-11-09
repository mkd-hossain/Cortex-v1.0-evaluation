"""Generate an academic-style completion report from saved evaluation artifacts."""
from datetime import datetime
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from dashboard_data import comparison_rows


def build_report(data,path,allow_partial=False):
    if not data['report_ready'] and not allow_partial:
        raise ValueError('Completion report requires every evaluation job to finish.')
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether

    navy=colors.HexColor('#14233d');teal=colors.HexColor('#087d78');muted=colors.HexColor('#62748a')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ReportTitle',fontName='Helvetica-Bold',fontSize=25,leading=30,textColor=navy,spaceAfter=10))
    styles.add(ParagraphStyle(name='SectionTitle',fontName='Helvetica-Bold',fontSize=14,leading=18,textColor=navy,spaceBefore=16,spaceAfter=9,keepWithNext=True))
    styles.add(ParagraphStyle(name='ReportBody',fontName='Helvetica',fontSize=9,leading=13,textColor=navy,spaceAfter=9))
    styles.add(ParagraphStyle(name='ReportSmall',fontName='Helvetica',fontSize=7.5,leading=10.5,textColor=muted,spaceAfter=5))
    styles.add(ParagraphStyle(name='Cell',fontName='Helvetica',fontSize=7.4,leading=10,textColor=navy,splitLongWords=True))
    styles.add(ParagraphStyle(name='CellHead',fontName='Helvetica-Bold',fontSize=7.4,leading=10,textColor=navy))
    output=BytesIO()
    doc=SimpleDocTemplate(output,pagesize=A4,rightMargin=17*mm,leftMargin=17*mm,topMargin=22*mm,bottomMargin=20*mm,
        title='Benchmark Evaluation Lab - Cortex comparative evaluation',author='Benchmark Evaluation Lab')
    story=[]
    def p(text,style='ReportBody'):
        return Paragraph(escape(str(text)).replace('\n','<br/>'),styles[style])
    def table(rows,widths,header=True):
        cells=[[p(value,'CellHead' if i==0 and header else 'Cell') for value in row] for i,row in enumerate(rows)]
        t=Table(cells,colWidths=widths,repeatRows=1 if header else 0,hAlign='LEFT')
        t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),4),
            ('BOTTOMPADDING',(0,0),(-1,-1),4),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf2f5')),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#c4d9df')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8fafc')]),
            ('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#e0e7ed'))]))
        return t
    def score(entry):
        if isinstance(entry.get('value'),(int,float)):
            value=f"{entry['value']*100:.1f}%"
            return value+(f"\nn={entry['n']}" if entry.get('n') else '')
        return 'Not in matched test' if entry.get('status')=='not-applicable' else str(entry.get('status','pending')).capitalize()
    def name(value):
        return str(value).replace('haerae_','HAE-RAE / ').replace('kmmlu_','KMMLU / ').replace('mmlu_','MMLU / ').replace('_',' ')
    def footer(canvas,document):
        canvas.saveState();width,height=A4
        canvas.setStrokeColor(colors.HexColor('#d9e4ec'));canvas.line(17*mm,height-15*mm,width-17*mm,height-15*mm)
        canvas.setFont('Helvetica-Bold',8);canvas.setFillColor(teal);canvas.drawString(17*mm,height-12*mm,'BENCHMARK EVALUATION LAB')
        canvas.setFont('Helvetica',7);canvas.setFillColor(muted)
        canvas.drawString(17*mm,12*mm,'Exploratory short evaluation | No overall capability claim')
        canvas.drawRightString(width-17*mm,12*mm,f'Page {document.page}')
        canvas.restoreState()

    story.append(Spacer(1,12*mm))
    story.append(p('Cortex v1.0\nComparative evaluation','ReportTitle'))
    story.append(p('Seven-category short evaluation - NVIDIA DGX Spark - BF16','ReportBody'))
    if allow_partial:
        story.append(p('LAYOUT VALIDATION - PARTIAL SNAPSHOT. This is not a completed benchmark report.','SectionTitle'))
    else:
        story.append(p('Completion report','SectionTitle'))
    starts=[j['started'] for j in data['jobs'] if j.get('started')]
    ends=[j['ended'] for j in data['jobs'] if j.get('ended')]
    duration=f"{(max(ends)-min(starts))/3600:.2f} hours" if starts and ends else 'Not available'
    generated=datetime.now().astimezone().isoformat(timespec='seconds')
    story.append(table([['Run','Completed jobs','Observed wall time'],[data['run_id'],f"{data['completed']} / {len(data['jobs'])}",duration]],[79*mm,43*mm,54*mm]))
    story.append(Spacer(1,6*mm))
    story.append(p('Interpretation','SectionTitle'))
    story.append(p('These are small exploratory samples, not a full benchmark. No overall winner, statistical significance, production readiness or training-data independence is established. Only Qwen3-8B-Base and Cortex v1 are compared. All categories are in one table; brief prompt-format notes distinguish knowledge tasks from behavior probes.'))
    story.append(p(data['note']))
    story.append(p('Generated: '+generated,'ReportSmall'))
    if data['warnings']:
        story.append(p('Audit notes requiring review','SectionTitle'))
        for warning in data['warnings']:
            story.append(p(warning,'ReportSmall'))

    story.append(PageBreak())
    story.append(p('Models and fixed revisions','SectionTitle'))
    seen={}
    for job in data['jobs']:
        seen[job['model']]=job['revision']
    for model,revision in seen.items():
        story.append(p(model,'ReportBody'));story.append(p('Revision: '+revision,'ReportSmall'))
        story.append(p('Source: https://huggingface.co/'+model,'ReportSmall'))
    story.append(p('Protocol','SectionTitle'))
    for text in [
        'All models use BF16 on the same NVIDIA GB10. Standard task seeds: 0,1234,1234,1234. Standard tasks take the first 10 test examples per selected subtask. This fixed convenience sample is not a representative full-suite estimate.',
        'KMMLU samples computer science, Korean history and economics. MMLU samples computer security, world religions and high-school geography. HAE-RAE samples its child tasks. Five shots are used for KMMLU, HAE-RAE, MMLU and GSM8K; zero for the other standard tasks.',
        'Matched completion compares Cortex to Qwen3-8B-Base without a chat template. Custom behavior probes compare Cortex to Qwen3-8B-Base using an identical plain transcript and tool instructions, with matched generation budgets and sampling.',
        'The synthetic assistant diagnostic contains 14 bilingual chat constraints, 13 mocked tool cases and 6 arithmetic/word-problem cases. Thinking math uses seeded temperature 0.6, top-p 0.95, top-k 20, with a 1536-token output budget. Other custom cases allow 256 output tokens. Truncated responses count as failures.',
        'Tool evaluation checks tool selection, argument schema and specified content, batched search, mocked multi-step actions, result grounding and safe failed-lookup behavior. No external tools or real email actions are executed. These are newly written constraint tests, not a standardized tool benchmark.',
        'Long-context probes use two deterministic synthetic documents per 4K/16K/32K context budget for both checkpoints. They combine key retrieval, addition across records and source labels. Input lengths reserve output space. The 64K extension is Cortex-only. These are not RULER or LongBench results.',
        'The requested GSM8K harness generation cap is 512 tokens. Runtime override warnings, where detected, are listed explicitly. Differences affected by such warnings are withheld pending review of the effective generation budgets.',
        'Raw per-case samples and task fingerprints are preserved on the evaluation host. This PDF summarizes their aggregate metrics; training overlap and dataset decontamination have not been established.'
    ]: story.append(p(text))

    for track,title,comparator in [('completion','All seven categories','Qwen3-8B-Base')]:
        story.append(PageBreak());story.append(p(title,'ReportTitle'))
        story.append(p('Cortex v1.0 vs '+comparator+'. Differences are percentage points; no significance claim.'))
        rows=[['Benchmark / subtask','Cortex v1.0',comparator,'Difference','Metric']]
        for row in comparison_rows(data,track):
            c,q=row['cortex'],row['qwen'];delta='-'
            if c.get('warnings') or q.get('warnings'):delta='Review budget'
            elif isinstance(c.get('value'),(int,float)) and isinstance(q.get('value'),(int,float)) and c.get('metric')==q.get('metric'):
                delta=f"{(c['value']-q['value'])*100:+.1f} pp"
            metric=c.get('metric') or q.get('metric') or '-'
            label=name(row['task'])+('\nCortex-only extension' if row['extension'] else '')
            metric_label={'acc_norm,none':'Normalized accuracy','acc,none':'Accuracy','pass_rate':'Constraint pass rate',
                          'exact_match,strict-match':'Exact match (strict)','exact_match,flexible-extract':'Exact match (flexible)'}.get(metric,metric)
            rows.append([label,score(c),score(q),delta,metric_label])
        story.append(table(rows,[63*mm,30*mm,30*mm,23*mm,30*mm]))
        if track=='assistant':story.append(p('Synthetic pass rates and standardized task accuracies measure different things. Do not average them into one overall score.','ReportSmall'))
        if track=='context':story.append(p('Context labels are total budgets. Exact input token counts, raw outputs and truncation flags are in the saved custom-sample artifacts. No paired 64K baseline result is claimed.','ReportSmall'))

    story.append(PageBreak());story.append(p('Job inventory','ReportTitle'))
    rows=[['Model / comparison track','Task','State','Sampling / settings']]
    for job in data['jobs']:
        settings=(f"Context budget {job.get('context')} tokens" if job.get('suite')=='long-context' else
                  '14 chat / 13 tools / 6 thinking math cases' if job.get('suite')=='assistant' else
                  f"n={job.get('limit')} per subtask; {job.get('fewshot')}-shot")
        rows.append([job['model'].split('/')[-1]+'\n'+job['track'],job['task'],job['status'],settings])
    story.append(table(rows,[58*mm,47*mm,23*mm,48*mm]))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_bytes(output.getvalue());temporary.replace(path)
    return path
