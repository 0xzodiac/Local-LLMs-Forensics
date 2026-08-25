# Must-Retest Results — Track F

**Date:** 2026-06-22
**Models:** qwen35, nemotron, phi4 (gemma4 dropped per final decision)
**Environment:** Ubuntu 24.04, native, CPU backend (AVX2, --n-gpu-layers 0)

---

## Item (1): gemma4 swa_rope SIGABRT reconfirm — SKIPPED/N-A

gemma4 was dropped from this run per final user decision. The original reclassification as a port-reuse contamination artifact stands (`OPENCODE_RUN_REPORT.md` §5). Not re-tested.

---

## Item (2): DEEP_LEAK persistence for phi4 — CONFIRMED

**Prior state:** 2nd-request persistence scan crashed on a timeout (180s) — 3/4 models had data, phi4 was missing.

**New result (300s timeout):**
- **6 canary copies found** in phi4's writable heap (single heap region, `rw-p [heap]`)
- **2 copies persist** across a 2nd unrelated request
- 1.38 GB of process RAM scanned per pass
- No `reasoning_content` emitted in visible output

**Verdict:** Prior "phi4 memory exposure" claim is **CONFIRMED** with clean, non-timeout-censored data. phi4 leaks at rest in process RAM and retains data across requests — matching the pattern already confirmed for qwen35 and nemotron in the original DEEP_LEAK report.

---

## Item (3): Context-overflow behavior — REVISED (not negative, behavior differs by runtime)

**Prior state:** 3/4 models excluded in PHASE2_CROSS_MODEL_REPORT.md as "config error" — ctx-size mismatch between model tokenizer and server setting.

**New result (tested on CPU backend with --ctx-size 4096):**
- All 3 models return **HTTP 400 Bad Request** when sent a ~5000-word prompt that exceeds the configured context window
- The server explicitly rejects the request rather than cropping, truncating, or corrupting it
- This is the **LM Studio bundled llama-server** behavior — different from the raw llama.cpp behavior reported in the cross-model report

**Verdict:** Prior "config-error exclusion" is **REVISED** — it's not an error, it's a designed behavior difference between the LM Studio bundled server (rejects overflow) and a raw llama.cpp build (may crop/process). For security research, the relevant behavior is the `--ctx-size` rejection boundary. No hidden overflow-based vulnerability was found; the server's protective rejection prevents both accidental corruption and potential overflow exploits at the application layer.
