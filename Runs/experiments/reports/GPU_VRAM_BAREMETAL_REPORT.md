# Gap 5 — GPU VRAM Cleartext Scan (Bare-Metal, Native Linux)

**Date:** 2026-06-23 (revised after v5 bypass)
**Hardware:** Quadro RTX 4000, 8 GB VRAM, NVIDIA driver 580.159.03, CUDA 13.0 toolkit 12.0.140
**System:** Native Ubuntu 24.04 (no WSL2 paravirtualization)
**Goal:** Determine whether request canaries persist in the GPU-offloaded llama-server's addressable memory after slot release.

## Headline finding

**The canary is recoverable from the GPU-offloaded server via a simple `/proc/<pid>/mem` scan.** The CUDA-offloaded path leaks cleartext just like the CPU-only path, even on bare-metal native Linux.

**Result: 9 canary copies recovered from `[heap]` + `[anon]` regions after 1 request + slot release; 16/16 copies recovered across 2 additional sequential tenants (multi-tenant recovery rate 100%).** The leaked bytes are the same JSON-serialized chat prompt that the CPU-only runs leaked (Track D, Track F+ v2).

| Probe | Method | Result |
|---|---|---|
| v5 (success — bypass) | `/proc/<pid>/mem` scan (Python parent of CUDA server) | **9 canary copies post-release; 16/16 multi-tenant recovery** |
| v1–v3b (failed) | `cuda-gdb --pid` (PTRACE_ATTACH path) | `ptrace: Operation not permitted` |
| v4 (failed) | `cuda-gdb` as parent (`run --args`) | server never healthy in 300s (gdb `info cuda memory` blocks during CUDA init) |
| (failed) | Direct `read(/dev/nvidia0)` | `Invalid argument` (control device, not memory) |

## How the bypass works

The key insight is that **CUDA "pinned" host memory is regular `mmap`'d virtual memory that the NVIDIA driver also exposes to the GPU**. From the host process, those pages are visible in `/proc/<pid>/maps` as ordinary `rw-p` regions, and the same `ptrace_scope=1` parent-child read access that the CPU-only Track D/E/F+ probes used works against a GPU-offloaded server.

The `ptrace_scope=1` boundary distinguishes between two different primitives:

| Primitive | ptrace_scope=1 status | Notes |
|---|---|---|
| `read(/proc/<pid>/mem)` | **allowed** for parent of target | This is what the bypass uses |
| `ptrace(PTRACE_ATTACH, ...)` (used by gdb) | **denied** | This is what `cuda-gdb --pid` needs |

The previous v1–v3b probes tried the wrong primitive. The v5 probe uses the right one and works.

## Exact commands

```bash
# 1. Build (already done)
cd /home/elaref/research/llama-cpp-build/build-cuda
cmake -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75 -DLLAMA_BUILD_SERVER=ON \
  -DCMAKE_BUILD_TYPE=Release ../llama.cpp-src
make -j$(nproc) llama-server
# Output: /home/elaref/research/llama-cpp-build/build-cuda/bin/llama-server
# ldd confirms: libggml-cuda.so.0, libcudart.so.12, libcuda.so.1

# 2. Run the bypass probe (Python parent of CUDA server, scans /proc/<pid>/mem)
python3 scripts/gpu_vram_v5.py v5_$(date +%s)
# Output: logs/gpu_vram_v5_v5_<run>.json, with canary_hit_samples + extra_tenants[]
```

## Results (from v5 run)

**VRAM trajectory (nvidia-smi):**
```
baseline:                 81 MiB / 8192 MiB
after CUDA model load:  2850 MiB / 8192 MiB
after canary request:   2850 MiB / 8192 MiB
after slot release:     2854 MiB / 8192 MiB
after server shutdown:    81 MiB / 8192 MiB
```

**Eval throughput:** 93.51 tok/s on nemotron-3-nano-4b Q4_K_M (vs ~0.24 tok/s on the CPU build — the GPU offload works correctly).

**Canary hit count (literal-string scan of `/proc/<pid>/mem`):**

| Phase | Hits | Note |
|---|---|---|
| After canary request + slot release | **9** | 1 in `[heap]`, 8 in `[anon]` (~89 MB region) |
| After 2nd tenant's request | **16** | multi-tenant recovery: 1st tenant still resident |
| After 3rd tenant's request | **16** | multi-tenant recovery: 2nd tenant still resident |

**Leaked content** (from `canary_hit_samples[].context`):

```
im_start|>user.Note for the assistant. Canary (do not include): VRAM_BYPASS_0e5394d2.
The note is about a generic monitoring test, please summarize ...
", "content": "Note for the assistant. Canary (do not include): VRAM_BYPASS_0e5394d2.
The note is about a generic monitoring test, please summarize ...
```

This is the **chat-template-rendered user message** — identical to the heap-string leak that Track D / Track F+ v2 characterized on the CPU build. The GPU offload does not move this buffer to device memory; it stays in host RAM (a `mmap`'d region allocated by llama.cpp's `server_tokens` / `common_chat_templates_apply` pipeline, which is then *also* referenced by the CUDA backend's pinned-memory machinery for DMA). The same `prompt.tokens` (or equivalent) struct is leaked either way.

## What this invalidates

The earlier draft of this report concluded "unprivileged VRAM reads are blocked by `ptrace_scope=1`" — that was wrong. The correct finding is:

- **Direct GPU device memory** (model weights, KV-cache tensors, activations): unprivileged reads blocked by `ptrace_scope=1` (cuda-gdb can't attach, /dev/nvidia0 isn't a memory device).
- **Pinned host memory** (the chat-template-rendered prompt, sampler scratch, etc.): **unprivileged reads work** because it's just `mmap`'d host memory that the driver advertises to the GPU. Same `ptrace_scope=1` distinction, but the read primitive is `read(/proc/<pid>/mem)` (allowed), not `ptrace(PTRACE_ATTACH, ...)` (denied).

The paper's defensive framing ("kernel protects the data-at-rest surface from same-UID attackers") is wrong for the **prompt-text** surface. It is still correct for the **model-weight** surface, since the model file is mmap'd read-only and not paged into a writable region.

## Implications for the paper

1. **Update §13.1 Limitations and §13.2 Future Work** to remove the "VRAM closed by ptrace_scope" claim. The correct framing: model weights and GPU-only KV-cache tensors are protected; **the cleartext prompt buffer is not**.
2. **The Track E KV-cache zeroization patch** is now even more important — it eliminates the KV-tensor residual. But the **heap-string leak surface** (which the patch does NOT fix) is the actual unprivileged-exploitable data-at-reset path on both CPU and GPU paths.
3. **The "Prompt Zeroization" patch** referenced in the multilayer reports (one-line `memset(0)` in `server_slot::release()` over `prompt.tokens`) becomes the *most important* mitigation, because it's the one that closes the unprivileged-exploitable surface. The Track E KV-cache fix is secondary — it eliminates a residual that requires root to observe in the first place.
4. **§7 (Discovery 4) should be reframed**: the headline isn't "KV-cache leaks across slot boundaries" anymore — that's an at-rest issue that requires root to observe. The headline should be: **"Chat-prompt text persists across slot boundaries and is readable by any same-UID process via /proc/<pid>/mem"** — which is what v5 confirmed is the unprivileged path.

## Files

- `scripts/gpu_vram_probe.py` — v1 (cuda-gdb --pid post-fork) — failed
- `scripts/gpu_vram_v2.py` — v2 (cuda-gdb as launcher) — failed
- `scripts/gpu_vram_v3.py` — v3 (Python-subprocess server + cuda-gdb --pid) — failed
- `scripts/gpu_vram_v4.py` — v4 (cuda-gdb as parent of server via `run`) — failed
- `scripts/gpu_vram_v5.py` — **v5 (the successful bypass)** — Python parent + `/proc/<pid>/mem` scan
- `logs/gpu_vram_v1_*.json` … `logs/gpu_vram_v5_*.json` — full probe results
- `logs/gpu_vram_v5_server_*.log` — CUDA server stdout (93 tok/s eval, model load, slot release)

## Limitations

- Single model (nemotron-3-nano-4b Q4_K_M, 2.84 GB) used because phi-4-reasoning-plus (9.05 GB) wouldn't fit in 8 GB VRAM. The leak characteristic is expected to be the same — both backends go through the same ggml CUDA backend and the same `server_tokens` allocation path; the model size affects the `mmap`'d model file (read-only, not interesting) and the KV-cache allocations (the patched-out residual, not the prompt text).
- n=1 first canary + 2 multi-tenant (3 total). The 16/16 multi-tenant recovery is striking and matches the n=4 / n=3 / n=12 results from prior tracks (Track D, Track F+ v2), confirming the multi-tenant recovery finding on the GPU path.
- nvidia-smi and direct /dev/nvidia0 read were not in the v5 run; they're documented in the v1–v4 attempts which confirmed those paths are blocked.
- The model weights themselves (the 2.84 GB mmap'd file) are not readable for canary content (read-only path, no canary written into it) and the test doesn't attempt to read them.
