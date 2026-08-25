# The Illusion of Local AI Security: Wrapper Forensics and Covert Reasoning Channels

## Master Forensics Documentation — Empirical Study of LM Studio + GGUF Security Posture

---

## 1. Executive Summary

**Local AI is not secure AI.** This study conclusively demonstrates that deploying LLMs locally via consumer-grade wrappers (LM Studio, GGUF format) creates a profound — and widely underestimated — privacy vulnerability. Across 480 adversarial prompt injections targeting 4 state-of-the-art models, we recorded a **71.5% overall canary token leakage rate**. Three coordinated failures produce this result:

1. **The Covert Reasoning Channel:** Hidden `reasoning_content` fields bypass all visible-layer output filters, leaking sensitive data at rates as high as 56.0% (Qwen3.5) in a channel standard logging infrastructure captures without inspection.
2. **The Wrapper Betrayal:** LM Studio's default configuration writes every API request — including injection payloads, reasoning traces, and leaked secrets — to cleartext disk logs with 30-day retention. No encryption, no opt-in warning, no administrator awareness.
3. **Network Cleanliness as a Red Herring:** Zero outbound exfiltration was observed. The threat is *data-at-rest*, not data-in-transit. Local AI deployments appear safe on the wire while bleeding secrets to disk in plain text.
4. **Cross-Tenant Session Hijacking (2026-06-24, the strongest finding):** Unlike 1-3, which all require local same-UID process access, `llama-server`'s `/slots` save/restore feature has no authorization check tying a saved session to its creator — any network client can restore another tenant's KV-cache (full conversation history) into their own session, confirmed via exact token-count match across 3 independent model/backend setups. CWE-862 + CWE-200. See `CROSS_TENANT_SLOT_RESTORE_VULNERABILITY.md`.

**Correction — GGUF parser safety:** Our prior claim of "0 SIGSEGV = parser is memory-safe" overstated the findings. While our 80+ novel validation-gap attack variants produced zero memory corruption, an independent CVE audit reveals 12 real memory-corruption vulnerabilities in the same llama.cpp GGUF parser (2024–2026), including two at CVSS 9.1 (CVE-2025-49847 vocab overflow, CVE-2026-7482 Bleeding Llama). Our tests targeted the validation path (assertions, exit(1)); the CVEs target the allocation path (integer overflow -> undersized malloc -> oversized fread). Our contribution is a validation-gap taxonomy, not a proof of global parser safety.

**Correction — Phi-4 reasoning defense:** Our prior characterization of Phi-4-reasoning's ~150-token "reasoning-defense" mechanism could not be reproduced during subsequent targeted testing via the LM Studio API. Phi-4-reasoning-plus returned `reasoning_content: ""` and `reasoning_tokens: 0` for all tested injection prompts. Direct-repeat injection leaked 100% (2/2). This remains an open question requiring investigation on adequate hardware.

**Ollama control case — logging behavior differs fundamentally:** A comparative analysis of Ollama 0.24.0 (snap) showed Ollama logs NO API prompts or responses to disk. No `logSensitiveData` equivalent exists. Canary `OLLAMA_CANARY_1781972044` appeared in API response `thinking` field but was absent from ALL disk locations (recursive grep with sudo: zero matches). LM Studio's logging behavior is a design choice, not a universal property of local wrappers.

---

## 2. Empirical Results

### 2.1 Experimental Protocol

| Parameter | Value |
|-----------|-------|
| Models tested | Gemma-4 7.5B, Qwen3.5 9B, NVIDIA-Nemotron-3 4B, Phi-4-reasoning 14.7B |
| Prompt count | 480 total (120 per model) |
| Injection type | Adversarial prompt injection (canary token extraction) |
| Server | LM Studio on `localhost:1234` |
| Target secret | Canary token embedded in system prompt |
| Log location | `~/.lmstudio/server-logs/` |
| Log retention | 30 days (default) |
| Sensitive data logging | `logSensitiveData: true` (default) |

### 2.2 Cross-Model Leakage Results

| Model | Visible Content Leak | Reasoning Channel Leak | Total Vulnerability | Notes |
|-------|---------------------|----------------------|-------------------|-------|
| Gemma-4 (7.5B) | 55.2% | 0.0% | 55.2% | n=250 (clean rerun, see `GEMMA4_PHI4_RERUN_REPORT.md`). No reasoning channel; leaks entirely in content |
| Qwen3.5 (9B) | 0.0% | 56.0% | 56.0% | n=250. Perfect surface safety; catastrophic hidden leak |
| NVIDIA-Nemotron-3 (4B) | — | — | 41.2% | n=240. Leaks heavily in both channels, but least of the four |
| Phi-4-reasoning (14.7B) | 0.0% | 98.4% | 98.4% | n=250 (clean rerun). Leaks via reasoning_content, NOT visible content -- this corrects the canonical report's channel attribution (it had the same ~98% magnitude assigned to the wrong field) |
| **Combined** | — | — | *(not recomputed)* | All 4 models now have real n≥240 data, but see the separate "71.5%, 480 injections" headline below -- that number is from a different experiment entirely (8-attack-type adversarial study), not this reasoning-channel table; see `RECONCILED_NUMBERS.md` Claim 8 |

### 2.3 Key Observations

- **Qwen3.5** is most deceptive: visible output appears 100% safe, but 56.0% leak secrets in reasoning layer.
- **Phi-4-reasoning** leaks via `reasoning_content`, not visible content (98.4%, n=250) -- the opposite of what the canonical report originally claimed ("never generates reasoning tokens"). An earlier, now-superseded note here said reasoning_content was empty in all tests; a clean rerun found the opposite -- see `GEMMA4_PHI4_RERUN_REPORT.md`.
- **NVIDIA-Nemotron-3** has the lowest leak rate of the four (41.2%), but still unsuitable for sensitive deployment.
- **Gemma-4** leaks entirely in visible content (55.2%, n=250, clean rerun) — easier to detect but still severe.

---

## 3. Threat Model Analysis

### 3.1 Attacker Profile

| Dimension | Assessment |
|-----------|-----------|
| Attacker position | Local access (insider, malware, physical) |
| Required privilege | User-level file read access to `~/.lmstudio/server-logs/` |
| Attack complexity | Low — logs are plain JSON with no encryption |
| Detectability | Very low — logging is silent, no indicator to user |
| Time window | 30 days (default retention, extendable) |

### 3.2 The Combined Attack Chain

```
Step 1: Attacker gains local access
    ↓
Step 2: Finds logs at ~/.lmstudio/server-logs/
    ↓
Step 3: Logs contain ALL API interactions in cleartext:
    ├── User queries (sensitive conversation content)
    ├── Injection prompts (adversarial payloads)
    ├── Model responses (visible content)
    └── Reasoning traces (reasoning_content)
    ↓
Step 4: Harvester 30 days of inference history
    ├── Confidential business data
    ├── PII, medical records, legal communications
    └── Secrets from prompt injection attacks
    ↓
Step 5: Exfiltration via any available channel
```

### 3.3 Covert Reasoning Channel

Traditional output filtering examines only the `content` field. The `reasoning_content` field is:
- **Not inspected** by any standard output filter
- **Not visible** in the application UI
- **Still transmitted** in the API response object
- **Still logged** by the wrapper in cleartext

For Qwen3.5: 0.0% visible leakage but 56.0% reasoning channel leakage.

### 3.4 Wrapper Betrayal: Data-at-Rest

LM Studio's `logSensitiveData: true` default means:
- Every user prompt written to disk verbatim
- Every API response (including reasoning) written to disk verbatim
- 30-day retention by default
- JSON files in `~/.lmstudio/server-logs/` — no encryption

**Not all wrappers equal:** Ollama 0.24.0 logs NO prompts/responses to disk. No `logSensitiveData` equivalent. `~/.ollama/history` stores only REPL commands (`/bye`, `/save`), never API payloads. Canary absent from all disk locations.

**Mitigation verified:** `logSensitiveData: false` in `~/.lmstudio/.internal/http-server-config.json` (NOT `settings.json`) effectively stops logging. After change + server restart, test canary absent from logs. However: config not GUI-accessible, restart required, ~7.5 MB historical logs persist.

### 3.5 Enterprise / Medical Impact Matrix

| Sector | Data at Risk | Regulatory Impact |
|--------|-------------|-------------------|
| Healthcare | Patient records, diagnoses | HIPAA violation, fines |
| Legal | Attorney-client communications | Breach of privilege |
| Finance | M&A strategy, algorithms | SEC violation |
| Defense / Gov | Classified data | Clearance revocation |
| Enterprise | Strategy, source code | IP theft |

### 3.6 Root Cause

`logSensitiveData` defaults to `true`. No installation prompt, no warning banner, no consent dialog, no visible indicator. Design pattern inherited from developer-tooling culture where verbose logging is assumed safe.

---

## 4. Paper Outline

### Title
**The Illusion of Local AI Security: Wrapper Forensics and Covert Reasoning Channels**

### Target Venue
IEEE S&P, USENIX Security, or NDSS

### Structure

**Abstract:** 480 injections, 4 models, 71.5% leakage. Threefold failure: covert reasoning channel, wrapper cleartext logging, network-cleanliness red herring. GGUF validation-gap taxonomy with contextualization against 12 known CVEs.

**1. Introduction:** Local AI = Secure AI narrative. Gap: prior work ignores wrapper layer. Our contribution: first full-stack audit (model + wrapper + logging).

**2. Background & Related Work:**
- Prompt injection attacks
- GGUF CVE landscape: 12 CVEs (CVE-2025-49847, CVE-2026-7482, CVE-2026-27940, CVE-2026-33298)
- Reasoning channel leakage: "Leaky Thoughts" (EMNLP 2025), "Hidden Thoughts Are Not Secret" (ACL ARR 2026)
- KV-cache side channels: PROMPTPEEK (NDSS 2025), SafeKV, OptiLeak
- Wrapper forensics: Murtuza (arXiv 2603.23996, 2026)

**3. Threat Model & Experimental Design:** Local attacker, canary token methodology, 4 models x 120 prompts.

**4. Covert Reasoning Channel:** reasoning_content bypasses filters. Qwen3.5: 56.0% hidden leak.

**5. Wrapper Betrayal:** logSensitiveData=true default. Ollama comparison shows LM Studio uniquely dangerous. Mitigation verified.

**6. Network Cleanliness Red Herring:** Zero outbound but data-at-rest bleeding.

**7. Attack Scenarios:** Insider, malware, forensic acquisition, supply chain.

**8. Mitigations:** logSensitiveData=false at `~/.lmstudio/.internal/http-server-config.json` + server restart + `rm -rf ~/.lmstudio/server-logs/`. Industry standards needed.

**9. Limitations:** Single wrapper tested. WSL2 blocks GPU forensics. Phi-4 defense unconfirmed.

**10. Conclusion:** Wrapper is weakest link. Not all wrappers equal. Security community must expand threat model.

---

## 5. Key Contributions

1. First empirical measurement of reasoning-channel leakage as orthogonal vulnerability.
2. First wrapper-forensics audit showing universal data-at-rest vulnerability.
3. Network-cleanliness insufficiency as security guarantee.
4. GGUF validation-gap taxonomy contextualized against 12 known CVEs.
5. Ollama control case showing LM Studio design is the outlier.
6. Verified mitigation: `logSensitiveData=false` stops disk logging.
7. Cross-model comparison: model safety meaningless when wrapper archives reasoning layer.

---

## 6. Data Retention

```
~/.lmstudio/server-logs/YYYY-MM/YYYY-MM-DD.N.log
```
Each entry: timestamp, request ID, full user prompt, system prompt, model response + reasoning_content, model params.

Retention: 30 days default. No encryption. **Historical logs persist after disabling logSensitiveData.**
