# GPU VRAM Forensics Report

**Date:** 2026-06-20
**Environment:** WSL2 (kernel 6.6.87.2-microsoft-standard-WSL2)
**GPU:** NVIDIA T1200 Laptop GPU (4 GB GDDR6)
**Driver:** 581.95, CUDA 13.0

## 1. Tools Survey

| Tool | Status | Notes |
|------|--------|-------|
| `nvidia-smi` | ✅ Installed | WSL2 paravirtualized (`/usr/lib/wsl/lib/nvidia-smi`) |
| `nvtop` | ❌ Not installed | Available via `apt install nvtop` |
| `cuda-gdb` | ❌ Not installed | Available via `apt install nvidia-cuda-gdb` |
| `nvidia-cuda-mps-control` | ❌ Not installed | Not in apt |
| `nvcc` (CUDA compiler) | ❌ Not installed | No `/usr/local/cuda*` directory |
| `pynvml` | ❌ Not installed | pip install blocked by PEP 668 |
| `pycuda` / `cupy` | ❌ Not installed | Not available |
| `libcudadebugger.so.1` | ✅ Present (10 MB) | At `/usr/lib/wsl/lib/`, but no `cuda-gdb` binary |
| `cuCoredump*` API symbols | ✅ In libcuda.so.1 | `cuCoredumpGetAttribute`, `cuCoredumpSetAttribute` exported — but no tool to invoke them |

**Installed CUDA packages:** `nvidia-cuda-cupti-cu12` (12.8.90), `nvidia-cuda-nvrtc-cu12` (12.8.93), `nvidia-cuda-runtime-cu12` (12.8.90) — runtime libraries only, no development tools, debugger, or profiler.

## 2. GPU Memory Measurements

### Baseline (idle, no model loaded)

| Metric | Value |
|--------|-------|
| Total VRAM | 4096 MiB |
| Reserved | 158 MiB |
| Used (idle) | 55 MiB |
| Free | 3884 MiB |
| GPU Util | 0% |
| Temperature | 68°C |

### During phi-4 Inference Attempt (LM Studio)

| Metric | Value |
|--------|-------|
| Baseline used | 109 MiB |
| Peak used during load | 3087 MiB (75% of total) |
| GPU util peak | 87% |
| Memory util peak | 85% |
| Post-timeout persistence | 3085 MiB (>5 min) |

Memory allocation timeline (lm_sdk.csv):
```
Time    Used (MiB)  GPU Util  Notes
T+0s    109         0%        Pre-inference
T+1s    2433        58%       Model loading to VRAM  
T+2s    3077        62%       phi-4 model (~3 GB) loaded
T+3s    3085        87%       Inference active (model reasoning)
T+60s   3085-3196   0-50%     After timeout, model stays in VRAM
```

### During deepseek-r1 Inference (Ollama, successful)

| Metric | Value |
|--------|-------|
| Baseline used | 55 MiB |
| Peak used during load | 2379 MiB |
| GPU util during inference | 75% peak |
| Duration | 59s |
| Eval count | 200 tokens |
| Post-inference used | 3140 MiB (model remains loaded) |

## 3. GPU Memory Dump Capability

**No direct GPU VRAM dump possible on this system.**

| Method | Result | Reason |
|--------|--------|--------|
| `/proc/driver/nvidia/gpus/*/memory` | ❌ Missing | Not available in WSL2 |
| `/sys/class/drm/card*/device/mem_info_vram_total` | ❌ Missing | No DRM device in WSL2 |
| `/dev/nvidia*` | ❌ Missing | WSL2 GPU abstraction layer |
| `/dev/dri/` | ❌ Missing | No DRI device |
| `cuda-gdb attach` | ❌ Not installed | `libcudadebugger.so.1` exists but no `cuda-gdb` binary |
| `nvidia-smi --gpu-reset` | ❌ Option missing | WSL2 version doesn't support GPU reset |
| CUDA cuCoredump* APIs | ⚠️ Symbols present | In libcuda.so.1, but no tooling to invoke |
| Process memory dump (CPU) | ✅ Possible | `cat /proc/<pid>/maps` + `gdb dump memory` works for CPU-side allocations |

**Root cause:** WSL2 GPU is paravirtualized through `/usr/lib/wsl/lib/libcuda.so.1`. All GPU memory is managed by the Windows host NVIDIA driver. Linux side only sees memory statistics via `nvidia-smi`, never raw VRAM contents. Actual VRAM lives in Windows GPU driver address space, inaccessible from WSL2.

## 4. Key Findings

1. **WSL2 GPU virtualization is the blocker.** No `/dev/nvidia*`, no `/proc/driver/nvidia`, no `/sys/class/drm`. GPU memory lives on Windows host — invisible from Linux.

2. **Models persist in VRAM after failed inference.** phi-4 loaded ~3 GB into VRAM and remained for >5 min after API timeout. Memory not freed until process termination.

3. **LM Studio API unreliable under load.** Workers enter uninterruptible sleep (Dl state) after inference failures. API port shows LISTEN but connections timeout. Killed workers restart automatically but get stuck again.

4. **libcudadebugger present but unusable.** 10 MB library at `/usr/lib/wsl/lib/` contains GPU coredump APIs (`cuCoredumpGetAttribute`, `cuCoredumpSetAttribute`), but no `cuda-gdb` binary exists to exercise them.

5. **Ollama inference works.** deepseek-r1 (8.2B, Q4_K_M) runs on GPU via ollama. Memory climbs from 55 MiB to 2379 MiB during load, settles at 3140 MiB after inference. Canary not echoed in response.

## 5. Recommended Toolchain for GPU VRAM Forensics

Run from **bare-metal Linux** (not WSL2):

### Essential tools
| Tool | Purpose | Install |
|------|---------|---------|
| `nvidia-smi` | Memory + utilization stats | Built-in with NVIDIA driver |
| `nvtop` | Real-time GPU process monitor | `apt install nvtop` |
| `cuda-gdb` | Attach to GPU process, dump memory | `apt install nvidia-cuda-gdb` |
| CUDA Toolkit (full) | cuCoredump* API access, nvcc, samples | `apt install nvidia-cuda-toolkit` |
| `pynvml` | Programmatic NVML access | `pip install pynvml` |

### Recommended experiment (bare-metal Linux)

1. Install full CUDA toolkit + `cuda-gdb` + `nvtop`
2. Measure baseline: `nvidia-smi -q -d MEMORY`
3. Run inference with known canary token (e.g., `GPU_CANARY_$(date +%s)`)
4. **VRAM snapshot during inference:**
   - `cuda-gdb attach <pid>`
   - `set cuda memcheck on`
   - `info cuda device 0 memory` — list all GPU allocations
   - For each allocation: `cuda device 0 memory <addr> <size>` → dump to file
   - `find /d '<canary>' <start> <end>` — search each GPU buffer for canary bytes
5. **VRAM after inference** (same process, model idle, post-generation)
   - Re-scan all GPU allocations for canary bytes
   - Check KV cache retention after response completion
6. **VRAM after unload** (unload model → check for residual)
7. Compare snapshots across requests

### Alternative: `/dev/nvidia*` direct dump
- `nvidia-smi -r` (GPU reset) then `dd if=/dev/nvidia0 of=/tmp/vram.bin bs=1M count=$(nvidia-smi --query-gpu=memory.total --format=csv)`
- Requires bare metal with `/dev/nvidia0` exposed and `nvidia-peermem` kernel module
- Captures full VRAM contents including GPU driver caches

### WSL2 workaround
- Use Windows-side tools on the host: Windows `nvidia-smi`, `nsight`, Windows `cuda-gdb`
- WSL2 GPU process (llmster, ollama runner) → Windows NVIDIA driver allocates memory
- Windows `nvidia-smi` shows memory; VRAM dump requires Windows forensic tools
- `NvFBC`/`NvIFROGL` capture possible on Windows host with Tesla/Quadro GPUs

## 6. Conclusion

GPU VRAM dumping not feasible from WSL2. WSL2 GPU paravirtualization prevents direct memory access from Linux. Models do load into VRAM (phi-4: ~3 GB, deepseek-r1: ~2.3 GB) and persist after inference failures/completions, but actual VRAM contents managed by Windows host driver.

Definitive answer requires bare-metal Linux with full CUDA toolkit + cuda-gdb. CPU RAM finding from DEEP_LEAK_REPORT.md (11-42 canary copies in server RAM, persisting across requests) is independently reproducible. VRAM investigation remains future work on non-WSL2 system.
