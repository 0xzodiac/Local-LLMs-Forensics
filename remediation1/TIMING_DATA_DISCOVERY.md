# Timing-data discovery

## Search scope

The targeted search covered `Runs/`, `from-scratch/`, the manuscript directory, named archives, repository Git objects, and accessible research directories. It checked machine-readable files and filenames for TTFT, time-to-first-token, first-token, prompt-evaluation, cached/uncached, ROC/AUC, and prefix-cache fields, and searched for analysis scripts associated with the rendered timing figure.

## Result

No raw per-request TTFT vector, paired cached/uncached timing table, ROC/AUC input, or timing analysis script was found. Four CSV files under `Runs/logs/` are unrelated phase/track records. Some cross-tenant JSON records contain `tokens_cached`, but they do not contain paired TTFT measurements or the AUC calculation inputs. The only timing-specific packaged artifacts are `LLAnalyzer-revised-10point/figures/timing_auc_decay.pdf` and `.png`.

No timing campaign was started. No synthetic timing data were created. The reported AUC remains a manuscript-level reported value that cannot be independently recomputed from the retained artifacts in this session.

## Reproduction requirement

A future run must retain one row per request with request identity, cache condition, prompt/token configuration, TTFT, measurement timestamp, warm-up status, model/build identity, and the exact script that computes the curve and AUC. The result should be independently recomputable from those rows before any timing claim is upgraded.
