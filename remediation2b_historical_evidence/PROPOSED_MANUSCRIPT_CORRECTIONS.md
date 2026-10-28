# Proposed manuscript corrections

No manuscript source was overwritten. The following are author-review proposals only.

| Current claim type | Evidence problem | Proposed wording | Impact/approval |
|---|---|---|---|
| Historical prompt-zeroisation caused 29%/69% reductions | Historical patch malformed and executable identity absent | “The retained baseline and sanitised records report descriptive reductions of 29.09% in canary-copy count and 69.06% in a recorded cleartext-volume field; causal attribution to the historical implementation is unresolved.” | Downgrades causal claim; author approval required |
| GGUF campaign establishes parser safety | No per-input corpus/fuzz raw results or binary linkage | “No failure was reported in the explored historical corpus and fuzz run; the retained artifacts do not support universal parser-safety claims.” | Narrows negative result; author approval required |
| LM Studio records prompts by default | Evidence is a tested configuration, not a clean-install default | “In the evaluated LM Studio configuration with `logSensitiveData` enabled, canary-tagged prompt data were reported in plaintext log artifacts.” | Removes default inference; author approval required |
| AUC = 1.000 is independently validated | TTFT vectors and AUC script absent | “The historical record reports AUC = 1.000 under the evaluated conditions; the raw TTFT/AUC chain was not retained for independent recomputation.” | Central timing downgrade; author approval required |
| API keys provide distinct tenants for the slot test | Harness records keys but not a full principal/resource authorization manifest | “The configured clients used different valid credentials; the retained rows demonstrate cross-client state transfer under that configuration.” | Avoids overclaiming tenant identity; author approval required |
| Remediation 2 validates the historical mitigation | Remediation 2 is a new pinned-source implementation without model-backed inference | “Remediation 2 validates a newly engineered buffer-cleanup implementation at source/build/control-test level; it does not reproduce the historical forensic result.” | Separates engineering from historical science; author approval required |
