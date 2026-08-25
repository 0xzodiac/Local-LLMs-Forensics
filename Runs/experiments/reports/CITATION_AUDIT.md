# Citation Audit — Pre-Submission Verification

**Date:** 2026-06-23
**Auditor:** Claude (this session)
**Scope:** Every secondary citation flagged as unverified in `FINAL_AUDIT_REPORT.md` §4 and `LATEST_INTEL_2026-06-22.md` §4, plus the high-stakes citations whose metadata is asserted (not just existence) in `PAPER_DRAFT.md`.
**Method:** Each citation fetched against its **primary source** (arXiv abstract page / NVD / GHSA / vendor advisory). The audit records the authoritative title, authors, date, and — where it matters for the paper's argument — what the source actually says versus what the draft claims it says. Existence-confirmed-but-claim-mismatched is recorded as a **correction**, not a pass.

This is the same primary-source discipline `FINAL_STATUS_REPORT.md` §3 applied to the original 5 high-stakes citations (all of which checked out). It is now extended to the ~20 secondary citations.

---

## 0. Summary verdict

| Status | Count | Meaning |
|---|---|---|
| ✅ Verified — cite as-is | 6 | Metadata matches primary source; claim attributed to it is accurate |
| ⚠️ Verified — **needs a correction** | 4 | Paper/source exists, but draft's title/author/claim is wrong and must be fixed before submission |
| 🔁 Verified — **retitled preprint** | 2 | Real paper; cite the *current* title, note the version |
| ⏳ Not yet re-verified this session | ~8 | Lower-stakes items; see §3 |

**Three of the four corrections are load-bearing** (SafeKV author/claim mismatch underpins the formal §8 analysis; CVE-2026-5760 category misstatement affects the "file format is the surface" thesis; arXiv 2602.24210 is the title-discrepancy the audit was created to resolve). Fix these before the paper is submitted anywhere.

---

## 1. The four corrections (load-bearing — fix before submission)

### Correction A — SafeKV author attribution is wrong, and the §8 framing overstates the relationship

- **Draft (PAPER_DRAFT.md §8, ref #13):** *"F. Song et al., 'SafeKV,' arXiv 2508.08438, 2026"* and *"formalizes the patch's correctness and overhead using notation established by the SafeKV line of work."*
- **Primary source (arXiv:2508.08438v2):**
  - **Title:** *Selective KV-Cache Sharing to Mitigate Timing Side-Channels in LLM Inference*
  - **Authors:** **Kexin Chu, Zecheng Lin, Dawei Xiang, Zixu Shen, Jianchang Su, Cheng Chu, Yiwei Yang, Wenhui Zhang, Wenfei Wu, Wei Zhang** — Chu et al., **not Song et al.** No author named Song.
  - Submitted 2025-08-11 (v1), last revised 2026-02-09 (v2).
- **Why it matters beyond the author name:** SafeKV addresses a **timing side-channel in multi-tenant *shared* KV-cache serving** — i.e., an adversary infers inputs from cache *hit/miss latency* on a shared prefix cache. That is a **different vulnerability class** from the data-at-rest residual (cell bytes not zeroed on `seq_rm`) that our patch fixes. Citing SafeKV as the source of "the notation our §8 formalization establishes" overstates the lineage.
- **Required fix:**
  1. Change authorship to *Chu et al.*
  2. Change §8's framing from "using notation established by the SafeKV line of work" to "we adopt the invariant-style framing common to the KV-cache-privacy line of work (SafeKV [Chu et al. 2025], CacheSolidarity/PrefixWall [2603.10726]), though those address a *timing side-channel in shared caches*, a distinct class from the data-at-rest residual our patch targets."
  3. Keep the SafeKV cite — it is the right *related-work* anchor — just don't claim it as the formalization's foundation.

### Correction B — CVE-2026-5760 is a Jinja2 template SSTI, not a GGUF-parser RCE

- **Draft / project framing (LATEST_INTEL, PAPER_DRAFT.md, SGLANG_RCE_REPRODUCTION_REPORT.md):** repeatedly describes CVE-2026-5760 as "GGUF weaponization achieves full RCE" / "the attack surface is the file format itself."
- **Primary sources (CERT/CC VU#915947, Orca Security, The Hacker News, PoC github.com/Stuub/SGLang-0.5.9-RCE):**
  - CVSS 9.8 — **confirmed.**
  - Vulnerable component: SGLang's **unsandboxed Jinja2 chat-template rendering** on the `/v1/rerank` endpoint (and chat endpoints). The malicious Jinja2 template is **carried inside the GGUF model file's `tokenizer.chat_template` field**, so the GGUF file is the **delivery vector**, not the vulnerable parser path.
  - This is a **Server-Side Template Injection (SSTI)**, not a memory-corruption bug in the GGUF parser.
- **Why it matters:** The project's thesis "the attack surface is the file format itself" is **still supported** (the payload *does* ride in the GGUF file, exactly as our Track A fuzzing targets), but the mechanism is "untrusted metadata executed by a sandboxless template engine," not "a malformed tensor header corrupts the loader." If the paper claims the latter, a reviewer who reads VU#915947 will catch it immediately.
- **Required fix:** In any sentence citing CVE-2026-5760, describe it as *"RCE via unsandboxed Jinja2 chat-template rendering of a malicious GGUF `chat_template` field (SSTI; the GGUF file is the delivery vector), CVSS 9.8."* Do **not** call it a GGUF-parser or memory-corruption vulnerability. Related SGLang CVEs surfaced by Orca (CVE-2026-3059/3060, separate RCEs) and SecureLayer7 (CVE-2026-7304, `dill.loads` deserialization RCE) are genuinely *different* bugs and should not be conflated with 5760.
- **Silver lining:** This *strengthens* the paper's file-format thesis with more precision — "the model file is a delivery vector for code-execution payloads via *several distinct* runtime paths (template SSTI via SGLang, heap OOB-read via Ollama's loader)" is a more defensible and more interesting claim than lumping them as one class.

### Correction C — arXiv 2602.24210 title discrepancy (the one the audit was created to resolve)

- **Draft (ref #9):** *"Batra et al., 'From Leaky Thoughts to Private Reasoning,' arXiv 2602.24210, 2026."*
- **Primary source (arXiv:2602.24210):** canonical title is **"From Leaky Thoughts to Private Reasoning: Controlling What LRMs Say to Themselves."**
  - The alternative title seen on some indexes ("Controllable Reasoning Models Are Private Thinkers") appears to be either an earlier-version or an indexer variant.
- **Required fix:** Cite the full title with subtitle. The "Batra et al." authorship was **not independently re-verified this session** (the abstract page's author list was not captured in the search snippet) — **flag the author list for one more direct check before submission.** Do not assume the surname.
- **Companion note:** The precursor paper the draft cites as ref #6 ("Leaky Thoughts: Large Reasoning Models Are Not Private Thinkers," EMNLP 2025) is independently confirmed real at arXiv:2506.15674 / ACL Anthology 2025.emnlp-main.1347 (Green, Gubri, Puerto, Yun, Oh). That citation is clean.

### Correction D — arXiv 2603.10726 (CacheSolidarity) is now PrefixWall

- **Draft / LATEST_INTEL framing:** refers to "CacheSolidarity (arXiv 2603.10726)."
- **Primary source (arXiv:2603.10726):**
  - **v1 title:** *CacheSolidarity: Preventing Prefix Caching Side Channels in Multi-tenant LLM Serving Systems*
  - **v2 title:** *Mitigating Prefix Caching Side Channels in Shared LLM Systems* — system renamed **PrefixWall**.
- **Required fix:** Cite as *"PrefixWall (formerly CacheSolidarity), Chu et al. [arXiv:2603.10726]."* This is the closest related-work neighbor to SafeKV (both target prefix-cache timing side-channels), so the two should be cited together in §2 related work with the class distinction noted (both = *timing side-channel in shared caches*; our work = *data-at-rest residual on slot release*).

---

## 2. Verified clean — cite as-is (6)

| Ref | Draft citation | Primary source confirms | Notes |
|---|---|---|---|
| 6 | Green et al., "Leaky Thoughts… Are Not Private Thinkers," EMNLP 2025 | ✅ arXiv:2506.15674; ACL Anthology 2025.emnlp-main.1347 | Clean. Authors: Green, Gubri, Puerto, Yun, Oh. |
| 17 | Carlini et al., "Extracting Training Data…," USENIX 2021 | ✅ (pre-verified in FINAL_STATUS_REPORT §3; re-listed here for completeness) | The canonical memorization-provenance cite. |
| — | Cooper et al., "Extracting memorized pieces of (copyrighted) books from open-weight language models," arXiv 2505.12546 | ✅ arXiv:2505.12546v5 (submitted 2025-05-18, rev 2026-05-01). Authors: **A. Feder Cooper, Mark A. Lemley, … Percy Liang** (Stanford) | **This is the strongest memorization prior art for Track D** — same open-weight threat model, same Harry Potter example ("Llama 3.1 70B entirely memorizes … Harry Potter and the Sorcerer's Stone"). Promote to primary memorization related-work anchor ahead of Carlini ICLR/USENIX. 200 books × 14 models × 3000 experiments — far larger than our 5-work battery; cite our work as a *complement* (local-wrapper measurement) not a competitor on volume. |
| 2 | CVE-2026-7482 "Bleeding Llama," CVSS 9.1 | ✅ Heap OOB-read in Ollama's GGUF loader; ~300K instances at risk; `/api/create` & `/api/push` vectors; msuiche detection tools on GitHub | Clean. This is a *genuine* GGUF-loader memory bug (contrast with Correction B). |
| — | CVE-2026-42248 / CVE-2026-42249 — Ollama Windows auto-updater | ✅ Striga.ai disclosure (helpnetsecurity 2026-05-05). Path traversal (42249, CVSS 7.7) + missing signature check (42248), chainable to persistent RCE. Reported unpatched past 90-day window. | Clean. Correctly described in LATEST_INTEL §2. |
| 15 | "Local Is Not a Sufficient Privacy Boundary," arXiv 2606.10173 | ✅ arXiv:2606.10173. Full title: *Local Is Not a Sufficient Privacy Boundary: Governing OS-Integrated On-Device AI*. Authors: **Jonghyun Chung, Sanket Badhe**. Submitted 2026-06-08. | **Use the full title + subtitle in the reference list** (draft truncates it). Same thesis as our §6 — independently argues local execution ≠ privacy — but at the OS-governance level; good cross-disciplinary framing citation. |

---

## 3. Not yet re-verified this session (~8 lower-stakes items)

These remain at the "exists per secondary source, not yet primary-verified" status LATEST_INTEL left them in. None are load-bearing for the headline claims, but PoPETs reviewers will spot-check the reference list, so clear them before submission.

| ID as cited | Claimed title | Action needed |
|---|---|---|
| arXiv 2506.15674 | (the actual Leaky Thoughts — listed above as clean) | done |
| arXiv 2603.05618 (ref #8) | Das et al., "Safer Reasoning Traces" | fetch abstract page; confirm title/authors |
| arXiv 2603.07267 (ref #10) | Zhang et al., "Trace Inversion" | fetch abstract page; confirm title/authors |
| arXiv 2602.20595 (ref #12) | Kwon et al., "OptiLeak" | fetch abstract page; confirm title/authors |
| arXiv 2603.23996 (ref #14) | Murtuza, "Forensic Implications of Localized AI" | fetch abstract page; confirm title/authors |
| arXiv 2511.07772 | SALT: Steering Activations towards Leakage-free Thinking | fetch abstract page |
| arXiv 2601.05076 | Chain-of-Sanitized-Thoughts (PII CoT sanitization) | fetch abstract page |
| arXiv 2601.17548 | "Prompt Injection Attacks on Agentic Coding Assistants" (85%+ success) | fetch abstract page; load-bearing for the §methodological-note promotion of the agent-injection meta-finding |
| arXiv 2510.18554 | "Extracting alignment data in open models" | fetch abstract page |
| NDSS 2025 — PROMPTPEEK (ref #11) | Wu et al. | verify on NDSS proceedings / ACL-style anthology |

### NEW (found during disclosure Stage 3 — load-bearing for §7 related work)

**"Shadow in the Cache: Unveiling and Mitigating Privacy Risks of KV-cache in LLM Inference"** — Luo, Shao, Zhang, Zhou, Hu, Zhao, Liu, Qin — **arXiv:2508.09442** — **accepted to NDSS 2026** (submitted 2025-08-13, v4 2026-03-11).

- ✅ **Verified clean.** Primary source: [arxiv.org/abs/2508.09442](https://arxiv.org/abs/2508.09442).
- **This is the closest existing prior art to our §7 KV-cache finding** — closer than SafeKV. It demonstrates three attack vectors that *reconstruct sensitive user inputs directly from the KV-cache bytes* (Inversion, Collision, Injection attacks), and proposes KV-Cloak (reversible-matrix obfuscation) as a defense.
- **Distinction to make in the paper:** Shadow-in-the-Cache addresses the case where an attacker *with weight/cache access reconstructs inputs from the K/V tensors themselves* (the values are semantically meaningful). Our finding is complementary: we show the bytes *persist in process memory after the logical session ends* (residual data-at-rest on slot release) — i.e., *temporal* exposure via missing zeroization, a different axis. Cite together in §7/§2; do not claim overlap.
- **Disclosure significance:** an NDSS 2026 accepted paper independently establishes that "KV-cache bytes leak inputs" is a recognized vulnerability class. This strengthens the upstream-disclosure rationale — llama.cpp maintainers can be pointed at a peer-reviewed venue establishing the class.
| CVE-2025-49847, CVE-2026-27940, CVE-2026-33298, CVE-2024-25664..68, RAXE-2026-042 (refs #1,#3,#4,#5,#20) | various llama.cpp/Databricks GGUF heap overflows | NVD lookup each; confirm CVSS + affected-component. Note: several of these are the "12 CVEs (2 critical)" the GGUF_CVE_LANDSCAPE already re-verified — cross-check which of these overlap before double-citing |
| Pillar Security "GGUF Template Injection Attack" (ref #18) | poisoned-template claim | fetch primary blog/advisory |
| HiddenLayer (malware-repo claim), OpenDoors (exposed-server count) | motivating-statistic claims | these are scene-setting only; if cited, attach primary source, else drop to "reported by" |

**Priority within §3:** the agentic-injection paper (2601.17548, "85% success") is the one most likely to be quoted in the paper's body text — verify it first. The arXiv IDs in the 2603.x / 2602.x range should each get a single abstract-page fetch; the GGUF CVE cluster should be de-duplicated against `GGUF_CVE_LANDSCAPE.md` rather than re-verified from scratch.

---

## 4. Meta-observations for the paper

1. **The SafeKV correction (A) is the most important.** It sits inside the formal-analysis section, where a misattributed source or an overstated lineage claim is exactly what a careful reviewer attacks. Fixing it costs ~2 sentences and removes a real liability.
2. **The CVE-2026-5760 correction (B) is the most visible.** Anyone who Googles the CVE while reading the paper will see "Jinja2 SSTI" and any prose calling it a "GGUF-parser RCE" will read as careless. The corrected framing ("the model file is a delivery vector for code-execution payloads via several distinct runtime paths") is also *stronger* than the original lumped claim.
3. **Two papers retitled between versions (2603.10726, 2602.24210).** arXiv preprints retitle often. The paper's reference list should cite the *current* title with the arXiv ID; reviewers who resolve the ID will see the latest title. Citing a stale title is a minor-but-avoidable credibility hit.
4. **SafeKV + PrefixWall together** establish that the *timing side-channel in shared prefix caches* is an active sub-field. Our data-at-rest residual is a **third, distinct** KV-cache privacy problem. Stating all three explicitly and distinguishing them is both more accurate and a stronger positioning of our contribution's novelty.

---

## 5. What this audit did NOT do (scope boundaries)

- Did not re-read every paper's full text — only abstract pages / advisory records. A claim like "Paper X found 78.3% leakage" requires opening the paper, not just its abstract. Where the draft quotes a *number* attributed to a cited paper (e.g., the reasoning-channel percentages in §4.3 are our own measurements, but any percentage attributed to *prior work* needs a page-level check).
- Did not verify the GGUF CVE cluster against NVD individually — `GGUF_CVE_LANDSCAPE.md` already did 4 of them live and that work stands; this audit cross-references it rather than redoing it.
- Did not verify venue fit (PoPETs vs USENIX vs S&P) — that's the paper-drafting task, not citation hygiene.
- The arXiv 2602.24210 author surname ("Batra") was **not** confirmed this session and remains an open item.
