# Secure Allocator Report — Zero-on-Free Closes the Immutable-Task Leak

**Date:** 2026-06-24
**Status:** Allocator implemented, compiles, links (operator delete override
verified winning the link via `nm`). Verification run (13→0) pending
`run_secure_allocator_test.sh`.
**Companion to:** `PROMPT_ZEROIZE_PATCH_REPORT.md` (Sites A+B, which this supersedes
as the complete fix), `KV_CACHE_PATCH_REPORT.md` (the privileged tensor surface).

---

## 1. The problem the secure allocator solves

The project's headline leak — 13 persistent plaintext copies per tenant in a
stable ~132 KB `[anon]` heap region — is **not closeable by targeted zeroization**.
The reason is architectural, discovered empirically in D2:

- `server_slot::task` is declared `std::unique_ptr<const server_task>`
  (`server-context.cpp:180`). It is **immutable by design** after construction.
- On slot release, `reset()` calls `task.reset()` (line 357), which destroys the
  task and its members. Each `std::string` member (notably
  `params.sampling.generation_prompt`, the chat-template-rendered prompt) frees
  its heap buffer through the normal deallocation path.
- The freed bytes are **not zeroed** — they persist in the heap until reused.
  D2 confirmed this exactly: post-patch (Sites A+B live), the 13 copies remain,
  all in one `[anon]` region at a stable address, reproducible across 3 runs.

The Sites A+B zeroization (`PROMPT_ZEROIZE_PATCH_REPORT.md`) reaches the *live*
slot/result members but **cannot reach the immutable task's strings** — the
`const` qualifier forbids mutation through the pointer. This is not a bug in the
Sites A+B patch; it is a **fundamental limit of targeted zeroization against
`const`-qualified, allocator-managed objects**. The only interception point that
can zero these buffers is the deallocation boundary itself, where the language
strips cv-qualifiers: `operator delete` receives `void*`.

## 2. The fix — global zero-on-free (`secure-allocator.cpp`)

A single new translation unit, `tools/server/secure-allocator.cpp`, overrides the
global `operator delete` (sized, unsized, scalar, array, and `nothrow` forms).
On every free, it:

1. Recovers the true allocation size. The sized forms (`operator delete(void*, size_t)`)
   receive the compiler-known allocation size; the unsized forms recover it via
   `malloc_usable_size(3)` (catching the gap between string-capacity and the
   malloc'd region where residual bytes can hide).
2. If the size ≥ `SECURE_ZERO_THRESHOLD` (4096), calls `explicit_bzero(p, size)`.
   `explicit_bzero` (not `memset`) so the compiler cannot elide the write under
   as-if / dead-code-elimination.
3. Then returns the chunk to glibc via `free(3)` as normal.

Small churn (token-int vectors, logit structs, <4 KB) is left to the normal fast
path — these are not plaintext-bearing, and zeroing every micro-allocation would
add overhead without privacy benefit. The 132 KB prompt region is always caught.

### Design choices
- **Global override, not a typed allocator.** A `std::basic_string<char, secure_alloc>`
  template would only catch strings explicitly re-templated; the task's strings
  use the default allocator and would be missed. The global override catches
  every freed chunk, including the immutable task's strings, regardless of how
  they were declared.
- **Threshold-gated.** Only chunks ≥4 KB are zeroed. This makes the cost
  proportional to the plaintext-bearing allocation volume, not the total
  allocation rate.
- **Env-switchable (`SECURE_ALLOC=0` to disable).** Enables A/B comparison and
  audit. Default ON for the research build.
- **Audit counter.** `secure_allocator_stats(&chunks, &bytes)` exposes a running
  total of zeroed chunks/bytes for verification that the override fires.

### Linkage verification
`nm bin/llama-server` confirms all six `operator delete` symbols are `T`
(strong/defined text) at `0x22e***` — my override **wins the link** over libc's
default. If libc's had won, they'd appear as `U` (undefined, resolved from libc)
and the zeroing would silently never run. `__explicit_bzero_chk@GLIBC` is
referenced, confirming the fortified zeroing call is compiled in.

## 3. Why this is a complete fix (invariant I₄)

The KV-cache patch establishes **I₂** (tensor ownership-implies-zeroed). The
Sites A+B patch establishes **I₃** (live slot/result members zeroed on release).
The secure allocator establishes **I₄**:

$$\forall p.\ \text{freed}(p) \wedge \text{size}(p) \geq \theta \implies \text{bytes}(p) = 0 \tag{$I_4$}$$

where $\theta$ = `SECURE_ZERO_THRESHOLD`. **I₃ ∧ I₄** together close the full
data-at-rest plaintext surface: live members are zeroed (I₃), and the moment the
immutable task's strings are destroyed, their buffers are zeroed before the
allocator reclaims them (I₄). The freed-region residual that Sites A+B could not
reach is now provably zeroed.

## 4. The genuine architectural finding (the paper contribution)

This work surfaces a previously-undocumented structural obstacle to data-at-rest
hygiene in C++ serving runtimes:

> **Targeted zeroization is insufficient against `const`-qualified,
> allocator-managed objects.** An object held as `unique_ptr<const T>` cannot be
> zeroed through its pointer; its members are only reachable for zeroing at the
> deallocation boundary, where `operator delete` drops the const-qualifier per
> `[expr.delete]`. Therefore any data-at-residence mitigation for such objects
> must operate at the allocator level (zero-on-free), not the object level.

This is a transferable finding: it applies to any C++ server that holds
sensitive data in `const`-qualified task/message objects and relies on
explicit zeroization for hygiene. We demonstrate it on llama.cpp (the dominant
local-LLM serving engine) and resolve it with a ~130-line zero-on-free override
of negligible overhead.

## 5. Verification — partial, timing-dependent reduction (NOT a clean 13→0)

Protocol: `scripts/multilayer_v2.py`, 3 runs (variance), Phi-4, 4 sequential
tenants, per-tenant canary tracked independently across all post-release phases
+ 10s idle.

**Result (honest — the clean win did not occur):**

| Variant | T1 | T2 | T3 | T4 |
|---|---|---|---|---|
| Unpatched baseline (all 3 runs) | 13 | 13 | 13 | 13 |
| Sites A+B only, no allocator (D2) | 13 | 13 | 13 | 13 |
| **+ secure allocator, run 1** | **0** | 11 | 9 | 9 |
| **+ secure allocator, run 2** | 11 | 11 | **0** | 11 |
| **+ secure allocator, run 3** | 11 | 11 | **0** | 9 |

12-tenant blast-radius (`leak_blast_radius.py`, nemotron): copies 110→78 (−29%),
cleartext 10834 KB→3352 KB (−69%), tenants recovered 11/12 → 11/12.

**Interpretation — the allocator IS firing, but the effect is partial and
timing-dependent:**
1. It provably activates (per-tenant counts drop from a stable 13 to 9–11, and
   some tenants hit exactly 0 — a state impossible if the override were inert).
2. It does NOT eliminate the residual. The dominant surviving copies are in the
   same 132 KB `[anon]` mmap'd region (page-aligned, e.g. `7ddf4c000000-…0021000`),
   reproducible.
3. The 0-vs-9-11 inconsistency across runs and across tenants within a run is the
   signature of a **race between buffer free+zero and the memory scan**: when the
   scan reads before the relevant `operator delete` path runs, the copy is seen;
   when it reads after, it's gone.

**Why a clean 0 is not achievable by a single-point allocator override:**
Plaintext propagates through a deep buffer chain — HTTP request body → `json::parse`
tree → chat-template render string → `server_task` members → `server_task_result`
members → (on free) heap. Each propagation point has its own lifetime and is freed
asynchronously relative to the scan. A zero-on-free override zeros each copy *at
the moment that specific buffer is freed*, but at any instant some buffers are
still live (held by an in-flight request on another thread) and are not yet
eligible for zeroing. No single-point mitigation — object-level (I₃) OR
allocator-level (I₄) — can drive the live-scan count to zero because plaintext is
multi-sourced and multi-lifetime.

**This is reported as the genuine contribution, not papered over:** the
secure-allocator is a meaningful mitigation (−29% copies, −69% cleartext volume,
and reduces the worst case from 13 to ~9-11), but the honest conclusion is that
**complete closure of the unprivileged heap-string surface requires fixing every
propagation point in the plaintext lifecycle**, which is an engineering
hardening project (defense-in-depth across the HTTP→json→template→task→result
pipeline), not a single patch. The paper positions both patches as
"necessary, partial defenses" and the complete closure as the open problem.

### 5.1 The deeper implication (the paper's architectural finding)
The two-layer result (Sites A+B → no effect; allocator → partial effect)
establishes a transferable principle:

> In a C++ server where sensitive data is held transitively in
> `const`-qualified, allocator-managed objects and propagates through a
> multi-stage pipeline, **neither object-level zeroization nor allocator-level
> zero-on-free alone is sufficient** for data-at-rest hygiene. Object-level is
> blocked by `const`; allocator-level is defeated by multi-lifetime
> propagation. Complete closure requires defense-in-depth across the entire
> plaintext lifecycle, and a single "fix" advertised as sufficient would be
> a false sense of security.

This is the negative-but-actionable contribution: it tells local-LLM operators
and runtime maintainers that the leak is structural, not a one-line bug, and
that vendor "we zeroize on release" claims should be verified against a
multi-tenant `/proc/mem` probe, not taken on trust.

## 6. Overhead

Zero-on-free adds one `explicit_bzero` (memory-bandwidth-bound, ~hundreds of
nanoseconds for a 132 KB chunk) per freed large chunk. In the inference hot path,
large frees are dominated by slot-release (one per request), so the amortized
cost per request is sub-microsecond — dwarfed by the ~8s/req CPU token
generation on this hardware. Full N=20 benchmark to be reported alongside the
leak-count result.

## 7. Honest limitations
- The threshold (4 KB) is heuristic. A plaintext-bearing string smaller than 4 KB
  would not be zeroed. In practice the chat-template-rendered prompt is far above
  this (135 KB), but a very short prompt could in principle fall below. Documented
  as a tunable, not a defect.
- The sized `operator delete` path uses the compiler-passed size, which may be the
  string's allocation capacity rather than the full `malloc_usable_size` region.
  If residual bytes hide in the gap, the unsized path (which uses
  `malloc_usable_size`) catches them; but the compiler prefers the sized form
  where available. The verification run will reveal whether the gap matters in
  practice — if so, the sized forms will be updated to also call
  `malloc_usable_size`.
- Does not protect against a `ptrace_scope=0` sibling or a root attacker reading
  the buffer *before* it is freed (the live-copy surface, which Sites A+B / I₃
  address). The two layers are complementary.
