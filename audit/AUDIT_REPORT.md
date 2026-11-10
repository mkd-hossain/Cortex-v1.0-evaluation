# Cortex v1 benchmark audit — 2026-11-09

The previous pilots are exploratory diagnostics and should not establish an overall winner. A potentially serious model configuration/runtime mismatch must be resolved before rerunning either model. A focused benchmark can fairly measure Cortex's intended strengths, but cannot promise that Cortex wins.

## Evidence inspected

- GitHub training repository `MKD-CORP/mkd-keural-be-cortex-8b`, branch `phase7-dpo`, commit `b40ab0b1f4cd3fcd38f861675c71336331c271d9`; inventory of 358 source files in `evidence/source-inventory.json`.
- Hugging Face Cortex v1 revision `a592a43fe940299b5a025e5b719459cda97ae1e6`: card, configuration, generation configuration and tokenizer/chat template.
- Public SFT dataset `mkd-hossain/keural-cortex-8b-sft`, revision `5e7bad9a68ba29f88da9d7c5e7ca861188e10fa5`: card, manifest and file identity. This was not a complete scan of all training examples.
- 160 saved custom pilot responses, summarized in `evidence/pilot-response-audit.json`; original results remain preserved.
- 120 deterministic examples from the final agent data generator, to examine family/language coverage.

## Findings that affect interpretation

1. **Runtime compatibility is a blocking issue.** Published v1 stores theta 1,000,000 and YaRN factor 2 under `rope_parameters`, and identifies Transformers 5.17.0. The pilot used Transformers 4.57.6. That version's Qwen3 configuration defaults to top-level theta 10,000 and `rope_scaling=None`; its rotary implementation reads `rope_scaling`. Static source inspection indicates the newer fields may be ignored. This could affect short as well as long inputs. Confirm effective configuration and rotary frequencies in the actual inference process before attributing low scores to training. The CPU-only local configuration check is separate from remote model execution. Spark was unreachable during the final audit checks; no successful remote runtime check is claimed.
2. **Some zero context scores mean formatting failures.** Saved responses include fenced JSON containing the correct facts, rejected by strict `json.loads`. Preserve the strict score, but report semantic retrieval and strict formatting separately. Other responses are empty, repetitive or incorrect, so this does not explain every failure.
3. **The previous synthetic tool suite does not exactly match the final training contract.** The source contract has `search_web`, `fetch_web_urls`, `retrieve_documents`, and `ask_clarification`. The pilot also tested contact/email tools and different argument constraints. Novel-tool generalization is a useful separate test, not evidence of failure on the trained contract.
4. **Plain transcripts and native chat are different conditions.** Cortex was trained with a native chat/tool template. The shared plain-transcript pilot measures prompt-based completion behavior. Its scores cannot be treated as a complete assessment of native assistant integration.
5. **Generation settings require a fresh audit.** Saved math warnings indicate overridden output budgets. Published generation defaults also differ, including repetition penalty. Equal prompts alone do not establish equal effective decoding settings.
6. **Training validation is not independent generalization evidence.** The final generator uses `family=i%12` and Korean when `i%2==0`: each family occurs in only one language in the inspected generator. Its template-derived validation should be supplemented with new templates, scenarios and both languages for every family.
7. **Public dataset provenance is incomplete for final v1.** The public SFT snapshot and later repository manifests describe different stages. Source records suggest CPT → context extension → SFT → DPO → agent SFT, but an export/weight checksum manifest is needed to prove the exact published checkpoint's lineage.
8. **Contamination and licensing remain open.** Existing word n-gram checks miss short questions and do not certify the final checkpoint against every evaluation set. Some source data has redistribution restrictions. Public audit packs should contain new permitted fixtures and evaluation outputs, not restricted training examples or private repository content.

## What a base model's tool-shaped response means

A base model can continue a prompt into JSON or a tool-like string. This does not establish supported native tool calling, execution permissions, or reliable agent behavior. Label prompt-based results as such. Validate tool choice, arguments, abstention and multi-turn grounding; execute only against deterministic mock tools. Native function-calling and prompt-based modes must be identified explicitly.

## Publication recommendation

### Grounding fixture answer leakage (verified November 10)

All 240 responses per model in the supplied-tool-result extraction fixture matched the expected JSON, with no truncations. However, the fixture generator sets the ticket number equal to the requested allocation, so the answer is present in the initial user ticket ID as well as in the tool result; the required citation is explicitly supplied. Therefore the 100%/100% result does not isolate grounding or native tool-calling ability. Preserve the original result files and task identifiers, but label figures as **simple extraction with answer leakage** and exclude these scores from capability claims. A follow-up needs independent identifiers/answer values, distractors, missing/conflicting evidence, and frozen scoring. Do not modify this run's cases or retroactively substitute follow-up results.

### Follow-up generation-default audit

The full-run development calibration on Spark emitted a Transformers warning that model-specific defaults could replace library-default-valued settings in a separately supplied `GenerationConfig`, including `do_sample` and repetition penalty. Consequently, requested greedy settings alone are insufficient evidence that the first 48-response smoke used the intended effective decoding. Preserve that smoke as provisional integration evidence. The new budgeted runner sets `use_model_defaults=False`, passes `do_sample=False`, repetition penalty 1.0 and the token cap explicitly, and checks the effective generation preparation path. A regression test reproduces a model with sampling-enabled repository defaults and verifies those settings cannot override the requested full-run values. Revised calibration outputs are separate from the first calibration and first smoke; no prior scores are overwritten.

### Full-window automatic generation probe

The budgeted-run preflight exposed a separate harness issue: automatic batch detection for generation calls `_detect_batch_size()` without request lengths, so it probes the full configured 32,768-token window, repeats forward/log-softmax passes five times, and starts from the maximum batch size. This is much larger than the short math prompts. Spark reached approximately 105 GiB used memory with swap activity and became unresponsive to SSH/dashboard requests. The launch service was asked to stop; remote termination could not be confirmed while the host was unresponsive. No scored full-run job had started. The corrected runner uses a fixed math-generation batch of two, retaining automatic batching only for multiple-choice requests where the probe receives actual request lengths. Resume requires host recovery and rerunning the corrected math preflight. Preserve the failed preflight separately; it is not a model accuracy result.

After recovery on November 10, the two-question generation preflight failed cleanly because its padding creates a non-null attention mask unsupported by the forced flash kernel. The final generation setting is therefore **batch size one** for both models, with a separate `math-preflight-v3` artifact directory. The standard classification path retains its already tested automatic batch policy. These are operational changes before scored inference, not edits to model outputs or accuracy scores.

### Confirmed local configuration reproduction

An isolated CPU-only Transformers 4.57.6 environment loaded the pinned downloaded Cortex configuration with `AutoConfig`. It returned `rope_theta=10000.0`, `rope_scaling=null`, while preserving the newer `rope_parameters` as a separate attribute. See `evidence/local-config-check.json` and `check_local_config.py`. Combined with that version's rotary implementation reading `rope_scaling`, this confirms an incompatible interpretation in the reproduced configuration path. It does not substitute for inspecting the remote inference process or proving its constructor supplied no overrides. Treat earlier Cortex comparisons as provisional until that path is verified and corrected.

Keep both pilots and their raw outputs unchanged. Attach this audit to any shared charts; do not describe the pilots as proof of overall superiority. Resolve runtime configuration, decoding and scoring issues first, then freeze the new protocol before viewing holdout results. Report all wins, ties and losses. No retraining is required to correct an inference configuration or evaluation bug; improvement is not guaranteed.

Primary references: [Cortex model](https://huggingface.co/mkd-hossain/Keural-Cortex-8B-v1.0), [public dataset](https://huggingface.co/datasets/mkd-hossain/keural-cortex-8b-sft), [Transformers 4.57.6 Qwen3 configuration](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/qwen3/configuration_qwen3.py), [Qwen3 rotary implementation](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/qwen3/modeling_qwen3.py), [BFCL methodology and leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html).
