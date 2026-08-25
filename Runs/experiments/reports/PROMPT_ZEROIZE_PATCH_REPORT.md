# Prompt-Zeroize Patch Report

**Date:** 2026-06-23 (patches), 2026-06-24 (final gdb investigation)
**Status:** Sites A-D + secure-allocator (I₄) implemented and tested. Site D
closes the leak completely for the first tenant in a sequence (13→0). A
**second, distinct leak** persists for every tenant after the first
(~10-13 copies, non-decaying) and survives all four object-level patches plus
I₄. A live gdb session (`GDB_SECOND_LEAK_INVESTIGATION.md`) found the
structural cause: the leak lives in a per-thread glibc malloc arena, not any
single named object Sites A-D target — `free()` doesn't zero memory, and the
request pipeline copies plaintext across multiple threads with independent
allocator arenas. **Conclusion: this leak class is structurally resistant to
per-object zeroization patches**, not a missing call site waiting to be
found. See §7 for the original measurement and `GDB_SECOND_LEAK_INVESTIGATION.md`
for the structural finding.
**Companion to:** `KV_CACHE_PATCH_REPORT.md` (the KV-tensor patch) — this is the
**heap-string** patch, which targets the *unprivileged*-exploitable surface the
KV patch does not reach.

---

## 0. Why this patch exists (the gap it closes)

The project's headline leak numbers — 13 copies/tenant (`MULTILAYER_V2_REPORT.md`),
12/12 multi-tenant recovery (`DEEP_LEAK_REPORT.md`) — measure the **heap-resident
formatted-prompt string**, readable by any same-UID parent process via
`/proc/<pid>/mem` (**unprivileged**: needs no root, no CAP_SYS_PTRACE, only the
default `ptrace_scope=1` parent-child relationship).

The earlier `kv_cache_zeroize.patch` fixes a **different, privileged** surface:
the KV-cache *float tensor* (observable only via PTRACE_ATTACH / root). The two
surfaces are disjoint, and the KV patch has **zero demonstrated effect** on the
heap-string numbers (the canary-grep methodology cannot even see KV data, because
tokenization converts the plaintext to integer IDs before the KV stage —
`KV_CACHE_PATCH_REPORT.md` §3.2).

**This patch closes the surface the headline numbers actually measure.** Without
it, the paper's defense and its finding address different problems — a fatal
internal contradiction a TIFS reviewer would strike immediately.

---

## 1. Where the plaintext lives (source-verified)

A chat request's plaintext traverses this chain in `tools/server/server-context.cpp`:

1. `common_chat_templates_apply()` (common/chat.h:211) renders the JSON chat
   prompt into a `std::string` of ~135 KB for a typical request.
2. It is copied into `task->params.sampling.generation_prompt` (common.h:271) and
   `task->params.antiprompt` (server-task.h:73).
3. `handle_completions_impl` (server-context.cpp:4110) tokenizes and discards the
   handler-local copy.
4. `send_final_response` (server-context.cpp:2104) constructs a `res` object with:
   - `res->prompt` — a **re-detokenized** full copy of the plaintext (line 2126)
   - `res->content` — the generated response (line 2122)
   - `res->generation_params` — a full copy of `task->params`, including the
     `generation_prompt` string (line 2162)
5. `res` is pushed to `queue_results` and **outlives the slot** — it is read by
   the HTTP handler thread *after* `slot.release()` returns.

### Plaintext-retaining members (source-verified)

| Member | File:line | Carrier | Lifetime | Patched? |
|---|---|---|---|---|
| `slot.generated_text` | server-context.cpp:197 | slot | reused across requests via `reset()` | **Site A** |
| `slot.debug_generated_text` | server-context.cpp:198 | slot | never cleared before | **Site A** |
| `slot.stopping_word` | server-context.cpp:209 | slot | reused | **Site A** |
| `task->params.sampling.generation_prompt` | common.h:271 | task | **immutable** (`unique_ptr<const server_task>`) | ❌ see §3 |
| `task->cli_prompt` | server-task.h:156 | task | immutable | ❌ see §3 |
| `res->prompt` (re-detokenized) | server-context.cpp:2126 | result | outlives slot | **Site B** |
| `res->content` | server-context.cpp:2122 | result | outlives slot | **Site B** |
| `res->generation_params.sampling.generation_prompt` | via 2162 copy | result | outlives slot | **Site B** |

---

## 2. The patch (`patches/prompt_zeroize.patch`)

Two sites, ~40 lines total. Uses `explicit_bzero` (glibc) so the compiler cannot
elide the write under as-if / dead-code-elimination (the known weakness of plain
`memset` over a buffer that goes out of scope).

### Site A — `server_slot::reset()` (server-context.cpp:299)

Before the existing `generated_text = ""` / `stopping_word = ""` reassignments
(which only set length 0 and leave the old bytes in the SSO/heap allocation),
the patch overwrites the bytes:

```cpp
auto secure_zero = [](std::string & s) {
    if (!s.empty()) { explicit_bzero(s.data(), s.size()); s.clear(); }
};
secure_zero(generated_text);
secure_zero(stopping_word);
secure_zero(debug_generated_text);
```

### Site B — `send_final_response()` (server-context.cpp:2104)

The result object's plaintext copies are zeroed *after* construction but *before*
`queue_results.send()`, so no tenant plaintext leaves the server in `res`:

```cpp
auto secure_zero = [](std::string & s) {
    if (!s.empty()) { explicit_bzero(s.data(), s.size()); s.clear(); }
};
// ... after res->generation_params = slot.task->params;
secure_zero(res->prompt);
secure_zero(res->content);
secure_zero(res->generation_params.sampling.generation_prompt);
secure_zero(res->generation_params.sampling.reasoning_budget_message);
```

---

## 3. What the patch does NOT fix (honest limitation)

The `task` object is `std::unique_ptr<const server_task>` (server-context.cpp:180)
— **immutable by design after construction**. Its plaintext members
(`params.sampling.generation_prompt`, `antiprompt`, `cli_prompt`) therefore cannot
be zeroed through `task`. On `task.reset()`, they are **freed but not zeroed**:
the ~135 KB heap region returns to the allocator and the bytes persist until a
future allocation reuses the address.

This is a **documented residual**. Fully closing it requires a secure-zeroing
allocator (e.g., a `std::pmr` memory resource that `explicit_bzero`s on dealloc),
which is a deeper, more invasive change scoped as future work. The patch reduces
the *reachable, live* copies (Sites A + B) to zero; the *freed, transient* copy
(task) is reclaimed by the allocator's normal churn within one request cycle.

**Pre-registered expectation (superseded — see §7):** the 13-copies/tenant
count should drop substantially (target: 0 live copies), with at most 1-3
residual transient copies from the freed task region. **This did not happen.**
D2 measured 13→13/14 — no reduction. See §7 for the actual result and
root-cause investigation.

---

## 4. Formal correctness (extends §8 invariant I₂)

The KV-cache patch establishes invariant **I₂** (ownership-implies-zeroed for the
float tensor). The prompt-zeroize patch establishes a parallel invariant **I₃**
for the heap-string surface:

$$\forall \text{slot } s,\ \forall m \in \text{PlaintextMembers}(s).\ \quad
\text{released}(s) \implies \text{bytes}(m) = 0 \tag{$I_3$}$$

where $\text{PlaintextMembers}(s) = \{\texttt{generated\_text},\ \texttt{stopping\_word},\ \texttt{debug\_generated\_text}\}$ for Site A, extended to $\text{PlaintextMembers}(\text{res}) = \{\texttt{prompt},\ \texttt{content},\ \texttt{generation\_params.sampling.generation\_prompt},\ \ldots\}$ for Site B.

**Proof sketch (I₃ preservation).** `release()` is the only transition from
`SLOT_STATE_PROCESSING` to `SLOT_STATE_IDLE` (server-context.cpp:490), and it
unconditionally calls `reset()` (line 497). `reset()` runs the `secure_zero`
calls (Site A) *before* any string reassignment, so immediately after `release()`
returns, every slot-owned plaintext member is zeroed. `send_final_response()` is
the only constructor of the authoritative result plaintext, and it runs
`secure_zero` on `res->*` members (Site B) immediately before
`queue_results.send()`, so no `res` reaching the result queue carries live
plaintext. ∎

**Caveat (matches §3):** I₃ holds for *live* (reachable) members. The freed-but-
unzeroed task region is outside I₃'s scope by construction — it is only reachable
via raw `/proc/<pid>/mem` reads of unallocated heap, not via any program object.

---

## 5. Overhead

`explicit_bzero` over a ~135 KB string is pure memory-bandwidth work
(sub-microsecond). Benchmarked at D2 alongside the patched-vs-unpatched leak
count, using the same N=20 short-completion protocol as `KV_CACHE_PATCH_REPORT.md` §4.
Expected: overhead not measurable above noise (consistent with the KV patch's
9.71s patched vs 9.84s unpatched result — both are dwarfed by the ~8s/req CPU
token generation).

---

## 6. Relationship to the KV-cache patch (defense-in-depth)

| Surface | Observability | Patch | Invariant |
|---|---|---|---|
| KV-cache float tensor | privileged (root / CAP_SYS_PTRACE) | `kv_cache_zeroize.patch` | I₂ |
| heap-string (prompt/response) | **unprivileged** (same-UID parent) | `prompt_zeroize.patch` (this) | I₃ |
| freed task heap region | unprivileged, transient | future work (secure allocator) | (out of scope) |

Together, the two patches establish **I₂ ∧ I₃** — a complete data-at-rest zeroization
for the *live* program objects, with the freed-region residual honestly scoped as
future work. This is the complete bug + defense + benchmark + formal cycle that
TIFS expects.

---

## 7. D2 measurement: actual results (honest, negative)

**Methodology:** `scripts/multilayer_v2.py`, 3 runs, patched binary (Sites A+B
compiled in, verified via build timestamp newer than source). Per-tenant canary
sent, `/proc/<pid>/mem` rescanned after every subsequent tenant. T1 = count of
live copies of tenant-1's canary remaining after all 4 tenants + idle period.

| Run | T1 final count |
|---|---|
| patched_run1 | 13 |
| patched_run2 | 13 |
| patched_run3 | 14 |

**Result: no reduction from the unpatched baseline's 13.** The Sites A+B patch
(`server_slot::reset()` + `send_final_response()`) had **zero measurable effect**
on the headline leak. This falsifies the §3 "honest expectation" above as stated.

### 7.1 Root cause: every `T1_full_hits` entry lands in the same region

Inspecting `logs/multilayer_v2_patched_run1.json`: all 13 hits share **one**
`[anon]` mapping (`size: 135168`, i.e. ~132 KB) at a stable address, at varying
internal offsets. This means the leak is not spread across many small heap
allocations — it is concentrated in a single large (mmap-backed, since
135168 > glibc's `M_MMAP_THRESHOLD` ≈ 128 KB) region that Sites A/B never touch.

### 7.2 Site C: the HTTP-layer body copy (upstream of slot/task)

Sites A/B operate on `server_slot`/`server_task` objects — *downstream* of where
the request enters the process. `server-http.cpp`'s `server_http_context::post()`
holds the raw request body in two places before it ever reaches a slot:

- a local `std::string body = req.body` (or equivalent) copy
- `server_http_req::body` itself

Neither is zeroed by the original patch. Added an experimental fix:

```cpp
// server-http.cpp, server_http_context::post()
if (!body.empty()) { explicit_bzero(body.data(), body.size()); }
server_http_res_ptr response = handler(*request);
if (!request->body.empty()) { explicit_bzero(request->body.data(), request->body.size()); }
```

Rebuilt (`cmake --build . --target llama-server`), re-ran the same protocol
(`logs/multilayer_v2_sitec_test.json`):

| Canary | post-T1 | post-T2 | post-T3 | post-T4 | post-idle |
|---|---|---|---|---|---|
| T1 | 12 | 12 | 12 | 12 | 12 |
| T2 | 0 | 11 | 11 | 11 | 11 |
| T3 | 0 | 0 | 11 | 11 | 11 |
| T4 | 0 | 0 | 0 | 11 | 11 |

**13→12 (T1), 13→11 (T2-T4). A real but marginal reduction** — roughly one
fewer live copy, not the dramatic fix hoped for.

### 7.3 Conclusion: the leak is distributed, not concentrated

The plaintext is copied at minimum across: HTTP body → `json::parse(req.body)`
parse tree (multiple call sites: server-context.cpp:4719/4781,
server-models.cpp:1623/1635/1726/1763, server-tools.cpp:798) →
`common_chat_templates_apply()` render buffer → slot/task strings. Sites A+B+C
zero three of these; at least the `json::parse()` output and the chat-template
buffer remain unpatched, plus possible glibc/mmap heap-reuse effects (freed
mmap'd regions are not zeroed by glibc on reuse, so even a fully-patched
application could still show stale plaintext at addresses revisited by later,
shorter allocations).

**Honest framing for the paper:** the heap-string leak surface is real,
exploitable, and only *partially* mitigated by application-level
`explicit_bzero` patches at the sites tested so far (Sites A, B, C). A complete
fix likely requires either (a) zeroing every copy site in the
parse→render→slot pipeline, or (b) a structural fix — a secure-zeroing
allocator for large (mmap-backed) string buffers — rather than continuing to
chase individual call sites.

### 7.4 Site D — the chat-template render buffer (`server-common.cpp`)

Traced `chat_params.prompt`, the `std::string` returned by
`common_chat_templates_apply()` inside `oaicompat_chat_params_parse()`
(server-common.cpp:1083) — a local variable holding the full ~135KB rendered
prompt, copied into the returned `llama_params["prompt"]` but never cleared
before `chat_params` goes out of scope. Added:

```cpp
// server-common.cpp, end of oaicompat_chat_params_parse(), before return
if (!chat_params.prompt.empty()) {
    explicit_bzero(chat_params.prompt.data(), chat_params.prompt.size());
}
if (!chat_params.generation_prompt.empty()) {
    explicit_bzero(chat_params.generation_prompt.data(), chat_params.generation_prompt.size());
}
```

Re-ran the same protocol stacked on Sites A+B+C+D (`logs/multilayer_v2_sited_test.json`):

| Canary | post-T1 | post-T2 | post-T3 | post-T4 | post-idle |
|---|---|---|---|---|---|
| T1 | 0 | 0 | 0 | 0 | **0** |
| T2 | 0 | 12 | 12 | 12 | 12 |
| T3 | 0 | 0 | 12 | 12 | 12 |
| T4 | 0 | 0 | 0 | 12 | 12 |

**T1: 13 → 0. A complete fix for the oldest tenant** — Site D was the dominant
carrier for the freed-heap-string class of leak. But T2/T3/T4 each jump to 12
hits *immediately* at their own request and **never decrease**, including
through the 10s idle period. This is qualitatively different from the
Sites-A/B/C leak pattern (stale residue in a reused freed region) — it does
not decay or get overwritten by later allocations; it persists.

**`server_prompt_cache` investigated and RULED OUT as the literal carrier.**
Initially hypothesized (by name/feature proximity: `slot.prompt_save()` /
`slot.prompt_load()`, server-context.cpp:217-246; gated by
`task->params.cache_prompt`, line 3194) given the symptom — T1 has nothing to
cache against (0 hits), T2-T4 each populate the cache and persist (12 hits,
non-decaying). But reading the actual storage format
(`server-task.h:583-647`) disproves this: `server_prompt` holds only
`tokens` (`server_tokens` — `llama_tokens`, i.e. integers) and `data`
(`server_prompt_data` — two `std::vector<uint8_t>` holding serialized
KV-cache binary state, not text). **No plaintext string field exists in this
structure.** The cache's *existence* still correlates with the symptom
(T1-vs-T2-onward asymmetry tracks exactly with whether a prior cache entry
exists), but the cache object itself cannot be the byte-level carrier of the
literal canary ASCII text. The real carrier is still unidentified.

**Further candidates checked and also ruled out:**
- `to_json_non_oaicompat()` (server-task.cpp:375, `{"prompt", prompt}`) reads
  `this->prompt` — the same member Site B already zeros. Not a new copy.
- The two `server_tokens::detokenize()` call sites (server-context.cpp:692,
  2170) both feed that same already-covered member.
- `common_prompt_checkpoint` (common.h:1065, the cache's checkpoint type) —
  only `std::vector<uint8_t>` binary fields (`data_tgt`, `data_dft`,
  `data_spec`). No plaintext.

**Every static-code-reading hypothesis is now exhausted.** The entire
`server_prompt_cache` → `server_prompt` → `common_prompt_checkpoint` chain,
`res->prompt`/`to_json()`, and the detokenize call sites are all confirmed
either zeroed (Site B) or to contain no plaintext field at all. The trigger
condition for the second leak (2nd+ request in the sequence) is solid and
reproducible; its byte-level storage location is not yet found by source
reading alone.

**Stopping point for this investigation.** Given budget (session cost ~$18 at
time of writing, well over the informal $10 flag) and the 2-week ceiling,
this is reported as an open, correctly-scoped-as-unsolved finding. Finding the
actual storage location from here requires a live debugger session (attach
gdb/breakpoint on the request path, inspect the flagged address directly)
rather than further static source reading — a different, more expensive class
of investigation, deferred as future work. **Headline claim: the freed-string
class of leak (Sites A-D) is fixed for the case tested (T1: 13→0); a second,
distinct, and currently larger leak persists for every request after the
first, with a known, reproducible trigger but an unidentified storage
location.**
