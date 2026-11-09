# Seven-category short evaluation

This is an exploratory comparison, not a full benchmark or a claim of superiority.
Original pilot artifacts remain in `runs-pilot`. This run uses `runs-short-all-v1`.

## Comparison tracks

- Raw completion: pinned Cortex v1 vs pinned Qwen3-8B-Base, identical task prompts.
- Native chat: pinned Cortex v1 vs pinned Qwen3-8B, native templates, thinking disabled
  for standardized tasks and operational chat/tools. Both models use seeded sampling
  at temperature 0.6/top-p 0.95/top-k 20 in the separate thinking-math diagnostic.
- Precision: BF16 throughout. Fixed 32K maximum for standardized tasks. No quantization.
- GSM8K generation budget: 512 new tokens. Other standard suites use log-likelihood.

## Standard test coverage

All eleven planned suites are represented, using the first ten test examples per
subtask. KMMLU is restricted to computer science, Korean history and economics;
MMLU to computer security, world religions and high-school geography. These are
domain samples, not full-suite KMMLU/MMLU scores. HAE-RAE uses ten per child task.
Five shots for KMMLU/HAE-RAE/MMLU/GSM8K, zero for other tasks. Both sides use the same
examples and seeds. They may overlap the original pilot. No model tuning is performed.

## Synthetic assistant diagnostics

14 bilingual chat constraints: exact/JSON formatting, factual answer, extraction,
grounded answer, and multi-turn correction. These do not measure broad conversational quality.
13 tool cases: direct greetings, current-information search, URL fetch, exhaustive
document retrieval, clarification, batched search, two mocked multi-step send flows,
failed/errored contact lookup, and tool-result grounding. No real tools are executed.
Six bilingual arithmetic/word-problem cases explicitly permit thinking with a
1,536-token total output budget. Exhausted budgets are recorded as failures and
must be distinguished from completed incorrect answers. Scores use transparent
exact/constraint/regex rules; no independent human or LLM judge is used.

## Long context

Two deterministic synthetic records at each common context budget: 4K, 16K, 32K.
Each asks for key retrieval, addition across cited records, and source labels.
Actual input token counts are logged and stay below the context budget to reserve
output space. Identical document content is built with the Cortex reference tokenizer
for both chat models. A separate two-case 64K Cortex-only extension is reported.
These are synthetic retrieval/grounded-QA probes, not RULER or LongBench scores.

## Durability and reporting

Each custom sample is flushed to disk with prompt/content hashes, model revision,
template hash, settings, raw response, score, runtime, token counts and truncation.
On restart, completed custom samples are reused only with the same protocol.
Standard harness tasks retain completion at job boundaries; an interrupted standard
job restarts. UI pause suspends its full process group. Close the browser freely.
No aggregate winner should be inferred from these small heterogeneous samples.
Task/dataset fingerprints and raw sample artifacts must accompany any report.
Training contamination has not been ruled out.
