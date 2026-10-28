# Verified statistics and calculations

All calculations below are reproduced in
`remediation2b_historical_evidence/scripts/independent_reanalysis.py` and its
JSON output. Source files are read-only.

## Memory aggregate arithmetic

| Quantity | Formula | Value |
|---|---|---:|
| Baseline copy total | sum retained baseline tenant map | 110 |
| Sanitised copy total | sum retained sanitised tenant map | 78 |
| Copy reduction | `(110-78)/110 * 100` | 29.090909% |
| Baseline recorded KB | retained field | 10,834 |
| Sanitised recorded KB | retained field | 3,352 |
| Recorded-KB reduction | `(10834-3352)/10834 * 100` | 69.060366% |
| Baseline recovery | recovered tenants / 12 | 11/12 = 0.916667 |
| Sanitised recovery | recovered tenants / 12 | 11/12 = 0.916667 |

The calculation validates the stored fields and per-tenant maps. It does not
reconstruct raw memory regions, offsets, physical pages, or the validity of the
historical acquisition path. “Recorded KB” must remain that exact phrase in the
paper.

## Saved-slot and continuation arithmetic

| Outcome | x | n | Proportion | 95% Wilson interval |
|---|---:|---:|---:|---:|
| Direct state transfer | 200 | 200 | 1.000000 | [0.9811547, 1.0000000] |
| Model-mediated continuation | 126 | 200 | 0.630000 | [0.5612263, 0.6938739] |

Per-model continuation:

| Model | Hits | n | Proportion |
|---|---:|---:|---:|
| Gemma | 50 | 50 | 1.00 |
| Qwen | 50 | 50 | 1.00 |
| Nemotron | 25 | 50 | 0.50 |
| Phi-4 | 1 | 50 | 0.02 |

The Wilson intervals describe observed trial proportions. They do not erase the
shared-server, sequential-order, credential-principal, or model-stopping
assumptions.

## KV benchmark descriptive checks

The retained KV overhead JSON contains 50 latencies per model and condition; all
stored mean fields exactly match recomputation. Patched minus unpatched means:

| Model | Unpatched mean (s) | Patched mean (s) | Difference (s) | Relative difference |
|---|---:|---:|---:|---:|
| Gemma | 2.89062994 | 2.90797044 | +0.01734050 | +0.599887% |
| Nemotron | 2.83813105 | 2.82248000 | -0.01565104 | -0.551456% |
| Qwen | 4.69237354 | 4.70497018 | +0.01259664 | +0.268449% |
| Phi-4 | 8.40271630 | 8.42224649 | +0.01953020 | +0.232427% |

The descriptive Welch-normal intervals for all four differences cross zero.
This is not a formal equivalence test, and these data do not support the
manuscript's cached-versus-uncached timing AUC.

## Deterministic mechanism record

The KV patch report records 56/56 targeted cells with nonzero data immediately
before the zero write. This supports the mechanism-level statement that the
instrumented patch encountered live data and overwrote the targeted cell path.
It does not establish that the historical prompt patch, whose retained diff is
malformed, caused the aggregate memory comparison.

## Non-recomputed results

- RQ1 campaign totals and per-input outcomes lack a complete machine-generated
  local chain.
- LM Studio's original plaintext server-log file is absent.
- The original cached/uncached TTFT vectors, order manifest, and AUC script are
  absent.
- Dr. Ikram's rerun numbers and server records are absent.

