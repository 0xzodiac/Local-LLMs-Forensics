# Responsible Disclosure Plan

**Date:** 2026-06-23
**Status:** Disclosure arms identified and verified; notification drafts below. **Not yet sent.** Sending requires a user decision on sender identity and timing (see §5).
**Purpose:** Satisfy the responsible-disclosure requirement that is a **publication blocker** at PoPETs (PETS), USENIX Security, IEEE S&P, and NDSS. None of these venues will accept a paper disclosing a live vulnerability without either (a) a disclosure statement + timeline, or (b) an explanation of why disclosure is not required (e.g., already public/CVE'd).

This document covers **two independent disclosure arms**. They are unrelated bugs in unrelated components and should be disclosed on independent timelines.

---

## 0. Verification that determines the disclosure path

Before drafting, I verified the live state of both surfaces against primary sources this session (2026-06-23):

### Arm 1 — LM Studio `logSensitiveData: true` default
- **State:** Behavior reproduced directly in `MITIGATION_TEST_REPORT.md` and re-confirmed in `FINAL_AUDIT_REPORT.md` §1 (Finding 3). Config at `~/.lmstudio/.internal/http-server-config.json`, default `true`, no GUI control, 6.3 MB/day cleartext of prompts+responses+reasoning traces.
- **Existing advisory search:** No CVE, GHSA, or vendor advisory found for this behavior. LM Studio's documentation does not flag the default as a security consideration. **This is an undisclosed finding** → full responsible-disclosure process applies.
- **Severity rationale:** The default writes full conversation contents (including reasoning traces that the model may not intend to surface) to cleartext disk with 30-day retention, in a location discoverable by any process with the user's UID. For the stated use case of local LLMs (privacy-sensitive data kept off cloud APIs), this directly defeats the deployment's purpose. Self-rated CVSS ~5.3 (Local access required; confidentiality impact; low complexity) — moderate, but the *threat-model mismatch* is the substance, not raw CVSS.

### Arm 2 — llama.cpp KV-cache residual data on slot release
- **Live state of upstream (verified against `ggml-org/llama.cpp` HEAD `3eb769a`, 2026-06-23):** `llama_kv_cache::seq_rm()` still calls only `cells.seq_rm(i, seq_id)` (owner-bitmap update) + head-pointer bookkeeping. **No** backend-buffer zeroization on the release path. The bug described in `KV_CACHE_PATCH_REPORT.md` and `PAPER_DRAFT.md` §7 is **live and unfixed in current master.**
- **Existing upstream issue/PR search:** No existing llama.cpp issue found for "zeroize on seq_rm" / "KV-cache privacy residual." The existing `clear(bool data)` primitive exists but is whole-buffer-only and never called on the slot-release path.
- **Prior art establishing the class:** **"Shadow in the Cache" (Luo et al., NDSS 2026, arXiv:2508.09442)** independently establishes that KV-cache bytes leak reconstructable inputs — a peer-reviewed, accepted paper. This is not a speculative class; it is recognized. → strengthens the disclosure rationale: upstream can be pointed at a published venue, not just our preprint.
- **Decision:** Because the bug is live, unfixed, untracked, **and** sits in a class a peer-reviewed paper has already established, the correct path is to **upstream our patch as a PR** rather than file a private-security-only report. The patch is 89 lines, self-contained, backend-portable, and benchmarked at unmeasurable overhead. "We disclosed + shipped a working patch" is materially stronger for the paper than "we reported."

---

## 1. Arm 1 — LM Studio cleartext logging default

### 1.1 What to disclose

| Item | Value |
|---|---|
| Component | LM Studio (inference server, all versions current as of 2026-06-19) |
| Surface | Default HTTP server configuration |
| Finding | `logSensitiveData` defaults to `true`; writes full request/response bodies (prompts, completions, `reasoning_content`, system prompts) as cleartext JSON to `~/.lmstudio/server-logs/YYYY-MM/YYYY-MM-DD.N.log` |
| Non-discoverability | Setting lives in `~/.lmstudio/.internal/http-server-config.json` (not the user-facing `settings.json`); no GUI toggle; no first-run warning; state-change requires server restart |
| Persistence | 30-day default retention (`apiPredictionHistoryEviction.ttlDays`); historical logs persist after setting is flipped to `false` (manual `rm -rf ~/.lmstudio/server-logs/` required) |
| Measured volume | 6.3 MB single-day log, 2,312 `content` entries, 777 full response bodies (`MITIGATION_TEST_REPORT.md`) |
| Threat model | Any process with the user's UID (stealer malware, insider, forensic acquisition) can harvest 30 days of conversation history. Local LLMs are deployed *precisely* to keep this data off cloud — the default defeats the deployment's purpose. |

### 1.2 Recommended fixes (for the vendor)

1. Default `logSensitiveData` to `false`.
2. Surface the setting in the GUI server-configuration panel with a clear warning when active.
3. Show a first-run warning when logging is enabled on a server bound to non-loopback interfaces.
4. Optionally: write logs to an OS keychain-protected / encrypted store, or at minimum `0600` perms.
5. Provide a one-click "purge historical logs" affordance.

### 1.3 Draft notification (LM Studio)

> **Subject: Security disclosure — cleartext logging of API payloads enabled by default**
>
> To the LM Studio team,
>
> I'm an independent security researcher preparing a privacy-analysis paper on local LLM tooling. During testing I found that LM Studio's inference server enables logging of full API payloads by default, in a configuration that is not exposed through the UI. I'm disclosing this to you in advance of publication per responsible-disclosure practice; I'd like to coordinate a fix and a disclosure timeline.
>
> **Finding.** The server configuration at `~/.lmstudio/.internal/http-server-config.json` ships with `logSensitiveData: true` as the default. With this setting active, every HTTP request and response body — including prompts, completions, system prompts, and reasoning traces — is written as cleartext JSON to `~/.lmstudio/server-logs/YYYY-MM/YYYY-MM-DD.N.log`, retained for 30 days by default.
>
> **Why this matters.** The primary motivation for running local LLMs is to keep sensitive data off cloud APIs. A default that silently archives 30 days of conversation contents to cleartext disk, in a path any process with the user's privileges can read, directly defeats that motivation. The setting is not visible in the GUI configuration panel, and changing it requires a server restart, so a typical user has no indication it is active.
>
> **Reproduction.** (brief steps + the measured 6.3 MB/day figure + canary-absent-after-`false` confirmation.)
>
> **Suggested fixes.** Default to `false`; expose the setting in the GUI with a warning; first-run warning for non-loopback binds; consider encrypted/at-rest-protected logs.
>
> **Coordination.** I'd welcome a CVE/advisory if you agree this warrants one, and I'm happy to align the paper's disclosure timeline with your patch. I propose a 90-day disclosure window from your acknowledgment, standard for this category. Please confirm a contact and I'll share the full reproduction details and the measurement artifacts.
>
> [researcher identity / PGP key]

### 1.4 Timeline

| Step | Owner | Target |
|---|---|---|
| Send notification | researcher | T0 (user-authorize first) |
| Vendor acknowledgment | LM Studio | T0 + 5 business days (re-escalate via GitHub if no response) |
| Patch / advisory | LM Studio | T0 + 90 days (standard) |
| Paper disclosure statement finalized | researcher | patch date + 14 days |
| Paper submission | researcher | after disclosure statement locked |

---

## 2. Arm 2 — llama.cpp KV-cache residual data + zeroization patch

### 2.1 What to disclose

| Item | Value |
|---|---|
| Component | `ggml-org/llama.cpp`, `src/llama-kv-cache.cpp`, `llama_kv_cache::seq_rm()` |
| Surface | KV-cache backend buffer (RAM and VRAM) |
| Finding | On slot/sequence release (`seq_rm`), the cell owner bitmap is updated and the cell marked free, but the underlying K/V float bytes in the `ggml_backend_buffer_t` are **not** zeroed. They persist until a future request physically overwrites the same cell. On a quiescent server, residual data persists indefinitely. |
| Exploitability | Process with the server's UID reading `/proc/<pid>/mem` (CPU) or same-UID bypass on pinned host buffers (GPU) recovers 11–42 canary copies after slot release; 12/12 sequential tenants recoverable from a single ~1.24 MB memory read (`DEEP_LEAK_REPORT.md`). |
| Class | Established by "Shadow in the Cache" (Luo et al., NDSS 2026, arXiv:2508.09442) — KV-cache bytes leak reconstructable inputs. Our finding is the *temporal/residual* axis of that class. |
| Fix | `patches/kv_cache_zeroize.patch` — 89 lines, hooks `seq_rm()`'s cell-release branch to call a new `zero_cell_data()` that overwrites the released cell's K/V bytes via `ggml_backend_tensor_set()`/`_2d()` (backend-portable: CPU + GPU). Verified directly: 56/56 zeroed cells had real non-zero data pre-zero; 0/56 post. Overhead unmeasurable above noise (N=20, patched nominally faster). |

### 2.2 Why a PR (not just a private report)

1. The bug is **live in master**, not in a historical version.
2. The class is **already publicly established** by an NDSS 2026 paper — there is no secrecy benefit to private-only disclosure; the risk surface is already known to anyone reading that paper.
3. We have a **working, benchmarked, formally-analyzed patch** that is small and safe. Shipping it maximally reduces real-world exposure.
4. "Disclosed + patched upstream" is a strictly stronger paper contribution than "disclosed."

### 2.3 PR / issue description (llama.cpp)

> **Title: [security] Zeroize KV-cache cell bytes on sequence release (residual data-at-rest)**
>
> ## Problem
>
> `llama_kv_cache::seq_rm()` updates the per-cell owner bitmap on sequence removal but does not clear the underlying K/V bytes in the backend buffer. Released cells retain their computed K/V values until a future write happens to land on the same offset. On a quiescent or lightly-loaded server, prompt/response data therefore persists in the KV-cache buffer (RAM or VRAM) indefinitely after the originating session ends.
>
> This is the *temporal/residual* axis of the KV-cache privacy class independently characterized in "Shadow in the Cache" (Luo et al., NDSS 2026, arXiv:2508.09442). A process sharing the server's UID can read the residual bytes via `/proc/<pid>/mem` (host buffers) or same-UID access to pinned host buffers backing GPU DMA.
>
> ## Fix
>
> This PR adds a `zero_cell_data(s, i)` method called from `seq_rm()` **only on the branch where `cells.seq_rm()` reports the cell has no remaining owners** (i.e., it is safe to zero — no other sequence still references it). `zero_cell_data` overwrites the cell's K and V bytes in every layer's backend tensor using `ggml_backend_tensor_set()`/`_2d()`, handling both the contiguous-K, contiguous-V (`v_trans=false`, flash-attn) and transposed-V (`v_trans=true`) layouts to match `get_k()`/`get_v()` exactly.
>
> ## Safety
>
> - Zeroing runs only when `cells.seq_rm(i, seq_id)` returns true (owner set empty) → cannot corrupt another active sequence's K/V.
> - Offsets mirror `get_k()`/`get_v()` read offsets exactly → no off-by-one or alignment gap that attention could later read.
> - `ggml_backend_tensor_set` is backend-portable → works on CPU and GPU buffers.
>
> ## Overhead
>
> N=20 short-completion requests, CPU-only: mean 9.71s patched vs 9.84s unpatched (within noise; patched nominally faster). The added work is one buffer write per released cell — memory-bandwidth-bound, microseconds-to-low-milliseconds.
>
> ## Verification
>
> Direct mechanism check via `ggml_backend_tensor_get()` before/after the zero call: 56/56 zeroed cells had real non-zero data immediately before zeroing; 0/56 had any non-zero byte afterward.
>
> (attach patch + benchmark log)

### 2.4 Note on scope the PR does NOT claim

The patch fixes the **KV-cache float tensor** residual only. A **separate** heap-string leak surface (the formatted-prompt buffer held in `server_slot`, ~135 KB/slot, never freed on `slot.release()`) is documented in `MULTILAYER_V2_REPORT.md` and explicitly left as future work — it needs a secure-zero in `server_slot::release()`, not in the KV-cache path. **Do not conflate the two in the PR**; mention the second surface as a known-related-but-separate item so maintainers don't think the PR is claiming more than it fixes.

### 2.5 Timeline

| Step | Owner | Target |
|---|---|---|
| Open PR + issue | researcher | T0 (user-authorize first) |
| Maintainer triage | ggml-org | T0 + 7–14 days (typical) |
| Merge / revision | both | T0 + 30–60 days |
| Paper disclosure statement | researcher | merge date (or 90-day fallback if stalled) |

---

## 3. Coordinated-disclosure statement for the paper (template)

PoPETs (and the other A* venues) require a disclosure statement. Draft text, to be inserted in the paper's front-matter or a "Responsible Disclosure" subsection, updated with real dates once arms are sent:

> **Responsible Disclosure.** Prior to submission, we disclosed two findings to affected vendors under coordinated-disclosure practice. (1) LM Studio's default `logSensitiveData: true` server-logging configuration was reported to [vendor] on [date]; at the time of submission the status is [patched on [version] / under remediation / unpatched, [N] days into a 90-day window]. (2) The llama.cpp KV-cache residual-data issue (§7) and our accompanying zeroization patch were submitted upstream to `ggml-org/llama.cpp` as PR #[N] on [date]; status at submission: [merged / under review]. All measurement artifacts and the patch are released as reproducibility artifacts accompanying this paper. We cite CVE-2026-7482 ("Bleeding Llama") and CVE-2026-5760 (SGLang Jinja2 SSTI) only in their already-publicly-disclosed capacity and do not claim to have discovered them.

---

## 4. Legal / process notes

- **Authorization.** Both arms concern software the researcher ran on their own machine; no third-party system was accessed. Disclosure is good-faith vulnerability reporting, protected in most jurisdictions. Still — **do not send either notification without explicit user authorization**, since sending creates a dated, attributable communication to a vendor.
- **Anonymity vs attribution.** PoPETs permits anonymous submission; the disclosure notifications can be sent from a non-attributed research mailbox + PGP key. The PR to llama.cpp is public by nature (GitHub) and will be attributable; that is normal and expected for upstream code contributions.
- **Embargo.** Once a vendor acknowledges, honor an embargo until their patch ships or the 90-day window elapses, whichever is first. Do not submit the paper's camera-ready with exploit detail until the embargo lifts.
- **CVE requests.** The LM Studio finding may warrant a CVE; the llama.cpp fix may be merged without one (many llama.cpp security fixes are). Do not request a CVE unilaterally — coordinate with the vendor/MITRE through the standard channel.

---

## 5. Decision needed from the user before sending anything

This is the blocking gate. I will **not** send either notification without explicit instruction, because:

1. Sending attributes the research to a real sender identity (mailbox / GitHub account).
2. It starts a vendor timeline that constrains the paper's submission date.
3. The llama.cpp PR is public and permanent.

Options:
- **(a) Send both now** — fastest path to clearing the publication blocker; locks a ~90-day submission horizon from today (2026-06-23 → paper submittable ~2026-09-21).
- **(b) Send the llama.cpp PR now, hold the LM Studio notification** — the llama.cpp path is lower-risk (public, class already known) and unblocks the stronger paper contribution; LM Studio notification can follow once sender identity is settled.
- **(c) Hold both** — continue with paper drafting and variance-bar work; send disclosures closer to intended submission. Risk: the longer findings sit undisclosed before publication, the weaker the "responsible disclosure" framing reads to reviewers.

I recommend **(b)**: open the llama.cpp PR now (it's the highest-value contribution and the class is already public), and prepare the LM Studio notification for sending once the user confirms sender identity. Awaiting instruction.
