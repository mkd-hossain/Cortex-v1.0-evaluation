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
        canvas.drawString(17*mm,12*mm,'Time-budgeted evaluation | No overall capability claim')
        canvas.drawRightString(width-17*mm,12*mm,f'Page {document.page}')
        canvas.restoreState()

    story.append(Spacer(1,12*mm))
    story.append(p('Cortex v1.0\nComparative evaluation','ReportTitle'))
    story.append(p('Seven-category budgeted evaluation - NVIDIA DGX Spark - BF16','ReportBody'))
    if allow_partial:
        story.append(p('LAYOUT VALIDATION - PARTIAL SNAPSHOT. This is not a completed benchmark report.','SectionTitle'))
    elif data['status']=='budget_exhausted':
        story.append(p('PARTIAL REPORT - HARD RUNTIME BUDGET REACHED. Pending and interrupted work is not a completed result.','SectionTitle'))
    else:
        story.append(p('Completion report','SectionTitle'))
    starts=[j['started'] for j in data['jobs'] if j.get('started')]
    ends=[j['ended'] for j in data['jobs'] if j.get('ended')]
    duration=f"{(max(ends)-min(starts))/3600:.2f} hours" if starts and ends else 'Not available'
    generated=datetime.now().astimezone().isoformat(timespec='seconds')
    story.append(table([['Run','Completed jobs','Observed wall time'],[data['run_id'],f"{data['completed']} / {len(data['jobs'])}",duration]],[79*mm,43*mm,54*mm]))
    story.append(Spacer(1,6*mm))
    story.append(p('Interpretation','SectionTitle'))
    story.append(p('This evaluation uses seeded samples and synthetic fixtures, not all official full test splits. No overall winner, statistical significance, production readiness or training-data independence is established. Only Qwen3-8B-Base and Cortex v1 are compared. Standard completion and deployment behavior have explicitly different prompt formats.'))
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
        'BF16 on NVIDIA GB10. Standard task seeds: 0,1234,1234,1234. Seeded random selection uses up to 50 samples per leaf task, frozen before scored inference. The manifest records exact indices and dataset fingerprints; not all official full test splits are evaluated.',
        'All 45 installed KMMLU subjects and 57 MMLU subjects are included. Five shots for KMMLU, HAE-RAE, MMLU and GSM8K; zero for other standard tasks. Sample counts remain visible beside scores.',
        'Standard tasks use matched raw completion. Deployment fixtures use Cortex native chat versus Qwen Base plain transcript. Identical example content, schemas and evidence are supplied, but serialization differs explicitly.',
        'Deployment fixtures: 480 routing, 240 abstention/no-tool, 240 grounding, 160 supplied-history multi-turn and 160 instruction-constraint cases per model. Both models use greedy generation, repetition penalty 1.0 and a 128-token cap. Model-default inheritance is disabled explicitly. Strict and semantic formatting scores are separate.',
        'Tool arguments have deterministic checks. Clarification fields are checked for presence rather than full human-rated semantic quality. Multi-turn fixtures supply history rather than executing autonomous live workflows. No external tool actions occur. Cases are synthetic parameter-held-out fixtures, not independent holdout evidence.',
        '40 context cases per budget at 4K, 16K and 32K for each model; 40 Cortex-only 64K cases. Same source text in paired tests, actual input tokens recorded. The extension is unpaired. These are not RULER or LongBench results.',
        'GSM8K uses a verified explicit 512-token cap with greedy decoding and repetition penalty 1.0. Effective model configuration and generations are saved; Cortex RoPE translation is asserted before inference.',
        'A hard wall-clock deadline stops the process group and preserves saved responses. Pending or interrupted work is not zero accuracy. Resume after deadline requires a new authorized budget. Raw outputs, manifests and uncertainty summaries remain available for audit. Training-data independence is unproven.',
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
        settings=(f"n={job.get('sample_count')}; context {job.get('context')}" if job.get('suite')=='context' else
                  '14 chat / 13 tools / 6 thinking math cases' if job.get('suite')=='assistant' else
                  f"n={job.get('sample_count')}; {job.get('fewshot')}-shot")
        rows.append([job['model'].split('/')[-1]+'\n'+job['track'],job['task'],job['status'],settings])
    story.append(table(rows,[58*mm,47*mm,23*mm,48*mm]))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_bytes(output.getvalue());temporary.replace(path)
    return path
