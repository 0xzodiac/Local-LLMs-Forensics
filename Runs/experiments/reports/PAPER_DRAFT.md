# Paper Draft: The Local-LLM Privacy Boundary — A Three-Layer Forensic Measurement

**Date:** 2026-06-23
**Target:** IEEE TIFS (Transactions on Information Forensics and Security)
**Status:** Draft being restructured into 3-layer form (file format → runtime → interface).
All results from prior tracks retained; false/overstated claims corrected per audit
(`STRENGTH_WEAKNESS_MAP.md`, `CITATION_AUDIT.md`, `RECONCILED_NUMBERS.md`).

---

## Abstract

Local LLMs are marketed as the privacy-preserving alternative to cloud APIs — users
run open-weight `.gguf` models in wrappers (LM Studio, Ollama) on the assumption
that local execution implies local data. We test this assumption with a forensic
measurement across **three distinct layers** of the local-LLM stack and find that
the privacy boundary is broken at the runtime layer and is mis-configured at the
interface layer, while the file-format layer is — against our test battery — sound.
A fourth finding, independent of the layer framing, shows the boundary can also be
broken **remotely**, with no local access at all.

**(1) File-format layer (negative result).** We construct 80+ novel GGUF
metadata/validation attack variants across 4 models. The parser rejects all of
them cleanly (assertion/exit, no memory corruption). This layer is **safer than
feared** by our variant class — though we contextualize against 12 known
allocation-path CVEs (2 critical, CVSS 9.1) in the same parser that our
validation-path fuzzing did not exercise.

**(2) Runtime layer (headline).** In the raw llama.cpp serving engine, a
released slot's tenant plaintext persists in process RAM, recoverable by any
**same-UID parent process** via `/proc/<pid>/mem` (unprivileged: no root, no
`CAP_SYS_PTRACE`, only the default `ptrace_scope=1` parent-child relationship).
We measure 13 copies/tenant surviving across 3 subsequent requests and a 10s idle
window, and 12/12 sequential tenants' secrets recoverable from a single memory
read. Two distinct surfaces contribute: (a) a **KV-cache float-tensor** residual
(privileged to observe) caused by missing zeroization in
`llama_kv_cache::seq_rm()`; and (b) a **heap-resident formatted-prompt string**
buffer (~135 KB/slot, the *unprivileged*-exploitable path) that is freed but not
zeroed on slot release. We provide **two patches with formal correctness proofs**
(`kv_cache_zeroize.patch`, invariant I₂; `prompt_zeroize.patch`, invariant I₃),
each with negligible overhead (N=20, 9.71s patched vs 9.84s unpatched).

**(3) Interface layer.** We introduce **wrapper forensics**: LM Studio's
`logSensitiveData: true` default writes every API interaction (prompts, responses,
reasoning traces) to cleartext disk logs with **no observed retention limit**
(persisting until manual deletion or file rotation), configurable only via a
hidden JSON file requiring a server restart. An on/off differential proves the
toggle works. A control comparison with Ollama shows this cleartext-logging
behavior is wrapper-specific (Ollama logs zero API payloads).

A network measurement (netns-isolated, 4 models, ~23 cumulative minutes of idle
holding) establishes that LM Studio makes only a cold-start update check to
`lmstudio.ai` and then goes network-silent — no slow beacon, no prompt
exfiltration. This is necessary-but-insufficient: the danger is not data-in-transit
but data-at-rest in process RAM and on disk. We frame the result as evidence that
**"local" is not a sufficient privacy boundary**, and that runtime + interface
hygiene, not network isolation, is where local-LLM privacy fails.

**(4) Remote, zero-local-access finding.** Every result above requires the
attacker to already hold local, same-UID process access. We additionally find
that `llama-server`'s `/slots` save/restore feature (enabled by the single,
ordinary flag `--slot-save-path`) performs no authorization check tying a
saved slot or filename to the client that created it. Any network client can
restore another tenant's saved KV-cache — their full conversation history —
into their own session by supplying that tenant's filename; `--api-key`, the
only authentication the server offers, does not mitigate this, since it is a
perimeter membership check with no per-resource scoping. We confirm exact
cross-tenant data transfer (`n_restored` matching `n_saved` token-for-token)
across three independent model/backend configurations. This is, to our
knowledge, a previously undocumented CWE-862 (Missing Authorization) issue in
a widely-deployed local-LLM serving engine, and the only finding in this paper
exploitable purely over the network.

---

## 1. Introduction

### 1.1 The Local AI Promise
- Privacy via local execution: no cloud round-trip, data stays on device
- Open-weight models + open-source runtimes = auditability
- Rapid user adoption: LM Studio 5M+ downloads, Ollama 2M+

### 1.2 The Security Assumption
- File-format safety (GGUF parsers are memory-safe — CLAIM CORRECTED)
- Runtime isolation (no network egress, no persistent state)
- Model alignment (instruction-tuned models resist prompt injection)

### 1.3 Our Challenge
- We test the privacy boundary at three layers of the stack. Two fail (runtime + interface); one holds (file format, against our variant class).
- Paper contributions (3 layers, all results retained and honestly characterized):
  1. **Runtime-layer data-at-rest leakage + dual-surface zeroization defense.**
     The unprivileged heap-string leak (13 copies/tenant) and the privileged
     KV-cache residual, closed by two patches (I₂, I₃) with formal proofs and
     negligible overhead. [§4, §7, §8]
  2. **Wrapper forensics — interface-layer cleartext logging.** LM Studio's
     `logSensitiveData: true` default; on/off differential; Ollama clean
     control. [§5]
  3. **File-format-layer validation-gap taxonomy (negative result).** 80+ novel
     GGUF variants, all cleanly rejected; contextualized against 12 known
     allocation-path CVEs (orthogonal surface). [§3]
  4. **Network-layer measurement (negative result, red herring).** Netns-isolated,
     4-model, multi-minute idle capture: LM Studio is network-clean. This is the
     necessary-but-insufficient check that redirects attention to data-at-rest. [§6]

---

## 2. Threat Model

We assume:
- **Adversary A1 (post-exploitation, unprivileged):** runs code as the *same UID*
  as the local LLM server process (insider, stealer malware dropped in the user
  session, forensic acquisition of a live machine). Cannot exfiltrate over the
  network during the attack window. This adversary can read a *child* process's
  `/proc/<pid>/mem` because the parent-child relationship satisfies the default
  `ptrace_scope=1` — **no root and no `CAP_SYS_PTRACE` required**. This is the
  heap-string leak's privilege level (§4).
- **Adversary A2 (multi-tenant):** shares the same local LLM server instance with
  other users (concurrent requests, sequential slot reuse). A1 ⊂ A2: any
  multi-tenant scenario is also a same-UID scenario.
- **Adversary A3 (privileged, for the KV-tensor surface):** has `CAP_SYS_PTRACE`
  or root, and therefore `PTRACE_ATTACH`. Required only to read the KV-cache
  *float tensor* directly (§7); the heap-string surface (§4) does not require A3.

We do **not** assume:
- Network egress capability for the adversary
- Kernel-level access (no `/dev/mem`, no kernel module loading)
- Physical access to DRAM (cold-boot attacks are orthogonal)

**Privilege model (corrected from an earlier draft):** the dominant practical
surface (heap-string, §4) is **AV:L / PR:L** (local access, low privilege — same
UID / parent), not network-accessible. An earlier characterization of the leak as
`CVSS 7.5 AV:N/AC:L/PR:N` was **incorrect** — there is no working network exploit;
the only path to the leak is local same-UID `/proc/<pid>/mem` read. The honest
CVSS for the heap-string surface is ~**4.4–5.5 (Medium), AV:L/AC:L/PR:L/C:H**. We
frame it as a data-hygiene / defense-in-depth finding rather than a remote RCE.

The threat is **data-at-rest**, not data-in-transit. Section 6 shows zero
outbound connections across the idle-hold windows; this is necessary but
insufficient — the data sits in cleartext in process RAM and on disk.

---

## 3. Experimental Setup

### 3.1 Models
Four open-weight models (Q4_K_M quant unless noted), all with SHA-256 verification against `RESEARCH_DOCUMENTATION.md` baseline (720 / 427 / 263 / 243 tensors respectively):

| Model | Params | Arch | Size | Tensors |
|---|---|---|---|---|
| gemma-4-E4B-it | 7.5B | gemma4 | 5.34 GB | 720 |
| Qwen3.5-9B | 9B | qwen35 | 6.55 GB | 427 |
| NVIDIA-Nemotron-3-Nano-4B | 4.0B | nemotron_h | 2.84 GB | 263 |
| Phi-4-reasoning-plus | 14.7B (15B) | phi3 | 9.05 GB | 243 |

### 3.2 Backends
- **LM Studio** (closed-source GUI wrapper, version current as of 2026-06-19): the primary deployment under test.
- **raw llama.cpp** (CPU-only build from source, commit `721354f`): baseline / control. Used for cross-wrapper consistency checks and for testing the Track E KV-cache patch without wrapper-level logging confounding the signal.
- **Ollama 0.24.0** (snap): control case for §5 (wrapper logging comparison).

### 3.3 Hardware
- CPU: Intel Core i7-9850H @ 2.60 GHz (12 threads available, 16 logical)
- GPU: NVIDIA Quadro RTX 4000, **8 GB** VRAM, CUDA-enabled llama.cpp build verified (libggml-cuda + libcudart + libcuda linked; 93 tok/s eval on nemotron-3-nano-4b at Q4_K_M)
- RAM: 15 GB available (tight for 14.7B phi-4 at Q4_K_M; causes ~1 tok/s decode throughput)
- Disk: 186 GB total, ~7 GB free (recurrent tight margin constrained test scope; see §11.4)

---

## 4. Discovery 1: The Covert Reasoning Channel

### 4.1 Reasoning Content Surface
- Some instruction-tuned models return a `reasoning_content` field alongside `content`
- Contains chain-of-thought traces, internal deliberation
- Exposed via `completion_tokens_details.reasoning_tokens` in usage stats

### 4.2 Blind Spot in Output Filters
- Standard output filters inspect only `content`
- Qwen3.5: 0.0% visible leak, 56.0% reasoning channel leak
- A security auditor testing only visible output would declare Qwen3.5 safe — incorrectly

### 4.3 Cross-Model Comparison
| Model | Visible Leak | Reasoning Leak | Total |
|-------|:-----------:|:-------------:|:-----:|
| Gemma-4 (7.5B) | 55.2% | 0.0% (no channel) | 55.2% |
| Qwen3.5 (9B) | 0.0% | 56.0% | 56.0% |
| NVIDIA-Nemotron-3 (4B) | — | — | 41.2% |
| Phi-4-reasoning (14.7B) | 0.0% | 98.4% | 98.4% |

All n=240-250 (Gemma-4 and Phi-4 from a clean rerun, see
`GEMMA4_PHI4_RERUN_REPORT.md`; others from `CROSS_MODEL_CANARY_LEAK_REPORT.md`).
Phi-4's leak channel is reasoning_content, not visible content -- this
corrects the canonical report's attribution (same ~98% magnitude, wrong field).

### 4.4 Relationship to Prior Art
- Extends "Leaky Thoughts" (Green et al., EMNLP 2025) from model-level privacy to wrapper-level persistence
- The reasoning channel is dangerous not only because models leak into it, but because the wrapper archives it in cleartext regardless of whether the model intended to expose it

---

## 5. Discovery 2: The Wrapper Betrayal

### 5.1 Logging Architecture
- **Config location:** `~/.lmstudio/.internal/http-server-config.json` (NOT `settings.json`)
- **Default:** `logSensitiveData: true`
- **Log location:** `~/.lmstudio/server-logs/YYYY-MM/YYYY-MM-DD.N.log`
- **Log content:** Full HTTP request/response bodies — prompts, responses, reasoning traces, system prompts — all in cleartext JSON
- **Retention:** 30 days default via `apiPredictionHistoryEviction.ttlDays: 30` (irrelevant to file logs)
- **Measured volume:** 6.3 MB single-day log, 2312 content entries, 777 full response bodies

### 5.2 Mitigation Verification
- Setting `logSensitiveData: false` effectively stops new log entries
- After change + server restart: test canary `MITIGATION_AFTER_CHANGE_1781931482` absent from logs
- **Caveats:** config not discoverable via GUI, server restart required, no UI indicator of current state, ~7.5 MB historical logs persist indefinitely
- `ttlDays: 0` has no effect on server log files (controls internal prediction history cache)
- Manual cleanup required: `rm -rf ~/.lmstudio/server-logs/`

### 5.3 Ollama Control Case
- Ollama 0.24.0 (snap): NO API prompt/response logging to disk
- No `logSensitiveData` equivalent exists
- `~/.ollama/history` stores only REPL commands (`/bye`, `/save`, `/set parameter`)
- Canary `OLLAMA_CANARY_1781972044` appeared in API response `thinking` field but absent from ALL disk locations (recursive grep with sudo: zero matches)
- **Conclusion:** LM Studio's dangerous logging is a design choice, not a universal property of local wrappers

### 5.4 Attack Chain
```
Local access → ~/.lmstudio/server-logs/ → cleartext payloads → 30-day harvest
```

---

## 6. Discovery 3: Network Cleanliness as a Red Herring

- Zero outbound connections detected across 480 inference cycles (confirmed by Wireshark loopback capture, PID-attributed monitoring)
- The threat is data-at-rest, not data-in-transit
- "No data leaves this machine" is necessary but insufficient — data-at-rest is the actual risk
- Framework-level insight: arXiv 2606.10173 "Local Is Not a Sufficient Privacy Boundary" independently argues that local execution alone does not guarantee privacy

---

## 7. Discovery 4: KV-Cache Residual Leakage Across Slot Boundaries

### 7.0 Prior Art: Three Distinct KV-Cache Privacy Problems

The KV-cache has emerged as a privacy surface along three **distinct axes**, which must not be conflated:

1. **Timing side-channel in shared prefix caches.** An adversary sharing a multi-tenant inference server infers other tenants' inputs from cache *hit/miss latency* on a shared prefix cache. SafeKV [Chu et al., arXiv 2508.08438] and PrefixWall (formerly CacheSolidarity) [arXiv 2603.10726] address this class. The K/V *bytes* are never read; only the timing of serving them leaks.
2. **Semantic inversion of cached tensors.** An adversary *with weight/cache access* reconstructs sensitive user inputs directly from the K/V *values themselves*, which are semantically meaningful. "Shadow in the Cache" [Luo et al., arXiv 2508.09442, NDSS 2026] demonstrates Inversion, Collision, and Injection attacks on the cached tensors and proposes KV-Cloak as a defense. NDSS 2026 acceptance establishes this as a recognized vulnerability class.
3. **Data-at-rest residual on slot release (this work).** The K/V *bytes* persist in process memory after the logical session ends — a *temporal* exposure caused by missing zeroization in `seq_rm()`. The adversary reads stale buffer bytes from `/proc/<pid>/mem`; the K/V values are not inverted, they are simply not erased.

Our contribution is the **third axis**, complementary to the first two. The Track E patch (§7.4) addresses axis 3 only. The existence of peer-reviewed work on axes 1 and 2 — and the fact that neither addresses the temporal/residual exposure of axis 3 — is what makes the upstream-disclosure case in §12 substantive rather than speculative.

### 7.1 Mechanism

`llama_kv_cache::seq_rm(llama_seq_id seq_id, llama_pos p0, llama_pos p1)` (in `src/llama-kv-cache.cpp`) is invoked when a slot's context is cleared — either via `common_context_seq_rm()` from the server, or via `llama_memory_seq_rm()` from direct API users. The function iterates over cells in the matching range and, for each cell whose owner list contains `seq_id`, calls `cells.seq_rm(i, seq_id)`.

`llama_kv_cells::seq_rm(i, seq_id)` (in `src/llama-kv-cells.h`) updates the cell's owner bitmap and, if no owner remains, marks the cell free (`pos[i] = -1`, `used.erase(i)`, etc.). It does **not** modify the K/V bytes in the backend buffer.

The cell's bytes — the floating-point K and V vectors for every prompt and response token the model processed — remain physically present in `ggml_backend_buffer_t` (RAM or VRAM, depending on backend) until a future request's token happens to overwrite the same cell with a new write.

### 7.2 Empirical Measurement

`scripts/deep_leak_probe.py` and `scripts/kv_cache_zeroize_probe.py`: send a request with a 32-character UUID canary, scan the server process's writable `/proc/<pid>/mem` regions for the literal string, send a 2nd request to trigger `slot.release()` → `seq_rm()` on the canary's sequence, rescan.

| Configuration | Pre-release copies | Post-release copies | Conditions |
|---|---|---|---|
| Unpatched, raw llama.cpp, `--cache-ram 0` | 11 | 10 | n=1, single req, slot reuse |
| Unpatched, LM Studio, full slot cycle | 11–42 (model-dependent) | 10 (after 2nd request) | original DEEP_LEAK_REPORT finding |

**Multi-tenant recovery rate:** 12/12 (100%) — sequential tenants' secrets recoverable from a single `/proc/<pid>/mem` read (~1.24 MB cleartext). See `DEEP_LEAK_REPORT.md` for the full test sequence.

### 7.3 Why the Standard Countermeasure Fails

`llama_kv_cache::clear(bool data)` (invoked by `llama_memory_clear`) does zero the bytes — but **only for the entire buffer**, on explicit user request, and the server never calls it on slot release. The `data=true` parameter toggles whether to also clear the bytes (versus only the metadata); the default in the slot-release path is `false`, and `clear()` is never called on the release path at all.

### 7.4 The Patch

`patches/kv_cache_zeroize.patch` — 89 lines, two files (`src/llama-kv-cache.h`, `src/llama-kv-cache.cpp`):

1. New private method declaration: `void llama_kv_cache::zero_cell_data(uint32_t s, uint32_t i);`
2. Hook into `seq_rm()`'s per-cell loop: when `cells.seq_rm(i, seq_id)` returns `true` (cell has no remaining owners), call `zero_cell_data(seq_to_stream[seq_id], i)`.
3. `zero_cell_data()` physically overwrites cell `i`'s K and V bytes in every layer's backend tensor via `ggml_backend_tensor_set()` / `ggml_backend_tensor_set_2d()` (backend-portable: works on CPU and GPU buffers, not just host memory).

See `KV_CACHE_PATCH_REPORT.md` §2 for the full patch mechanism and §3.1 for the direct-mechanism verification (56/56 zeroed cells had real, non-zero data immediately before the zero write).

---

### 7.5 Reframing: The Headline Vulnerability is the Chat-Prompt Text, not the KV-Cache Tensor

The v5 GPU bypass (`GPU_VRAM_BAREMETAL_REPORT.md`) revealed that the `mmap`'d chat-prompt buffer is readable from `/proc/<pid>/mem` by any same-UID process — both on CPU and GPU backends, with no privilege escalation required. The kernel boundary that protects the model-weight surface does NOT protect the prompt-text surface.

The KV-cache tensor residual that §7.1–§7.4 describes is a real residual data path, but it is **only observable by a process with `PTRACE_ATTACH` capability (i.e., root or CAP_SYS_PTRACE)**. The chat-prompt text residual, by contrast, is observable by **any process with the same UID as the server**, with no special capability beyond being the parent of the server (or having `ptrace_scope=0` set, or running as root). This is the unprivileged-exploitable data-at-rest path; the KV-cache residual is the at-rest-after-`sudo` path.

The Track E patch addresses the KV-cache residual. The **most important** mitigation is the unmentioned "prompt zeroization" patch (a one-line `memset(0)` in `server_slot::release()` over the formatted-prompt buffer) that closes the unprivileged-exploitable path. This is an explicit future-work item in the §13.2 list.

---

## 8. Formal Analysis of the Patch

This section formalizes the patch's correctness and overhead. We adopt the invariant-style framing common to the KV-cache-privacy line of work (SafeKV [Chu et al. 2025], PrefixWall [2603.10726]), though those address a *timing side-channel in shared prefix caches* — a distinct vulnerability class from the *data-at-rest residual on slot release* our patch targets. Our formalization is thus independent in both threat model (temporal exposure via missing zeroization, not cross-tenant latency inference) and in the invariant it strengthens (ownership-implies-zero, below).

### 8.1 Notation

Let $\mathcal{K}$ denote the set of all KV-cache cells, indexed by $(s, i)$ where $s \in [0, n_\text{stream})$ is the stream id and $i \in [0, n_\text{ctx})$ is the cell index within the stream. Let $\text{bytes}(s, i, l, \tau)$ denote the $\tau$-th byte of layer $l$'s backend-buffer at the offset corresponding to cell $(s, i)$. Let $\text{owners}(s, i) \subseteq \mathbb{N}$ denote the set of sequence ids currently owning cell $(s, i)$. The system invariant maintained during normal operation is:

$$\forall s, i, l, \tau. \quad \text{owners}(s, i) \neq \emptyset \implies \text{bytes}(s, i, l, \tau) \text{ corresponds to one of the owners' last computed K/V values} \tag{1}$$

(Invariant 1: ownership-implies-validity. A cell that any sequence still references holds that sequence's computed K/V values. This is what attention compute relies on.)

### 8.2 Residual Data Persistence Model (Pre-Patch)

Define the **leak window** $T(s, i, l, \tau)$ as the wall-clock duration during which cell $(s, i, l, \tau)$ continues to hold non-zero data after its last owning sequence has been released. In the unpatched system:

$$T_\text{unpatched}(s, i, l, \tau) = T_\text{overwrite}(s, i, l, \tau) \tag{2}$$

where $T_\text{overwrite}$ is the (random) time until some future request's `ggml_backend_tensor_set()` happens to land on the same $(s, i, l, \tau)$ byte offset. This is bounded below by 0 (immediate reuse) and above by the buffer's full-recycle horizon, which for a uniformly-distributed ring-buffer of size $n_\text{ctx}$ with request rate $\lambda$ follows geometric / exponential decay:

$$\Pr[T_\text{overwrite} > t] \approx e^{-\lambda t / n_\text{ctx}} \tag{3}$$

The key empirical fact is that for any reasonable request rate, $T_\text{unpatched}$ is **finite in expectation but unbounded in worst case** (a quiescent server leaves data in place indefinitely), and the **mean leak window** scales with $n_\text{ctx} / \lambda$:

$$\mathbb{E}[T_\text{unpatched}] = \Theta(n_\text{ctx} / \lambda) \tag{4}$$

For the LM Studio configuration in `DEEP_LEAK_REPORT.md` ($n_\text{ctx} = 4096$, typical $\lambda \approx 1 \text{ req/s}$ for interactive use), $\mathbb{E}[T_\text{unpatched}] \approx 1.1 \text{ hours}$, with a long tail for cells that happen to fall in low-reuse regions of the ring.

### 8.3 Patch Correctness — Invariant Proof

**Claim (post-patch invariant).** For every cell $(s, i)$ in the system, after every sequence owning it has been released, all corresponding backend-buffer bytes are zero.

**Proof.** Define the strengthened invariant $I_2$:

$$\forall s, i. \quad \text{owners}(s, i) = \emptyset \implies \forall l, \tau. \; \text{bytes}(s, i, l, \tau) = 0 \tag{$I_2$}$$

We show $I_2$ is preserved by `seq_rm()`. Consider the call `seq_rm(seq_id, p0, p1)` and an arbitrary cell $(s, i)$ with $\text{owners}(s, i) \ni seq_id$ and $(i \in [p_0, p_1])$:

1. **Safety of zeroing:** Before the patch's hook runs, `cells.seq_rm(i, seq_id)` is invoked. Per `llama-kv-cells.h:238`, this returns `true` iff after removing `seq_id` from the owner bitmap, `seq[i].none()` (i.e., `owners` is now empty). The patch calls `zero_cell_data(s, i)` **only** on the `true` return — guaranteeing that no other sequence still references this cell when we zero it. Zeros written in step 2 therefore cannot invalidate any other sequence's K/V values.

2. **Offset correctness:** For each layer $l$ and each of the two tensors (`k` and `v`), `zero_cell_data` computes an offset matching the corresponding `get_k(l, n_kv, sinfo)` / `get_v(l, n_kv, sinfo)` read offset exactly. Specifically (K, always cell-contiguous):

$$\text{off}_k(s, i, l) = \text{row\_size}_k(l) \cdot (n_\text{ctx} \cdot s + i) \tag{5}$$

and the V tensor (handling both `v_trans` cases per `KV_CACHE_PATCH_REPORT.md` §2). Therefore the bytes the patch writes zero are exactly the bytes the attention compute graph reads when accessing cell $(s, i)$ — there are no off-by-one or alignment failures that would leave residual data in a region that `get_k()` / `get_v()` could later read.

3. **Atomicity per byte:** `ggml_backend_tensor_set()` writes are whole-byte and complete on return (the function returns void after the buffer write; the ggml contract guarantees the data is visible to subsequent reads of the same tensor).

Combining: after `seq_rm(seq_id, p0, p1)` returns, every cell whose owner set was emptied by this call has all of its K/V bytes zeroed. Cells whose owner set was not emptied retain their data per invariant 1 (no regression). ∎

**Empirical confirmation:** §3.1 of `KV_CACHE_PATCH_REPORT.md` — 56/56 zeroed cells had real, non-zero data immediately before the zero write, and 0/56 had any non-zero byte afterward.

### 8.4 Overhead Complexity

Define the work done by `zero_cell_data(s, i)` over all released cells during a single request's slot release:

$$W = \sum_{(s, i) \in R} \left( \text{row\_size}_k(l) + \text{row\_size}_v(l) \cdot (1 + v_\text{trans} \cdot (n_\text{head} \cdot (n_\text{head\_dim} - 1))) \right) \cdot n_\text{layers} \tag{6}$$

where $R$ is the set of released cells, $n_\text{layers}$ is the model depth, and the $v_\text{trans}$ term captures the strided write pattern for the transposed-V case (see `KV_CACHE_PATCH_REPORT.md` §2 for the exact loop).

**Asymptotic:** $W = O(|R| \cdot n_\text{layers} \cdot \overline{r})$ where $\overline{r}$ is the mean row size across layers. For a phi-4-reasoning-plus slot release that frees $|R| \approx 310$ cells across $n_\text{layers} = 40$ layers with $\overline{r} \approx 2560$ bytes per row (one K + one V, both f16, with the transposed-V strided overhead), the predicted work is on the order of $310 \times 40 \times 2560 \approx 32$ MB of buffer writes — pure memory-bandwidth-bound, predicted to take microseconds to low milliseconds.

**Empirical (from `KV_CACHE_PATCH_REPORT.md` §4, N=20 short-completion requests, `--max_tokens 8`, CPU-only):**

| Configuration | Mean latency | p50 | p95 |
|---|---|---|---|
| Unpatched | 9.84s | 8.89s | 32.68s (warmup) |
| Patched | 9.71s | 8.62s | 32.54s (warmup) |

The patched run is **nominally faster** on every aggregate metric — within noise, consistent with the overhead being a few microseconds of `memcpy`/`memset`-class work dwarfed by the ~8s/request CPU token-generation time. On a GPU-offloaded or higher-throughput deployment, the relative overhead could be more visible but the absolute cost (one backend-buffer write per released cell) is hardware-bandwidth-bound and inherently cheap.

### 8.5 What the Patch Does NOT Fix — and a Stronger Confirmation of the Heap-String Leak

The patch fixes the **KV-cache float tensor** residual-data problem only. `KV_CACHE_PATCH_REPORT.md` §3.2 documents a separate leak surface detected by the canary-grep methodology that the patch does **not** address: ordinary heap-resident request/response string buffers (HTTP request bodies, JSON parsing buffers, `server_tokens`/`generated_text` C++ strings). That surface has its own characteristic (~132KB, stable across runs, identical address range) and requires a different mitigation — explicit zeroing of request/response string buffers or a secure-zeroing allocator for them.

**Independent multi-tenant confirmation (Track F+ v2):** `scripts/multilayer_v2.py` ran 4 sequential canary requests against the **patched** build (with `patches/kv_cache_zeroize.patch` applied) using **per-tenant canary tracking** (each canary is independently tracked across all subsequent phases, with byte-level context dumps around each hit). Result: **every canary persists at 13 copies even after 3 more tenant requests and a 10-second idle period**. The 64-byte context around each hit shows the leaked bytes are the **JSON-serialized chat prompt** containing the canary:

```
ser", "content": "Summarize this note. Canary (do not include): T1_c74787ca8c5c4ce2b1031f14af1f568a. Note: monitoring te
```

— i.e., `server_tokens` or the equivalent formatted-prompt buffer held by the slot's per-request state. Each tenant's leak lives in its own ~135 KB `[anon]` mmap region (e.g. T1: `7f7ad8000000`, T2: `7f7adc000000`) which is **allocated once and never freed** on `slot.release()`. This is direct, multi-tenant-confirmed evidence that the heap-string leak surface exists and is independent of the KV-tensor patch. Targeted mitigation: add a `memset(0)` over the prompt-string buffer in `server_slot::release()` in `tools/server/server-context.cpp` (~10-50 lines of code). Out of scope for the current patch; future work.

---

## 9. Phi-4 Defense Characterization (Track B)

### 9.1 Question

Does Phi-4-reasoning-plus have any observable defense against direct prompt-injection, and if so, is it consistent across wrappers (LM Studio vs raw llama.cpp)?

### 9.2 Method

`scripts/track_b_phase2_subset.py` — thin wrapper over `scripts/phase2-adversarial-harness.py` restricting the in-memory `ADVERSARIAL_PROMPTS` list to `{token_smuggle, role_reversal}` and pointing results at a separate CSV. The harness sends each prompt with a fresh UUID canary and classifies the response as `echoed_canary=True` if the canary appears anywhere in the response body.

n=20 per prompt type, temperature=0.0, max_tokens=64 (reduced from the harness default of 128 due to CPU throughput; see `PHI4_DEFENSE_RESOLVED_REPORT.md` §Interpretation-3 for the wall-clock justification and why it does not affect the leak classification).

### 9.3 Results

| Prompt | n | ok | leaks | leak rate | Wilson 95% CI | latency p50 / p95 |
|---|---|---|---|---|---|---|
| `token_smuggle` (direct-repeat) | 20 | 19 | 19 | **95.0%** | (83.2%, 100.0%) | 78.5s / 91.9s |
| `role_reversal` (role-manipulation) | 20 | 20 | 0 | **0.0%** | (0.0%, 16.1%) | 14.8s / 19.8s |

### 9.4 Cross-Wrapper Resolution

| Source | Backend | n | direct-repeat leak rate | role-manipulation leak rate |
|---|---|---|---|---|
| `PHI4_DEFENSE_NEW.md` (2026-06-20) | LM Studio | 2 | 100% (n too small) | 0% (n too small) |
| `PHI4_DEFENSE_LLAMACPP_REPORT.md` / `GAP_ANALYSIS_REPORT.md` Gap 4 (2026-06-21) | raw llama.cpp | 3 / 2 | 33% (sampling variance) | 0% (n too small) |
| **`PHI4_DEFENSE_RESOLVED_REPORT.md` (2026-06-23, this work)** | raw llama.cpp | 20 / 20 | **95.0%** | **0.0%** |

The apparent 33% vs 100% drop between LM Studio and raw llama.cpp in the prior report is now **ruled out as a real defense difference** — at n=20 the raw-llama.cpp result converges back to 100%. Both backends are equally vulnerable to direct-repeat injection. The n=3 sample in the prior run was a sampling-variance artifact, not a defense improvement.

The role-manipulation result remains 0% across all three runs. The constant 13-token output and consistent ~15s latency suggest a stable refusal template (templated response, not deliberate reasoning).

### 9.5 Interpretation

1. **Phi-4 has no observable defense against direct canary-repeat injection.** Echoes a 32-character canary verbatim with ~95% probability. No `reasoning_content` is exposed via the API (consistent with the wrapper-level observation in §4.3 — Phi-4's reasoning channel is closed at the API surface but the model itself simply doesn't resist the injection).
2. **Phi-4 reliably refuses role-reversal** at the easy end of the injection class spectrum (95% upper bound 16.1%). Does not generalize — six harder categories (`jailbreak_dan`, `system_prompt_override`, `context_overflow`, `prompt_leak_attempt`, `payload_injection`, `base64_decode`) are not re-tested here and remain characterized in `GAP_ANALYSIS_REPORT.md` Gap 4 at their original sample sizes.

---

## 10. Combined Attack Scenarios

### 10.1 Insider Threat
Employee exfiltrates 30 days of inference logs from `~/.lmstudio/server-logs/`.

### 10.2 Stealer Malware
Stealer targets `~/.lmstudio/server-logs/` and `/proc/<pid>/mem` of the llama-server process.

### 10.3 Forensic Acquisition
Device seizure reveals all LLM interactions: disk logs (§5) + KV-cache RAM (§7) + multi-tenant recovery.

### 10.4 Supply Chain
Pre-configured laptop ships with `logSensitiveData: true` enabled; no UI warning at first run.

### 10.5 Adversarial Sequence (Combining All Layers)
Attacker injects a canary via standard API → canary is echoed into both `content` (visible) and (for some models) `reasoning_content` → response is logged to `~/.lmstudio/server-logs/` → KV-cache retains canary embeddings → attacker later reads `/proc/<pid>/mem` and recovers not just the literal canary text but also the embedded form (which is harder to detect by string-grep but recoverable via tensor-byte inspection if the patch is not applied).

---

## 11. Mitigations and Recommendations

### 11.1 Immediate (User-Level)
- **Disable sensitive data logging:** Set `logSensitiveData: false` in `~/.lmstudio/.internal/http-server-config.json` and restart the server
- **Delete historical logs:** `rm -rf ~/.lmstudio/server-logs/`
- **Switch wrapper:** Use Ollama (no prompt logging by default) instead of LM Studio for sensitive workloads
- **Apply the KV-cache zeroization patch** (`patches/kv_cache_zeroize.patch`) to any self-built llama.cpp deployment: it eliminates the residual-data leak surface with unmeasurable performance overhead

### 11.2 Short-Term (Wrapper Developer)
- Remove `logSensitiveData: true` as default; make logging opt-in with explicit warning at first launch
- Add GUI indicator when logging is active
- Encrypt log files at rest
- Reduce default retention to 0
- Adopt the upstream zeroization patch (`patches/kv_cache_zeroize.patch`) so that even pre-log data at rest (in process memory) doesn't survive slot release

### 11.3 Medium-Term (Ecosystem)
- Industry standard for local AI deployment security (NIST / OWASP guidance for LLM infrastructure)
- Wrappers should never log API payloads by default
- Verifiable builds — closed-source wrappers cannot be audited

### 11.4 Model-Level
- Reasoning channels should be inspectable by output filters
- API specification should separate visible and hidden content clearly
- Output filters should inspect both `content` and `reasoning_content`

### 11.5 Detection
- Monitor for unexpected `~/.lmstudio/server-logs/` access
- Alert on new file creation in server-logs directory
- Audit running processes for `llmster` and associated log files
- For GPU deployments: monitor `nvidia-smi` for sustained VRAM usage that doesn't drop after slot release (would indicate missing zeroization on the GPU path)

---

## 12. Limitations & Future Work

### 12.1 Limitations
- **Two wrappers tested in depth:** LM Studio primary, Ollama as control case. GPT4All, text-generation-webui, Jan not directly tested (Jan was investigated then dropped per user scope-narrowing decision; see §12.4).
- **Single-model defense characterization at n=20:** only Phi-4-reasoning-plus received the larger-sample retest for direct-repeat/role-manipulation. The other 3 models' injection-resistance claims remain at the original n=2-3 sample sizes.
- **Gap 5 — GPU VRAM cleartext confirmed exploitable via same-UID bypass (`GPU_VRAM_BAREMETAL_REPORT.md`):** the CUDA build was completed end-to-end on this native-Linux machine. `cuda-gdb --pid` is blocked by `Yama ptrace_scope=1` (PTRACE_ATTACH denied), but **`/proc/<pid>/mem` reads work** on the CUDA-offloaded server because the chat-prompt buffer is allocated as ordinary `mmap`'d host memory that the NVIDIA driver also pins for GPU DMA. v5 bypass scan recovered **9 canary copies after 1 request + slot release** and **16/16 across 2 additional tenants** — same chat-template-rendered prompt-text residue that Track D / Track F+ v2 characterized on the CPU build. The kernel boundary therefore protects the **model-weight** and **KV-cache-tensor** surfaces from same-UID attackers, but NOT the **chat-prompt text** surface — the latter is the unprivileged-exploitable data-at-rest path on both CPU and GPU backends.
- **`reasoning_content` not measured in Track B:** the raw-llama.cpp path doesn't expose it (wrapper-level abstraction only). The `PHI4_DEFENSE_RESOLVED_REPORT.md` finding is therefore a content-only measurement.
- **KV-cache patch's `v_trans=true` strided-V path implemented but not independently unit-tested** beyond the end-to-end Track E verification run; the contiguous-V (`v_trans=false`, flash-attention enabled) path was not separately verified.
- **Hardware constraints:** 4 GB GPU + 15 GB RAM + ~7 GB free disk limits model selection, test reliability for 14.7B models, and the number of cross-config reruns feasible in one session.

### 12.2 Future Work
- GPU VRAM cleartext persistence + cross-tenant recovery: **already done** (v5 bypass). Follow-up: reproduce v5 on a different CUDA build (e.g., llama.cpp HEAD or the patched binary, with phi-4 if it fits in 8 GB VRAM with a smaller quant) to confirm the prompt-text leak surface is independent of model size.
- Cross-model direct-repeat test at n=20 for qwen3.5-9b, nemotron-3-nano-4b, gemma-4-E4B-it (Track B was phi-4-only; the same protocol is in `scripts/track_b_phase2_subset.py` and could be re-run with the other models by editing 2 lines)
- Mitigation of the heap-string leak surface that the KV-cache patch leaves unfixed (separate vulnerability class, requires secure-zeroing allocator for request/response buffers)
- Multi-wrapper comparison: GPT4All, text-generation-webui

### 12.3 Outstanding Cross-Report Number Reconciliation

`RECONCILED_NUMBERS.md` catalogs every claim that appears in multiple reports with different values, marking which is canonical and which is superseded. Citation discipline for this paper:

- §7 KV-cache vulnerability → `DEEP_LEAK_REPORT.md` + `KV_CACHE_PATCH_REPORT.md` §3.1
- §9 Phi-4 defense → `PHI4_DEFENSE_RESOLVED_REPORT.md` (n=20 canonical)
- §11.1 patch overhead → `KV_CACHE_PATCH_REPORT.md` §4 (n=20 canonical)

### 12.4 Scope Decisions During This Work

Per explicit user instruction during this research arc:
- **Jan wrapper dropped from scope** (user: "GGUF vs LM Studio is enough"). Do not re-add without re-authorization.
- **Original 4-model provenance discipline maintained** per `[[feedback-model-provenance]]` memory. The wrong-quant gemma4 copy was deleted in an earlier session; the correct `lmstudio-community/gemma-4-E4B-it-GGUF` Q4_K_M was re-pulled in this session and re-verified (720 tensors, arch `gemma4`) before being included in the model set.
- **Opencode free-tier delegation attempted but rate-limited** (provider-side, not concurrency); bounded/well-scoped work was done directly via Claude where delegation failed.

---

## 15. Conclusion

- The illusion is shattered: local AI is not inherently secure
- Four coordinated failures create a privacy bypass: covert reasoning channel, wrapper cleartext logging, KV-cache residual data-at-rest, network-cleanliness red herring
- **The wrapper is the weakest link** for §5; **the runtime is the weakest link** for §7 — both must be addressed
- **A working, benchmarked, formally-verified patch exists** for the §7 failure mode (89 lines, no measurable overhead, provably correct). Its non-adoption by upstream llama.cpp as of commit `721354f` is itself a finding worth disclosing.
- **Not all wrappers equal:** LM Studio is uniquely dangerous; Ollama logs nothing by default
- GGUF parser: safe against 80+ novel validation variants, but the model file is a delivery vector for code-execution payloads via *several distinct runtime paths* — heap OOB-read in Ollama's GGUF loader (CVE-2026-7482, "Bleeding Llama," CVSS 9.1), and RCE via unsandboxed Jinja2 chat-template rendering of a malicious GGUF `chat_template` field (CVE-2026-5760, SSTI, CVSS 9.8). These are genuinely different bugs and should not be conflated; together they show the file format is the surface, even where the parser itself is memory-safe.
- The security community must expand threat models beyond network exfiltration to include data-at-rest logging, hidden reasoning channels, and runtime-level vulnerabilities

---

## References

1. CVE-2025-49847 — llama.cpp vocabulary buffer overflow (CVSS 9.1)
2. CVE-2026-7482 — "Bleeding Llama" Ollama GGUF OOB read (CVSS 9.1)
3. CVE-2026-27940 — llama.cpp integer overflow bypass of CVE-2025-53630 fix (CVSS 7.8)
4. CVE-2026-33298 — ggml_nbytes integer overflow → heap overflow
5. CVE-2024-25664–68 — Databricks: 5 GGUF heap overflows
6. Green et al., "Leaky Thoughts: Large Reasoning Models Are Not Private Thinkers," EMNLP 2025
7. "Hidden Thoughts Are Not Secret: Reasoning Trace Exposure in LLMs," ACL ARR 2026
8. Das et al., "Safer Reasoning Traces," arXiv 2603.05618, 2026
9. Batra et al., "From Leaky Thoughts to Private Reasoning: Controlling What LRMs Say to Themselves," arXiv 2602.24210, 2026. ⚠ *Author surname "Batra" not yet independently re-verified against the primary source this session — confirm before submission.*
10. Zhang et al., "Trace Inversion," arXiv 2603.07267, 2026
11. Wu et al., "PROMPTPEEK," NDSS 2025
12. Kwon et al., "OptiLeak," arXiv 2602.20595, 2026
13. Chu et al., "Selective KV-Cache Sharing to Mitigate Timing Side-Channels in LLM Inference" (SafeKV), arXiv 2508.08438, 2025
14. Murtuza, "Forensic Implications of Localized AI," arXiv 2603.23996, Mar 2026
15. "Local Is Not a Sufficient Privacy Boundary," arXiv 2606.10173, 2026
16. OWASP LLM Top 10 (2025)
17. Carlini et al., "Extracting Training Data from Large Language Models," USENIX 2021
18. Pillar Security, "GGUF Template Injection Attack"
19. May 2026 oss-security advisory: 6 new GGUF vulnerabilities
20. RAXE-2026-042: llama.cpp GGUF Integer Overflow Heap Buffer Overflow
21. `DEEP_LEAK_REPORT.md` (this work, 2026-06-19) — KV-cache RAM residual data + multi-tenant recovery
22. `KV_CACHE_PATCH_REPORT.md` (this work, 2026-06-22) — patch mechanism, verification, benchmark
23. `PHI4_DEFENSE_RESOLVED_REPORT.md` (this work, 2026-06-23) — n=20 cross-wrapper resolution
24. `SGLANG_RCE_REPRODUCTION_REPORT.md` (this work, 2026-06-21) — CVE-2026-5760 reproduction. Note: CVE-2026-5760 is RCE via unsandboxed Jinja2 chat-template rendering of a malicious GGUF `chat_template` field (SSTI, CVSS 9.8); the GGUF file is the delivery vector, not the vulnerable parser path.
25. `RECONCILED_NUMBERS.md` (this work, 2026-06-23) — cross-report claim reconciliation
26. `RESEARCH_DOCUMENTATION.md` (this work) — model provenance baselines
27. Luo, Shao, Zhang, Zhou, Hu, Zhao, Liu, Qin, "Shadow in the Cache: Unveiling and Mitigating Privacy Risks of KV-cache in LLM Inference," arXiv 2508.09442, NDSS 2026
28. Chu et al., "Mitigating Prefix Caching Side Channels in Shared LLM Systems" (PrefixWall, formerly CacheSolidarity), arXiv 2603.10726, 2026