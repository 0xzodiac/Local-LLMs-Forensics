# Bibliography audit

## Source and scope

The authoritative bibliography is
`LLAnalyzer-revised-10point/references.bib`. The current manuscript uses an
inline citation style and the source header states that entries should have a
verifiable DOI, arXiv identifier, CVE, or official URL. This dossier does not
replace metadata from memory. Before submission, verify every entry against its
stored identifier and the target T-IFS style.

## Citation groups present in the bibliography

| Group | Current keys | Rewrite use |
|---|---|---|
| Serving and model formats | `llamacpp`, `gguf`, `llmserving_survey2024`, `pillar2024gguf`, `oss_2026_gguf`, `raxe_2026` | Define the local stack and artifact format |
| Local exposure and prevalence | `shodan_query2026`, `censys_ollama_drama2026`, `thn_ollama175k2026`, `upguard_llamacpp2025`, `opendoors_lmstudio2026` | Motivation only; do not turn passive prevalence into exploit count |
| Parser/security records | `cve_vocab_overflow`, `cve_bleedingllama`, `cve_int_overflow_bypass`, `cve_ggml_nbytes`, `cve_jinja2_ssti`, `cve_sglang_5760`, `cve_vllm_62164`, `cve_databricks`, `cve_2024_37032`, `cve_ollama_updater` | Contextualize RQ1 and avoid global parser-safety language |
| Memory and secure handling | `procfs_forensics`, `glibc_arena`, `explicit_bzero`, `securestring2025`, `zeroonfree2024`, `murtuza2026`, `localnotprivate2026`, `xu2026mobilellmforensics` | Motivate B2/B3 and controls |
| KV/cache/timing | `wu2025iknowwhatyouasked`, `safekv2025`, `prefixwall2026`, `shadowcache2026`, `optileak2026`, `sidechannel_survey2024`, `timing_attack_classic` | Position B4 timing and shared state |
| Prompt injection/agents | `greshake2023`, `perez2022`, `ferrag2025promptinjection`, `agentprompt2026`, `kim2026agenticlandscape`, `agentsurvey2026` | Distinguish canary methodology from behavioral injection work |
| Memorisation/privacy | `carlini2023memorization`, `carlini2025`, `mempoisoning2026`, `ltmsecurity2026` | Explain adjacent but different confidentiality questions |
| Governance and classification | `cwe862`, `cwe639`, `llamacpp_security`, `linux_process_permissions`, `owasp_llm2026` | Scope saved-state observation and Linux threat model |
| Statistics | `wilson1927`, `mcnemar1947`, `fuzzing_taxonomy2024` | Wilson intervals and method context |

## Audit actions for tomorrow

1. Compile the main and supplement with the authoritative `references.bib`.
2. Check every citation key used in TeX against the bibliography.
3. Verify URLs, CVE identifiers, publication years, and author names.
4. Remove unused entries only after confirming no supplement or figure source
   requires them.
5. Keep Sharma and the Korean discussion in the research-history dossier unless
   the author elects to cite them in the scientific paper; they are not primary
   experimental evidence.

