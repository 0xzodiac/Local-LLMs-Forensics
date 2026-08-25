# D5 — Ollama netns Network-Egress Control Case

**Verdict (4/4 models): NO EGRESS DETECTED. No canary leaving the host in
any run.** Fills the `PAPER_DRAFT_TIFS.md` §6.1 "pending D5" placeholder:
this is the cross-tool control for the LM Studio netns-isolation finding.

## Method

Exact same netns-isolation harness as the LM Studio run
(`TELEMETRY_FINDINGS_4MODELS.md`): isolated `lmns` namespace, sole egress via
the `lmns-br` veth, host-side NAT, `tcpdump` on `lmns-br` as ground truth
(L1, wire-level, unspoofable). Same 4 GGUFs LM Studio was tested with
(`nemotron-3-nano-4b`, `qwen3.5-9b`, `gemma-4-e4b-it`,
`phi-4-reasoning-plus`), imported into Ollama **offline** via
`ollama create <name>-local -f Modelfile` (`FROM <local .gguf path>`) — zero
network pull, reuses the exact files LM Studio already downloaded.

**Differences from the LM Studio harness, and why:**

- **No LD_PRELOAD hook layer (L2).** Ollama is a Go binary; the Go runtime
  issues `connect()`/`getaddrinfo()` via its own syscall stubs, not libc, so
  an LD_PRELOAD on libc symbols would silently miss Go's own network calls —
  a false-negative risk, not a methodology we'd want to claim coverage for.
  L1 (packet capture, language-agnostic, wire-level) is the sole ground-truth
  layer here.
- **Trigger = `/api/generate`, not `/v1/chat/completions`.** Ollama's native
  API; same semantic role (model_load + benign, then a canary prompt).
- **Idle hold: 3 min**, vs. LM Studio's 4–9 min. Shorter window — documented
  asymmetry, not parity. Sufficient to cover the trigger-bound channels
  (load, chat, canary) that are the primary disclosure target; does not rule
  out a beacon slower than 3 min as confidently as the LM Studio run rules
  out one slower than 4 min.
- **Disk-bounded sequential execution.** `ollama create` copies the GGUF
  into its own blob store (not a symlink) — duplicating 3–9GB per model.
  Host had ~20GB free, not enough for all 4 simultaneously, so each model
  was imported, tested, and removed (`ollama rm`) before the next.

## Result

| Model | Params / Arch | Idle hold | Packets | Ext IPs | DNS | Canary leaked | Model loaded OK |
|---|---|---|---|---|---|---|---|
| nemotron-3-nano-4b | 4B / nemotron_h | 3 min | 41 | 0 | 0 | **No** | Yes |
| qwen3.5-9b | 9B / qwen35 | 3 min | 8 | 0 | 0 | **No** | Yes |
| gemma-4-e4b-it | 7.5B / gemma4 | 3 min | 56 | 0 | 0 | **No** | Yes |
| phi-4-reasoning-plus | 15B / Phi-3 | 3 min | 1 | 0 | 0 | **No** | Yes |

All 4 runs: 0 unique external destination IPs, 0 DNS queries, 0 canary hits
in the pcap. The handful of captured packets per run are local mDNS/IGMP
multicast (`224.0.0.251`, `224.0.0.22`) from the ns's own loopback-adjacent
traffic — classified as local infrastructure, not egress, by the same
`analyze.py` filter used for the LM Studio runs.

## A real operational hazard hit during this run (documented for honesty + reuse)

The first attempt (all 4 models in one pass) failed for gemma4 and phi4 with
`"model requires more system memory (X GiB) than is available"`. Root cause:
`ollama serve` forks `ollama runner` child processes (the actual GPU/RAM-
heavy inference workers); the harness launched the parent via `setsid` for
clean detachment but originally killed only the parent PID at teardown. The
runner children survived as orphans, accumulating across the nemotron and
qwen35 iterations — 3 leaked processes holding ~9.4GB RAM/VRAM, driving the
host to 357MB free / swap full by the time gemma4 ran. Fixed by killing the
whole process group (`kill -9 -- -<pid>`, negative PID = group, since
`setsid` makes the parent a new session/process-group leader) instead of the
single PID. Reran gemma4 and phi4 cleanly after the fix; both loaded and
produced the same zero-egress result as the first two models.

A second, separate hazard: the harness initially used `pkill -x ollama` to
clear stale daemons before each run. `ip netns exec` isolates the *network*
namespace only — not PIDs/proc — so a name-based kill would also have
matched the host's own systemd-managed `ollama.service` (PID 2883, serving
unrelated production traffic on the host's own loopback). Caught before any
run executed; fixed by tracking the exact spawned PID in a pidfile and never
killing by process name. Worth keeping in mind for anyone adapting this
harness to a different daemon: namespace isolation tools are easy to assume
give you PID isolation too, and they don't.

## Interpretation

Network egress behavior is invariant to local-LLM tool choice, at least
across these two tools and these four models: LM Studio (0 canary egress,
but does dial out — Cloudflare-fronted hosts on cold start, unrelated to
prompt content, see `TELEMETRY_FINDINGS_4MODELS.md`) and Ollama (0 canary
egress, **and observed zero external connections of any kind** across all 4
models). This strengthens the paper's "prompt content does not leave a
locally-run model's process" claim by showing it generalizes across runtimes
with very different architectures (Electron+Node daemon vs. a single Go
binary), not just across models within one tool.

It does **not** show the tools are equally network-silent in general — LM
Studio's cold-start telemetry calls are a real, separate finding that this
run doesn't speak to either way (no idle-hold-only comparison run was done
for Ollama at matched duration; the 3 vs. 4–9 min asymmetry is real and
should be stated as a limitation, not glossed over).

## Honest limitations

- n=1 run per model (no repeats; LM Studio's nemotron got 2 repeats, this
  did not — variance bars would need ≥3 repeats per model on both sides).
- Idle hold shorter than the LM Studio runs (3 min vs. 4–9 min) — weaker
  bound on slow/delayed beacons for Ollama specifically.
- No L2 (LD_PRELOAD) layer — single ground-truth layer (L1 packet capture)
  instead of the 2-layer cross-check used for LM Studio. Justified (Go
  bypasses libc), but it is genuinely less coverage, not equivalent coverage
  by a different method.
- Host had a live, unrelated production `ollama.service` running throughout
  (PID 2883) — confirmed never touched, but worth flagging as a
  co-residency detail for reproducibility.
- Disk constraints forced sequential model testing (import → test → delete)
  rather than the LM Studio run's pattern; this doesn't affect the network
  result but is a meaningful operational difference worth noting for anyone
  reproducing this on a similarly disk-constrained host.
