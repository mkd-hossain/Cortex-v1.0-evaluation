# Cortex v1 versus Qwen3-8B-Base — proposed frozen protocol

Status: prepared for review; no new inference run launched. This is a domain-focused evaluation of a Korean–English enterprise agent, with a separate standard capability reference panel. It is not a universal model ranking.

## Models and prerequisites

Only Cortex revision `a592a43fe940299b5a025e5b719459cda97ae1e6` and Qwen/Qwen3-8B-Base revision `49e3418fbbbca6ecbdf9608b4d22e5a407081db4` are eligible. No Qwen instruction-tuned checkpoint. Record resolved repository, revision, weight hashes, tokenizer hash, runtime/container digest, driver, attention backend and effective positional configuration.

Before inference: prove Cortex theta=1,000,000 and YaRN factor=2/original context=32768 are actually active. Check baseline configuration independently. Validate output on a small predeclared development set. Fix shared effective decoding settings explicitly: greedy, one attempt, equal output budget, repetition penalty=1.0, identical task content and available evidence; record model-specific EOS and tokenization. Do not suppress or discard failed cases.

## Comparison modes

1. **Matched completion:** same standard benchmark prompts, examples, few-shot count and scoring on both models. This estimates underlying completion capabilities.
2. **Deployment behavior:** Cortex uses its published native chat/tool serialization. The base model receives an openly documented plain transcript with the same instructions, tool schemas and evidence. The base has no official assistant template. Label this as a deployment comparison with different serialization, not identical token prompts. Freeze the base wrapper using development examples only; offer both the matched transcript and deployment mode where useful.

Results from these modes remain distinguishable in the same table. Do not average them into an overall winner.

## Focused panel

| Track | Full evaluation proposal | Main scoring |
|---|---:|---|
| Four-tool routing and arguments | 480 cases: four tools × two languages × 60 | Tool choice; JSON/schema validity; argument correctness separately |
| Clarification, missing evidence and no-tool decisions | 240: two languages × 120 | Required abstention/clarification; unnecessary-call rate |
| Grounded answers after tool results | 240: two languages × 120 | Correct facts; supported citations; fabricated-claim rate |
| Multi-turn/topic changes and tool failures | 160: two languages × 80 | End-to-end state and recovery success |
| Korean–English instruction constraints | 160: two languages × 80 | Independently scored constraints; report content and format separately |
| Context retrieval | 120 paired cases: 4K/16K/32K × two languages × 20 | Fact retrieval, citation and strict-format scores; latency/tokens |
| Cortex-only context extension | 40 cases: 64K × two languages × 20 | Same metrics; unpaired extension, no baseline win/loss |

Total proposal: 1,400 matched scenarios per model plus 40 Cortex-only extension scenarios. These sample counts are design targets, not a claim of statistical power for every subgroup. Both languages must cover every family. Use unseen domains, entities, paraphrases, document layouts and distractors; balance single/batched search and document exhaustive/non-exhaustive cases. Separate familiar four-tool tasks from optional novel-tool generalization.

Contract: `search_web(queries: string or string[], search_type?: string)`; `fetch_web_urls(urls: string or string[])`; `retrieve_documents(query: string, file_ids?: string[], exhaustive?: boolean)`; `ask_clarification(question: string, checklist: string[])`. Encode unions with valid JSON Schema. Provide deterministic mock search/page/document results; no live internet variation or paid external judges in the primary score.

## Standard reference panel

Use official held-out test splits of selected KMMLU, HAE-RAE, KoBEST, MMLU, HellaSwag, ARC-Challenge, WinoGrande and GSM8K. Pin dataset and harness revisions, published few-shot/normalization settings and exact filters. For the full run, use complete eligible test splits of the declared tasks rather than the first ten examples. Publish the task inventory and exact counts after loading pinned datasets. Keep the domain-focused results and standard-reference results separate; disclose any training overlap or unavailable contamination check.

## Ten-minute development smoke test

After the runtime fixes, try 24 paired short cases (four tools × two languages × two cases, plus eight no-tool/grounding cases), with a fixed small output budget. Calibrate measured throughput first: ten minutes is a target, not a guarantee. Exclude 16–64K context and full standard suites. This tests integration and scoring; do not advertise its accuracy as a benchmark result. Development cases must not enter the final holdout.

## Independence and audit

Before final inference, commit the entire protocol, scoring rules, all eligible task families, split hashes and selection seed. Have an independent reviewer author or hold the final cases where possible. Cases authored after examining prior pilot failures are development evidence until tested on a fresh holdout. Run exact and near-duplicate checks against accessible training data, including short-text and Korean character matching; state inaccessible-data limits. Do not tune prompts or thresholds on final holdout outcomes.

Preserve per-case prompt/messages, rendered prompt hash, tool schema, fixture hashes, raw response, parsed response, expected answer, score components, error/truncation flags, token counts, timings and effective settings. Store restricted material separately; publish only permitted fixtures. Release holdout prompts and references after evaluation, alongside JSONL responses, scoring code, dependency lockfile, manifest/SHA256 checksums and PDF. Never expose credentials or private training rows.

## Reporting and operation

Use side-by-side results by track, language, serialization mode and sample count. Report paired differences with 95% paired bootstrap confidence intervals and, where suitable, paired binary tests. Predeclare primary endpoints and multiplicity treatment before making significance claims. Include all failures/timeouts; avoid aggregating heterogeneous metrics into a single winner. Native-tool support is a separate compatibility label from prompt-based success.

Preserve prior results as separate run IDs. Dashboard should show completed scenarios and jobs separately, uncertainty, errors and immutable downloadable records. Save each completed response atomically, resume unfinished cases after restart, and cap concurrency from measured memory/throughput rather than trying to fill all RAM. Test recovery before final evaluation. Long-context runtime stability must pass before scheduling 64K.
