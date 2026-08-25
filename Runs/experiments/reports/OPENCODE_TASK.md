# Task: GGUF tensor-field attack pass (hunt SIGSEGV, not more assertions)

Working dir: /home/sharks/research

## Context
Prior work (GGUF_SURGICAL_REPORT.md) ran 180 tests, found 9 crashes — ALL are
SIGABRT (GGML_ASSERT assertion failures). Zero memory corruption (SIGSEGV) found.
Those tests attacked hparams (rope.dimension_count, counts). The UNEXPLORED frontier
is tensor-info structures and the unvalidated SWA rope path.

Two confirmed gaps in llama-monitor/build/llama.cpp-src/src/llama-model.cpp:
- line 1161: n_rot validation only for LLAMA/DECI/FALCON/LLAMA_EMBED.
- line 1180: `rope.dimension_count_swa` read into n_rot_swa with NO validation at all.

## Goal
Find a TRUE memory-safety crash (SIGSEGV) — not an assertion — or prove the parser
holds. Assertion crashes (SIGABRT) are already documented; only NEW signal types matter.

## Do this
1. Create scripts/gguf-tensor-attacks.py. REUSE the mmap patch + server-check
   primitives from scripts/gguf-chained-attacks.py (functions pref/meta/mpatch/get_arch/check).
   Do not rewrite them from scratch — import or copy verbatim.
2. Attack tensor-info fields (these feed raw pointer/offset math → SIGSEGV candidates),
   not just hparams. At minimum:
   - tensor n_dims set huge / to 0
   - a tensor dimension size to 0x7FFFFFFFFFFFFFFF and to 0
   - ggml_type field to an out-of-range enum value (type confusion)
   - tensor data offset to just-past-EOF and to a huge value
   - rope.dimension_count_swa set to 0x7FFFFFFF on the gemma4 model (the only SWA model)
   To locate the first tensor-info block, parse the GGUF header properly (magic, version,
   tensor_count, metadata_kv_count, then skip the metadata KV section) rather than byte-scanning.
3. Run each attack against all 4 models in logs/ultimate/models/ (gemma4, nemotron, phi4, qwen35).
   ALWAYS operate on a COPY of the model file (shutil.copy to /tmp or logs/tensor/), never
   the originals — patches are destructive.
4. Write results to logs/tensor/tensor_results.csv with columns:
   attack, model, arch, signal, crashed, elapsed, error. Classify signal precisely
   (SIGSEGV vs SIGABRT vs exit(rc) vs OK).
5. Write GGUF_TENSOR_REPORT.md: one table of all results, and a short section listing
   any SIGSEGV found with exact field + value + crash backtrace line. If zero SIGSEGV,
   say so plainly — that is a real finding (parser is memory-safe under these inputs).

## Constraints
- Server binary: llama-monitor/build/llama.cpp/bin/llama-server, flags: --check-tensors -m <copy> --port <p> --host 127.0.0.1
- 30s timeout per test, kill if still running (= loaded OK, no crash).
- Disk: models are 3-9GB each. Copy ONE model at a time, delete the copy after its
  attacks finish, before copying the next. Do not hold 4 copies at once.
- Do NOT modify the originals in logs/ultimate/models/. Do NOT rebuild llama.cpp.
- Keep the script under ~150 lines. No new pip deps (stdlib struct/mmap/subprocess only).
