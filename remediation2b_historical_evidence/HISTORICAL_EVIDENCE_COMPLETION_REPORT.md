# Historical evidence completion report

## Final classification

**B: maximum defensible historical verification completed; full experimental reproduction remains unavailable.**

## Answers to the requested final questions

1. **Artifacts inspected:** 3,277 files under `Runs/`, 14 under `remediation1/`, 277 under the revised manuscript directory, and the Remediation 2 tree; 7,585 JSON files parsed successfully and 292 JSON parse errors recorded. New Remediation 2 source/build internals were not treated as historical observations.
2. **Original result files found:** two memory aggregate JSONs; the four-model slot-transfer JSON; four 50-trial cross-tenant extraction JSONs; patched/unpatched KV benchmark vectors; telemetry directories and summaries; model-digest metadata; scripts and reports.
3. **Independent calculations verified:** memory aggregate sums/rates/reductions; 200/200 transfer; 126/200 continuation; per-model continuation counts; Wilson intervals; and patched/unpatched KV benchmark means and descriptive differences.
4. **Machine-generated support:** strongest for memory aggregates, slot/extraction rows, KV vectors, and telemetry captures. RQ1 headline fuzz counts and timing AUC lack identifiable raw chains.
5. **Summary-dependent claims:** GGUF headline campaign, LM Studio plaintext-log persistence, historical sanitisation causality, and timing AUC.
6. **What Sharma checked:** Wilson/percentage arithmetic, consistency of headline results, public source and documentation, security policy, disclosure artifacts, configuration prerequisites, statistical and scope limitations. He did not document an independent rebuild or experiment.
7. **External reproduction:** none evidenced. The Korean article is a secondary technical summary, not an execution record.
8. **New source/run metadata:** no historical checkout, executable hash, startup manifest, or valid historical prompt patch. Remediation 2's pinned commit is new engineering evidence only.
9. **Timing data:** no original cached/uncached TTFT vectors or AUC script located.
10. **RQ grades:** RQ1 E4; RQ2 aggregate arithmetic E1 with causal attribution unresolved; RQ3 mixed E4 for LM Studio logging and E2 for bounded Ollama monitoring; RQ4 slot/continuation E1 from retained rows and timing E4.
11. **Claims needing revision:** universal parser safety, default LM Studio logging, causal historical patch attribution, fully validated AUC, WAN/general deployment scope, and API-key-to-tenant equivalence.
12. **No-new-model strategy:** Strategy C, or strict Strategy B, is scientifically defensible if the manuscript clearly separates retained archival observations from verified contributions. Full-study submission readiness is not established.
13. **Blockers:** historical source-to-binary linkage, valid historical prompt patch, raw memory-acquisition metadata, raw TTFT/AUC data, and author-approved claim restructuring.
14. **Most efficient next action:** decide whether to narrow the manuscript around E1/E2 records and archival framing. If timing remains central, recover the TTFT vectors and analysis script; if mitigation causality remains central, recover or rerun the historical implementation with a complete provenance chain.

## Preservation statement

No raw dataset, manuscript source, Remediation 1 report, or Remediation 2 engineering artifact was overwritten. The independent analysis script and generated JSON are under this directory. Exact consumed-file hashes are in `analysis/independent_reanalysis.json`.
