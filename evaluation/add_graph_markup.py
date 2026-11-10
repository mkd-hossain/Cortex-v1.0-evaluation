"""Add read-only graph UI to the existing dashboard; no server changes."""
from pathlib import Path
p=Path(__file__).with_name('dashboard.html');text=p.read_text(encoding='utf-8')
if 'id="graph-nav"' not in text:
    text=text.replace('<a href="#activity">Live logs</a>','<a href="#activity">Live logs</a><a href="#graphs" id="graph-nav" aria-controls="graphs" aria-expanded="false">Graphs</a>')
    panel='''<section id="graphs" class="glass graph-panel" aria-labelledby="graph-heading" hidden>
<div class="section-heading"><div><p class="eyebrow">CURRENT RUN · LIVE COMPARISON</p><h2 id="graph-heading">Benchmark graphs</h2><p>Saved results only. Same 0–100% scale for both models; pending scores are never plotted as zero.</p></div><button id="close-graphs" class="button secondary">Close graphs</button></div>
<div class="graph-filters"><label>Category<select id="graph-category"><option value="">All categories</option><option>Korean knowledge</option><option>Korean understanding</option><option>English knowledge/reasoning</option><option>Math reasoning</option><option>Tool calling</option><option>Chat</option><option>Long context</option></select></label><label>Find a benchmark<input id="graph-search" type="search" placeholder="e.g. Korean history, GSM8K" maxlength="120"></label><label>Score view<select id="graph-score"><option value="primary">Primary / strict scores</option><option value="semantic">Semantic fixture scores</option></select></label><label>Order<select id="graph-order"><option value="original">Benchmark order</option><option value="cortex">Largest Cortex advantage</option><option value="qwen">Largest Qwen advantage</option></select></label><label class="graph-check"><input id="graph-paired" type="checkbox" checked>Completed pairs only</label></div>
<div id="graph-summary" class="graph-summary" aria-live="polite"></div>
<div class="graph-legend"><span><i class="cortex-swatch"></i>Cortex v1.0</span><span><i class="qwen-swatch"></i>Qwen3-8B-Base</span><small id="graph-updated"></small></div>
<p class="graph-caution">Percentages use each task’s declared metric. Higher is better; differences are percentage points, not significance tests. Row counts are descriptive, not an overall model ranking. Standard completion and deployment fixtures have different declared prompt formats.</p>
<div id="graph-chart" class="graph-chart" role="region" aria-label="Side-by-side benchmark score bars" tabindex="0"></div>
<p id="graph-empty" hidden>No matching results yet. Try another filter or include unfinished pairs.</p>
<p class="graph-caution">Sample counts and metrics appear with every row. Strict and semantic fixture scores are shown separately to avoid counting the same cases twice. Cortex-only 64K tests are unpaired and never treated as a baseline loss.</p>
</section>'''
    text=text.replace('<section id="results">',panel+'\n<section id="results">')
p.write_text(text,encoding='utf-8')
