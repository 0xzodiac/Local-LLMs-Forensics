# PoPETs Execution Plan — "The Local-LLM Privacy Boundary"

**Target:** PoPETs (Privacy Enhancing Technologies), CORE A, rolling submission.
**User constraint:** PhD application in Australia; needs CORE A/A*; limited time.
**Key decision:** Optional disclosure (not blocking PoPETs — see ethics section).

---

## Why PoPETs (honest)

- CORE A — accepted for Australian PhD applications (A* not strictly required).
- Rolling submission (4 issues/year, no hard deadline) — submit when ready.
- Topically optimal: "Privacy Enhancing Technologies" is literally the venue name.
- Lower barrier than TIFS on coordinated-disclosure strictness (BUT we still write
  an ethics statement — see below).

## The honest disclosure position for PoPETs

PoPETs does expect responsible disclosure for *exploitable live-software
vulnerabilities*. Our position, stated honestly:
- `logSensitiveData:true` — this IS disclosable; we will disclose it (timeline
  in the paper). PoPETs is fine with "disclosed, vendor response pending."
- KV-cache/heap-string residual — this is a **design analysis / data-hygiene
  finding**, NOT an exploitable vuln with a privilege boundary crossing. We
  treat it as research contribution + upstream PR, not a CVE-track disclosure.

This is defensible. We will NOT hide the logSensitiveData disclosure — we'll
state the timeline honestly. The 90-day clock is not a hard PoPETs blocker
(the way it is for S&P/USENIX) because PoPETs reviews the methodology, not
the live-exploit window.

---

## Paper restructure: 2 contributions, not 5

**OLD (overstated, 5 contributions):** KV-cache + reasoning channel + wrapper
forensics + GGUF taxonomy + SGLang.

**NEW (honest, 2 strong contributions):**

**Contribution 1 — Unprivileged data-at-rest leakage in local LLM serving.**
The heap-string leak surface: ~135KB/slot formatted-prompt buffer, never freed
on slot release, readable by any same-UID parent process via `/proc/<pid>/mem`.
13 copies/tenant persist across 3 subsequent requests + 10s idle. Multi-tenant
recovery 100% (12/12 — TO RE-RUN WITH RETAINED LOG). This is the headline.

**Contribution 2 — Wrapper forensics: default-on cleartext logging.**
LM Studio's `logSensitiveData:true` default writes every API interaction to
cleartext disk logs (no observed retention limit). On/off differential proven.
Ollama clean control (disk axis). This is the forensics contribution.

**Supporting (demoted from contribution → evidence):**
- Network negative result (4 models, netns isolation) = §"red herring" / RQ1.
- KV-cache patch + formal proof = §defense-in-depth (NOT headline — the patch
  fixes a different surface than the leak we measure; we state this honestly).
- Prior-art positioning (Shadow NDSS 2026, SafeKV, Leaky Thoughts) = §related.

**DROPPED (negative/false results dressed as positive):**
- GGUF "80+ variants" → negative result, parser is safe → mention as RQ0 only.
- SGLang "reproduced" → NOT reproduced, patched → drop entirely.
- "12 CVEs contextualization" → 1-sentence related-work mention.
- Reasoning channel as headline → demote to appendix (prior-art-heavy).

---

## Execution order (priority-ordered for time pressure)

### Phase A — Fix the data (highest value, ~3-4h)
1. **Re-run 12/12 multi-tenant probe WITH retained JSON log.** This is the
   single weakest headline number (no artifact). Fix it first.
2. **n≥3 on heap-string leak** (multilayer_v2, 3 independent runs) → variance bars.
3. **Correct the number discrepancies** documented in STRENGTH_WEAKNESS_MAP.md.

### Phase B — Restructure the paper (~6-8h)
4. Rewrite Abstract to 2-contribution form.
5. New §1 intro, §2 threat model (PR:L same-UID, not AV:N).
6. §3 setup (4 models, 3 backends: LMS/llama.cpp/Ollama).
7. §4 Contribution 1 (heap-string leak) — the headline.
8. §5 Contribution 2 (wrapper forensics).
9. §6 RQ1 network red-herring (negative result).
10. §7 KV-cache patch as defense-in-depth (formal proof §8).
11. §9 related work (Shadow/SafeKV/Leaky Thoughts/Cooper memorization).
12. §10 limitations + ethics (disclosure timeline).
13. §11 conclusion.

### Phase C — PoPETs formatting (~3-4h)
14. Continuous prose (not outline).
15. IEEEtran/De Gruyter template.
16. Ethics statement (disclosure status).
17. Limitations honest (n, single hardware, GPU path).

### Phase D — Optional (~1 day)
18. Disclosure send (if user ready) — strengthens the ethics section.
19. Ollama network control (strengthens §6).

**Total realistic: ~2-3 days focused work → PoPETs-ready.**
