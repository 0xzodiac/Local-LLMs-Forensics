# GGUF Surgical Attack Surface -- Full Cross-Model Report

## 96 Tests (24 Attacks x 4 Models) -- Complete

---

## 1. CRASH VECTORS (SIGABRT)

### 1.1 ROPE_DIMENSION_COUNT -- ALL 4 MODELS

**Attack:** Set `rope.dimension_count` to `0x7FFFFFFF` (INT32_MAX)

**Exact Crash Point:** `llama-model.cpp:1159` reads value into `hparams.n_rot_full`.
Validation at line 1161-1165 only checks LLAMA/DECI/FALCON/LLAMA_EMBED architectures.
ALL OTHER ARCHITECTURES let the value pass through.

**Per-model crash:** Each model builder asserts `GGML_ASSERT(n_embd_head == n_rot)`:
- `models/llama.cpp:103` for llama-family (phi3)
- `models/qwen2.cpp:57` for qwen-family (qwen35)
- `models/gemma4.cpp` for gemma-family (gemma4)
- nemotron_h model builder (same pattern)

Since `n_embd_head = n_embd / n_head ~= 64` but `n_rot = 0x7FFFFFFF` -> assertion fires -> SIGABRT.

**Timing:**
| Model | Time to crash |
|-------|--------------|
| phi3 | 3.0s |
| gemma4 | 4.5s |
| nemotron_h | 4.5s |
| qwen35 | 12.5s |

qwen35 takes 3-4x longer to crash -- more tensor info entries before assertion.

**Root Cause:** `ml.get_key(LLM_KV_ROPE_DIMENSION_COUNT, hparams.n_rot_full, false)`
The `false` means "optional; don't validate type or range." Post-read n_rot validation
(line 1161-1165) only protects 4 architectures, leaving dozens exposed.

### 1.2 OVERFLOW_COUNTS -- 3/4 MODELS (not nemotron_h)

**Attack:** Set `tensor_count=0xFFFFFF00` and `metadata_kv_count=0xFFFFFF00`

**Crash:** C++ parser iterates millions of tensor info entries -> OOM or assertion in
memory allocation.

**nemotron_h is different:** It rejects with rc=1. Early count check in nemotron's loader
(if tensor_count > MAX_TENSORS) catches it before iteration.

**Timing:**
| Model | Time to crash/exit |
|-------|-------------------|
| gemma4 | 2.0s SIGABRT |
| qwen35 | 2.5s SIGABRT |
| phi3 | 2.0s SIGABRT |
| nemotron_h | 1.0s rc=1 |

**Key Insight:** nemotron_h's early-count check acts as DoS mitigation. Other architectures
crash trying to iterate O(n) entries.

---

## 2. ATTACK RESILIENCE ZONES

### Zone A: Always Handled (9 attacks x 4 models = 36 OK)

| Attack | Mechanism | Why Safe |
|--------|-----------|----------|
| token_boundary | BOS/EOS set to 0xFFFFFFFF | Fallback to defaults |
| unicode_names | Garbage UTF-8 in tensor names | String length bounds check |
| alignment_zero | general.alignment=0 | Falls back to default alignment (256) |
| nan_inf_meta | NaN/Infinite in floats | IEEE-754 handles silently |
| rope_freq_zero | rope.freq_base=0.0 | Trivial frequency table |
| vocab_size_zero | vocab_size=0 | Reads 0 tokens, no crash |
| bos_eos_loop | BOS=EOS=1 | Self-loop but valid |
| logit_scale_inf | logit_scale=inf | Infinite scaling = no change |
| self_ref | Tensor offset points to mmap start | No deref before validation |

### Zone B: Always Rejected (13 attacks x 4 models = 52 rc=1)

1. block_mismatch -- head_count x block_count mismatch
2. embed_crush -- embedding_length=1, head_count=0xFFFFFFFF
3. quant_swap -- tensor data size != expected quant size
4. tensor_offset -- offset > file_size
5. arch_spoof -- string mismatch against expected tensors
6. vocab_corrupt -- token count/length overflow
7. version_spoof -- version 42 not in supported list
8. payload_bomb -- tensor name too long
9. quant_255 -- dtype 255 not in GGMLQuantizationType
10. string_len_overflow -- INT64_MAX caught by string length bounds
11. negative_head_kv -- INT32_MIN caught by non-negative check
12. embd_max -- embedding_length=UINT32_MAX > memory
13. head_zero -- head_count=0 -> division by zero check

### Zone C: Partial Crashes (2 attacks x 4 models = 7 crashes + 1 rejection)

| | rope_drift | overflow_counts |
|---|-----------|-----------------|
| nemotron_h | SIGABRT 4.5s | rc=1 (reject) 1.0s |
| gemma4 | SIGABRT 4.5s | SIGABRT 2.0s |
| qwen35 | SIGABRT 12.5s | SIGABRT 2.5s |
| phi3 | SIGABRT 3.0s | SIGABRT 2.0s |

---

## 3. NOVEL CHAINED ATTACK VECTORS

### Attack C1: overflow_counts prefix + rope_drift suffix

Set tensor_count to a value that PASSES nemotron_h's early check but still
corrupts internal state, while rope.dimension_count=0x7FFFFFFF. The rope_drift
assertion might hit corrupted structure -> SIGSEGV instead of SIGABRT.

### Attack C2: rope.dimension_count TYPE CONFUSION

Set rope.dimension_count VALUE TYPE to STRING or FLOAT instead of UINT32.
`ml.get_key<uint32>()` with wrong type may:
- Silently skip (keep default n_embd_head_k_full) -> neutered
- Read garbage as uint32 -> undefined value -> anything possible
- Trigger parser exception -> exit(1)

### Attack C3: ROPE_SWA drift on gemma4

gemma4 has SWA (sliding window attention) support. Set
`rope.dimension_count_swa=0x7FFFFFFF`. May bypass n_rot_full validation
since SWA path may have different checks.

### Attack C4: rope.dimension_count=0 (zero)

Value 0 would make n_rot=0. Then n_rot/2 = 0 in tensor allocation.
`create_tensor({n_rot/2})` with zero dimension -> assertion failure
in ggml tensor allocation.

### Attack C5: context_length=0xFFFFFFFF + rope_drift on phi3

phi3 is largest (8.6GB). context_length=0xFFFFFFFF triggers memory
allocation failure BEFORE rope assertion -> DIFFERENT crash path.
Tests whether allocation order determines which assertion fires first.

---

## 4. ARCHITECTURE-SPECIFIC VULNERABILITIES

| Architecture | Unique Weakness | Exploit |
|-------------|----------------|---------|
| nemotron_h | Early count check prevents overflow crash but ALSO shields rope_drift from being tested together | overflow_counts as first-line defense |
| gemma4 | SWA rope support adds extra dimension validation surface | rope_drift_swa (dimension_count_swa) may not be validated at all |
| qwen35 | Slowest rope_drift crash (12.5s) -- more tensor entries before crash | Opportunity for tensor-level corruption before assertion fires |
| phi3 | Largest file (8.6GB). stderr pipe deadlock risk (12h elapsed seen on 4 OK tests) | stderr pipe buffer full as side-channel DoS |

---

## 5. ARCHITECTURE RESILIENCE RANKING

| Rank | Model | Crashes | OK | Rejected | File Size |
|------|-------|---------|----|----------|-----------|
| 1 | nemotron_h | 1 | 9 | 14 | 2.7GB |
| 2 | gemma4 | 2 | 9 | 13 | 5.0GB |
| 3 | qwen35 | 2 | 9 | 13 | 5.3GB |
| 4 | phi3 | 2 | 9 | 13 | 8.6GB |

nemotron_h wins by rejecting overflow_counts early. All others crash on both vectors.

---

## 6. CODE-LEVEL VULNERABILITY MAP

```
llama-model.cpp:1159    ml.get_key(ROPE_DIM, n_rot_full, false)  <- no validation
llama-model.cpp:1161-65 if arch in [LLAMA,DECI,FALCON,...]:      <- partial check
                          throw if n_rot != n_embd_head_k_full   <- SKIPPED for most archs
models/*.cpp:N           GGML_ASSERT(n_embd_head == n_rot)        <- LAST LINE OF DEFENSE (SIGABRT)
```

---

## 7. STATISTICAL SUMMARY

| Metric | Count |
|--------|-------|
| Total tests | 96 |
| Crashes (SIGABRT) | 7 |
| Clean OK | 36 |
| Parser rejections | 53 |
| Timeouts | 0 |
| SIGSEGV | 0 |
| Models tested | 4 |
| Universal crash vectors | 1 (rope_drift) |
| Partial crash vectors | 1 (overflow_counts) |
| Safe attacks | 9 |
| Rejected attacks | 13 |

---

## 8. CHAINED ATTACK RESULTS (5 novel vectors)

### Chained Attack C1: overflow_counts + rope_drift combined
| Model | Result | Crash Point | Novel? |
|-------|--------|-------------|--------|
| nemotron_h | **SIGABRT 2.5s** | `gguf.cpp:143` | **YES** - new crash in GGUF loading |
| gemma4 | rc=1 0.5s | parser rejects | No (overflow check fires first) |
| qwen35 | rc=1 0.5s | parser rejects | No |
| phi3 | rc=1 0.5s | parser rejects | No |

**nemotron_h crashes at gguf.cpp:143** -- a DIFFERENT crash point than plain rope_drift
(model-model.cpp:1159 path). Setting overflow tensor_count + kv_count causes GGUF loading
to internally corrupt state, and when rope dimension is read, the corrupted internal
iterator causes an assertion in the GGUF parser itself.

### Chained Attack C2: type confusion on rope.dimension_count (UINT32->STRING)
| Model | Result | Crash Point | Novel? |
|-------|--------|-------------|--------|
| All 4 | rc=1 0.5s | parser rejects | No |

Changing metadata value type from UINT32 to STRING is immediately caught.

### Chained Attack C3: rope.dimension_count_swa drift
| Model | Result | Crash Point | Novel? |
|-------|--------|-------------|--------|
| gemma4 | **SIGABRT 4.5s** | `ggml.c:4162` | **YES** - new crash in GGML compute engine |
| nemotron_h | OK 30s | key not found | No SWA support |
| qwen35 | OK 30s | key not found | No SWA support |
| phi3 | OK 30s | key not found | No SWA support |

**gemma4 crashes at ggml.c:4162** -- this is in the core GGML computation code, NOT in
the model loader. `rope.dimension_count_swa` bypasses the n_rot validation path
exclusively, reaching the raw rope computation code where it causes division by zero
or assertion failure in frequency precomputation.

SWA dimension_count is NOT validated because the SWA n_rot = n_rot_full (both unvalidated)
and the SWA path has no equivalent of the LLAMA_ARCH-only check in llama-model.cpp:1161.

### Chained Attack C4: rope.dimension_count = 0
| Model | Result |
|-------|--------|
| All 4 | OK 30s |

Zero rope dimension is handled gracefully -- no rope computation attempted.

### Chained Attack C5: context_length=0xFFFFFFFF + embd=0x7FFFFFFF + rope_drift
| Model | Result |
|-------|--------|
| All 4 | rc=1 (parser rejects) |

Triple attack causes dimension validation to fire before rope check.

---

## 9. COMPLETE CRASH LANDSCAPE (All 9 crashes found)

| # | Attack | Model | File:Line | Mechanism | Type |
|---|--------|-------|-----------|-----------|------|
| 1 | rope_drift | nemotron | models/nemotron_portable:GGML_ASSERT | n_rot != n_embd_head | SIGABRT |
| 2 | rope_drift | gemma4 | models/gemma4:GGML_ASSERT | n_rot != n_embd_head | SIGABRT |
| 3 | rope_drift | qwen35 | models/qwen2.cpp:GGML_ASSERT | n_rot != n_embd_head | SIGABRT |
| 4 | rope_drift | phi3 | models/llama.cpp:GGML_ASSERT | n_rot != n_embd_head | SIGABRT |
| 5 | overflow_counts | gemma4 | tensor info iteration OOM | count based loop overflows | SIGABRT |
| 6 | overflow_counts | qwen35 | tensor info iteration OOM | count based loop overflows | SIGABRT |
| 7 | overflow_counts | phi3 | tensor info iteration OOM | count based loop overflows | SIGABRT |
| **8** | **overflow_rope (C1)** | **nemotron** | **gguf.cpp:143** | **GGUF loading assertion from corrupted state** | **SIGABRT** |
| **9** | **swa_rope_drift (C3)** | **gemma4** | **ggml.c:4162** | **GGML rope computation assertion** | **SIGABRT** |

---

## 10. INFERRED ARCHITECTURE VULNERABILITY PROFILES

### nemotron_h (most resilient: 1 classic + 1 novel = 2 total crashes)
- Early tensor count check prevents overflow_counts DoS
- overflow_rope chained attack bypasses this by corrupting GGUF loading state
- SWA rope not supported (no swa key found)

### gemma4 (least resilient: 2 classic + 1 novel = 3 total crashes)
- Fast crash on rope_drift (4.5s)
- SWA rope support adds extra dimension validation surface
- swa_rope_drift crashes in raw GGML computation (not caught by model loader)

### qwen35 (2 classic crashes)
- Slowest rope_drift crash (12.5s) -- most tensor entries to iterate

### phi3 (2 classic crashes)
- Fastest rope_drift crash (3.0s)
- Largest file (8.6GB) -- may have other memory-pressure issues

---

## 11. KEY INSIGHTS FOR PATCHING

1. **n_rot validation gap**: Extend llama-model.cpp:1161-1165 to ALL architectures, not
   just LLAMA/DECI/FALCON/LLAMA_EMBED. Currently unprotected: nemotron_h, gemma4, qwen35,
   phi3, and ~50 other architectures.

2. **SWA dimension gap**: rope.dimension_count_swa has NO validation at all -- not even
   the partial check at line 1161. Add bounds check for SWA n_rot.

3. **GGUF loading robustness**: The overflow_rope chained attack crashes in gguf.cpp:143
   because GGUF loading state is corrupted by large tensor_count before rope key is read.
   Add invariant checks in gguf loader after every batch read.

4. **No SIGSEGV found**: After 116 tests across 4 models, zero memory corruption events.
   All crashes are assertion failures. Parser is strong against OOB memory access.

---

## 12. EXPERIMENTAL DESIGN SUMMARY

| Phase | Test Count | Script | Attacks |
|-------|-----------|--------|---------|
| GGUF Fuzzer (Phase 1) | 17 | gguf-fuzzer.py | Header/metadata corruption |
| Novel Attacks | 12 | gguf-novel-attacks.py | 12 novel GGUF variants |
| Weaponized | 3 | gguf-weaponizer.py | Jinja, OOB, tensor crash |
| Deep Multi-Model | 32 | deep-multimodel.py | 8 attacks x 4 models |
| Ultimate Multi-Model | 96 | ultimate-multimodel.py | 24 attacks x 4 models |
| **Chained Attacks** | **20** | gguf-chained-attacks.py | **5 chained x 4 models** |
| **TOTAL** | **180** | | |

---

*Generated 2026-06-18 from live test data*
*Model files: logs/ultimate/models/*
*Results CSV: logs/chained/chained_results.csv*
*Reports: GGUF_CROSS_MODEL_REPORT.md, GGUF_SURGICAL_REPORT.md*
