# Cortex v1.0 evaluation

Evaluation code, saved pilot outputs, charts, configuration audit and a proposed domain-focused protocol for **Keural Cortex 8B v1.0 versus Qwen3-8B-Base** on NVIDIA DGX Spark.

**Read the audit before interpreting any chart.** Earlier Cortex pilots used an incompatible interpretation of its published positional configuration. Those results are preserved as provisional historical evidence, not a validated overall model ranking. The current run is a small development integration test, not the full benchmark.

## Start here

- [Audit findings and evidence scope](audit/AUDIT_REPORT.md)
- [Proposed full evaluation protocol](audit/BENCHMARK_PROTOCOL.md)
- [Current development prompts and tool schemas](benchmark/audited-smoke/public-cases.json)
- [Current runner and scoring](benchmark/audited-smoke/smoke.py)
- [Saved current-run outputs](audit/audited-smoke-run/)
- [Remote configuration preflight](audit/evidence/spark-preflight.json)
- [Recorded Spark dependencies](audit/evidence/spark-requirements.txt)
- [Historical base-only pilot](audit/base-only-run/)
- [Preserved mixed pilot and instruction-tuned comparison](benchmark/archives/)
- [Historical charts](benchmark/output/) — exploratory; see audit limitations

## Exact checkpoints

| Model | Hugging Face revision |
|---|---|
| `mkd-hossain/Keural-Cortex-8B-v1.0` | `a592a43fe940299b5a025e5b719459cda97ae1e6` |
| `Qwen/Qwen3-8B-Base` | `49e3418fbbbca6ecbdf9608b4d22e5a407081db4` |

The current runner rejects other checkpoints. Historical archives include an explicitly separate Qwen3-8B instruction-tuned comparison. Do not merge its results with the Base comparator.

## Current development validation

24 bilingual cases per model: 16 four-tool cases and 8 direct/grounded-answer cases. Each tool family appears in Korean and English. No real external tools execute. Cortex uses its native chat template; the Base model uses a documented plain transcript. Requests, schemas, greedy decoding, repetition penalty 1.0 and the 192-token cap match; **serialization and model-specific stop tokens differ**.

The compatibility adapter maps Cortex's newer `rope_parameters` into the installed Transformers 4.57.6 fields: theta 1,000,000, YaRN factor 2, original context 32,768. This changes inference configuration, not weights. `runtime.json` records original/effective configuration; `generation.json` records decoding settings. Preflight verifies rotary type before model loading.

These newly written cases are development cases and partly motivated by earlier failures. They are not an independent holdout. The short scorer checks tool choice, schema and limited arguments; it does not fully judge every search query or clarification's semantic quality. Truncated output fails the case. Do not claim general superiority from this run.

## Reproduce the small validation

### Completed development snapshot

| Track | Cortex native chat | Qwen Base plain transcript |
|---|---:|---:|
| Four-tool contract | 14/16 | 0/16 |
| Direct/grounded answers | 7/8 | 0/8 |

These numbers describe this exact development setup. The Base model repeatedly continued to the output cap rather than producing a completed protocol response; truncation is scored as failure. This is evidence about integration under this wrapper and budget, not proof that the Base model has zero underlying ability. Inspect raw responses, truncation flags and differing serialization before drawing conclusions. A matched-format comparison and independent holdout remain necessary. Earlier pilot numbers must not be substituted for this run.

Use an isolated Linux environment with a GB10-compatible CUDA/PyTorch stack. Inspect the recorded dependency list; do not replace your GPU stack blindly. Download only the pinned checkpoints, then run from `benchmark/audited-smoke`:

```bash
python test_smoke.py
python preflight.py
python smoke.py --model mkd-hossain/Keural-Cortex-8B-v1.0 --revision a592a43fe940299b5a025e5b719459cda97ae1e6 --output ./runs/cortex
python smoke.py --model Qwen/Qwen3-8B-Base --revision 49e3418fbbbca6ecbdf9608b4d22e5a407081db4 --output ./runs/base
```

Model loading is cache-only: pre-download the two revisions using Hugging Face tooling. Rerunning an identical command resumes saved complete cases; changed code/cases require a new run directory. The Linux controller supports manual process pause/resume. After a machine restart, completed cases persist and the interrupted case restarts. The deployment helper is specific to the original host; adapt it before use.

## Live dashboard

[Public read-only dashboard](https://cortex-benchmark-spark.tail73fbf3.ts.net/). Availability depends on Spark and its network. Public control requests are rejected. Operator access stays private through Tailscale. The repository is a dated artifact snapshot, not automatically synchronized live state.

## What is included and excluded

Includes evaluation source, plans, responses, score files, charts, runtime evidence, protocol documents and historical artifacts. Historical README files describe their own stage and may be superseded by this top-level README and audit.

Excludes model weights, private training checkout/Git history, restricted training rows, credentials, SSH keys, local virtual environments and internal visual-QA snapshots. Training source was inspected at commit `b40ab0b1f4cd3fcd38f861675c71336331c271d9`; file hashes are retained for provenance. Exact public-weight-to-training-export lineage and complete training contamination clearance remain unproven.

Public copies replace deployment account paths and local connection addresses with placeholders. This means hashes of those sanitized files differ from original manifests embedded in old runs. Prompt content and numeric scores are not deliberately edited. `SHA256SUMS.json` describes this publication; historical manifests describe original snapshots. Upstream model, dataset and source licenses continue to apply; no blanket license is granted over third-party artifacts. Newly authored synthetic development cases are marked CC0 in their case file.

## Next full benchmark

Resolve all runtime/scoring issues, freeze task selection and scoring before final inference, and use fresh independent holdout cases. Publish all wins, ties, failures, truncations and confidence intervals. Keep standard completion, deployment behavior and Cortex-only context extension results distinguishable. See the proposed protocol for sample counts and audit requirements.
