# External expert review audit

Sources reviewed in full where accessible:

- [P. K. Sharma briefing](https://www.pk-sharma.com/briefing/local-llm-prompts-leak-memory-logs-llama-cpp-slots), 17 September 2026.
- [Korean technical discussion](https://hacksms.tistory.com/367), 20 September 2026 presentation of the same preprint.

## What Sharma independently verified

### A. Independent arithmetic

Sharma recomputed the two-sided Wilson interval for 200/200 as approximately 98.1%–100% and recomputed the 110→78 copy reduction and 10,834→3,352 recorded-KB reduction as approximately 29% and 69%. He also checked the 126/200 continuation percentage and the model-specific counts against the paper's tables.

### B. Independent source and documentation inspection

He checked the public availability of the recorded llama.cpp revision, llama-server documentation for `--slot-save-path`, API-key behavior, prompt-cache and CORS settings, the llama.cpp security policy and repository history, LM Studio/Ollama documentation, and the disclosure-plan status described in the public artifact record.

### C. Analysis of the authors' results

He interpreted the 200/200 result as a state-transfer observation conditional on saved slots and a shared server, distinguished it from 126/200 model continuation, bounded the LM Studio logging result to the observed configuration, questioned the WAN generalization, and identified missing allocator-result, workload, disclosure, and execution details.

### D. Independent execution

No direct evidence in the article documents an independent rebuild, model-backed rerun, memory acquisition, slot campaign, or timing campaign. The article explicitly describes arithmetic and repository/documentation checks. The Korean discussion is a secondary technical summary and likewise provides no execution manifest or raw independent output. Neither source is classified as experimental reproduction.

## Relationship to the retained primary data

Sharma's arithmetic is consistent with the independent recomputation in this directory. His article strengthens the criticism and reception record; it does not replace the missing historical source-to-binary chain, memory acquisition metadata, or TTFT vectors. The Korean page independently repeats the headline findings at a summary level but does not provide a separate raw-data chain.

The full claim-by-claim mapping is in `EXTERNAL_REVIEW_CLAIM_MATRIX.md`.
