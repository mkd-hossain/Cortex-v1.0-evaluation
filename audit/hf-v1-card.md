---
language:
- en
- ko
license: apache-2.0
library_name: transformers
pipeline_tag: text-generation
tags:
- text-generation
- conversational
- korean
- english
- function-calling
- agent
---

# Keural Cortex Foundation Model (8B) — v1.0

<p align="center"><img src="assets/keural-cortex-agentic-logo.gif" alt="Keural symbol at the Cortex neural core with animated orbital energy" width="100%"/></p>

Keural Cortex is MKD's local-first Korean-English language-model program for Keural applications. This release is an 8B-parameter, instruction- and preference-aligned checkpoint with a structured tool-calling layer for enterprise workflows.

It is designed to run in customer-controlled infrastructure through an OpenAI-compatible vLLM endpoint. The host application—not the model—executes tools, enforces permissions, retrieves live data, and owns user data handling.

> **Release status:** Public v1.0. Evaluate on your own data, workflows, safety requirements, and target serving configuration before production deployment.

<p align="center"><img src="assets/architecture.svg" alt="Cortex 8B architecture overview" width="100%"/></p>

## IR-ready introduction

**English.** Keural Cortex is a locally deployable AI foundation-model capability built for Korean-English enterprise interaction. It combines efficient 8B-scale inference, controllable OpenAI-compatible serving, and structured tool-call generation so that Keural can connect users to approved enterprise workflows while retaining application-level control of data, permissions, and execution.

**한국어.** Keural Cortex는 한국어·영어 기반의 엔터프라이즈 AI 상호작용을 위해 설계된 로컬 배포형 파운데이션 모델 역량입니다. 8B 규모의 효율적인 추론, OpenAI 호환 서빙, 구조화된 Tool Call 생성을 결합하여 Keural이 승인된 업무 워크플로와 연동할 수 있도록 지원합니다. 데이터·권한·실행 통제는 모델이 아닌 Keural 애플리케이션 계층에서 관리합니다.

## Key strengths

| Strength | What it enables |
|---|---|
| **Local-first deployment** | On-premise or customer-controlled serving patterns; the application controls networking, credentials, access, and retention. |
| **Korean-English interaction** | Direct bilingual chat behavior for Keural user experiences. |
| **Structured tool calls** | Generates OpenAI-compatible calls for `search_web`, `fetch_web_urls`, `retrieve_documents`, and `ask_clarification` when those tools are provided. |
| **Agent-ready architecture** | Separates model decision-making from tool execution, allowing the product layer to apply authorization, auditing, retrieval, and real-time data policies. |
| **Long-context design** | Configuration supports a 65,536-token maximum position length. Serving limits should be set according to available GPU memory and workload. |
| **Efficient serving** | Tested with vLLM using an OpenAI-compatible `/v1/chat/completions` interface. |

## Version policy

Keural Cortex uses a two-track version policy:

- **Development versions** progress with each internal training milestone: `v1.0 → v1.1 → v1.2 → … → v1.5`.
- **Public versions** are released only after an internal version is validated as stable. This initial Hugging Face publication is **v1.0**; a later validated internal milestone may be published as a public version such as **v1.5**.

<p align="center"><img src="assets/deployment.svg" alt="Private local deployment pattern" width="100%"/></p>

## Model details

| Item | Value |
|---|---|
| Architecture | Decoder-only transformer language model |
| Transformer layers | 36 |
| Hidden size | 4,096 |
| Attention heads / KV heads | 32 / 8 |
| Vocabulary size | 151,936 |
| Maximum position length | 65,536 tokens |
| Weights | BF16 SafeTensors, ~16 GB |
| Alignment path | Continued training, supervised instruction tuning, preference optimization, and Keural agent/tool-contract tuning |

## Verified serving smoke tests

The following were verified through vLLM's OpenAI-compatible API in the release environment:

- Plain Korean chat returned a direct answer without emitting a tool call.
- A current-information request generated a structured `search_web` call.
- An exhaustive document request generated `retrieve_documents` with `exhaustive: true`.
- An underspecified revision request generated `ask_clarification` with a question and checklist.

These are smoke tests, not a substitute for domain-specific benchmarking or safety evaluation.

## Quick start: vLLM

```bash
vllm serve <MODEL_PATH> \
  --served-model-name keural-cortex-8b-v1.0 \
  --tool-call-parser hermes \
  --enable-auto-tool-choice
```

For text-only chat, send a normal OpenAI Chat Completions request **without** `tools` or `tool_choice`. For agent workflows, provide only the tools your application authorizes, validate all tool arguments server-side, and execute calls outside the model process.

## Example tool contract

```json
{
  "type": "function",
  "function": {
    "name": "retrieve_documents",
    "description": "Search content in the user's available documents.",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {"type": "string"},
        "file_ids": {"type": "array", "items": {"type": "string"}},
        "exhaustive": {"type": "boolean"}
      },
      "required": ["query"]
    }
  }
}
```

## Limitations and responsible use

- Outputs can be inaccurate, incomplete, or inconsistent across prompts and serving configurations. Verify important information.
- The model has no inherent live-web access, private-document access, or authority to take external actions. These capabilities must be supplied and governed by the host application.
- Tool calls are model suggestions. Validate schemas, authorization, user intent, and side effects before execution.
- Do not use this preview as the sole basis for high-stakes medical, legal, financial, safety, employment, credit, or access-control decisions.

## Certification, license, and attribution

**Certification note.** Keural Cortex Foundation Model (8B) v1.0 is based on Qwen3-8B-Base and is released under Apache-2.0. Please retain applicable upstream notices and comply with the license terms.

## Citation

```bibtex
@misc{keural-cortex-8b-v1.0,
  title={Keural Cortex Foundation Model (8B) — v1.0},
  author={MKD AI},
  year={2026},
  publisher={Hugging Face}
}
```
