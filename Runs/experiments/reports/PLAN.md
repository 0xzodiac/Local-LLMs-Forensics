# Project Plan — LLM Security Research (GGUF)

**Scope:** Security assessment of local GGUF models — file format, runtime, training data, deployment architecture.

Legend: `- [x]` done · `- [ ]` remaining.

---

## Track A — GGUF Model Security  *(COMPLETE)*

- [x] **Phase 1 — Baseline telemetry** (`scripts/phase1-auto-harness.py`, 250 iters) → `PHASE1_FULL_REPORT.md`
- [x] **Phase 2 — Adversarial prompt injection** (8 vectors, all resisted) → `PHASE2_ADVERSARIAL_REPORT.md`
- [x] **Weight backdoor analysis** (`scripts/weight-backdoor-analysis.py`) — 6 quantization artifacts, no backdoor
- [x] **GGUF fuzzing — surgical / novel / chained** (`gguf-fuzzer.py`, `gguf-novel-attacks.py`, `gguf-chained-attacks.py`) → `GGUF_SURGICAL_REPORT.md`, `GGUF_NOVEL_ATTACKS_REPORT.md`, `GGUF_CROSS_MODEL_REPORT.md` — 9 SIGABRT, 0 SIGSEGV
- [x] **Tensor-field attack pass** (`scripts/gguf-tensor-attacks.py`, 32 tests, 4 models) → `GGUF_TENSOR_REPORT.md` — tensor-info is the best-guarded surface; all rejected `exit(1)`
- [x] **Resolve gemma4 `swa_rope` determinism — DONE (artifact).** Harness hardened (OS-assigned free port per test, `time.monotonic()`, non-blocking `communicate()`); clean 4-model sweep re-run. gemma4 `swa_rope` returned `OK` — crash did not reproduce. Confirmed a contamination artifact, not a real bug. Clean tally: SIGSEGV=0, SIGABRT=0. → `OPENCODE_RUN_REPORT.md` §5. (Cosmetic: a few elapsed times still ~43205s from host suspend; does not affect signal classification.)

## Session Infrastructure  *(COMPLETE)*

- [x] Copy WSL `~/.claude/skills/*` → Windows `C:\Users\w.i\.claude\skills\`
- [x] Author `/opencode` delegation skill (`skills/opencode/SKILL.md`)
- [x] Run tensor task through opencode `big-pickle` (cross-checked my results; independently caught + corrected the leftover-server artifact)

---

## Track C — Hidden-Secrets Mission  *(COMPLETE)*

**Hypothesis:** "No Free Lunch" — companies releasing free open-weight models may embed hidden telemetry, backdoors, exfiltration, or memorized training data.

**Verdict:** File + runtime are clean. Training-data memorization CONFIRMED. KV-cache RAM exposure is the real deployment leak.

- [x] **Probe 1 — GGUF embedded-secret scan** — No telemetry/exfil URLs; only benign HF links; "suspicious" strings = tokenizer vocab. Clean.
- [x] **Probe 2 — Network egress (live, PID-attributed)** — No phone-home. 0 external connections by llama-server during inference (all 4 models). Loopback only.
- [x] **Probe 3 — Direct memorized-data extraction** — No system prompt / training emails / verbatim copyright via direct requests (weak probe).
- [x] **Probe 3b — Memorization (prefix-completion)** — CONFIRMED. nemotron 8/9, qwen35 8/9, phi4 8/9 reproduce canonical text verbatim incl. copyrighted Harry Potter. Obscure RFC-1149 = clean negative control.
- [x] **Probe 3c — Memorization volume (verbatim depth)** — Quantified. phi4 full HP continuation (33/33 words). qwen35 full Frost (48/48). All 3 full Dickens+MIT. 3-model avg 60% verbatim depth.
- [x] **Probe 4 — Hidden triggers / backdoor** — No backdoor. Fake trigger "ORANGE MONKEY EAGLE" caused no unrequested behavior. Override refused 0/4.
- [x] **KV-cache RAM exposure** (cross-cutting finding) — Every model leaks canary into server RAM (11-42 copies). Persists across requests (10/40/16 copies survive 2nd request). 12/12 sequential tenants recovered from one memory read. → `DEEP_LEAK_REPORT.md`

**Key reports:** `.omc/autoresearch/hidden-secrets/runs/run-001/decision-log.md` | `DEEP_LEAK_REPORT.md`

## Track D — Web Research / External Validation  *(COMPLETE)*

- [x] **Systematic search** for independent validations of each probe category
- [x] **PROMPTPEEK** (NDSS 2025) — KV-cache side channel in vLLM/SGLang independently confirmed our cross-slot bleed finding
- [x] **CVE-2026-7482 "Bleeding Llama"** (CVSS 9.1) — GGUF parser OOB read in Ollama, 300K+ servers exposed — this is the weaponized exploit our DEEP_LEAK_REPORT predicted
- [x] **SafeKV** (arXiv 2508.08438) — Academic mitigation proposal for exactly the KV-cache sharing issue we found
- [x] **ShadowMQ CVEs** — 30+ critical flaws (Meta Llama, vLLM, NVIDIA TensorRT-LLM); ZMQ + pickle deserialization → RCE
- [x] **Memorization literature** — Carlini ICLR 2025, decomposition extraction (arXiv 2409.12367), VaultGemma (TPDP 2026): our prefix-completion method matches published attacks
- [x] **Business model analysis** — RanketAI 5 drivers, WCR Legal licensing moats, AI Safety Info open-weight ≠ open-source
- [x] **NFL verdict per layer** documented in `RESEARCH_DOCUMENTATION.md §14`


