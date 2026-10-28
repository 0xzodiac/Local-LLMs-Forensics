# Claim-to-citation map

| Paper claim | Citation keys to consider | Citation role | Placement |
|---|---|---|---|
| Local LLM serving stack and GGUF | `llamacpp`, `gguf`, `llmserving_survey2024` | System and format definitions | Introduction, Method |
| Local exposure motivation | `shodan_query2026`, `censys_ollama_drama2026`, `upguard_llamacpp2025`, `opendoors_lmstudio2026` | Context, not experiment evidence | Introduction |
| Parser vulnerabilities exist beyond this corpus | `cve_vocab_overflow`, `cve_bleedingllama`, `cve_int_overflow_bypass`, `cve_ggml_nbytes` | Bound RQ1 negative claim | RQ1/Related Work |
| Memory acquisition semantics | `procfs_forensics`, `linux_process_permissions` | Explain F and A1 | Threat Model, RQ2 |
| Allocator/zeroisation controls | `glibc_arena`, `explicit_bzero`, `securestring2025`, `zeroonfree2024` | Mechanism and mitigation context | RQ2/Discussion |
| Wrapper artifact forensics | `murtuza2026`, `localnotprivate2026`, `xu2026mobilellmforensics` | Position B3 | Related Work, RQ3 |
| Shared KV/timing state | `wu2025iknowwhatyouasked`, `safekv2025`, `prefixwall2026`, `shadowcache2026`, `optileak2026` | Position B4 | Introduction, RQ4 |
| Prompt injection and hidden channels | `greshake2023`, `perez2022`, `ferrag2025promptinjection`, `agentprompt2026` | Distinguish threat class | Background |
| CWE framing | `cwe862`, `cwe639`, `cwe200`, `cwe285` if retained in bibliography | Classification context only | RQ4/Disclosure |
| Wilson intervals | `wilson1927` | Statistical method | Method/Supplement |
| Upstream security policy | `llamacpp_security` | Report policy scope, not vendor verdict | RQ4/Disclosure |

## Citation discipline

Use citations to establish prior work or official behavior. Use retained local
records to establish LLAnalyzer's results. Do not cite a public article as if it
were an independent replication of this study.

