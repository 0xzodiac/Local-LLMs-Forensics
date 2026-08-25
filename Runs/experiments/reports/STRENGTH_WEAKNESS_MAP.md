# Honest Strength/Weakness Map — TIFS Readiness

*Built from full-corpus read + 3 independent audits. No sugar-coating.*

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FINDING-BY-FINDING VERDICT                          │
│  ✅ submit-ready   ⚠️ fix-needed   ❌ drop-or-downgrade                │
└─────────────────────────────────────────────────────────────────────────┘

1. KV-cache zeroization patch (89 lines) ............................. ✅
   - Real, backend-portable, safety-gated, benchmarked (n=20, overhead
     unmeasurable). Formal proof I2 in §8 is sound.
   - BUT: v_trans=false path NOT unit-tested; GPU path untested.

2. logSensitiveData:true default → cleartext disk logs ............... ✅
   - Strongest single piece of evidence in the whole corpus (on/off
     differential, MITIGATION_TEST_REPORT §3). Real, reproducible, mitigable.

3. Unprivileged heap-string leak (~135KB/slot, 13 copies) ........... ✅
   - multilayer_v2 + monitor logs back it. The ACTUAL unprivileged path.
   - BUT: this is what the numbers measure — NOT the KV-tensor the patch fixes.

4. Network negative result (no telemetry, 4-model + cross-instrument) . ✅
   - Real, but it's a NEGATIVE result. Role = §6 "red herring," not headline.

5. Prior-art positioning (Shadow-in-the-Cache delta, SafeKV axis) .... ✅
   - Best-prepared part: 3 axes cleanly distinguished. NDSS 2026 cited.

6. Ollama clean control (disk-logging axis) .......................... ✅
   - Real (recursive grep). Network-axis control gap CLOSED: D5 re-ran the
     same netns-isolation harness against Ollama across all 4 models —
     0 external connections of any kind, stronger than LM Studio's result.
     See `TELEMETRY_FINDINGS_OLLAMA.md`.

7. Cross-model reasoning-channel split (visible vs reasoning_content)  ✅
   - Number discrepancy RESOLVED (D6 + a clean n=250 rerun): Qwen 56.0%
     reasoning leak (was correctly 56% already); Phi-4 corrected from a
     misattributed 98.3%-via-content to 98.4%-via-reasoning_content (same
     magnitude, right channel now); Gemma-4 measured at 55.2% visible leak
     (replacing an unsourced 76.7%/100% guess). See
     `GEMMA4_PHI4_RERUN_REPORT.md`, `RECONCILED_NUMBERS.md` Claim 8. Leaky
     Thoughts EMNLP 2025 remains close prior art — still cite it.

8. Multi-tenant KV recovery (12/12, 1.24MB) .......................... ⚠️
   - HEADLINE number but NO retained artifact. Must re-run or downgrade.

9. GPU VRAM "9 copies, 16/16" ........................................ ⚠️
   - Real logs back it — but it's host pinned-mem (RAM), NOT GPU VRAM.
     n=3. Honestly self-corrected (v5 invalidates v1-v4).

10. Phi-4 no-defense (100% leak, n=20, Wilson CI) ................... ⚠️
    - Real, statistically defensible. BUT only phi-4 at n=20; other 3 models
      stuck at n=2-3. Prompt-injection = well-trodden ground.

11. GGUF "80+ attack variants, 9 logic failures" .................... ❌
    - NEGATIVE result dressed as positive. Parser is SAFE against these
      variants (all exit(1)/assert). "Validation-gap taxonomy" reads as
      padding. The real CVEs are someone else's already-patched work.

12. SGLang RCE (CVE-2026-5760) "reproduced" ......................... ❌
    - Explicitly NOT REPRODUCED (SGLang 0.5.13 patched). Misframed in draft
      as GGUF-parser RCE — it's Jinja2 SSTI (GGUF is delivery vector).

13. Memorization (59.6%/61.7%/40.2%) ............................... ⚠️
    - Real data, but Cooper et al. arXiv 2505.12546 (200 books × 14 models)
      DWARFS it. Not novel as standalone; cite as complement.

14. CVSS 7.5 AV:N (DEEP_LEAK) ....................................... ❌
    - WRONG for THIS finding. Primitive is LOCAL, same-UID, parent-of-victim.
      Honest CVSS ~4.4-5.5 AV:L. Reviewer will strike.
    - BUT: a genuine AV:N finding now exists separately (#16) — don't fix
      this by overclaiming DEEP_LEAK; cite #16 instead for the AV:N axis.

15. "30-day retention" for server logs .............................. ❌
    - Contradicted by project's OWN mitigation report: server logs have NO
      TTL, persist indefinitely. Fix wording (ironically stronger claim).

16. Cross-tenant `/slots` restore — unauthenticated session hijacking ✅
    - NEW this session. Genuinely AV:N (no local access, no /proc/mem) —
      the finding #14 above wished it had. Confirmed via exact
      n_saved/n_restored match, 3 independent setups (nemotron/CPU,
      Phi-4/CPU, Qwen3.5/GPU). CWE-862 + CWE-200. Real CVSS candidate:
      AV:N/AC:L/PR:N(or L if --api-key set, since the key check is global
      not per-resource)/UI:N — should self-rate, don't hand-wave.
    - Honest gap: no verbal/textual extraction demo completed (blocked by
      an unrelated build-wide parser bug, not the exploit) — the data-copy
      proof at the protocol level stands on its own and doesn't need it.
    - This should be the paper's headline finding, or at minimum sit
      alongside #2/#3 as a third pillar — it's the only result that needs
      no local host access.
```

## The 3 structural problems (these decide everything)

```
PROBLEM 1: THE PATCH AND THE NUMBERS MEASURE DIFFERENT THINGS
──────────────────────────────────────────────────────────────
  Patch fixes:    KV-cache FLOAT TENSOR (privileged to observe)
  Numbers prove:  HEAP-STRING leak (unprivileged, 13 copies)
                  
  → The patch has ZERO demonstrated effect on any headline number.
    A hostile reviewer reads this as "the patch does nothing."
    FIX: reframe headline = unprivileged heap-string leak (the real
         finding); patch = KV-tensor defense-in-depth (separate axis).

PROBLEM 2: SCOPE INFLATION
──────────────────────────
  Draft Abstract claims 5 contributions across 3 layers.
  Reality: 2 are real & strong (KV/heap + logSensitiveData), 2 are
  negative results (network, GGUF-parser), 1 is overstated (reasoning
  channel, prior-art-heavy). SGLang "reproduced" is a fourth, false one.
  
  FIX: cut to a 2-contribution paper. Depth > breadth for TIFS.

PROBLEM 3: DISCLOSURE NOT DONE (PUBLICATION BLOCKER)
─────────────────────────────────────────────────────
  Zero vendor notifications sent. No llama.cpp PR. No CVE.
  TIFS/S&P/USENIX/NDSS ALL require coordinated disclosure statement.
  This is the single largest non-empirical blocker.
```

## TIFS readiness scorecard

```
                              NOW    AFTER FIXES (36h)
Methodology rigor              7/10      8/10
Novelty (vs Shadow/Leaky)      5/10      6/10
Evidence/artifact backing      6/10      8/10
Formal depth (proof)           7/10      7/10
Reproducibility (n≥3)          4/10      6/10
Coordinated disclosure         0/10      10/10 (if you send)
Writing (continuous prose)     3/10      5/10
─────────────────────────────────────────────────────
OVERALL TIFS-readiness         ~46%      ~67%

Realistic target venue:
  NOW:           workshop / B-tier (AsiaCCS, EuroS&P-W)
  AFTER 36h:     PETS (PoPETs) A — best topical fit
                 USENIX Security A* — if disclosure done + n≥3
  TIFS:          needs the most work (writing + 1 more cycle)
```
