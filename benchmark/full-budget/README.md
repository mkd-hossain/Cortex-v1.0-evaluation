# Fifteen-hour budgeted evaluation

## Live graphs

Use **Graphs** beside **Live logs** on either dashboard, or open the dashboard with `/#graphs`. The optional panel uses the current run's saved metrics and refreshes every five seconds. It provides category and benchmark filters, completed-pairs-only selection, primary/strict versus semantic views, paired bars on a fixed 0–100% scale and difference ordering. Pending scores remain missing, never zero. Cortex-only extension tests remain unpaired. Displayed higher/tied counts are descriptive row counts, not an overall model ranking or significance test. All numerical views retain sample counts and declared metric labels. The graph update changes only HTML/CSS/JavaScript; the controller and evaluator are not restarted. `node test_graphs.cjs` checks zero versus missing scores, mismatched metrics, warning rows, filtering, ordering and rendering against a saved live-data snapshot.

**November 10 continuation:** after 22 of 39 jobs completed and the original deadline stopped the run, the user authorized finishing the remaining 17 jobs. The controller's hard stop is now explicitly disabled. Completed artifacts and scoring/prompt/sample source hashes were checked unchanged. The interrupted job resumes its durable per-case responses. Runtime-extension events and the prior partial summary/checksums are archived under `runs-full-budget-v1/runtime-extensions/`. The numeric year-9999 field retained in `plan.json` is solely compatibility for the unchanged per-case worker; it is not a scheduled deadline. The dashboard's effective deadline is null. Manual Pause/Resume remains available; no scoring scope was expanded.

This is a fixed-budget evaluation of Cortex v1 and Qwen3-8B-Base across all requested categories. It is **not an uncapped evaluation of all official test splits**. Standard tasks sample up to 50 seeded random examples per leaf task; smaller splits use all examples. The frozen manifest publishes exact counts and indices. Preserve the earlier development smoke as a different run.

## Preconditions

Run `freeze_standard.py` in the tested Spark environment to save exact datasets locally, their fingerprints and SHA256 checksums. It uses the installed harness definitions for KMMLU, HAE-RAE, KoBEST, MMLU, HellaSwag, ARC-Challenge, WinoGrande and GSM8K. No standard inference starts until freezing finishes. Record installed dependencies and source hashes with the run. Dataset snapshots stay on Spark; public audit packs retain identities and selection indices. Dataset licenses govern redistribution of prompts/documents.

`calibrate.py` checks a separate four-case development subset per model, validating explicit stopping boundaries before deployment evaluation. Those cases never enter the larger synthetic fixture set. The wrapper, demonstrations, stop rules and scorer freeze before final inference. Calibration does not select a winning prompt based on final cases.

## Model configuration and generation

Only the two revisions in `base_protocol.EXPECTED_MODELS` are accepted. Translate Cortex's serialized `rope_parameters` to the installed legacy `rope_theta`/`rope_scaling` fields before constructing weights, then assert the actual model rotary type. Base keeps default rotary type and theta 1,000,000. No weights change.

Standard tasks use matched raw completion and harness few-shot definitions, BF16 and flash-only SDPA, automatic multiple-choice batches capped at 16; math generation uses a fixed batch of one to avoid the harness full-window probe. GSM8K explicitly receives greedy generation with a 512-token cap and repetition penalty 1.0; no inherited repository output budget. Record requests, completions, settings and response cache. A larger cap might change math scores and is a separately declared protocol change.

Deployment fixtures use Cortex's native chat/tool template versus a Base plain transcript. Both receive identical example content, tool schemas, available evidence, greedy decoding, repetition penalty 1.0 and a 128-token cap. Both stop at tool-call closure, an explicit answer boundary, model EOS or the same transcript role boundaries. Preserve raw tokens/text and truncation flags; do not call serializations identical.

## Coverage

- 480 bilingual four-tool routing cases, 240 abstention/no-tool cases, 240 tool-result grounding cases, 160 supplied-history multi-turn state cases, 160 instruction constraint cases: 1,280 per model.
- 40 cases each at 4K, 16K and 32K per model; 40 Cortex-only 64K cases. Same source text at paired lengths; input token counts recorded, no silent context truncation.
- All declared standard leaf tasks receive the frozen sample, rather than testing only three selected MMLU/KMMLU domains.

The synthetic fixtures are generated from templates with new parameters. They are **not independently authored holdout evidence**. Multi-turn fixtures provide previous history and results, rather than measuring autonomous live execution. Tool arguments have declared deterministic checks; nonempty clarification fields do not establish human-rated clarification quality. Report strict output formatting separately from semantic JSON extraction. A proper independent benchmark still needs externally reviewed cases, contamination checks and confidence intervals; this run does not grant those claims.

## Time budget, recovery and reporting

Recovery on November 10 found Spark healthy again. The original hard deadline is retained, so only about two hours remained at recovery. The queue can therefore finish with partial coverage; the 14,340-scenario inventory is planned work rather than a guarantee of completion. The unsafe math auto-batch preflight is preserved separately; the recovered launcher validates the fixed generation batch of one before starting scored work.

`plan.json` records a hard wall-clock deadline. Preparation/calibration uses a conservative 14-hour remaining window, leaving time within the user's 15-hour constraint. Manual pauses consume wall-clock time. The controller stops the process group at the deadline, resumes paused processes before termination, saves interrupted state and rejects further Start/Resume until a new budget is authorized. This bounds runtime; it cannot guarantee every scenario completes.

The run is successful only for completed jobs. At the deadline publish partial coverage and pending/interrupted jobs explicitly; missing results remain blank. Do not score missing work as zero or announce a winner from incomplete pairs. Previous runs remain immutable under their own IDs. Custom responses are fsynced per case; an interrupted case restarts. Standard inference caches responses in SQLite; after a restart aggregation reuses saved responses, though in-flight work may repeat.

Monitor `runs-full-budget-v1/state.json`, per-job logs, progress files and runtime metadata through the existing dashboard. Do not fill RAM just to claim maximum utilization. Limit simultaneous model processes to one and validate context stability. If the driver fails, preserve results and require recovery rather than launching duplicate evaluators.
