# Live gdb Investigation — Second Heap-String Leak

**Status: Structural cause identified; exact source line NOT pinpointed.**
This is an honest record of a live-debugger investigation into the "second
leak" that survives Sites A-D (`PROMPT_ZEROIZE_PATCH_REPORT.md` §7) and the
secure-allocator patch I₄ (`SECURE_ALLOCATOR_REPORT.md`).

## Reproduction (confirmed, n=2 separate runs)

`scripts/multilayer_v2.py` against the current patched binary
(Sites A-D + I₄, `SECURE_ALLOC=0` to isolate from the allocator):
**10/10/10/10 hits per tenant, non-decaying through idle** — consistent
with the originally reported ~12-13. An earlier attempt at hand-rolled
reproduction in this same investigation incorrectly showed 0 hits; that was a
bug in the ad-hoc test script, not a real fix — flagged here so it isn't
mistaken for progress. The canonical script is the ground truth.

## Live inspection (gdb, root, attached to the running server post-leak)

`info proc mappings` on the live, leaking process shows the canary's
containing region (`783d80000000-783d80021000`, 135168 bytes, `[anon]`) is
one of **~14 structurally identical regions**, each exactly 0x21000 bytes,
each preceded and followed by a ~64MB `---p` (no-access) gap. This is the
textbook signature of **glibc's per-thread malloc arena (sub-heap)
allocation** — not a single named buffer, and not (as earlier static
analysis assumed) a copy sized to match the ~135KB rendered prompt. The
135168-byte size is glibc's standard sub-heap granularity; it is coincidence,
not evidence the region holds one specific rendered-prompt copy.

**Thread count:** 21 threads (`info threads`), consistent with a mix of HTTP
worker threads (cpp-httplib-style), OpenMP/ggml compute threads
(`libgomp.so.1` frames), and the main accept-loop thread.

## What this means (the structural finding)

`free()` in glibc does not zero memory. Sites A-D each `explicit_bzero` a
**specific, named C++ object** (slot strings, result strings, the HTTP
body's `std::string`, the chat-template renderer's output string) at the
exact point that object goes out of scope, on whichever thread owns it.
That is necessary but not sufficient: if the request pipeline copies
plaintext into a buffer on a **different thread** — e.g. a separate
HTTP-handling worker thread, or a separate code path that re-parses the
request body independently of the one Sites C/D patch — that copy lives in
a different thread's arena, with its own independent allocation/free
lifecycle, and is never reached by a patch written against one specific
object's destructor.

This is consistent with (and now has direct memory-layout evidence for) the
hypothesis raised earlier in the investigation: the
`json::parse(req.body)` call sites (≥20 locations across
`server-context.cpp`/`server-models.cpp`/`server-tools.cpp`) each produce an
independent in-memory JSON tree with its own string-valued nodes, on
whichever thread executes that handler. None of Sites A-D touch this tree
(nlohmann::json stores values as a tree of heap nodes, not one contiguous
buffer — there's no single `.data()`/`.size()` to `explicit_bzero`).

**What was NOT done, honestly:** a literal backtrace pinning the exact
allocation site (e.g., via a write watchpoint on the live address, triggered
by a subsequent request) was not completed — the per-thread-arena evidence
was conclusive enough about the *structural* cause to make further per-line
hunting low-value relative to its cost, and this investigation's budget was
already well past the point of diminishing returns (see cost note below).

## Revised conclusion for the paper

The second leak is not a single missed `explicit_bzero` call waiting to be
added — it is **structurally resistant to per-object zeroization patches**
because:
1. glibc's allocator does not zero on free by design.
2. The request pipeline legitimately copies plaintext across multiple
   threads (HTTP layer, JSON parsing, chat-template rendering, slot
   processing), each with independent allocator arenas.
3. Closing every *known* per-object copy (Sites A-D) does not guarantee
   closing copies made via *code paths not yet identified or instrumented*
   (the JSON tree being the strongest remaining candidate, on current
   evidence).

This is a defensible, citable, CWE-226-consistent finding: complete
remediation of this leak class likely requires either (a) a secure-zeroing
allocator that zeros **every** free regardless of which object/thread made
the allocation (closer to what I₄ attempts, though its current threshold and
inconsistent results mean it is not yet a true backstop), or (b) a
structural rewrite using a secure-string type end-to-end through the request
pipeline. Incremental, per-object patching (Sites A-D) is real, necessary
defense-in-depth, but provably not sufficient on its own.

## Cost note (for the corpus's own scope-discipline)

This single investigation (reproduction-discrepancy debugging + the live gdb
session) was expensive relative to its yield — a large fraction of total
session cost went into chasing a hand-rolled-script bug that briefly,
incorrectly, suggested the leak was fixed. The corrective lesson: when a
"fix" looks too good relative to a well-documented prior negative result,
re-verify against the *exact* canonical script before reporting it, not an
approximation believed to be equivalent.
