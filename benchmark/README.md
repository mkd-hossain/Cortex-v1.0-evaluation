# Cortex benchmark controller

## Redesigned live dashboards

Public view: https://cortex-benchmark-spark.tail73fbf3.ts.net/

Private operator view: https://cortex-benchmark-spark.tail73fbf3.ts.net:8443/

The controller remains on loopback 8765. Separate dashboard processes serve public
read-only traffic on 8766 and private controls on 8767. Redeploying those web
processes must not restart `cortex-benchmark.service`. Benchmark state and model
processes remain independent. Frontend assets are `dashboard.html`, `dashboard.css`,
and `dashboard.js`; animations respect reduced-motion preferences.

The results adapter reads saved per-task artifacts and pairs matching subtasks.
Raw completion, native assistant and long-context tracks remain separate. PDF
download is enabled and served only after every job finishes successfully. The
report includes requested settings and detected generation-budget override warnings.
Layout QA uses a clearly marked partial snapshot that is not published as a final
report. The public server rejects all control requests.

Status: prepared locally; not deployed, no benchmark scores collected yet.

## Evaluation contract

Compare pinned Keural v1 and Qwen3-8B-Base revisions in BF16, using identical
completion prompts without chat templates. Fixed seed: `0,1234,1234,1234`.
Few-shot counts are explicit in each plan. Full plans use complete test splits;
the pilot uses only 20 examples per task and cannot support published claims.
The harness task definitions, dataset revisions, environment and rendered prompts
must be inspected and frozen on Spark before the full run. Do not use the older
four-H200 runner unchanged. Knowledge results do not establish chat/tool quality.

## Setup on Spark

Use a dedicated, GPU-compatible Linux Python environment. Install and pin a tested
lm-evaluation-harness revision after checking Spark's CUDA/PyTorch stack; do not
replace system PyTorch blindly. Save `pip freeze`, hardware info and harness Git
revision with each run. Run `python prepare_plan.py` after obtaining model metadata.

Pilot launch (no work begins until Start is clicked):

```sh
python controller.py --plan pilot.json --data runs-pilot
```

Full suite uses a different state directory:

```sh
python controller.py --plan plan.json --data runs-full
```

After edits to a plan, use a new run directory: persisted state is authoritative.
Each job saves its exact command, logs, sample predictions and harness results.
Only exit code zero with a results file marks a task completed. Failures stop
the queue. An operator must diagnose a failed task before explicitly resetting
its status to pending while the controller is stopped.

## Pause/resume semantics

Linux process-group SIGSTOP pauses the active evaluator, including child processes;
SIGCONT resumes it. This retains GPU allocation and does not free memory for other
work. Closing the browser does not stop the controller. Use a systemd service with
KillMode=control-group for unattended deployment. A restart preserves completed
tasks and requeues the interrupted task; partial-task progress is not durable.
Power loss/SIGKILL without service process-group cleanup must be checked for orphan
evaluators before restarting. Only one controller can hold a run directory lock.

## Remote access

The dashboard binds only to 127.0.0.1; it has no built-in user authentication.
For the laptop on the local network, forward it through SSH:

```sh
ssh -N -L 8765:127.0.0.1:8765 hct-keural@SPARK_LAN_IP
```

Open http://127.0.0.1:8765 on the laptop. Access from a different network needs
an authenticated private network such as Tailscale and a private HTTPS endpoint,
or a cloud gateway protected by identity-aware access. A public tunnel without
authentication is unsuitable for this controller. Cloud connection is not yet
configured; a local URL is not a remote-access deployment.

## Reporting

Report individual benchmark scores, paired differences and uncertainty. Do not
average parent groups together with their child tasks. Audit training overlap.
Long-context and held-out application/tool tests require separate protocols;
they are not implemented by this initial core-suite plan.
