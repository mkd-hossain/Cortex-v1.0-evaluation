# Launch recovery checkpoint

The 39-job scored queue has **not started**. Dataset freezing and both corrected stopping calibrations completed; matched raw-completion harness preflights passed for both models. The original math preflight triggered the harness's oversized full-window automatic batch probe, causing severe host memory pressure. Remote stop was requested, but SSH and dashboard access became unavailable.

After Spark restarts:

1. Check SSH, GPU response and memory. Check no `standard.py`, `behavior.py` or launcher process remains from the failed preflight. Preserve all calibration and pilot artifacts.
2. Upload the latest source from this directory before retrying. In particular, `standard.py` must use **fixed batch 1 for GSM8K** and `launch_verified.py` must use the separate `math-preflight-v3` output directory. Do not reuse the unsafe auto-generation probe.
3. Preserve `/home/<user>/cortex-benchmark/full-budget/frozen-standard`, both original calibration directories and failed math preflight. The data manifest is frozen to 50 samples per standard leaf. Never overwrite those with a fresh latest-dataset selection silently.
4. Run the six regression tests with the benchmark environment, then rerun `launch_verified.py` as a background user service. It reuses completed classification preflights, performs corrected math preflight, and only deploys/starts the scored queue on success.
5. Verify `runs-full-budget-v1/state.json`, actual GPU work and both dashboard endpoints. The deadline remains **2026-11-10 11:48:14 KST**. If expired, obtain a newly authorized budget rather than resetting the clock silently.
6. Push the exact source, frozen manifest, preflight evidence and in-progress run status to GitHub after verified launch. Do not describe recovery/preflight output as full benchmark results.

The prior 48-response smoke and all older pilots remain saved under their separate run directories. The public GitHub repository is `mkd-hossain/Cortex-v1.0-evaluation`.
