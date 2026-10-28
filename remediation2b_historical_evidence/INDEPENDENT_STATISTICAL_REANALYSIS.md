# Independent statistical reanalysis

All results below come from `scripts/independent_reanalysis.py` and its generated JSON output.

## Recomputed binary quantities

- Memory copies: 110 baseline versus 78 sanitised; reduction 29.090909%.
- Recorded memory volume: 10,834 KB versus 3,352 KB; reduction 69.060366%.
- Recovery: 11/12 in both retained memory conditions.
- Direct state transfer: 200/200, Wilson 95% interval [0.9812, 1.0000].
- Model-mediated continuation: 126/200 = 63.0%, Wilson 95% interval [0.5612, 0.6939].
- Per-model continuation counts from the retained records: Gemma 50/50, Qwen 50/50, Nemotron 25/50, and Phi 1/50.

The Wilson intervals use the usual independent Bernoulli/binomial approximation. The sequential-slot design and shared server mean that independence is a modeling assumption, not an established property of the experiment.

## Retained KV benchmark vectors

The patched/unpatched vectors contain n=50 per model and their stored means are reproduced exactly by the independent calculation. Descriptive mean changes are:

| Model | Patched mean | Unpatched mean | Change | Relative change |
|---|---:|---:|---:|---:|
| Gemma | 2.907970 s | 2.890630 s | +0.017341 s | +0.599887% |
| Nemotron | 2.822480 s | 2.838131 s | -0.015651 s | -0.551456% |
| Qwen | 4.704970 s | 4.692374 s | +0.012597 s | +0.268449% |
| Phi | 8.422246 s | 8.402716 s | +0.019530 s | +0.232427% |

The script also reports descriptive Welch normal-approximation intervals. They cross zero for all four models. This is not an equivalence test and is not the manuscript's missing cached-versus-uncached TTFT experiment.

## What cannot be recomputed

The manuscript AUC = 1.000 claim cannot be recomputed. No per-request cached/uncached TTFT observations, request-order manifest, or original AUC script was found. Repeating AUC in an external article or manuscript does not create an independent measurement. No latency vectors were fabricated.
