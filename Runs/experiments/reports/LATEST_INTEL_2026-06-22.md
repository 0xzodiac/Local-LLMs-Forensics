# Latest Intel Sweep — 2026-06-22

**Method:** Web search across infosec/academic/dark-web-intelligence sources, run while Stage 0 model downloads completed in the background. Same evidence-labeling discipline as `RESEARCH_DOCUMENTATION.md` §14: every claim below is a **sourced fact** (from the cited outlet) unless marked **inference**. Nothing here was independently re-verified against primary sources (NVD/GHSA) the way `FINAL_STATUS_REPORT.md` did for the original 5 high-stakes citations — treat these as leads to verify before citing in the paper, not yet citation-grade.

---

## 1. NEW — CVE-2026-5760: GGUF Weaponization Achieves Full RCE on SGLang (CVSS 9.8)

**This is the single most significant new finding from this sweep.** Every prior CVE in our `GGUF_CVE_LANDSCAPE.md` (including Bleeding Llama, CVSS 9.1) is a memory-*disclosure* primitive — read past a buffer, leak heap contents. CVE-2026-5760 is reported as a full **remote code execution** vulnerability: a crafted GGUF model file compromises the SGLang inference server itself, not just its memory contents.

- Source: cybersecuritynews.com, letsdatascience.com ("Hackers Could Weaponize GGUF Models to Achieve RCE on SGLang Inference Servers")
- Severity: CVSS 9.8 (higher than any CVE currently in our landscape doc)
- Scope: model metadata supply-chain risk — the malicious payload rides in the GGUF file itself, same delivery vector as our entire Track A fuzzing work, just targeting a runtime (SGLang) we have never tested
- **Action:** `CONTINUATION_PLAN.md` Track A/G should add SGLang as a 5th runtime to test against, not just LM Studio/Ollama/raw-llama.cpp. This single CVE could become the paper's strongest "the attack surface is the file format itself, not any one runtime" argument — it's runtime-independent proof of the thesis.
- **Verify before citing:** primary source (NVD/GHSA advisory) not yet checked directly.

## 2. NEW — Ollama Auto-Updater RCE Chain (CVE-2026-42248, CVE-2026-42249)

Different attack surface entirely — not the GGUF parser, the **Windows update mechanism**.

- Source: Striga research via helpnetsecurity.com, "Unpatched flaws turn Ollama's auto-updater into a persistent RCE vector"
- CVE-2026-42249 (CVSS 7.7): path traversal — the Windows updater builds its installer staging path directly from unsanitized HTTP response headers
- Disclosed 2026-01-27, **still unpatched** as of the 90-day public-disclosure deadline
- **Relevance:** broadens the paper's "wrapper is the weakest link" thesis (Discovery 2) beyond LM Studio's logging default — Ollama, the project's own "clean control case" for logging, has its own unrelated critical wrapper-layer hole. Worth a sentence in Limitations/Discussion: "even the wrapper we used as a negative control has its own (orthogonal) critical vulnerability" — strengthens rather than undermines the paper, since it's a different vector than the one tested.

## 3. NEW — Two KV-Cache Mitigation Papers Not Yet in Our Reference List

- **CacheSolidarity** (arXiv 2603.10726) — "Preventing Prefix Caching Side Channels in Multi-tenant LLM Serving Systems." Same problem class as SafeKV (already cited), different mechanism. Should sit alongside SafeKV in `PAPER1_OUTLINE.md` §2.4.
- **Wiretapping LLMs: Network side-channel attacks on interactive LLM services** (2025) — network-layer side channel, broader than KV-cache specifically. Relevant context for Discovery 3 (network-cleanliness red herring) — shows the field is already moving past "no egress = safe" too.
- **SALT: Steering Activations towards Leakage-free Thinking** (arXiv 2511.07772) — reasoning-trace leakage mitigation via activation steering, reduces leakage on Llama-3.1-8B/QwQ-32B/DeepSeek-1.5B. Another mitigation candidate for §2.3.
- **Chain-of-Sanitized-Thoughts** (arXiv 2601.05076) — PII-specific CoT sanitization. Same section.

## 4. Citation Discrepancy Found — Flag for Audit

Our `PAPER1_OUTLINE.md` reference #9 cites **"From Leaky Thoughts to Private Reasoning" (Batra et al., arXiv 2602.24210, 2026)**. This sweep found the same arXiv ID (2602.24210) titled **"Controllable Reasoning Models Are Private Thinkers."** Either the paper was retitled between preprint revisions, or one of the two titles is wrong.

- **Action:** This is exactly the kind of secondary-citation gap `RESEARCH_PROGRESS_MASTER.md` §3 already flagged as unaudited. Add to Stage 5's `CITATION_AUDIT.md` task explicitly — pull the actual arXiv abstract page for 2602.24210 and confirm current title before the paper goes anywhere near submission.

## 5. NEW — Open-Weight-Specific Memorization Papers (Directly On-Point for Track D)

Our memorization finding (Probes 3b/3c) currently cites Carlini et al. ICLR 2025 (frontier API extraction) as the closest prior art. These are closer:

- **"Extracting memorized pieces of (copyrighted) books from open-weight language models"** (arXiv 2505.12546) — same exact threat model as our work (open-weight, not API), same target (copyrighted books — we used Harry Potter specifically).
- **"Extracting alignment data in open models"** (arXiv 2510.18554) — relevant to Track D's expansion plan.
- **Quantified comparator stat:** general open-source-model memorization literature reports extraction rates of **0.1%–1%** of training data (different metric than our "60% verbatim depth on known canonical texts," but worth citing as a field-calibration point — our number is intentionally targeting texts we know are memorizable, theirs is unconditional extraction rate across an unknown corpus. Don't conflate the two numbers in the paper; cite both with the metric difference explicit).
- **Action:** Track D (`CONTINUATION_PLAN.md`) should cite arXiv 2505.12546 as the primary related-work anchor instead of/alongside Carlini ICLR 2025 — it's a closer match to our exact setup.

## 6. NEW — Our Own Meta-Finding (Agent-Harness Injection) Is Part of a Documented 2026 Pattern

`AGENT_HARNESS_INJECTION_LOG.md` documents prompt injection aimed at the research agent itself, currently scoped as an interesting but isolated anecdote. This sweep found it's a recognized, actively-studied 2026 threat class:

- **"Prompt Injection Attacks on Agentic Coding Assistants: A Systematic Analysis of Vulnerabilities in Skills, Tools, and Protocol Ecosystems"** (arXiv 2601.17548, Jan 2026) — finds **85%+ of attacks succeed even against state-of-the-art defenses** on tools including Claude Code, Copilot, Cursor.
- **"Claudy Day"** (Oasis Security, March 2026) — full attack pipeline chaining invisible prompt injection with data exfiltration against claude.ai, stealing conversation history from a default session.
- SecurityWeek (2026): Claude Code, Gemini CLI, GitHub Copilot Agents all shown vulnerable to prompt injection via code comments.
- Anthropic shipped remediations in `claude-code-action v1.0.94` / `@anthropic-ai/claude-code v1.0.93`+.
- A practical defense pattern exists: planting a canary/honeypot string that should never trigger tool use, to detect injection attempts in real time (ianlpaterson.com).
- **Action:** This justifies promoting the agent-harness-injection meta-finding from a footnote to a proper short subsection in the paper (per `RESEARCH_PROGRESS_MASTER.md` §5's suggestion) — it's not an isolated anecdote, it's a documented instance of a named, actively-studied attack class, observed from the *defender's* side during a live security research session rather than as a deliberate red-team exercise. That framing (an attack hitting the tooling of researchers studying a different, unrelated attack surface) is a genuinely novel angle most papers in this space don't have.

## 7. Underground/Dark-Web Chatter — Context, Not Citable Evidence

Defensive-research framing only; none of this is independently verifiable and should not be cited as fact in the paper, only as motivating context for why the threat model matters:

- Dark-web threat-intel vendors (ZeroFox, CyberAngel, Group-IB) report an active marketplace: ~212 "malicious LLM" listings, jailbreak-as-a-service offerings, claimed jailbreaks for current frontier models advertised on Telegram/forums as of June 2026.
- A claimed extraction of a newly-released model's system prompt was advertised within a day of that model's public release (illustrates the speed of the adversarial-extraction ecosystem our Phase-2 work is part of, even if the specific claim is unverifiable marketing-for-criminals puffery).
- **Use only as scene-setting in the Introduction** ("a thriving underground market for exactly the kind of extraction this paper demonstrates exists") — never as a sourced technical claim.

## 8. Disclosure-Process Failure Worth Citing for Our Own Stage 3

CVE-2026-7482 (Bleeding Llama) timeline, now fully documented:

- Patched in Ollama v0.17.1 (2026-02-25) — **but the release notes didn't flag it as a security fix.**
- MITRE didn't respond to the CVE request for **two months**.
- Without a CVE number, the fix was invisible to scanners/patch management for that entire window.
- Public disclosure/CVE assignment landed ~3 months after the patch shipped.

**Action:** This is directly useful for `CONTINUATION_PLAN.md` Stage 3 (Responsible Disclosure) — it's evidence that even a well-intentioned, prompt patch can leave a multi-month real-world exposure window if the CVE/advisory process lags. Strengthens the argument for treating our own LM Studio logging-default finding and any Track E patch with an explicit, tracked disclosure timeline rather than assuming "we published a report" is sufficient.

---

## Summary: What to Fold Into Existing Docs

| New item | Target doc | Action |
|---|---|---|
| CVE-2026-5760 (SGLang RCE) | `CONTINUATION_PLAN.md` Track A/G, `PAPER1_OUTLINE.md` §2.1 | Add SGLang as 5th runtime; strongest new "file format is the surface" evidence |
| CVE-2026-42248/249 (Ollama updater) | `PAPER1_OUTLINE.md` §10 / Limitations | One sentence: even the logging-clean control wrapper has its own unrelated critical hole |
| CacheSolidarity, Wiretapping LLMs, SALT, Chain-of-Sanitized-Thoughts | `PAPER1_OUTLINE.md` §2.3/§2.4 references | Add to related-work list |
| arXiv 2602.24210 title mismatch | Stage 5 `CITATION_AUDIT.md` | Verify actual current title before submission |
| arXiv 2505.12546, 2510.18554 (open-weight memorization) | Track D, `PAPER1_OUTLINE.md` §2.2 | Cite as closer prior art than Carlini ICLR 2025 |
| arXiv 2601.17548, "Claudy Day" | `AGENT_HARNESS_INJECTION_LOG.md` cross-ref, paper Methodological Note | Promote meta-finding using this as supporting context |
| Bleeding Llama disclosure timeline | Stage 3 (Responsible Disclosure) | Cite as cautionary precedent for our own disclosure plan |

**Not yet done:** none of these citations have been verified against primary sources the way the original 5 high-stakes citations were in `FINAL_STATUS_REPORT.md` §3. Before any of this lands in the paper, run the same live-verification pass (fetch the actual NVD/arXiv/GHSA page, confirm CVSS/title/date match what's reported here).
