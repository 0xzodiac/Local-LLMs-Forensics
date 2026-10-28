# Master results catalog

This catalog is the writing reference for every material quantitative or
configuration-specific result retained in the current manuscript. “Reported”
does not mean “independently recomputed.” The evidence column is the authority
for wording.

| ID | Experiment / RQ | Model | Trials / scale | Condition and measurement | Result | Evidence | Source path | Interpretation and limitation | Manuscript target |
|---|---|---|---:|---|---|---|---|---|---|
| R1-1 | Structured GGUF battery / RQ1 | GGUF corpus | 80 cases | Malformed metadata, dimensions, offsets, and headers; loader outcome | No relevant failure reported | Historical/source-supported | `Runs/experiments/reports/GGUF_SURGICAL_REPORT.md`; `T-IFS.tex` RQ1 | Explored-state negative only; corpus manifest not retained in local audit | Evaluation RQ1; Table `tab:model_boundary_results` |
| R1-2 | Structural-header corpus / RQ1 | GGUF corpus | 21 files | C++ and Python parser behavior | No relevant failure reported | Historical/source-supported | `GGUF_CROSS_MODEL_REPORT.md`; supplement model-file corpus | Do not pool with later 96-test exploratory reports | Evaluation RQ1; supplement |
| R1-3 | Coverage-guided fuzzing / RQ1 | Parser | >1.2e7 executions / 24 h | AFL++ with ASan/UBSan as reported | No parser crash, sanitizer violation, or malformed load reported | Historical report | `T-IFS.tex`; `GGUF_*` reports | No complete campaign manifest or executable hash | Evaluation RQ1; scale table |
| R2-1 | Post-inference residue / RQ2 | Four-family study | Sequential tenants | UUID canary in writable process-memory regions | Canaries recoverable after inference | Machine-generated aggregate plus reanalysis | `Runs/logs/leak_blast_radius_*.json`; `RQ2_EVIDENCE.md` | Authorized F path; not arbitrary same-UID access | Evaluation RQ2.1 |
| R2-2 | Historical-client recovery / RQ2 | Four-family aggregate | 12 tenants | One long-lived server and post-sequence acquisition | 11/12 baseline; 11/12 sanitised | Raw-record-backed calculation | Same as R2-1 | Tenant outcome unchanged after sanitisation | Evaluation RQ2.1/RQ2.3 |
| R2-3 | Residual copies / RQ2 | Aggregate | 12 tenants | Baseline vs sanitised recorded matching copies | 110 -> 78; 29.090909% reduction | Raw-record-backed calculation | Same as R2-1 | Count of recorded matching copies, not unique plaintext objects | `tab:blast` |
| R2-4 | Recorded matching-region volume / RQ2 | Aggregate | 12 tenants | Baseline vs sanitised recorded KB | 10,834 -> 3,352 KB; 69.060366% reduction | Raw-record-backed calculation | Same as R2-1 | Recorded matching-region metric, not literal secret-byte volume | `tab:blast` |
| R2-5 | KV cell mechanism / RQ2 | Phi-4 configuration | 56 cells | Direct read immediately before zero write | 56/56 cells nonzero | Mechanism report | `Runs/experiments/reports/KV_CACHE_PATCH_REPORT.md` | New patch mechanism evidence; not historical causal proof | RQ2.2/RQ2.3; supplement |
| R2-6 | KV overhead / RQ2 | Gemma, Nemotron, Qwen, Phi | 50/model/condition | Patched vs unpatched latency vectors | Mean differences +0.01734, -0.01565, +0.01260, +0.01953 s respectively | Raw-vector-backed descriptive result | `Runs/logs/n50_audit/kv_overhead_ALL_audit1.json` | Descriptive intervals cross zero; not equivalence and not timing AUC | `tab:overhead` |
| R2-7 | GPU-assisted host residue / RQ2 | Qwen3.5 partial offload | Configuration-specific | Host scan during/after GPU-assisted inference | Host residue persists | Source/report-supported | `T-IFS.tex` RQ2.4; GPU reports | No device-memory access or universal GPU claim | RQ2.4; `tab:vram` |
| R3-1 | LM Studio persistence / RQ3 | Nemotron configuration | 10 baseline canaries plus mitigation check | `logSensitiveData=true`, then false + restart | Baseline canaries found in logs; post-change canary not found | Configuration-specific historical report | `Runs/experiments/reports/MITIGATION_TEST_REPORT.md` | Original plaintext log absent locally; not a product-wide default | Evaluation RQ3 |
| R3-2 | LM Studio log retention / RQ3 | Same | 2 log files in report | Existing logs and TTL setting | Historical logs remain; `ttlDays=0` does not control server logs | Source/document-supported | `MITIGATION_TEST_REPORT.md` | File rotation and prediction history are different mechanisms | RQ3 discussion |
| R3-3 | Ollama monitored egress / RQ3 | Four-model session set | 205 valid sessions + 1 incomplete | Packet, trigger, idle, and canary analysis | No captured canary in monitored external egress/artifacts | Retained bounded telemetry | `Runs/TELEMETRY_RUN_*`; `TELEMETRY_FINDINGS_OLLAMA.md` | Negative result is channel/version/observation bounded | RQ3 |
| R4-1 | Direct saved-slot transfer / RQ4 | Gemma, Qwen, Nemotron, Phi | 50/model; 200 pooled | Victim save, second-client restore | 200/200 | Raw-record-backed calculation | `Runs/logs/n50_audit/slot_exploit_ALL4_audit1.json` | Protocol transfer; API keys do not prove tenant principals | Evaluation RQ4 |
| R4-2 | Model continuation / RQ4 | Gemma | 50 | Restored state, greedy continuation | 50/50 | Raw-record-backed calculation | `cross_tenant_extract_gemma4_20260704_n50.json` | Model-mediated output channel | `tab:scope` / RQ4 |
| R4-3 | Model continuation / RQ4 | Qwen | 50 | Same | 50/50 | Raw-record-backed calculation | `cross_tenant_extract_qwen35_20260704_n50.json` | Same | RQ4 |
| R4-4 | Model continuation / RQ4 | Nemotron | 50 | Same | 25/50 | Raw-record-backed calculation | `cross_tenant_extract_nemotron_20260704_n50.json` | Model/stopping dependence | RQ4 |
| R4-5 | Model continuation / RQ4 | Phi-4 | 50 | Same | 1/50 | Raw-record-backed calculation | `cross_tenant_extract_phi4_20260704_phi4_n50.json` | Model/stopping dependence; do not replace with older inconsistent counts | RQ4 |
| R4-6 | Pooled continuation / RQ4 | Four models | 200 | Same | 126/200 = 63% | Raw-record-backed calculation | Four files above | Wilson interval; sequential/shared-server caveat | Evaluation RQ4 |
| R4-7 | Timing side channel / RQ4 | Four models | Reported 100/model | Cached vs uncached TTFT | AUC=1.000 reported | Historical report | `figures/timing_auc_decay.pdf/.png`; manuscript timing paragraph | TTFT vectors/order manifest/AUC script absent; no independent recomputation | RQ4; figure |
| R5-1 | Collaborative full rerun | Complete framework | Not supplied | Separate Ikram research server | Reported matching original results | Author-reported replication | `remediation2b_historical_evidence/IKRAM_*` | No server artifacts inspected; not third-party reproduction | Reproducibility statement |

## Negative and model-specific results to retain

The rewrite must not retain only the strongest positive numbers. It should
retain the RQ1 negative result, the Ollama negative observation, the unchanged
11/12 tenant recovery outcome after sanitisation, the model-specific continuation
rates, and the distinction between the KV benchmark and the missing timing
dataset. Those results constrain interpretation and show that LLAnalyzer is a
measurement framework rather than a collection of predetermined failures.

