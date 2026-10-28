# Final evidence grading matrix

| Research question/claim | Grade | Strongest defensible interpretation | Main limitation |
|---|---|---|---|
| RQ1 malformed-input and fuzz campaign headline | E4 | Historical bounded negative result is reported | No per-input raw table, sanitizer log, coverage record, or binary identity |
| RQ2 baseline/sanitised aggregate arithmetic | E1 | 110→78 copies, 10,834→3,352 recorded KB, 11/12 in both records | Stored KB and acquisition validity cannot be independently reconstructed |
| RQ2 causal attribution to historical sanitisation patch | E4/E5 boundary | Records are consistent with a reported intervention difference | Historical prompt patch malformed; source/binary/run chain absent |
| RQ3 LM Studio plaintext logging | E4 | Configuration-specific persistence is reported | Original log absent; not a default or universal claim |
| RQ3 Ollama monitored egress/artifacts | E2 | No canary observed in retained bounded sessions/artifacts | Version, files examined, and encrypted contents are bounded |
| RQ4 slot transfer | E1 | 200/200 protocol-level cross-slot transfer in retained rows | Client-principal and deployment generalization limits |
| RQ4 model continuation | E1 | 126/200 retained model-mediated secret reproductions | Dependent sequential trials and model behavior are not authorization proof |
| RQ4 timing AUC | E4 | AUC is a manuscript-level historical report | No TTFT vectors or AUC procedure |

E1 means independently recomputed from identifiable original raw records; E2 means retained machine-generated aggregate/structured records; E3 means source/document inspection; E4 means summary-only; E5 means unsupported, inconsistent, or contradicted if asserted beyond the record.
