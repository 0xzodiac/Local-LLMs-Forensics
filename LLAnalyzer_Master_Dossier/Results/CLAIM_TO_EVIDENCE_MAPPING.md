# Claim-to-evidence mapping

| Claim type | Exact safe claim | Evidence class | Local source | Where to qualify |
|---|---|---|---|---|
| B1 negative | No relevant parser failure observed in the explored corpus/campaign | Historical/source-supported | `GGUF_*` reports; RQ1 dossier | RQ1 opening and limitations |
| B2 residual existence | Prompt canaries remained recoverable under authorized F acquisition | Raw aggregate plus report | `leak_blast_radius_*.json` | Threat model and RQ2.1 |
| B2 aggregate reduction | Recorded copies and recorded matching-region KB fell 110->78 and 10834->3352 | Independently recomputed arithmetic | `analysis/independent_reanalysis.json` | RQ2.3 table caption |
| B2 causal mitigation | Sanitised condition is consistent with lower recorded exposure | Incomplete historical attribution | Remediation 1/2 and provenance audit | Do not say causal historical patch effect is fully proven |
| B2 KV mechanism | 56/56 targeted cells were nonzero immediately before the instrumented zero write | Direct mechanism report | `KV_CACHE_PATCH_REPORT.md` | Separate from literal-canary scan |
| B3 LM Studio | Tested sensitive logging setting persisted canaries in wrapper logs; disabling plus restart stopped new tested canary | Configuration-specific historical report | `MITIGATION_TEST_REPORT.md` | Never generalize to all versions/defaults |
| B3 Ollama | No canary observed in monitored 205-session capture scope | Bounded machine-generated monitoring | telemetry directories | State channels/files/version boundary |
| B4 direct transfer | Saved state transferred in 200/200 evaluated trials | Retained per-trial raw record | slot JSON/extraction files | Distinguish API authentication from authorization |
| B4 continuation | Secret appeared in 126/200 model continuations | Retained per-trial raw record | four extraction files | Separate from direct transfer; report model rates |
| B4 timing | Historical report states AUC=1.000 under evaluated conditions | Summary-only | timing figure/report | No independent AUC claim or WAN generalization |
| Full replication | Dr. Ikram reports complete cross-machine rerun with matching results | Author-reported collaboration | `IKRAM_*` audit files | No exact rerun values or artifact-verified wording |
| External review | Sharma recomputed arithmetic and inspected documentation/policy | Secondary expert review | `EXTERNAL_EXPERT_REVIEW_AUDIT.md` | Not experimental reproduction |

## Writing decision

Every paragraph containing a number should be traceable to one row in this
mapping and the master catalog. If a sentence combines an observation and a
causal explanation, split it: first state the measurement, then state the
mechanism evidence and its limitation.

