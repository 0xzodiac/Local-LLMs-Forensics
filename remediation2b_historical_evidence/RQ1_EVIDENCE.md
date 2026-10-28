# RQ1 evidence: GGUF integrity

## Finding

The claimed 80-case malformed-input battery, 21-file malformed-header corpus, and 24-hour campaign with more than 12 million executions are not independently recomputable from an identifiable machine-generated result table in the retained workspace.

## Retained material

`Runs/scripts/gguf-fuzzer.py` and related attack scripts are program sources. `Runs/experiments/reports/GGUF_SURGICAL_REPORT.md`, `GGUF_CROSS_MODEL_REPORT.md`, `GGUF_WEAPONIZATION_EXPLORATION.md`, and related reports are hand-written summaries. They report additional 96-test/weaponization observations, including crashes and clean rejections, which are not the same as a retained per-input 80/21/24-hour record and must not be silently pooled.

No machine-generated corpus manifest, per-input exit-status table, sanitizer log, coverage record, or binary hash was identified for the headline RQ1 campaign. A script or report containing numbers is not execution evidence.

## Grade

**E4 for the headline campaign:** reported in manuscript and summaries without sufficient surviving raw records. Some code-level claims are **E3** source inspection. The bounded wording “no failure observed in the explored state space” is not independently executable from the retained artifacts here, and it must not become a universal parser-safety claim.
