# Final v1 evaluation audit

This document concerns the completed 39-job run `runs-full-budget-v1`. Earlier exploratory pilots are not current evidence.

## Checkpoint identity and runtime

Cortex revision `a592a43fe940299b5a025e5b719459cda97ae1e6` and Qwen3-8B-Base revision `49e3418fbbbca6ecbdf9608b4d22e5a407081db4` are fixed in the plan and saved job records. No Qwen instruction-tuned checkpoint is part of this run.

The Cortex configuration stores rotary settings under `rope_parameters`, while Transformers 4.57.6 reads the legacy configuration path. The final adapter explicitly applies theta 1,000,000, YaRN factor 2 and original window 32,768 and checks effective rotary behavior. Base retains its default theta 1,000,000. This corrects runtime interpretation without changing checkpoint weights. See `../evaluation/base_protocol.py` and per-job runtime/provenance records.

Generation explicitly disables inherited model defaults (`use_model_defaults=False`), uses greedy decoding and repetition penalty 1.0. GSM8K uses a 512-token output cap and generation batch one. Deployment/context fixtures use a 128-token cap. Automatic full-window generation probing was unsuitable for Spark memory; final generation uses fixed batch one. Failed preflight attempts are not scored model outputs.

## Comparability

Standard benchmarks use matched completion prompts, dataset selections, few-shot settings and scoring. Each standard subtask contains 50 seeded questions; these are not full official test splits. KMMLU and MMLU means summarize 45 and 57 subjects respectively. Individual metrics and sample counts are preserved in the CSV and raw files.

Deployment fixtures use Cortex native chat versus a Base plain transcript. Requests, demonstrations, schemas and budgets are shared, but serialization differs. These measure deployment-contract compliance, not a controlled identical-serialization comparison. Four-tool routing does not establish arbitrary agent capability or authorize actual external tool execution. Supplied-history state fixtures do not demonstrate autonomous multi-turn interaction.

## Extraction fixture leakage

The task saved as `Tool-result grounding` sets the user ticket identifier equal to the expected allocation; the citation is supplied. Both models scored 240/240, but the answer is available outside the tool result. This is simple extraction with answer leakage, not isolated grounding. Raw task identifiers and results remain unchanged; presentation labels disclose the defect. These scores are excluded from capability claims and default graphs. A future independent fixture must use unrelated identifiers, withheld answers and conflicting/missing evidence.

## Context and scoring

Strict scores require the requested output contract. Semantic scores accept the recorded JSON-content normalization, including fenced JSON. Both are preserved, with correct-content and format failures distinguished. Paired 4K/16K/32K cases reserve output space. The 64K extension is Cortex-only; missing Base results must never be scored as zero or a loss.

## Evidence limits and publication

Synthetic cases are template-generated development fixtures, not an independently authored holdout. Training-set independence and contamination clearance are not established. No overall winner, significance claim, general production certification or aggregate across incompatible metrics is warranted.

The initial runtime deadline interrupted the run. Authorized continuation preserved completed jobs and subsequently finished all 39; completion is recorded in `../results/final-summary.json`. A completed benchmark does not mean all tests passed.

The static site removes live telemetry and unused presentation-level stderr fields; it does not fabricate confidence intervals. Original per-job files retain recorded outputs and scoring. Public archive paths may be sanitized; historical inference-time manifests and the new publication `SHA256SUMS` serve different purposes. Verify published bytes with the latter. Model weights and private training source are not distributed.
