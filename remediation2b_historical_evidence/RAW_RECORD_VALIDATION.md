# Raw-record validation

## Memory aggregates

The validator parsed both retained JSON objects, checked required fields and types, recomputed each per-tenant sum, counted positive tenants, and recomputed recovery rates.

| Condition | Tenants | Recovered | Copies recomputed | Recorded KB | Structural checks |
|---|---:|---:|---:|---:|---|
| Baseline | 12 | 11 | 110 | 10,834 | Pass |
| Sanitised | 12 | 11 | 78 | 3,352 | Pass |

Recomputed reductions are 29.090909% in copies and 69.060366% in the recorded KB field. Both recovery rates are 11/12 = 0.9166667. The JSON stores the KB aggregate but not the memory-region list, raw bytes, match offsets, or acquisition trace; therefore the KB values are retained observations, not independently byte-recomputed measurements.

## Slot and continuation records

`slot_exploit_ALL4_audit1.json` contains 4 models × 50 rows. Every row is `ok` and `exploit_confirmed`, so direct protocol-level transfer is independently recomputed as 200/200.

The four 2026-07-04 extraction files contain 50 rows per model, no duplicate trial IDs, and no duplicate secret values. Recomputed totals are:

| Channel | Count | N | Rate | Wilson 95% interval |
|---|---:|---:|---:|---:|
| Transfer confirmed | 200 | 200 | 1.00 | [0.9812, 1.0000] |
| KV continuation hit | 126 | 200 | 0.63 | [0.5612, 0.6939] |
| Memory channel hit | 200 | 200 | 1.00 | [0.9812, 1.0000] |
| Either channel hit | 200 | 200 | 1.00 | [0.9812, 1.0000] |

The continuation result is model-mediated and distinct from the direct state-transfer result. The rows do not establish independent authorization principals beyond the harness's client/key labels.

## Telemetry and persistence records

The retained telemetry directories contain 205 valid Ollama sessions with canary-generation records and one incomplete Ollama directory without a canary trigger. Six LM Studio hook summaries and six Ollama summaries are machine-readable envelopes; the remaining Ollama sessions retain lower-level packet/trigger/idle artifacts without the same summary envelope. The summaries report no canary in captured egress. This supports a bounded observation about the captured sessions, not a universal claim about encrypted payloads, later versions, or unexamined persistence locations.

The LM Studio plaintext server-log file itself is not in the project. Its presence is supported by historical reports and probe references, not by a fresh scan here.

## GGUF and timing raw-data status

The workspace contains GGUF scripts and hand-written reports, but no identifiable machine-generated 80-case, 21-file, or 24-hour fuzz result table with per-input outcomes and sanitizer logs. It contains timing-related manuscript figures and unrelated latency vectors, but no cached/uncached TTFT vector or original AUC script. Neither absence is filled with synthetic records.
