# Cortex v1 versus Qwen3-8B-Base - prepared, not started

Only these pinned model IDs are allowed; the runner rejects every other checkpoint:
- mkd-hossain/Keural-Cortex-8B-v1.0
- Qwen/Qwen3-8B-Base

31 jobs cover all seven categories. All results will appear in one comparison table
with Cortex, Qwen3-8B-Base, difference, sample count and a short protocol note.
No new model download is required. No Qwen Instruct checkpoint is referenced.

Standard tasks use identical completion prompts and a corrected explicit 512-token
generation cap on both models. Custom chat/tools/reasoning and long-context probes
use the same plain role transcript and tool instructions on both models. This avoids
requiring a chat template that the Base checkpoint may not have. It measures behavior
under this common format; it does not claim to measure Cortex at its optimal native
serving configuration. Thinking-math sampling and output budgets remain matched.

The 64K Cortex result is included in the same table, clearly marked as an unmatched
extension, rather than counted as a win over the Base model's 32K configuration.

Resource policy: adaptive standard-task batches, maximum 32; generation batches 8.
Custom diagnostics remain single-stream; long-context jobs run alone to avoid memory
exhaustion. Runtime tuning may be adjusted only without changing questions or scores.
More allocated memory alone is not a speed optimization.

This service file is staged only. It is not installed, enabled or started. Activating
the new run and single-table dashboard requires the user's next instruction. Original
completed artifacts and dashboard remain available throughout preparation.
