# PHI4_DEFENSE_LLAMACPP_REPORT Audit: Degradation or Flat-Rate-Plus-Variance?

**Verdict: Flat-rate-plus-variance. Progressive degradation is ruled out.**

## Evidence

### 1. Print_timing eval tok/s sequence — no monotonic trend

All six `print_timing` "eval time" entries (completed tasks only — timed-out tasks produce no print_timing):

| Log line | Task | Eval tok/s |
|----------|------|-----------|
| L50      | 0    | 0.24      |
| L65      | 11   | 0.23      |
| L80      | 24   | 0.20      |
| L120     | 91   | 0.27      |
| L138     | 106  | 0.27      |
| L153     | 119  | 0.23      |

Range 0.20–0.27 tok/s, mean 0.24. Sequence is **not** monotonically decreasing — if anything the later half (mean 0.257) is faster than the first half (mean 0.223). Tasks 106 and 119 are the two fastest of the whole run (Test 7 completed in 50.9s, Test 8 in 66.2s).

### 2. Completed tests interleaved among timeouts

The chronological task sequence from the log:

- tasks 0, 11, 24 (slot 3) → Tests 1–3 complete
- tasks 38, 61 (slot 3) → TIMEOUT
- tasks 91, 106, 119 (slot 2) → Tests 6, 7, 8 complete
- tasks 133, 160, 183, 209, 237, 252, 277 (slots 2→1) → TIMEOUT

Tests 6–8 complete **after** the first timeouts (tasks 38, 61). This is incompatible with progressive degradation — if the server were leaking memory or exhausting slots, later tasks would be slower, not faster.

### 3. Timeouts span all slots evenly

Slots 3 (3 ok, 2 timeout), slot 2 (3 ok, 2 timeout), slot 1 (0 ok, 5 timeout). The final 5 timeouts are on slot 1 simply because slots 2 and 3 were already occupied by concurrent requests. No slot-specific exhaustion pattern.

### 4. The 120s budget calculation explains pass/fail

At ~0.24 tok/s decode, each output token costs ~4.2s. Completed tests generate only 9–13 output tokens (total: 50–80s). A test generating >20 tokens at the same rate would need ~84s of decode plus variable prompt-eval time, easily exceeding 120s.

Task 237 (L219) is the context-overflow test: n_tokens=519 at timeout vs 279–289 for all other timeouts. The ~230 extra tokens are the filler text. Even at 6–7 tok/s prompt ingestion (L49, L119), this adds ~35–40s to prompt-eval alone, consuming ~1/3 of the timeout budget before decode begins.

## Conclusion

The 9/15 timeout pattern is **not** caused by progressive server degradation (memory leak, slot exhaustion, slowdown trend). It is the predictable consequence of:

1. A flat ~0.24 tok/s CPU decode rate creating a hard ceiling on output tokens per 120s window (~22–24 tokens max net of prompt eval)
2. Per-prompt variance in output length (some prompts induce longer responses pushing past the ceiling)
3. One outlier (context-overflow test, ~6000+ chars) whose prompt-eval alone consumes large fractions of the timeout
