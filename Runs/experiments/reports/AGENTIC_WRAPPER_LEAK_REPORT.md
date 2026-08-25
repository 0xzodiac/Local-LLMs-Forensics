# Agentic Wrapper (Claude Code) — Local-Backend Leak & Reliability Report

**Date:** 2026-06-20
**Wrapper:** Claude Code CLI (`claude -p`), via `ANTHROPIC_BASE_URL` override
**Backends tested:** LM Studio (localhost:1234), Ollama (localhost:11434)
**Environment:** same box as `PHI4_DEFENSE_ANALYSIS.md` (NVIDIA T1200 4GB VRAM, 15GB RAM)

## Question

Does pointing Claude Code at a "local" LLM backend actually keep generation
local end-to-end, or does the wrapper itself become a leak/reliability vector
(plaintext disk logging, oversized requests, silent hangs) that undermines
the "local = private" assumption?

## Method

1. `scripts/agentic_wrapper_test.py` — plants a canary, calls `claude -p`
   against each backend.
2. `scripts/agentic_log_scanner.py` — greps `~/.claude` and `~/.openclaw` for
   a given canary, skipping credential files by name.
3. Packet capture (`tshark` on `lo`, port 1234, via WSL) while reproducing
   the LM Studio hang, to see what actually crosses the wire.

## Results

| Backend | API shape | `claude -p` result | Notes |
|---|---|---|---|
| Ollama :11434 | OpenAI-style; no native Anthropic `/v1/messages` | Fails fast, clean: *"issue with the selected model (claude-sonnet-4-6)... Run --model"* | No inference occurs. Not a viable backend without a compat shim. |
| LM Studio :1234 | **Genuine Anthropic `/v1/messages` compat** (verified: real `type:"message"`, `content` blocks, `stop_reason`, `usage.cache_read_input_tokens`) | Hangs the full timeout (60–100s), **zero** stdout/stderr, every model tried (phi-4-reasoning-plus, qwen3.5-9b) | Backend is API-compatible in principle. |

A hand-crafted ~240-byte POST to the same LM Studio endpoint/model returned a
real response in 13.4s. `claude -p`'s own request never did, on any timeout
tried (60s, 100s).

### Root cause (packet capture)

- `claude -p` opens a new TCP stream and sends a **~130KB POST** to
  `/v1/messages` — Claude Code's full system prompt + tool-use schemas,
  split across 4 segments (16384 + 16384 + 53824 + 43411 bytes).
- LM Studio **fully ACKs every byte** of the request (confirmed at the TCP
  level).
- After that: **nothing.** No response bytes, no SSE/streaming chunks, no
  error, no FIN, no RST — for the full remaining ~72s of a 75s capture
  window.
- Post-incident, LM Studio stopped responding even to the trivial request
  that had worked in 13.4s minutes earlier. **Confirmed precisely:**
  `GET /v1/models` still returns 200 in 0.2s (HTTP server alive), but
  `POST /v1/messages` is still hung minutes later (>10s timeout, no
  response) — so specifically the *inference worker/queue* is wedged, not
  the whole process. This matches the "workers enter Dl state under load"
  instability already documented in `PHI4_DEFENSE_ANALYSIS.md`, but here
  triggered by Claude Code's *normal, unmodified* request size — no
  adversarial prompt needed. As of writing, the worker has not recovered on
  its own; a restart of LM Studio is likely required to clear it.

## Key Findings

1. **LM Studio's Anthropic-compat layer cannot handle Claude Code's actual
   request size/shape.** A real agentic coding wrapper's baseline payload
   (system prompt + tool schemas, ~130KB) silently wedges it. This is a
   reliability/availability finding, not a content leak: the local backend
   becomes unusable from one normal-sized request.
2. **The original disk-leak hypothesis is UNRESOLVED, not refuted.** No
   generation ever completed end-to-end through the wrapper on this
   hardware, so what (if anything) Claude Code persists to disk for
   genuinely local-model-sourced content was never observed.
3. **Methodological trap confirmed:** a canary typed directly into a Bash
   argument trivially "leaks" into Claude Code's own transcript of *that
   session* (it logs its own tool calls). Any future canary test must source
   the canary from inside the tested process's isolated output, not from the
   orchestrating shell, or the scanner will report a false positive against
   the wrong transcript.
4. Ollama's failure is a clean, instant API-shape mismatch — no risk surface
   there since no inference ever runs.

## Follow-up Required

- Confirm/restart LM Studio (it may still be wedged) before retrying.
- Retry with a *much* smaller tool-schema payload (e.g. `claude -p` with
  `--disable-slash-commands` / minimal tool set, if available) to see if a
  smaller-but-still-realistic request completes, isolating "payload size"
  from "payload shape" as the trigger.
- If a completion is ever obtained, re-run the scanner with a canary
  produced *inside* the spawned `claude -p` subprocess's own session
  directory (e.g. `~/.claude/projects/-tmp-wrapper_test/...`), not the
  orchestrating shell, to get a clean leak/no-leak answer to the original
  question.
- Consider testing LM Studio's `/v1/messages` directly with a synthetically
  large-but-simple body (e.g. 130KB of repeated text, no tool schemas) to
  isolate size vs. tool-schema complexity as the wedge trigger.
