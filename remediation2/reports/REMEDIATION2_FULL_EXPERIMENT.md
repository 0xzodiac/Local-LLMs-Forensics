# Remediation 2 full experiment

## Gate D verdict

The full C0/C1/C2/C3 comparison was not executed. The resource gate stopped the campaign before any model download or multi-hour run: no model weights are available, disk free space was approximately 5.7 GiB at final manifest generation, and the user request did not authorize a large model download or paid compute.

Consequently there are no new recovered-occurrence counts, recovered-region volumes, historical-client recovery rates, independent process repetitions, or latency vectors. `results/full/` is intentionally empty of scientific result records. The control records in `results/pilot/` must not be relabeled as a full experiment.

The exact continuation is: obtain an authorized compatible GGUF model and its SHA-256, record the model manifest, run each condition from an independent clean server process, use fresh UUID canaries, perform the permitted parent-child acquisition procedure without changing Yama, retain raw region metadata and offsets, and then rerun `scripts/analyze_memory_results.py` and the performance analysis. The run must stop if acquisition or model provenance fails.
