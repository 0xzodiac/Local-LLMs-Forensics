# D7 — End-to-End PII Attack-Chain Demo

**Status: PARTIALLY CONFIRMED, with a real scope correction.** The disk-log
channel is confirmed and more precisely characterized than prior reports
stated. The memory-residue channel, tested against LM Studio's actual
shipped binary (not the research llama.cpp build), did **not** reproduce —
this narrows, rather than extends, an existing claim, and is reported as
such rather than glossed over.

Uses synthetic, clearly-fake PII (`SSN 000-00-XXXX (SYNTHETIC_TEST_PII_...)`)
throughout — no real personal data was involved at any point.

## What was tested

Two leak channels documented separately in earlier work were meant to be
chained into one demo:

1. **Disk:** `~/.lmstudio/server-logs/` cleartext log
   (`logSensitiveData: true`, confirmed in `.internal/http-server-config.json`)
   — `PROVIDER_LEAK_MISSION_REPORT.md`.
2. **Memory:** `/proc/<pid>/mem` heap-string residue (Sites A-D fixed, a
   second leak still open) — `PROMPT_ZEROIZE_PATCH_REPORT.md`, extended
   cross-model in `D4_CROSS_MODEL_RESIDUE_REPORT.md`.

Script: `scripts/d7_pii_attack_chain.py`. Loaded `nvidia/nemotron-3-nano-4b`
in LM Studio, sent one chat request containing a synthetic PII string,
checked both channels.

## Result 1: disk channel — confirmed, with a correction

**First run** (long synthetic PII, ~85 chars in the `content` field):
0 hits searching for the exact string. Investigation found why: LM Studio's
log writer truncates long `content` field values, writing prefix +
`<Truncated in logs>` + suffix instead of the full string:

```
"content": "Please file this note for my records: SSN 000-00-7... <Truncated in logs> ...e53, not a real person). Just acknowledge briefly."
```

**Follow-up run** (short synthetic PII, `PII7409SHORT`, 12 chars): full,
exact match recovered verbatim from disk:

```
/home/elaref/.lmstudio/server-logs/2026-06/2026-06-24.1.log:
      "content": "note: PII7409SHORT"
```

**Correction to prior framing:** `PROVIDER_LEAK_MISSION_REPORT.md` and
`FINAL_COMPREHENSIVE_REPORT.md` describe this channel as "full cleartext"
retention without qualification. That holds for short content. For content
fields long enough to trigger the truncation behavior (threshold not yet
pinned down precisely — empirically somewhere under ~85 chars), only the
prefix and suffix survive verbatim on disk; a sufficiently long embedded
secret is **not** fully reconstructable from the disk log alone. This is a
real, previously-undocumented nuance, not a contradiction of the channel's
existence — the leak is real, just bounded by content length in a way the
earlier reports didn't test for.

## Result 2: memory channel — not reproduced on the production binary

Scanned the actual LM Studio inference worker process
(`/home/elaref/.lmstudio/.internal/utils/node ... llmworker.js`, the process
hosting `liblmstudio_bindings.node`, LM Studio's compiled llama.cpp
backend) for the synthetic PII string immediately after the chat request
completed. **0 hits**, across:
- the original 200MB region-size cutoff (matching `multilayer_v2.py`'s
  filter), and
- a widened 2GB cutoff after finding the worker has a 510MB writable region
  excluded by the original filter.

**This does not contradict D2 or D4.** Those findings (Sites A-D, the open
second leak, its cross-model persistence) were established against a
*separately built* research `llama-server` binary
(`llama-cpp-build/build/bin/llama-server`, the project's own compiled
checkout), never against LM Studio's actual shipped, bundled llama.cpp
backend. These are different compiled artifacts — possibly different
llama.cpp versions, different build flags, different allocator behavior.
**The heap-residue finding has only ever been demonstrated on the research
build.** Whether LM Studio's shipped binary has the same bug is an open
question this run could not answer with a single n=1 negative — it's
consistent with "LM Studio's bundled build doesn't have this specific bug,"
"the leak exists but needs a different trigger condition (the original
second leak's trigger was multi-request session bleed, not necessarily a
single first request)," or "the relevant buffer was freed/GC'd in the ~2s
between response and scan."

## Revised interpretation

The originally-assumed single end-to-end chain (one tool, one process,
secret recoverable from both disk and RAM) is **not what was demonstrated**.
What's actually proven, precisely:

- LM Studio **does** write prompt content to disk in cleartext by default
  (`logSensitiveData: true` is the shipped default per
  `.internal/http-server-config.json`), **bounded by a content-length
  truncation** that protects sufficiently long secrets from full disk
  recovery via this specific log file.
- The heap-residue bug (Sites A-D / the open second leak / D4's cross-model
  extension) is proven against the project's research llama.cpp build, and
  has **not** been shown to apply to LM Studio's actual shipped binary.

For the paper, this is a more defensible, more precise claim than the
originally hoped-for unified chain: two real, separately-scoped findings,
each with its own evidence and its own boundary condition, rather than one
overstated combined narrative.

## Honest limitations / follow-ups not done

- Did not pin down the exact truncation length threshold (would need a
  binary search over content lengths — cheap, just not done here).
- Did not retest the memory channel with near-zero scan latency (racing the
  scan against the response, rather than the ~2s gap used here) or against
  multiple requests (the original second leak's known trigger condition was
  session-level, not single-request).
- n=1 for both channels — no repeats.
- Did not test whether LM Studio's bundled backend is a router-mode or
  single-instance llama.cpp invocation, which (per D4) materially changes
  what's even architecturally possible to test.
