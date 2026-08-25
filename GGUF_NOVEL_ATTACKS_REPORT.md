# GGUF Novel Attack Vectors - Exploration Report

**Date:** 2026-06-18  
**Base Model:** NVIDIA Nemotron 3 Nano 4B (Q4_K_M, 2.7GB)  
**Total Variants Tested:** 12  
**Crashes (SIGABRT):** 1 (RoPE drift)  
**Clean Loads:** 1 (Token boundary)  
**Parser Rejections:** 10  

---

## Summary Table

| # | Variant | Technique | Result | Signal | Notes |
|---|---------|-----------|--------|--------|-------|
| 1 | `quant_mismatch` | Header claims Q4_0, data is Q8_0 | Rejected | exit(1) | Parser validates quant type consistency |
| 2 | `template_injection` | Append payload to tokenizer.ggml.model | Rejected | exit(1) | Metadata value injection doesn't affect template |
| 3 | `unicode_names` | Overlong UTF-8, null bytes in tensor names | Rejected | exit(1) | Tensor name validation catches malformed names |
| 4 | `rope_drift` | rope.dim=0x7FFFFFFF, context=0xFFFFFFFF | **SIGABRT** | -6 | **ASSERTION FAILURE** in rope scaling computation |
| 5 | `array_bomb` | 1000-deep nested arrays | Rejected | exit(1) | Python gguf-py handles it; C++ parser rejects |
| 6 | `token_boundary` | BOS=0xFFFFFFFF, EOS=0xFFFFFFFE | **OK** | exit(0) | Graceful fallback to default token IDs |
| 7 | `tensor_offset` | Corrupt tensor data offsets +1GB | Rejected | exit(1) | Offset validation catches mismatch |
| 8 | `arch_mismatch` | Change arch from nemotron_h to llama | Rejected | exit(1) | Architecture-specific validation rejects |
| 9 | `layer_mismatch` | block_count=1 but 42 blocks of tensors | Rejected | exit(1) | Block count vs tensor count mismatch |
| 10 | `dim_mismatch` | embedding_length=1, head_count=0xFFFFFFFF | Rejected | exit(1) | Dimension validation catches extreme values |
| 11 | `vocab_corrupt` | Token lengths set to 0x7FFFFFFFFFFFFFFF | Rejected | exit(1) | Token count validation catches overflow |
| 12 | `version_downgrade` | GGUF version 3->1 | Rejected | exit(1) | Version check rejects downgrade |

---

## Detailed Findings

### CRITICAL: RoPE Drift -> SIGABRT

**Attack:** Modified three metadata fields:
- `nemotron_h.rope.dimension_count`: 78 -> 0x7FFFFFFF
- `nemotron_h.context_length`: original -> 0xFFFFFFFF
- `nemotron_h.vocab_size`: original -> 0x7FFFFFFF

**Result:** `SIGABRT` (signal -6) - server crashed during initialization.

**Analysis:** The extreme `rope.dimension_count` value (0x7FFFFFFF = 2.1 billion) likely caused an integer overflow in the RoPE frequency computation. The GGML_ASSERT at `llama-model.cpp:1131` fires when `rope_scaling_type_train` is unspecified, but the actual crash is likely in the context allocation or rope embedding computation when trying to allocate 2.1 billion dimension frequencies.

**Security Implication:** This is a **denial-of-service** vector. A crafted GGUF with extreme RoPE parameters can crash the server without any memory corruption. The crash is clean (SIGABRT, not SIGSEGV), indicating an assertion failure rather than buffer overflow.

**Reproduction:** `novel_rope_drift.gguf` with modified rope.dimension_count, context_length, vocab_size.

---

### Token Boundary: Graceful Degradation

**Attack:** Set special token IDs to extreme values:
- BOS: 1 -> 0xFFFFFFFF (4294967295)
- EOS: 11 -> 0xFFFFFFFE (4294967294)
- Padding: 0 -> 0x80000000 (2147483648)
- Unknown: 0 -> 0x7FFFFFFF (2147483647)

**Result:** Server loaded and ran successfully.

**Log Output:**
```
W load: bad special token: 'tokenizer.ggml.bos_token_id' = 4294967295, using default id 11
W load: bad special token: 'tokenizer.ggml.eos_token_id' = 4294967294, using default id 11
W load: bad special token: 'tokenizer.ggml.unknown_token_id' = 2147483647, using default id -1
W load: bad special token: 'tokenizer.ggml.padding_token_id' = 2147483648, using default id -1
```

**Analysis:** llama.cpp validates special token IDs against the tokenizer vocabulary size. When IDs exceed the vocab range, it falls back to safe defaults. This is **good defensive programming** - the parser doesn't crash, it degrades gracefully.

**Generated output:** ", I'm a student in the 10th grade. I'm trying to understand how to solve a problem about a triangle with sides 13," - normal inference despite corrupted token IDs.

---

### Parser Rejections (10 variants)

All 10 rejected variants exited with code 1 (clean error, no crash). Key observations:

1. **Architecture mismatch** (`nemotron_h` -> `llama`): The model loader validates architecture against available tensor patterns. Nemotron tensors (ssm_a, ssm_conv1d, etc.) don't match llama architecture.

2. **Dimension mismatches**: embedding_length=1, head_count=0xFFFFFFFF, block_count=1 all fail validation against actual tensor dimensions.

3. **Quantization mismatch**: Parser validates that tensor data size matches expected size for claimed quantization type.

4. **Tensor offsets**: Corrupted offsets (+1GB) are caught during tensor data loading.

5. **Unicode names**: Overlong UTF-8 and null bytes in tensor names are rejected.

6. **Array bomb**: 1000-deep nested arrays rejected (likely stack depth limit in C++ parser).

7. **Version downgrade**: GGUF version 1 rejected for this model format.

8. **Vocab corruption**: Token count/length validation catches overflow.

---

## Novel Attack Categories

### Category A: Metadata Manipulation (8 variants)
- RoPE parameters, architecture, dimensions, token IDs, version
- **Success rate:** 1/8 (12.5%) - RoPE drift caused SIGABRT

### Category B: Structural Corruption (3 variants)
- Tensor offsets, quantization types, array nesting
- **Success rate:** 0/3 (0%) - all rejected

### Category C: Encoding Attacks (1 variant)
- Unicode edge cases in tensor names
- **Success rate:** 0/1 (0%) - rejected

---

## Recommendations

### For llama.cpp Developers
1. **Add bounds checking for RoPE dimension_count** - cap at reasonable maximum (e.g., 8192)
2. **Validate context_length against available memory** before allocation
3. **Add fuzzing harness for metadata-only mutations** (no tensor data changes)

### For Security Researchers
1. **Test older llama.cpp versions** - RoPE validation may be weaker
2. **Chain RoPE drift with prompt injection** - extreme dimensions + adversarial prompts
3. **Test custom inference servers** - many use their own GGUF parsers
4. **Explore tokenizer edge cases** - BPE merge operations with corrupted data

### For Model Deployers
1. **Validate GGUF files before loading** - check metadata ranges
2. **Run llama-server with `--check-tensors`** in production
3. **Monitor for SIGABRT** - indicates assertion failures from malformed inputs

---

## Files Generated

| File | Description |
|------|-------------|
| `logs/gguf_novel/novel_*.gguf` | 12 weaponized variants |
| `logs/novel_attacks_test_results.csv` | Test results (13 rows) |
| `scripts/gguf-novel-attacks.py` | Variant generator |
| `scripts/test-novel-attacks.py` | Test harness |
