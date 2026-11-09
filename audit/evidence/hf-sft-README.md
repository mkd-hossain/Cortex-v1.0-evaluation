---
language:
- ko
- en
license: other
license_name: mixed-see-licensing-section
task_categories:
- text-generation
tags:
- korean
- instruction-tuning
- sft
- tool-calling
- function-calling
- multi-agent
- orchestration
- chain-of-thought
- long-context
size_categories:
- 1M<n<10M
configs:
- config_name: main
  data_files: train.jsonl
- config_name: long64k
  data_files: train_long64k.jsonl
- config_name: korean_cot
  data_files: ko_cot.jsonl
---

# Keural-Cortex-8B SFT dataset

The supervised fine-tuning set used to train **Keural-Cortex-8B**, a Korean-first
bilingual model with a 64K context window, tool calling, and hybrid
thinking/non-thinking modes.

**1,568,649 rows · 1.87B estimated tokens · 1.80B real Qwen3 tokens · 73.7% Korean**

Three files:

| file | rows | what it is |
|---|---|---|
| `train.jsonl` | 1,564,042 | main set, all rows under 32,768 tokens |
| `train_long64k.jsonl` | 4,607 | the 32K–64K band, kept separate because it needs a different `seq_len` |
| `ko_cot.jsonl` | 25,515 | **Korean chain-of-thought, generated for this project** (also included inside `train.jsonl`) |

## Why this exists

Most Korean instruction sets are short single-turn QA. This one was assembled to
train four things at once — Korean conversation, English tool/agent use, Korean
*reasoning*, and long context — and the mix was chosen by measurement rather than
by whatever a token budget happened to reach.

The most useful thing here for other people is probably not the rows. It is
§"What was wrong and how we found it": every defect below was invisible to
structural validation and only appeared when the data was pushed through the
actual tokenizer and the actual chat template.

## Format

One JSON object per line, OpenAI-style messages:

```json
{
  "bucket": "tool",
  "pool": "merged",
  "source": "apigen",
  "lang": "en",
  "category": "tool_calling",
  "messages": [
    {"role": "system",    "content": "..."},
    {"role": "user",      "content": "..."},
    {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "...", "arguments": "{...}"}}]},
    {"role": "tool",      "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "tools": [{"type": "function", "function": {"name": "...", "parameters": {...}}}]
}
```

`tools` is present only on tool-calling rows. **Every `content` is a string** —
never `null` — for reasons explained below.

### Thinking / non-thinking

Rendered through a Qwen3-style chat template, a row containing `<think>…</think>`
becomes thinking mode, and a row without one becomes
`<think>\n\n</think>\n\nanswer` — which is exactly what `enable_thinking=False`
emits. So the split is carried by the data, not by a flag:

| mode | rows | share |
|---|---|---|
| non-thinking | ~1,469,770 | 93.6% |
| thinking (balanced `<think>`) | 98,879 | 6.4% |

## Composition

| bucket | rows | est. tokens | contents |
|---|---|---|---|
| `korean` | 1,125,921 | 445M | Korean chat, QA, writing style, safety, reading comprehension. **~1.7 passes** — Korean is supply-limited at 261.6M unique tokens |
| `tool` | 262,284 | 634M | tool calling, all shapes (see below). 5,107 Korean, 1,676 long-context |
| `core_en` | 114,399 | 240M | English multi-turn conversation and instruction following |
| `korean_cot` | 25,514 | 21.9M | **Korean chain-of-thought — generated, see below** |
| `reasoning` | 13,042 | 180M | English CoT traces |
| `long_context` | 7,858 | 230M | long-document QA with citations, long-form generation |
| `reasoning_math` | 10,217 | 40M | math, answer-verified |
| `code` | 9,414 | 80M | competitive programming |

### Tool calling, by call shape

Volume was never the problem; shape was. An earlier build of this set had
**43 single-call examples out of 89,003 English tool rows (0.05%)** and 94.9%
parallel calls — it would have taught a model to fire 2–3 calls at everything.
Each source is capped here by the shape it teaches:

| shape | rows | share |
|---|---|---|
| exactly 1 call | 66,574 | 25.5% |
| 2–3 calls | 124,221 | 47.5% |
| 4–9 calls (agentic) | 21,618 | 8.3% |
| 10+ calls (agentic) | 12,594 | 4.8% |
| **0 calls — declined to call** | 36,260 | **13.9%** |
| involves parallel calls | 121,938 | 46.7% |

16,304 distinct tool names / schemas. Includes **multi-agent orchestration**
where the "tools" are sub-agents (`"Delegate a subtask to the researcher
sub-agent"`), fanned out in parallel and then synthesised, plus error-recovery
traces where a tool returns `{"ok": false}` and the assistant adapts.

## The Korean CoT subset (`ko_cot.jsonl`)

A scan of every source found **zero Korean rows with a balanced `<think>`
block**. Thinking mode would have been English-only on a Korean-first model, and
no reweighting fixes that — so it was generated.

Seeds are real Korean questions that **ship with their own answers**, so the
teacher's output could be graded rather than trusted:

| seed source | rows | gradable how |
|---|---|---|
| `kmmlu_train` | 14,935 | answer ends `정답: (B)` → exact letter match |
| `orca_math_korean` | 13,600 | numeric answer → exact match |
| `kopen_platypus` | 9,552 | prose, ungraded |

Generated with DeepSeek-V4-Flash (local vLLM), then gated on: reasoning must be
Korean (Hangul ratio ≥ 0.30 — a Korean answer wrapped around English reasoning
teaches the model to think in English), answer must be Korean, reasoning ≥ 80
chars, non-degenerate, and **the graded answer must be correct**.

| | |
|---|---|
| generated | 34,917 |
| passed all gates | **25,535 (73.1%)** |
| after dedup | **25,515** |
| **answer-verified against ground truth** | **20,395 (80%)** |
| rejected — wrong answer | **2,786** |
| rejected — unparseable / truncated | 4,698 |

Those 2,786 rejections are the point. Fluent Korean reasoning that reaches the
wrong conclusion is worse than no reasoning data, and no text-level probe
detects it.

## What was wrong and how we found it

Structural validation passed this dataset completely: every row ended on an
assistant turn, no template markers leaked, every line was valid JSON. Seven
defects survived that and were only found by running the real tokenizer and the
real chat template over every row.

**1 — 30% of rows could not be rendered at all.** 341,077 rows raised on
`apply_chat_template`: 340,865 with `"content": null` on assistant tool-call
turns (`TypeError: argument of type 'NoneType' is not iterable`) and 212 missing
the `content` key entirely (`UndefinedError`). Of all tool rows, **85.7%
failed** — nearly the whole tool-calling capability. The data was not malformed:
`content: null` is the canonical OpenAI representation for a tool-call-only turn.
The data and the template simply disagreed, and nothing checked. Fixed on the
data side; every `content` in this release is a string.

**2 — the token estimate was 1.73× low on English.** Lengths were budgeted from
`len(text)/5.95`. Measured against the real tokenizer that ratio is ~3.44 for
English and ~1.33 for Korean, so **47% of the long-context file exceeded its own
65,536 cap** (max observed 157,783 tokens, past the model's 131,072 position
limit). Corrected — and the packer now gates on real tokenizer length, because a
character ratio is never exact.

**3 — tool schemas were never counted.** The template renders every schema into
the system prompt, so those tokens are trained on. Counting message content
alone under-read one bucket by 26% (240M budgeted vs 303M real).

**4 — the largest source was 0.2% unique.** One synthetic agentic source was 30%
of the corpus with flawless mechanics (0 schema violations across 3.07M tool
calls) but **2,950 distinct assistant sentences across 1,546,688 turns**; its 8
most frequent sentences covered 55.2% of its assistant turns, it used 24 tool
names, and its median final answer was 54 characters. Capped.

**5 — two thirds of the CoT data was truncated.** 7,581 rows opened `<think>` and
never closed it: 51–62K characters stopping mid-sentence, some degenerated into
another language. They teach a model to enter thinking mode and never leave.
Gated out.

**6 — 89,340 rows carried `Human:` / `GPT:` prefixes inside message content.**
100% of one Korean QA source. Would have trained the model to prefix its replies
with `GPT:`. The markers are plain words, so no special-token check caught them.
Stripped rather than dropped — Korean is the scarce half of this mix.

**7 — `seq_len` chosen from the median discards the reasoning.** At `seq_len
8192` (median row is 232 tokens for Korean) the packer would have dropped
**89.2% of the CoT traces**, whose median is 13,989 tokens. Measured per bucket
before choosing 16,384.

## Intended use

Built for SFT of an 8B Korean-first model. Mixed with a 445M-token Korean share
and 634M tokens of tool/agent data, it is not a general-purpose corpus and the
bucket ratios encode that goal.

## Limitations

- **Korean thinking is narrow.** All 25,515 Korean CoT rows derive from ~38k
  multiple-choice/math/reasoning seeds. They do not teach Korean reasoning over
  open-ended conversation.
- **No `/think` `/no_think` soft-switch data**, so "auto mode" is domain-driven
  rather than controllable by prompt.
- **Duplicates are not removed globally.** One source measured 42% duplicate
  prompts before capping; no cross-source dedup pass was run.
- **Korean is repeated ~1.7×.** Train for more than one epoch and Korean rows
  are seen 3.4+ times.
- **`train_long64k.jsonl` is ~1% assistant tokens** — long document in, short
  answer out. Expensive per unit of gradient.
- Some rows still exceed their nominal cap; gate on real tokenizer length.

## Licensing

**Mixed, and inherited from the upstream sources.** `license: other` above is
deliberate — verify the sources relevant to your use before redistributing.
Measured composition:

| status | rows | share |
|---|---|---|
| permissive (`apache-2.0`, `mit`, `cc-by-4.0`) | 1,429,942 | 91.2% |
| `unknown` upstream license | 67,840 | 4.3% |
| not tracked upstream | 66,049 | 4.2% |
| marked `internal` | 4,818 | 0.3% |

Sources whose upstream license was recorded as `unknown`: `koalpaca` (35,824),
`korquad_chat` (19,190), `kopen_platypus` (9,332), `carrot_ko_instruct` (2,934).
`keural_identity` (4,818) is project-internal persona data. `apigen` is tagged
`apache-2.0|cc-by-4.0` here, but some upstream xLAM releases are **CC-BY-NC** —
check before commercial use.

If you need a clean subset, filter on `source` against the table above.

## Reproduction

The pipeline is in the model repo: `assemble.py` (bucketed assembly + every
gate), `verify_render.py` (renders every row, reports real token counts and the
assistant-only trainable fraction), `pack_sft.py` (chat template → tokens →
assistant-only labels → packed memmaps), and
`SFT_details/01_data_preparation.md` (the full measurement record).

## Citation

```bibtex
@misc{keural_cortex_8b_sft,
  title  = {Keural-Cortex-8B SFT dataset},
  author = {Hossain, Md Najmul},
  year   = {2026},
  note   = {Korean-first bilingual SFT set with tool calling, multi-agent
            orchestration, generated Korean chain-of-thought, and 64K long context}
}
```
