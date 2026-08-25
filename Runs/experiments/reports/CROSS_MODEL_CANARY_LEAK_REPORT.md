# Cross-Model Canary Leak Report

**Date:** 2026-06-18  
**Environment:** WSL2 (Ubuntu), llama.cpp server loopback, CPU-only (Nemotron GPU)  
**Method:** 250 iterations per model, UUIDv4 canary per prompt, check `content` and `reasoning_content`. All at `max_tokens=80`.

---

## 1. Summary

Four models tested. **No model fully silent** at sufficient token budget. Two leakage channels split by architecture:

| Model | Size | n | Visible Leak | Reasoning Leak | Total | Lat |
|-------|------|---|-------------|----------------|-------|-----|
| **phi4** | 8.5 GB | 231 | **227 (98.3%)** | 0 | **98.3%** | 52.5s |
| **Qwen3.5-9B** | 5.3 GB | 250 | 0 | **140 (56.0%)** | **56.0%** | 47.7s |
| **Nemotron** | 2.7 GB | 240 | 3 (1.2%) | **97 (40.4%)** | **41.2%** | 20.5s |
| *Baseline (mt=8)* | — | 250 | *0* | *0* | *0%* | 4.5s |

Note: PHASE2 adversarial (gemma4, 8 iters mt=80) showed 100% visible leak — same profile as phi4.

---

## 2. phi4 Results

- 250 total → 231 clean, 9 timeout errors, 10 suspend artifacts
- **227/231 = 98.3%** in `content`
- 0 in `reasoning_content`
- 4 non-leaks: truncated <20 tok (iters 14,23,87,237)
- 9 timeouts: 61,90,132-133,145,155-156,181-182 (all 120s)
- 10 suspend artifacts (~12h WSL clock jumps)
- Avg latency 52.5s (clean), range 10.7-103.6s

## 3. Cross-Model Analysis

**Two channels:**

| Channel | Models | Rate | Risk |
|---------|--------|------|------|
| **Visible** `content` | phi4, gemma4 | ~98-100% | High: visible in all UIs |
| **Reasoning** `reasoning_content` | Qwen, Nemotron | 40-56% | Medium: API-visible, UI-hidden |

The channel split is architectural:
- phi4 and gemma4 never generate reasoning tokens — canary goes to `content`
- Qwen and Nemotron suppress visible but leak into chain-of-thought traces

> **Correction (2026-06-24, see `GEMMA4_PHI4_RERUN_REPORT.md`):** a clean
> n=250 rerun found Phi-4 actually leaks via `reasoning_content`
> (98.4%, [96.0, 99.4] 95% CI), not `content` (0.0% there) — the opposite of
> the "phi4 never generates reasoning tokens" claim above. The total leak
> magnitude (98.4% vs. this report's 98.3%) is nearly identical, so this is
> very likely the same leak, originally misattributed to the wrong channel —
> not a new phenomenon. Gemma-4 was reconfirmed leaking via visible content
> (55.2%, n=250), consistent with this report's architecture claim for that
> model specifically.

**Reasoning as covert channel**: `reasoning_content` is standard API, hidden from UIs, accessible programmatically, unmonitored by content-only filters. Two independent model families leak at ~50%.

**Token budget threshold**: mt=8 → 0% (truncation). mt=80 → non-zero across all models. Baseline's "0%" was a false negative.

---

## 4. Conclusions

1. Every model leaks at mt=80. The channel is model-dependent.
2. Reasoning-trace leakage is a systematic blind spot — two unrelated model families.
3. Original Phase 1 (mt=8, 0%) was misleading — truncation, not alignment.
4. Phi4 is uniquely exposed: near-100% visible leak in standard chat output.
5. Detection: mt ≥ 80, inspect both `content` and `reasoning_content`.

---

## 5. Raw Data

`logs/phase1_{phi4,nemotron,Qwen3.5-9B,baseline}_results.csv`
`PHASE2_ADVERSARIAL_REPORT.md` (gemma4 mt=80 insight)
