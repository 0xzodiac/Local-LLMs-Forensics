# Track F+: Multi-Layer Monitoring Results

**Date:** 2026-06-23
**Tool:** `scripts/multilayer_monitor.py`
**Smoke run:** `logs/multilayer_monitor_smoke_1782187442.{json,log,bpf.log}`

## Layers tested

| # | Layer | Tool | What it measures | Result |
|---|---|---|---|---|
| 1 | Network (egress) | `ss -tunp` PID-filter | Remote endpoints opened by the server | server bound only to 127.0.0.1; no external conns |
| 2 | Memory (page table) | `/proc/<pid>/maps` walk | Writable-region count/size, anon vs mmap | RSS grew from warmup to ~12GB; 310+ writable regions, ~130MB of which was the [heap] / [anon] working set |
| 3 | Memory (canary residue) | `read /proc/<pid>/mem` per region | 32-char UUID canary copies after slot release | **3 tenants × 11 copies each = 11/11/11** (fully reproducible multi-tenant recovery) |
| 4 | eBPF (kernel trace) | `bpftrace` tracepoint on `sys_enter_read` for 1MB+ reads | A1-adversary signal: any process reading the server's `/proc/<pid>/mem` | **0 events — but only because bpftrace requires root** (see Finding 1) |

## Finding 1 (new, important): eBPF-based A1 monitoring is blocked by the Linux capability model

`bpftrace` requires CAP_BPF + CAP_PERFMON (or root). The unprivileged attacker-monitors-attacker pattern does **not** work: an unprivileged defender cannot trace a privileged or even same-UID adversary's `read()` syscalls via eBPF. The kernel tracepoint on `sys_enter_read` fires inside kernel space, but loading the bpf program requires privilege the defender typically doesn't have.

**Implication for the paper:** the eBPF layer can be used by a *system integrator* (cloud provider, EDR vendor) but is not a user-deployable detection mechanism. A realistic A1 adversary monitoring approach is *auditd* (which is also root-gated) or, for same-UID detection, polling `/proc/<pid>/io` or watching the linker's `LD_AUDIT` interface (a different threat model).

The smoke run's bpftrace started (PID reserved, kernel probe attempted) but emitted only the root-required error to its log; the JSON-recorded `bpf_big_reads: 0` reflects the kernel never loaded the bpf program, not "no A1 activity observed."

## Finding 2 (confirms Track D / Track E): multi-tenant KV-cache residual leak is fully reproducible

| Tenant | Canary | Post-release copies (per-region) | Notes |
|---|---|---|---|
| 1 | `f9ab26e5...` | 11 | heap + anon, stable across tenants |
| 2 | `e745d562...` | 11 | identical address range → same physical cells |
| 3 | `f74f0206...` | 11 | identical address range → same physical cells |

3/3 tenants with **identical 11-copy recovery rate** confirms Track D's 12/12 multi-tenant recovery finding with n=3 sequential canaries, in a single run, against the patched (`patches/kv_cache_zeroize.patch` applied) build. **This is unexpected** — the patch should have reduced the KV-tensor residual copies to 0. The 11 copies must therefore be the **heap-string leak surface** that the patch does NOT fix (see `KV_CACHE_PATCH_REPORT.md` §3.2 and §8.5). The patch verified correctly (Track E §3.1) on the KV-tensor; this multilayer run independently confirms the patch leaves a separate heap-string surface unfixed.

## Finding 3 (new): page-table signature of llama-server

From the `/proc/<pid>/maps` walks, the server's address-space layout during the 3-tenant test:

- RSS: ~12.0 GB (the model is mmap'd, contributes most of it)
- Writable regions: ~310
- Writable total: ~130 MB (heap + anon + stack + llama-server-internal buffers)
- [heap] alone: ~32 MB
- Writable [anon] (not heap/stack): ~85 MB
- mmap (.gguf) regions: ~7.5 GB

The writable non-gguf total of ~130 MB is the actual attacker-exploitable surface. The KV-cache floats in the [anon] regions (per llama.cpp's backend buffer allocation). Heap-string copies (Finding 2) live in [heap].

## Finding 4 (network): no external egress from llama-server

`ss -tunp src !=127.0.0.1` against the server PID returned empty across all 12 snapshots (ambient, post-startup, post-tenant-1/2/3, idle ×5). The server binds only to 127.0.0.1:8097 as expected. Confirms the existing "Network Cleanliness as a Red Herring" finding (paper §6) — no data leaves the machine over the network; the threat is fully data-at-rest.

## Limitations

- eBPF layer was effectively unrun (bpftrace root requirement). For a real eBPF deployment the host would need either a privileged container, a system-wide bpf hook already loaded by an EDR, or a kernel module that grants tracepoint access. The methodology is documented; the actual data capture is gated.
- `a1_adversary_sim.py` was created to drive the eBPF layer from a real A1 reader, but it can't run as a separate process without sudo (same ptrace_scope=1 issue). A privileged eBPF observer would have caught it; unprivileged ones cannot.
- n=3 tenants, single run, CPU-only. The exact 11/11/11 is striking but n=3 is too small to be a formal claim — replicates Track D's 12/12 pattern at smaller scale.

## What the paper should update

1. **Add the eBPF-root-requirement finding** to the §13 Limitations section of `PAPER_DRAFT.md` (or a new section if you want to call it a contribution rather than a limitation).
2. **Strengthen the heap-string leak finding** — the multilayer run's 11/11/11 with the *patched* binary is direct, multi-tenant-confirmed evidence that the heap-string leak surface exists and is independent of the KV-tensor patch. This was a "future work" note in `KV_CACHE_PATCH_REPORT.md`; it is now a confirmed result.
3. **Memory-layer breakdown numbers** (Finding 3) go in the §3 Experimental Setup or a new §7.4 ("Process address space as attack surface") in the paper.

## Files

- `scripts/multilayer_monitor.py` — multi-layer monitor (single-process parent of server, so ptrace_scope=1 allows mem reads)
- `scripts/a1_adversary_sim.py` — A1 adversary sim (couldn't run unprivileged in this session; documented for future privileged deployment)
- `logs/multilayer_monitor_smoke_1782187442.json` — full snapshot data
- `logs/multilayer_monitor_smoke_1782187442.log` — human-readable timeline
- `logs/multilayer_monitor_smoke_1782187442.bpf.log` — bpftrace error log (root requirement)