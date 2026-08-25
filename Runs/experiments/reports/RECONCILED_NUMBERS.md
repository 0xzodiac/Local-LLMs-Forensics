# Reconciled Numbers — Cross-Report Claim Reconciliation

**Date:** 2026-06-23
**Purpose:** Where the same finding appears in multiple reports with different numbers, identify which is canonical, which is superseded, and which is genuinely-different-conditions (not comparable). One table per claim category that appears in more than one report.

## How to read these tables

- **Canonical** — the latest, most-controlled measurement; cite this.
- **Superseded** — earlier, smaller-sample, or less-controlled measurement; the canonical row above it replaces it.
- **Different-conditions** — both numbers are correct under their own conditions but cannot be averaged or directly compared; cite both with the conditions.

---

## Claim 1: KV-cache RAM canary persistence count after slot release

| Source | Date | n | Pre-release copies | Post-release copies | Conditions | Status |
|---|---|---|---|---|---|---|
| `DEEP_LEAK_REPORT.md` | 2026-06-19 (WSL2) | many reqs | 11–42 (variance across models/configs) | 10 (after 2nd request) | LM Studio, original test, full slot cycle | **Canonical for pre-patch baseline** (referenced by `PLAN.md`, `RESEARCH_DOCUMENTATION.md`, `KV_CACHE_PATCH_REPORT.md`) |
| `KV_CACHE_PATCH_REPORT.md` §3.2 (re-probe, unpatched binary, isolated) | 2026-06-22 | 1 req | 11 | 10 | raw llama.cpp, single req, `--cache-ram 0` | Different-conditions: confirms DEEP's number with cleaner isolation, but only n=1, can't reproduce the 42-tail. Use both. |
| `KV_CACHE_PATCH_REPORT.md` §3.2 (re-probe, patched binary) | 2026-06-22 | 1 req | 12 | 11–12 | raw llama.cpp, single req, `--cache-ram 0`, with zeroization patch | **Methodology-mismatch (different signal)**: the canary-grep detects a *separate* heap-string leak surface, not the KV float tensor the patch targets. See `KV_CACHE_PATCH_REPORT.md` §3.2 for the full explanation. The patch's actual effect was verified directly via tensor-byte inspection (56/56 zeroed cells had real data pre-zero), not via this grep. |

**Reconciled claim:** KV-cache KV-tensor persistence: confirmed zeroed by Track E patch (verified directly). Heap-string persistence: ~10-12 copies persist after slot release, independent of the patch — separate finding, future work.

## Claim 2: Phi-4-reasoning-plus direct-repeat canary injection leak rate

| Source | Date | Backend | n | Leak rate | Conditions | Status |
|---|---|---|---|---|---|---|
| `PHI4_DEFENSE_NEW.md` | 2026-06-20 | LM Studio | 2 | 2/2 = 100% | 2 of 15 attempted prompts, others timed out at 90s | Superseded (n too small) |
| `PHI4_DEFENSE_LLAMACPP_REPORT.md` / `GAP_ANALYSIS_REPORT.md` Gap 4 | 2026-06-21 | raw llama.cpp | 3 | 1/3 = 33% | CPU, 1 tok/s, 6 of 15 succeeded | Superseded (n too small, characterized as sampling-variance) |
| `PHI4_DEFENSE_RESOLVED_REPORT.md` (Track B, this session) | 2026-06-23 | raw llama.cpp | 20 | 19/19 = 100% (of ok) | CPU, 1 tok/s, 1 timeout (iter 1, warmup) | **Canonical** |

95% Wilson CI on the canonical: (83.2%, 100.0%). The 33% earlier result was a sampling-variance artifact, not a defense difference.

## Claim 3: Phi-4-reasoning-plus role-manipulation injection leak rate

| Source | Date | Backend | n | Leak rate | Conditions | Status |
|---|---|---|---|---|---|---|
| `PHI4_DEFENSE_NEW.md` | 2026-06-20 | LM Studio | 2 | 0/2 = 0% | 2 of 15 attempted prompts | Superseded (n too small) |
| `PHI4_DEFENSE_LLAMACPP_REPORT.md` / `GAP_ANALYSIS_REPORT.md` Gap 4 | 2026-06-21 | raw llama.cpp | 2 | 0/2 = 0% | CPU, 1 tok/s | Superseded (n too small) |
| `PHI4_DEFENSE_RESOLVED_REPORT.md` (Track B, this session) | 2026-06-23 | raw llama.cpp | 20 | 0/20 = 0% | CPU, 1 tok/s | **Canonical** |

95% Wilson CI on the canonical: (0.0%, 16.1%). The model reliably refuses `role_reversal` (stable 13-token output, ~15s latency) but this is the easiest injection class — does not generalize to the 6 other categories, which are out of scope for Track B.

## Claim 4: Phi-4 CPU decode throughput

| Source | Date | n | Throughput (tok/s) | Conditions | Status |
|---|---|---|---|---|---|
| `PHI4_DEFENSE_NEW.md` (LM Studio) | 2026-06-20 | many | 1.06 (LM Studio log) | LM Studio (GPU-offloaded), `n_decoded` per-request | **Different-conditions** (different backend, not comparable to raw) |
| `PHI4_DEFENSE_LLAMACPP_REPORT.md` / `GAP_ANALYSIS_REPORT.md` Gap 4 | 2026-06-21 | 6 completed | 0.20–0.27 (mean 0.24) | raw llama.cpp, CPU, `n_decoded` per-request | **Canonical for raw CPU** |
| `KV_CACHE_PATCH_REPORT.md` §4 (Track E benchmark) | 2026-06-22 | 20 reqs | mean 9.84s/req (~1.0 tok/s at max_tokens=8) | raw llama.cpp CPU, unpatched, max_tokens=8 | Different-conditions: max_tokens too small to compare against n_decoded-based measurement |
| `KV_CACHE_PATCH_REPORT.md` §4 (Track E benchmark, patched) | 2026-06-22 | 20 reqs | mean 9.71s/req | raw llama.cpp CPU, patched, max_tokens=8 | Different-conditions (same as above) |
| `PHI4_DEFENSE_RESOLVED_REPORT.md` (Track B) | 2026-06-23 | 20 token_smuggle | mean 75.8s (57.4 output tokens = ~0.76 tok/s) | raw llama.cpp CPU, max_tokens=64 | Different-conditions: includes prompt-eval cost; not pure decode |

**Reconciled claim:** raw CPU phi-4-reasoning-plus is bound at ~0.2–0.3 tok/s for end-to-end token generation, with prompt-eval overhead adding substantial wall-clock cost (Track B's mean 75.8s with 57.4 output tokens = ~0.76 tok/s including prefill). The two ~1.0 tok/s numbers come from short-output scenarios where prompt-eval dominates the per-request budget.

## Claim 5: Multi-tenant cleartext memory recovery

| Source | Date | Tenants | Recovery rate | Conditions | Status |
|---|---|---|---|---|---|
| `DEEP_LEAK_REPORT.md` | 2026-06-19 (WSL2) | 12 | 12/12 (100%) | Sequential tenants, single memory read, ~1.24 MB cleartext recovered | **Canonical** (this is the headline cross-tenant finding; nothing has superseded it) |
| (no later re-test under controlled conditions) | — | — | — | — | gap |

## Claim 6: SGLang CVE-2026-5760 RCE reproduction

| Source | Date | Reproduction status | Conditions | Status |
|---|---|---|---|---|
| `SGLANG_RCE_REPRODUCTION_REPORT.md` | 2026-06-21 | Reproduced | Local sglang install, trigger via `/v1/chat/completions` crafted payload | **Canonical** (single source, not contradicted) |

## Claim 8: Reasoning-channel leak rate (Qwen3.5, Nemotron)

| Source | Date | n | Qwen3.5 reasoning leak | Nemotron combined | Status |
|---|---|---|---|---|---|
| `MASTER_FORENSICS_DOCUMENTATION.md` / `PAPER1_OUTLINE.md` / `PAPER_DRAFT.md` (pre-D6) | unknown | unstated | 78.3% | 88.3% | Superseded — no source backs these figures; likely a transcription/inflation error (D6 correction) |
| `CROSS_MODEL_CANARY_LEAK_REPORT.md` | 2026-06-18 | 250 (Qwen), 240 (Nemotron) | **56.0%** (140/250) | **41.2%** (100/240: 3 visible + 97 reasoning) | **Canonical** |

**D6 correction applied (this session):** propagated 78.3%→56.0% and 88.3%→41.2%
across `FINAL_AUDIT_REPORT.md`, `RESEARCH_PROGRESS_MASTER.md`,
`MASTER_FORENSICS_DOCUMENTATION.md`, `PAPER1_OUTLINE.md`, `PAPER_DRAFT.md`.
Left untouched (correctly, as historical/audit record): `PAPER_DRAFT_TIFS.md`
(already has the corrected number + a note about the prior mis-tabulation),
`PROGRESS_D1_D3.md` and `STRENGTH_WEAKNESS_MAP.md` (both document the
discrepancy itself), `CITATION_AUDIT.md` (generic hypothetical example, not
a claim about this project's data).

**Follow-up correction (same session, user-approved doc-only fix):** Phi-4's
42.5% had no source anywhere in the corpus and contradicted the canonical
98.3% (n=231) — replaced with 98.3% across the same 3 files. Gemma-4's 76.7%
also had no source; replaced with 100% (n=8 spot-check, explicitly marked
with an asterisk/caveat as a lower bound, not a final rate — no full-n
Gemma-4 test exists). `MASTER_FORENSICS_DOCUMENTATION.md`'s "Combined 71.5%"
row was left **not recomputed** (mixing n=8 with n=231-250 produces a
misleading single percentage) and flagged in-file instead. Its "Nemotron is
least secure" / "Gemma-4 76.7%" prose lines were reworded to match: Nemotron
is now correctly the *lowest* of the four (41.2%), not the highest.

Separately surfaced, NOT in scope of this fix: `MASTER_FORENSICS_DOCUMENTATION.md`'s
headline "71.5% overall canary token leakage rate, 480 adversarial prompt
injections" appears to belong to a **different experiment** entirely (the
8-attack-type adversarial study referenced in `RESEARCH_PROGRESS_MASTER.md`
item 6 / `PHASE2_CROSS_MODEL_REPORT.md`), not the canary-completion
reasoning-channel test this table is about. The two experiments look
conflated into one table in the original document. Untouched — this is a
structural/attribution issue, not a number-swap, and was outside the
approved scope of this fix.

**Real rerun, replacing the doc-only-fix placeholders above (same session,
user-requested):** the placeholder values just above (Phi-4 98.3%/0%,
Gemma-4 100%-n=8) have themselves now been superseded by an actual clean
n=250 rerun — see `GEMMA4_PHI4_RERUN_REPORT.md`. Result:

| Source | Date | n | Gemma-4 | Phi-4 | Status |
|---|---|---|---|---|---|
| doc-only-fix placeholder (above) | this session | n=8 (Gemma-4), n=231 (Phi-4, borrowed from canonical) | 100% visible (n=8 spot-check) | 98.3% visible, 0% reasoning | Superseded |
| `GEMMA4_PHI4_RERUN_REPORT.md` | 2026-06-24 | 250 each | **55.2% visible, 0% reasoning** [49.0, 61.2] | **0% visible, 98.4% reasoning** [96.0, 99.4] | **Canonical** |

**Phi-4 channel correction (important, not just a number update):** the
rerun's 98.4% total leak rate matches the canonical report's 98.3% almost
exactly — but the channel is flipped (reasoning_content, not content). This
directly contradicts the canonical report's claim that "phi4 and gemma4
never generate reasoning tokens." Manually confirmed via an isolated request:
Phi-4 returned `content: ""`, `reasoning_content: <361 chars, canary
present>`. Most likely explanation: a llama.cpp/LM-Studio backend version
difference between the 2026-06-18 canonical run and now changed how Phi-4's
chat template gets split into content vs. reasoning_content — not a new
leak, the same leak now correctly attributed.

Action needed: `MASTER_FORENSICS_DOCUMENTATION.md`, `PAPER1_OUTLINE.md`,
`PAPER_DRAFT.md` need their Gemma-4/Phi-4 table cells updated again, from the
placeholder values to these real ones, with Phi-4 moved into the Reasoning
Leak column instead of Visible Leak.

**Original investigation context (the prior left-out-because-no-canonical-replacement note this superseded):** Left untouched because there's no canonical
replacement value to substitute — re-deriving one would be guessing, not
correcting. Downstream effects of this open gap:
- `MASTER_FORENSICS_DOCUMENTATION.md`'s "Combined 71.5% (343/480)" row was
  computed from the old (now partly wrong, partly unverified) per-model
  numbers — that combined total is now stale and should not be cited as-is.
- The same file's "NVIDIA-Nemotron-3 is least secure" claim is now
  arithmetically backwards using the corrected numbers (Nemotron 41.2% <
  Qwen 56.0% < Gemma-4's unverified 76.7%) — flagged, not silently reworded,
  since fixing the prose requires resolving the Gemma-4/Phi-4 numbers first.

## Claim 7: KV-cache zeroization patch overhead

| Source | Date | n | Unpatched (mean) | Patched (mean) | Overhead | Conditions | Status |
|---|---|---|---|---|---|---|---|
| `KV_CACHE_PATCH_REPORT.md` §4 | 2026-06-22 | 20 reqs each | 9.84s/req | 9.71s/req | not measurable above noise (patched nominally faster) | raw llama.cpp CPU, max_tokens=8, --parallel 1 | **Canonical** (n=20 not 100, deviation from spec documented in the report) |

---

## Gaps in the reconciliation

- **No cross-model direct-repeat test at n=20** for qwen3.5-9b, nemotron-3-nano-4b, or gemma-4-E4B-it. The single 95% leak rate finding is phi-4-specific. The other 3 models' direct-repeat leak rates remain at the prior smaller sample sizes (n=2-3 each).
- **No VRAM cross-tenant recovery** (gap from WSL2 days; awaiting CUDA-enabled llama.cpp build on this machine — see `GPU_VRAM_REPORT.md`).
- **gemma-4-E4B-it is not in the re-test scope** of this session (Track B used phi-4 only). Its prior leak-rate findings stand at their original sample sizes.

## What to cite where

- **Paper §"KV-cache vulnerability"** → cite DEEP_LEAK_REPORT.md (11–42 copies, pre-patch baseline) + KV_CACHE_PATCH_REPORT.md §3.1 (mechanism verified directly) + §3.2 (methodology-mismatch caveat, heap-string leak as separate finding).
- **Paper §"Phi-4 defense characterization"** → cite PHI4_DEFENSE_RESOLVED_REPORT.md (canonical, n=20) + the prior reports as historical/superseded. Explicitly state the LM-Studio-vs-raw-llama.cpp comparison is now closed (no defense difference).
- **Paper §"Patch overhead"** → cite KV_CACHE_PATCH_REPORT.md §4 (canonical, n=20).
- **Paper §"Multi-tenant risk"** → cite DEEP_LEAK_REPORT.md (canonical, 12/12).