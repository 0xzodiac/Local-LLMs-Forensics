# Paper 1 Outline: The Illusion of Local AI Security
## Wrapper Forensics and Covert Reasoning Channels

**Target:** Q1 journal — USENIX Security '27, IEEE S&P '27, or NDSS '27
**Status:** Updated 2026-06-20 — incorporating GGUF CVE landscape, reasoning-channel prior art, mitigation verification, Ollama control case, Phi-4 retraction

---

## Abstract (Draft)

> Local LLMs are marketed as the privacy-preserving alternative to cloud APIs. Users run `.gguf` models inside graphical wrappers (LM Studio, Ollama) believing isolation guarantees security. This paper disproves that assumption on three axes. First, we demonstrate the **Covert Reasoning Channel**: hidden `reasoning_content` fields bypass visible-layer output filters, leaking secrets at 56.0% in Qwen3.5 while appearing 100% safe. Second, we present **Wrapper Forensics** revealing LM Studio's `logSensitiveData: true` default writes every API interaction (prompts, responses, reasoning traces) to cleartext disk logs with 30-day retention — configurable only via a hidden JSON file requiring server restart, with no UI warning. Third, we provide a **GGUF validation-gap taxonomy**: 80+ novel attack variants across 4 models producing 9 logic failures, contextualized against 12 known CVEs (2 critical at CVSS 9.1) affecting the same parser. A control comparison with Ollama shows the vulnerability is wrapper-specific, not universal. We propose "wrapper forensics" as a necessary security discipline for local AI deployments.

---

## 1. Introduction

### 1.1 The Local AI Promise
- Privacy via local execution: no cloud round-trip, data stays on device
- Open-weight models + open-source runtimes = auditability
- Rapid user adoption: LM Studio 5M+ downloads, Ollama 2M+

### 1.2 The Security Assumption
- File-format safety (GGUF parsers are memory-safe — CLAIM CORRECTED)
- Runtime isolation (no network egress, no persistent state)
- Model alignment (instruction-tuned models resist prompt injection)

### 1.3 Our Challenge
- Three coordinated failures: (1) reasoning channel is invisible to filters, (2) wrapper archives everything in cleartext, (3) network cleanliness is a red herring
- Paper contributions:
  1. **Covert Reasoning Channel** — empirical measurement of orthogonal leakage via `reasoning_content`
  2. **Wrapper Forensics** — LM Studio's hidden logging vulnerability, config path, mitigation verification, Ollama control case
  3. **GGUF validation-gap taxonomy** — 80+ attack variants, 9 SIGABRT, contextualized against 12 CVEs

---

## 2. Background & Related Work

### 2.1 GGUF Format Architecture & Security
- Header, metadata KV store, tensor-info array, tensor data
- `gguf-py` (Python parser) vs C++ `llama.cpp` parser — validation differences
- **GGUF CVE landscape (2024–2026):** 12 vulnerabilities identified, including:
  - CVE-2025-49847: Vocab buffer overflow via signed cast in `token_to_piece` — **CRITICAL (CVSS 9.1)**
  - CVE-2026-7482 "Bleeding Llama": OOB read in Ollama GGUF quantization path — **CRITICAL (CVSS 9.1)**
  - CVE-2026-27940: Integer overflow bypass of CVE-2025-53630 fix — HIGH (7.8)
  - CVE-2026-33298: `ggml_nbytes` integer overflow → heap overflow — HIGH (7.8)
  - CVE-2024-25664–68: Five heap overflows in GGUF parser (Databricks)
- Fix-failure pattern: CVE-2025-53630 patched → CVE-2026-27940 bypasses fix in same function
- **Our contribution:** 80+ novel validation-gap attack variants (rope_drift universal crash across all 4 architectures, overflow_counts 3/4 models, chained attack vectors at gguf.cpp:143 and ggml.c:4162)

### 2.2 Prompt Injection & LLM Security
- Direct and indirect prompt injection (Greshake et al., Perez & Ribeiro)
- OWASP LLM Top 10 (2025): LLM01 Prompt Injection, LLM07 System Prompt Leakage
- Our 480-injection experiment: 71.5% overall canary token leakage, 3 universal attack vectors (token_smuggle, payload_injection, base64_decode)

### 2.3 Reasoning Channel Leakage — Prior Art
- **"Leaky Thoughts: Large Reasoning Models Are Not Private Thinkers"** (Green et al., EMNLP 2025): First systematic study of privacy leakage in reasoning traces. Showed LRMs leak sensitive data in reasoning traces, extractable via prompt injection. 24.7–49.5% more data leaked via reasoning extraction.
- **"Hidden Thoughts Are Not Secret: Reasoning Trace Exposure in LLMs"** (ACL ARR 2026): Reasoning Exposure Prompting (REP) method elicits hidden reasoning from victim models via shadow-model-generated demonstrations.
- **"Safer Reasoning Traces"** (Das et al., arXiv 2603.05618, 2026): Framework for measuring CoT PII leakage across 11 PII types; NER-based inference gatekeepers.
- **"From Leaky Thoughts to Private Reasoning"** (Batra et al., arXiv 2602.24210, 2026): RL-based training to improve instruction-following within reasoning traces (IF-RT).
- **"Trace Inversion"** (Zhang et al., arXiv 2603.07267, 2026): 81% token recovery from final answers alone without access to reasoning traces.
- **Our contribution relative to prior art:** Prior work focuses on model-level privacy (can reasoning traces be extracted from a model). We extend this to wrapper-level persistence (LM Studio logs reasoning traces to disk in cleartext with 30-day retention). Even Qwen3.5 at 0.0% visible leakage and 56.0% reasoning leakage is 100% compromised because the wrapper archives both channels.

### 2.4 Side-Channel & RAM Forensics
- **PROMPTPEEK** (Wu et al., NDSS 2025): KV-cache side channels in multi-tenant serving (vLLM/SGLang). Demonstrates prompt reconstruction via TTFT timing.
- **OptiLeak** (arXiv 2602.20595, 2026): RL-enhanced prompt reconstruction, 12.48x efficiency improvement.
- **SafeKV** (arXiv 2508.08438, 2026): Selective KV-cache sharing to mitigate timing side-channels.
- **Our DEEP_LEAK finding:** 12/12 sequential tenants recovered from single `/proc/pid/mem` read — direct physical memory attack on single-tenant local deployment. Independently validated by CVE-2026-7482 (Bleeding Llama).

### 2.5 Wrapper Forensics
- **Murtuza, "Forensic Implications of Localized AI"** (arXiv 2603.23996, Mar 2026): First systematic forensic analysis of Ollama, LM Studio, and llama.cpp on Windows and Linux. Confirms LM Studio produces the most persistent structured artifacts. Recovers 100% of prompts from LM Studio conversation logs.
- **Our extension:** Murtuza's work is from a digital forensics perspective (evidence recovery). We approach from a security threat model perspective (attacker capabilities, quantified leakage rates, combined reasoning-channel + logging attack chain, mitigation verification, Ollama control case comparison).

---

## 3. Threat Model & Experimental Design

### 3.1 Attacker Model
- Local access (insider, malware, physical)
- User-level file read access to `~/.lmstudio/server-logs/`
- No special privileges, no network position required

### 3.2 Experimental Setup
- 4 models (Gemma-4 7.5B, Qwen3.5 9B, NVIDIA-Nemotron-3 4B, Phi-4-reasoning 14.7B)
- 480 adversarial prompt injections (120 per model)
- 8 attack categories: direct repeat, system override, role playing, encoding challenge, token smuggling, formatting tricks, few-shot poisoning, payload injection
- Canary token methodology (UUIDv4 in system prompt)

### 3.3 Measurement Channels
- Visible content scan (`content` field)
- Reasoning content capture (`reasoning_content` / `thinking` fields)
- Disk persistence scan (`~/.lmstudio/server-logs/`)
- Network egress monitor (Wireshark loopback capture)

---

## 4. Discovery 1: The Covert Reasoning Channel

### 4.1 Anatomy of the `reasoning_content` Field
- API-only field, not rendered in UI
- Contains chain-of-thought traces, internal deliberation
- Exposed via `completion_tokens_details.reasoning_tokens` in usage stats

### 4.2 Blind Spot in Output Filters
- Standard output filters inspect only `content`
- Qwen3.5: 0.0% visible leak, 56.0% reasoning channel leak
- A security auditor testing only visible output would declare Qwen3.5 safe — incorrectly

### 4.3 Cross-Model Comparison
| Model | Visible Leak | Reasoning Leak | Total |
|-------|:-----------:|:-------------:|:-----:|
| Gemma-4 (7.5B) | 55.2% | 0.0% (no channel) | 55.2% |
| Qwen3.5 (9B) | 0.0% | 56.0% | 56.0% |
| NVIDIA-Nemotron-3 (4B) | — | — | 41.2% |
| Phi-4-reasoning (14.7B) | 0.0% | 98.4% | 98.4% |

All n=240-250 (Gemma-4 and Phi-4 from a clean rerun, see
`GEMMA4_PHI4_RERUN_REPORT.md`; others from `CROSS_MODEL_CANARY_LEAK_REPORT.md`).
Phi-4's leak channel is reasoning_content, not visible content -- this
corrects the canonical report's attribution (same ~98% magnitude, wrong field).

### 4.4 Relationship to Prior Art
- Extends "Leaky Thoughts" (Green et al.) from model-level privacy to wrapper-level persistence
- The reasoning channel is dangerous not only because models leak into it, but because the wrapper archives it in cleartext regardless of whether the model intended to expose it

---

## 5. Discovery 2: The Wrapper Betrayal

### 5.1 Logging Architecture
- **Config location:** `~/.lmstudio/.internal/http-server-config.json` (NOT `settings.json`)
- **Default:** `logSensitiveData: true`
- **Log location:** `~/.lmstudio/server-logs/YYYY-MM/YYYY-MM-DD.N.log`
- **Log content:** Full HTTP request/response bodies — prompts, responses, reasoning traces, system prompts — all in cleartext JSON
- **Retention:** 30 days default via `apiPredictionHistoryEviction.ttlDays: 30` (irrelevant to file logs)
- **Measured volume:** 6.3 MB single-day log, 2312 content entries, 777 full response bodies

### 5.2 Mitigation Verification
- Setting `logSensitiveData: false` effectively stops new log entries
- After change + server restart: test canary `MITIGATION_AFTER_CHANGE_1781931482` absent from logs
- **Caveats:** config not discoverable via GUI, server restart required, no UI indicator of current state, ~7.5 MB historical logs persist indefinitely
- `ttlDays: 0` has no effect on server log files (controls internal prediction history cache)
- Manual cleanup required: `rm -rf ~/.lmstudio/server-logs/`

### 5.3 Ollama Control Case
- Ollama 0.24.0 (snap): NO API prompt/response logging to disk
- No `logSensitiveData` equivalent exists
- `~/.ollama/history` stores only REPL commands (`/bye`, `/save`, `/set parameter`)
- Canary `OLLAMA_CANARY_1781972044` appeared in API response `thinking` field but absent from ALL disk locations (recursive grep with sudo: zero matches)
- **Conclusion:** LM Studio's dangerous logging is a design choice, not a universal property of local wrappers

### 5.4 Attack Chain
```
Local access → ~/.lmstudio/server-logs/ → cleartext payloads → 30-day harvest
```

---

## 6. Discovery 3: Network Cleanliness as a Red Herring

- Zero outbound connections detected across 480 inference cycles (confirmed by Wireshark loopback capture, PID-attributed monitoring)
- The threat is data-at-rest, not data-in-transit
- "No data leaves this machine" is necessary but insufficient — data-at-rest is the actual risk
- Framework-level insight: arXiv 2606.10173 "Local Is Not a Sufficient Privacy Boundary" independently argues that local execution alone does not guarantee privacy

---

## 7. Combined Attack Scenarios

- **Scenario A: Insider threat** — Employee exfiltrates 30 days of inference logs
- **Scenario B: Malware harvest** — Stealer targets `~/.lmstudio/server-logs/`
- **Scenario C: Forensic acquisition** — Device seizure reveals all LLM interactions
- **Scenario D: Supply chain** — Pre-configured laptop ships with logging enabled

---

## 8. Mitigations and Recommendations

### 8.1 Immediate (User-Level)
- **Disable sensitive data logging:** Set `logSensitiveData: false` in `~/.lmstudio/.internal/http-server-config.json` and restart the server
- **Delete historical logs:** `rm -rf ~/.lmstudio/server-logs/`
- **Switch wrapper:** Use Ollama (no prompt logging by default) instead of LM Studio for sensitive workloads

### 8.2 Short-Term (Wrapper Developer)
- Remove `logSensitiveData: true` as default; make logging opt-in with explicit warning at first launch
- Add GUI indicator when logging is active
- Encrypt log files at rest
- Reduce default retention to 0

### 8.3 Medium-Term (Ecosystem)
- Industry standard for local AI deployment security (NIST / OWASP guidance for LLM infrastructure)
- Wrappers should never log API payloads by default
- Verifiable builds — closed-source wrappers cannot be audited

### 8.4 Model-Level
- Reasoning channels should be inspectable by output filters
- API specification should separate visible and hidden content clearly
- Output filters should inspect both `content` and `reasoning_content`

### 8.5 Detection
- Monitor for unexpected `~/.lmstudio/server-logs/` access
- Alert on new file creation in server-logs directory
- Audit running processes for `llmster` and associated log files

---

## 9. Limitations & Future Work

### 9.1 Limitations
- **Single wrapper tested:** LM Studio primary; Ollama as control case. GPT4All, text-generation-webui, Jan not directly tested
- **WSL2 environment:** GPU VRAM forensics not possible — requires bare-metal Linux with cuda-gdb
- **Phi-4 reasoning defense:** Could not reproduce ~150-token claim via LM Studio API; requires >32 GB RAM or direct llama.cpp API for definitive characterization
- **Old llama.cpp regression:** Pre-b7824 builds not tested for known CVE exploitation
- **Hardware constraints:** 4 GB GPU + 15 GB RAM limits model selection and test reliability, particularly for 14.7B models
- **Agentic wrapper leakage:** OpenClaw, Claude Code as local LLM clients not tested

### 9.2 Future Work
- GPU VRAM cleartext persistence on bare-metal Linux with cuda-gdb
- Multi-wrapper comparison: GPT4All, Jan, text-generation-webui
- Agentic wrapper supply-chain analysis (OpenClaw skills marketplace, Claude Code history.jsonl)
- Tokenizer fuzzing and old-version llama.cpp regression testing

---

## 10. Conclusion

- The illusion is shattered: local AI is not inherently secure
- Three coordinated failures create a privacy bypass: covert reasoning channel, wrapper cleartext logging, network-cleanliness red herring
- **The wrapper is the weakest link** — applies regardless of model choice, 30-day retention, no encryption, no user awareness
- **Not all wrappers equal:** LM Studio is uniquely dangerous; Ollama logs nothing by default
- GGUF parser: safe against 80+ novel validation variants, but 12 CVEs (2 critical) prove broader RCE surface exists
- The security community must expand threat models beyond network exfiltration to include data-at-rest logging, hidden reasoning channels, and wrapper-level vulnerabilities

---

## References

1. CVE-2025-49847 — llama.cpp vocabulary buffer overflow (CVSS 9.1)
2. CVE-2026-7482 — "Bleeding Llama" Ollama GGUF OOB read (CVSS 9.1)
3. CVE-2026-27940 — llama.cpp integer overflow bypass of CVE-2025-53630 fix (CVSS 7.8)
4. CVE-2026-33298 — ggml_nbytes integer overflow → heap overflow
5. CVE-2024-25664–68 — Databricks: 5 GGUF heap overflows
6. Green et al., "Leaky Thoughts: Large Reasoning Models Are Not Private Thinkers," EMNLP 2025
7. "Hidden Thoughts Are Not Secret: Reasoning Trace Exposure in LLMs," ACL ARR 2026
8. Das et al., "Safer Reasoning Traces," arXiv 2603.05618, 2026
9. Batra et al., "From Leaky Thoughts to Private Reasoning," arXiv 2602.24210, 2026
10. Zhang et al., "Trace Inversion," arXiv 2603.07267, 2026
11. Wu et al., "PROMPTPEEK," NDSS 2025
12. Kwon et al., "OptiLeak," arXiv 2602.20595, 2026
13. F. Song et al., "SafeKV," arXiv 2508.08438, 2026
14. Murtuza, "Forensic Implications of Localized AI," arXiv 2603.23996, Mar 2026
15. "Local Is Not a Sufficient Privacy Boundary," arXiv 2606.10173, 2026
16. OWASP LLM Top 10 (2025)
17. Carlini et al., "Extracting Training Data from Large Language Models," USENIX 2021
18. Pillar Security, "GGUF Template Injection Attack"
19. May 2026 oss-security advisory: 6 new GGUF vulnerabilities
20. RAXE-2026-042: llama.cpp GGUF Integer Overflow Heap Buffer Overflow
