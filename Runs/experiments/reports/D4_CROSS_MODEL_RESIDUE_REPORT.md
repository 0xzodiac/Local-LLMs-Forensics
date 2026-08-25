# D4 — Cross-Model Heap Residue (in-process model swap)

**Status: CONFIRMED POSITIVE.** Plaintext from model A's request survives a
full in-process swap to a completely different model (B), present in B's
heap before B ever processes a single request.

## Why this needed a patch first

llama-server has no built-in way to swap models within one process:
- Router mode (`/models/load`) spawns a **separate child process** per
  model (`server-models.cpp`, `to_char_ptr_array` builds argv for `exec`) —
  no shared heap, cross-model residue isn't testable there.
- Single-instance sleep/wake (`server-context.cpp:980-992`,
  `handle_sleeping_state`) only reloads the **same** model path — a
  power-save feature, not a model swap.

Added a research-only endpoint, `POST /admin/swap_model` (`server.cpp`,
guarded by `if (!is_router_server)`), that calls the existing public
`server_context::load_model(common_params&)` with a path-overridden copy of
the launch params. `load_model()` assigns a new value to the
`llama_init` unique_ptr (`server-context.cpp:1187`), whose move-assignment
destroys the previous model/context/KV-cache before the new one loads —
so this is a real in-process unload+load cycle, same PID throughout.

## Method

`scripts/d4_cross_model_residue.py`: same canary-scan methodology as
`multilayer_v2.py` (UUID canary, `/proc/<pid>/mem` scan of writable maps).

1. Start `llama-server` with model A (NVIDIA-Nemotron-3-Nano-4B-Q4_K_M).
2. Send one chat request containing `canary_a`. Scan → baseline hit count.
3. `POST /admin/swap_model` with model B (Qwen3.5-9B-Q4_K_M). Confirm
   same PID. Scan for `canary_a` again — **before B serves any request**.
4. Send one chat request to model B containing `canary_b`. Scan for both.

## Result

| Phase | canary_a hits | canary_b hits |
|---|---|---|
| post model-A request | 13 | — |
| post-swap, pre-request (model B loaded, idle) | **13** | — |
| post model-B request | **13** | 11 |

Same PID confirmed before/after swap (`333364` → `333364`). All 13
`canary_a` hits land in one `[anon]` region (`212992` bytes) — the raw HTTP
request-body JSON string from model A's request:

```json
"...ser\", \"content\": \"Summarize this note. Canary (do not include): CANARY_A_b8a6f911c7f94dc8b55a11e8a66e451f. Note: monitoring test.\"}], \"max_tokens\": 8, ..."
```

## Interpretation

This is the **same unidentified leak class** already documented as open in
`PROMPT_ZEROIZE_PATCH_REPORT.md` §7 / `PROGRESS_D1_D3.md` (the persistent
12-13-copy leak that Sites A-D don't reach) — now shown to be **model-
independent**. The leaked buffer isn't owned by anything `load_model()`
frees or reallocates (it's not part of `model_tgt`/`ctx_tgt`/KV-cache at
all), so swapping the entire model underneath it has zero effect. Severity
implication: on a shared multi-tenant server that serves different models
to different users (a real, common deployment shape — router mode, or
sequential model-swap for resource-constrained boxes), **a later user
running a completely unrelated model can recover a previous user's
plaintext prompt**, not just same-model session bleed.

## Honest limitations

- n=1 swap cycle, one model pair (nemotron→qwen), CPU-only build.
- `/admin/swap_model` is a research patch, not upstream — not safe under
  concurrent traffic (no lock around the swap), added for this test only.
- Root storage location is still unidentified at the source level (same
  open status as the existing finding) — this result extends the severity
  claim, it doesn't resolve the location.
