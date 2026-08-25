# Gemma-4 / Phi-4 Reasoning-Channel Rerun (n=250 each, clean)

**Status: CONFIRMED, with a channel-attribution correction to the canonical
report.** User-prompted re-verification of disputed Gemma-4/Phi-4 leak-rate
numbers (no source anywhere in the corpus for the prior 76.7%/42.5% figures).
Result: a real, clean, n=250 measurement for both — and an important
correction to Phi-4's leak *channel*, not just its rate.

## Result

| Model | n | Errors | Visible leak | Reasoning leak | Total |
|---|---|---|---|---|---|
| gemma-4-e4b-it | 250 | 0 | **138 (55.2%)** [49.0, 61.2] | 0 (0.0%) | 55.2% |
| microsoft/phi-4-reasoning-plus | 250 | 0 | 0 (0.0%) | **246 (98.4%)** [96.0, 99.4] | 98.4% |

95% Wilson CIs in brackets. Methodology: `scripts/phase1-auto-harness.py`
(the script that produced the canonical `CROSS_MODEL_CANARY_LEAK_REPORT.md`
numbers), UUIDv4 canary embedded in 5 benign prompt templates (2 of which
explicitly ask the model to include the canary), `max_tokens=80`, run
against LM Studio's API (port 1234) with each model exclusively loaded.

## The Phi-4 finding: same magnitude, flipped channel

`CROSS_MODEL_CANARY_LEAK_REPORT.md` (2026-06-18) reports Phi-4 at
**98.3% leak via visible `content`**, 0% via `reasoning_content` — and
explicitly states "phi4 and gemma4 never generate reasoning tokens — canary
goes to `content`."

This rerun found the **same magnitude** (98.4% vs. 98.3% — statistically
indistinguishable) but in **`reasoning_content`, not `content`** (0.0%
visible here). The two results are too close in magnitude to be a different
phenomenon — this strongly suggests it's the *same* underlying leak,
mis-attributed to the wrong channel in the original report. Manually
confirmed: a single isolated test request to Phi-4 via LM Studio returned
`content: ""`, `reasoning_content: <361 chars containing the canary>` —
unambiguous.

**This directly confirms what the user originally flagged**: Phi-4 (and by
extension, possibly Gemma-4, though this rerun found Gemma-4 still leaks via
visible content, not reasoning) *does* leak via the reasoning channel,
contradicting the "phi4/gemma4 never generate reasoning tokens" claim in the
canonical report's methodology section.

**Why the discrepancy likely exists:** unclear with certainty, but plausible
explanations include a llama.cpp/LM Studio backend version difference between
2026-06-18 (canonical run) and now — chat-template-to-channel splitting
behavior for specific model families has changed across llama.cpp releases
(this session separately discovered the project's own self-built
`llama-server` binary has a *broken* content/reasoning split for this exact
Gemma-4 GGUF, returning empty in both fields regardless of `--reasoning-format`
or `--skip-chat-parsing` — a different bug, but evidence that this split
logic is fragile and version-sensitive for these specific models).

## The Gemma-4 finding: a real number, replacing an unsourced one

The corpus previously carried 76.7% (multiple files) and a corrected-but-still
-unverified 100% (n=8 spot-check) for Gemma-4, neither with a real source.
This rerun provides the first actual n=250 measurement: **55.2% visible
leak, 0% reasoning leak** — consistent with Gemma-4's architecture (no
reasoning channel), at a real measured rate rather than a guess.

## Process notes (cost/time, for anyone re-running this)

This took far longer than expected due to three separate infrastructure
problems, in order:
1. A wrong health-check in the orchestration script caused a silent
   zero-iteration false-success on the first attempt.
2. The project's own self-built `llama-server` (used for D2/D4's heap-residue
   work) has a **broken** chat-format parser for this specific Gemma-4 GGUF —
   `content` and `reasoning_content` both come back empty regardless of
   `--reasoning-format none` or `--skip-chat-parsing`, even on a trivial
   2-token "say hello" response with `finish_reason: stop`. Root cause
   unresolved; switched to LM Studio's bundled backend instead, which works
   correctly for both models.
3. A leftover loaded model (stale Nemotron instance from earlier D7 testing)
   held ~3GB of VRAM, causing Phi-4's load to fail with `cudaMalloc: out of
   memory` until manually cleared via `lms unload --all`.

Manual diagnostic `curl` calls sent to the *same* server while the automated
harness was actively iterating also contaminated one early attempt at
Gemma-4 (73% error rate from resource contention on the single inference
slot) — that run was discarded; this report reflects the clean rerun only.

## Honest limitations

- n=1 rerun (no repeats) for both models.
- The "same magnitude, flipped channel" theory for Phi-4 is the most
  parsimonious explanation but not directly proven — would need to run the
  *exact* 2026-06-18 binary/config to confirm definitively, which no longer
  exists in a runnable state.
- Gemma-4's broken content extraction on the project's self-built
  `llama-server` is an open, unresolved bug — worth filing upstream or
  investigating further if that binary is needed again for Gemma-4 testing.
