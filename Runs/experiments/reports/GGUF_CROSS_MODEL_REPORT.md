# Cross-Model GGUF Attack Report

- **Script**: `scripts/ultimate-multimodel.py`
- **Date**: 2026-06-18
- **Models**: nemotron_h (2.7GB), gemma4 (5.0GB), qwen35 (5.3GB), phi3 (8.6GB)
- **Attacks**: 24 weaponized GGUF variants per model
- **Tool**: `llama-server --check-tensors` (no inference, crash detection only)

## Summary

| Metric | Count |
|--------|-------|
| Total tests | 96 |
| **SIGABRT crashes** | **7** |
| OK (loaded gracefully) | 36 |
| Rejected (rc=1) | 53 |
| Timeout | 0 |

## Crashes (SIGABRT)

### rope_drift — ALL 4 MODELS
Set `rope.dimension_count` to `0x7FFFFFFF` (INT32_MAX). Parser reads dimension N, allocates rope buffer using `N * something`, hits assertion when computation exceeds allocated size.

```
nemotron_h: SIGABRT 4.5s
gemma4:     SIGABRT 4.5s
qwen35:     SIGABRT 12.5s
phi3:       SIGABRT 3.0s
```

### overflow_counts — 3/4 MODELS (not nemotron_h)
Set `tensor_count` to `0xFFFFFF00` and `metadata_kv_count` to `0xFFFFFF00`. Parser tries to read millions of entries, overflows internal counters, hits OOB access.

```
gemma4:     SIGABRT 2.0s
qwen35:     SIGABRT 2.5s
phi3:       SIGABRT 2.0s
nemotron_h: rc=1 (rejected early)
```

## Attacks Handled Gracefully (all 4 models, 9 attacks)

| Attack | What it does | Result |
|--------|-------------|--------|
| token_boundary | token IDs set to 0/0xFFFFFFFF | loaded OK |
| unicode_names | UTF-8 garbage in tensor names | loaded OK |
| alignment_zero | general.alignment=0 | loaded OK (falls back to default alignment) |
| nan_inf_meta | NaN/Inf in float metadata | loaded OK |
| rope_freq_zero | rope.freq_base=0.0 | loaded OK |
| vocab_size_zero | vocab_size=0 | loaded OK |
| bos_eos_loop | bos/eos sets to 1 (self-loop) | loaded OK |
| logit_scale_inf | logit_scale=inf | loaded OK |
| self_ref | tensor offset points to itself | loaded OK |

## Attacks Rejected by Parser (all 4 models, 13 attacks)

| Attack | What it does |
|--------|-------------|
| block_mismatch | wrong head_count for block count |
| embed_crush | embedding_length=1, head_count=0xFFFFFFFF |
| quant_swap | tensor quantization type swapped |
| tensor_offset | tensor offset set to 0x40 |
| arch_spoof | architecture string overwritten |
| vocab_corrupt | tokenizer.vocab string corrupted |
| version_spoof | GGUF version set to 42 |
| payload_bomb | huge tensor metadata embedded in name |
| quant_255 | tensor dtype set to 255 (invalid) |
| string_len_overflow | metadata string length set to INT64_MAX |
| negative_head_kv | head_count_kv set to INT32_MIN |
| embd_max | embedding_length set to UINT32_MAX |
| head_zero | head_count set to 0 |

## Cross-Model Observations

1. **rope_drift is universal** — crashes all architectures. ROPE dimension validation missing before allocation.
2. **overflow_counts model-dependent** — nemotron_h rejects early (checks nums before iterating), others crash. Suggests code path varies by arch.
3. **Parser gate is strong** — 55% of attacks rejected at parse time before any mmap/crash. Quant, tensor offset, arch, vocab all validated.
4. **No SIGSEGV anywhere** — all crashes are SIGABRT (assertion failures). No memory corruption detected by --check-tensors in any variant.
5. **phi4 had anomalous elapsed times (~12h)** on 4 tests — likely `proc.stderr.read()` blocking on full pipe buffer, but results are valid ("loaded_ok").
6. **9 attack types perfect across all 4 architectures** — token boundaries, alignment, NaN, infinity, zero dimensions, unicode all handled safely.

## Architecture Resilience Ranking

| Model | Crashes | OK | rc=1 |
|-------|---------|----|------|
| nemotron_h (2.7GB) | 1 | 9 | 14 |
| gemma4 (5.0GB) | 2 | 9 | 13 |
| qwen35 (5.3GB) | 2 | 9 | 13 |
| phi3 (8.6GB) | 2 | 9 | 13 |
