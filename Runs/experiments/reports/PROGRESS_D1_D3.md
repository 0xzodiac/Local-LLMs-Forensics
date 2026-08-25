# Progress Report — TIFS Plan, D1–D3 (2026-06-23)

## What's DONE (verified, no server needed)

### D1 — prompt-zeroize patch ✅
- Implemented Sites A (`server_slot::reset()`) + B (`send_final_response()`) in
  `llama.cpp-src/tools/server/server-context.cpp`.
- **Compiles cleanly** — CPU build links (`llama-server` rebuilt, exit 0).
- Design note: Site C (the `body_parsed` JSON) is `const json &` — cannot be
  zeroed in place. Secured the deeper source (the slot/result members) instead.
  Documented honestly in the patch report.
- Honest limitation surfaced & documented: `task` is `unique_ptr<const server_task>`
  (immutable by design), so its plaintext members are freed-not-zeroed. The patch
  zeros all *live/reachable* copies; the *freed* task region is a documented
  residual needing a secure allocator (future work).

### D3 — formal analysis + patch report ✅
- `PROMPT_ZEROIZE_PATCH_REPORT.md` written: source-verified plaintext chain,
  the two patch sites, invariant I₃ (parallel to KV patch's I₂), honest
  limitation, defense-in-depth framing (I₂ ∧ I₃).

### D9 (early) — paper writing ✅
- **Abstract** rewritten to honest 3-layer form (file/runtime/interface). All
  results retained; false claims fixed:
  - "30-day retention" → "no observed retention limit"
  - dropped reasoning-channel-as-headline (prior-art-heavy, 78.3% was inflated)
  - added the new prompt-zeroize patch (I₃)
  - GGUF reframed as the honest negative result it is
- **§1 contributions** reframed to 4 honest items (3 layers + network negative).
- **§2 threat model** fixed: the CVSS AV:N → AV:L correction is now explicit and
  honest (4.4–5.5 Medium, not 7.5). Privilege model clarified (A1 unprivileged
  same-UID parent; A3 privileged for KV-tensor only).

---

## D2 — RESOLVED, ran via `run_in_background: true` (no terminal needed after all) ⚠️ negative result

`run_in_background: true` on the Bash tool handles genuinely long-running
scripts (~15-20 min) fine — they complete and fire a notification. The earlier
"sandbox kills long servers" blocker only applied to detaching a process
*within* a returning call; it does not apply to the harness's own background
flag. Ran `bash run_d2_measurements.sh` this way (after fixing a self-matching
`pkill -f llama-server` bug that killed the launch on the first attempt).

**Result: the patch does NOT take 13 copies → 0.**

| Run | T1 final count |
|---|---|
| patched_run1 | 13 |
| patched_run2 | 13 |
| patched_run3 | 14 |

No measurable reduction from Sites A/B (`server_slot::reset()` +
`send_final_response()`). Blast radius (12-tenant, patched): 11/12 recovered,
~10.8 MB cleartext — confirms the leak survives the patch
(`logs/leak_blast_radius_20260623_213831.json`).

**Root cause (round 1):** every hit lands in one ~132 KB mmap'd `[anon]`
region, populated upstream of slot/task — in the HTTP layer
(`server-http.cpp`'s `server_http_context::post()`). Added Site C
(`explicit_bzero` on HTTP body copies): 13→12 (T1), 13→11 (T2-T4) — marginal.

**Root cause (round 2, the actual dominant carrier):** the chat-template
render buffer, `chat_params.prompt` (~135KB, from
`common_chat_templates_apply()` inside `oaicompat_chat_params_parse()`,
`server-common.cpp`) — never zeroed before going out of scope. Added Site D.
Result: **T1 13→0 — complete fix for the first tenant.** But T2/T3/T4 each
jump to 12 immediately and the count never decays (not idle-period residue —
permanent). Hypothesized carrier: `server_prompt_cache`
(`server-context.cpp`: `slot.prompt_save()`/`prompt_load()`, gated by
`cache_prompt`) — trigger condition matched exactly (T1 has no prior cache
entry, T2+ each populate one). **Checked source and RULED OUT**: its storage
(`server-task.h:583-647`, `server_prompt`) holds only `tokens`
(`llama_tokens` — integers) and `data` (`std::vector<uint8_t>` × 2 —
serialized binary KV-state). No plaintext string field exists. The cache's
presence/absence still correlates with the symptom, but it cannot be the
byte-level carrier of the literal canary text.

**Further candidates checked (per your request to keep hunting), all ruled
out:**
- `to_json_non_oaicompat()` (server-task.cpp:375) — `{"prompt", prompt}` reads
  the same `res->prompt` member Site B already zeros. Not new.
- Both `server_tokens::detokenize()` call sites (server-context.cpp:692, 2170)
  feed that same already-covered member.
- `common_prompt_checkpoint` (common.h:1065, the cache's checkpoint type) —
  only `vector<uint8_t>` binary fields (`data_tgt`/`data_dft`/`data_spec`), no
  plaintext.

**Every static-code-reading hypothesis is now exhausted.** `res->prompt`,
`to_json()`, the detokenize sites, and the entire
`server_prompt_cache`/`server_prompt`/`common_prompt_checkpoint` chain are all
confirmed either zeroed or plaintext-free at the source level. The trigger
condition (2nd+ request under `cache_prompt`) is solid; the storage location
is not findable by reading source alone — it needs a live debugger session
(gdb breakpoint on the request path, inspect the flagged address directly),
a different and more expensive class of investigation than what's been done
so far.

**Net status:** the freed-heap-string leak class (Sites A-D) is fixed for the
single-tenant case. A second, larger leak persists for every multi-request
session with a known, reproducible trigger but unidentified storage location.
Stopping the source-reading hunt here given session cost (~$18, well over the
informal $10 budget flag) and the 2-week ceiling.

Full writeup: `PROMPT_ZEROIZE_PATCH_REPORT.md` §7 (§7.1-7.4, corrected +
exhausted-candidates list). `PAPER_DRAFT_TIFS.md` §1/§4.4/§8.2-8.3/§10.1
updated to match.

**Decision needed:** invest in a live gdb session to find the exact storage
location within the 2-week ceiling, or report the second leak as
open-with-unknown-location (reproducible trigger, no identified fix) and move
to D4/D5/D7.

### D4, D5, D7 — done
- D4: cross-model heap residue (nemotron → qwen swap, in-process) —
  **confirmed positive**, model-independent. Required a research-only patch
  (`/admin/swap_model`) since router mode and sleep/wake don't support
  in-process swap. See `D4_CROSS_MODEL_RESIDUE_REPORT.md`.
- D5: Ollama netns control case — **0 egress, 0 canary leak, across all 4
  models** (nemotron, qwen3.5, gemma4, phi4), stronger than LM Studio's
  result (which has nonzero cold-start telemetry). See
  `TELEMETRY_FINDINGS_OLLAMA.md`.
- D7: end-to-end PII attack-chain demo — **partially confirmed, with a real
  scope correction.** Disk-log channel confirmed but content-length-
  truncated (short secrets fully recoverable, long ones only partially).
  Memory-residue channel did NOT reproduce on LM Studio's actual shipped
  binary (only ever proven on the research llama-server build) — this
  narrows the original combined-chain framing rather than confirming it.
  See `D7_PII_ATTACK_CHAIN_REPORT.md`.

### D8 — disclosure (needs your decision)
Before D8 I need your sender identity (real account vs research-only account)
for the llama.cpp PR + LM Studio email. **Now also needs to cover D10's
finding** (the cross-tenant slot vulnerability is more severe and arguably
the more urgent one to disclose first).

### D9 — gdb investigation of the second leak — done
Sites A-D close the heap-string leak completely for the first tenant (13→0).
A second, distinct leak persists for every tenant after the first
(~10-13 copies, non-decaying) and survives Sites A-D plus the secure
allocator (I₄, added in a parallel session). Live gdb attach on the actual
leaking process found the structural cause: the leak lives in a per-thread
glibc malloc arena, not any single named object the patches target — `free()`
doesn't zero memory, and the request pipeline copies plaintext across
multiple threads with independent allocator arenas. Conclusion: this leak
class is structurally resistant to per-object zeroization patches, not a
missing call site. An earlier hand-rolled reproduction attempt incorrectly
suggested the leak was fixed — that was a bug in the test script, caught and
corrected before being reported as real. See `GDB_SECOND_LEAK_INVESTIGATION.md`.

### D10 — cross-tenant session hijacking via unauthenticated `/slots` restore — done, strongest finding
`llama-server`'s `/slots/:id_slot` save/restore feature (gated only by
`--slot-save-path`, independent of `--slots`) has no authorization check
tying a slot or filename to the client that created it. Any client reaching
the HTTP API can restore another tenant's saved KV-cache into their own
session by knowing/guessing a filename — `--api-key` doesn't help (it's a
perimeter check, not per-resource authorization). Confirmed via exact
`n_saved`/`n_restored` token-count match across **three** independent setups
(nemotron/CPU, Phi-4/CPU, Qwen3.5/GPU-accelerated after rebuilding with
`-DGGML_CUDA=ON`). CWE-862 (Missing Authorization) + CWE-200. **This is the
first finding in the project that requires only network access — everything
else needs local same-UID process access.** A verbal "repeat the secret
back" demo was attempted but blocked by an unrelated, build-wide
chat-format-parser bug (empty content on every model/prompt, including
trivial unrelated ones) — the data-level proof doesn't depend on that being
fixed. See `CROSS_TENANT_SLOT_RESTORE_VULNERABILITY.md`.

---

## What's next
- D10 is the strongest disclosure candidate — likely should be filed/reported
  ahead of or alongside D8's original heap-string findings.
- D6 number corrections across the corpus (78.3%→56% etc.) — done, see
  `RECONCILED_NUMBERS.md` Claim 8.
- D8 disclosure PR/advisory draft needs to cover D9's structural finding and
  D10's vulnerability, not just the original Sites A-D patch — scope grew
  significantly since this was last planned.

## One-sentence status
The heap-string leak is structurally characterized (not just patched) via a
live gdb session, and a much more severe, independently-discovered
vulnerability — unauthenticated cross-tenant slot restore over the network,
zero local access required — is now the project's strongest, most
disclosure-worthy finding.
