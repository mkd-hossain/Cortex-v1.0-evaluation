# Recorded evaluation source

These files preserve the final evaluation implementation and configuration. The static dashboard in `../docs/` is independent of this GPU runner.

Start with `plan.json`, `frozen-standard-manifest.json`, `environment-provenance.json`, `requirements-recorded.txt`, `base_protocol.py`, `standard.py`, and `behavior.py`. Dataset source references and code manifests record provenance. The final records live in `../results/run/`; historical manifests describe files at inference time, while the root `SHA256SUMS` describes this published archive.

Reproduction requires a compatible Linux CUDA environment, the exact pinned model revisions, recorded dependency versions, and the frozen dataset selections. Inspect `standard.py --help`, `behavior.py --help` and `freeze_standard.py --help` in that isolated environment before executing. Rehydrate the datasets using the recorded dataset references and frozen sample indices/fingerprints; do not silently substitute newer datasets or model revisions. Cached dataset binaries and model weights are not distributed here.

Some orchestration scripts preserve the original Spark directory layout and must be configured for a new machine. They are evidence, not an automatic installer. Do not run controller/deployment helpers against an existing evaluation unless you intend to launch or manage GPU jobs.

The corrected rotary configuration and explicit generation settings are integral to reproduction. See `../methodology/AUDIT.md`. Standard completion prompts are matched; deployment fixtures use Cortex's native chat serialization and Base's plain transcript. Synthetic cases are development fixtures, not an independent holdout. The initial design document records proposed goals and must not be read as proof that every proposed acceptance condition was met.

To regenerate the readable figures, install matplotlib and numpy and run `python tools/chart_model_card.py` from the repository root. These figures use only the saved final metrics.
