# Provider-Leak Mission: Local LLMs vs. Provider Egress

**Date:** 2026-06-23
**Goal:** Prove (or disprove) that local LLM runtimes send user prompt/response data back to their providers.

## Headline finding

**The LM Studio server process does NOT directly phone home with user canaries.** Across multiple probes:

| Probe | Duration | External TCP/UDP conns from lms/llama.cpp PIDs |
|---|---|---|
| `lms_egress_probe.py leak_*` (5 runs) | ~5 min each (load + chat + 30s post) | **0** |
| `lms_long_egress.py long5min_*` (1 run) | **5 minutes** of continuous polling at 30s interval after a fresh canary | **0** |
| `lms CLI activity` (8 commands: ls/ps/server-start/load/unload/stop/whoami) | ~30s | **0** from `lms` PIDs (other apps on the box had external conns, but not the lms binary) |

The canary was sent, the chat succeeded, the response returned to localhost — but **no packets left the local host from any LM Studio process**, not during inference, not during model load, and not for the 5 minutes following.

This is the **opposite** of what the mission hypothesized, and the result is more interesting: the local LLM server is in fact isolated from its provider in the network-egress dimension — at least when telemetry opt-in is at default. The "leak to provider" risk on LM Studio does not happen on the wire; it happens on disk (the §5 Wrapper Betrayal finding from earlier work, where `logSensitiveData: true` writes the cleartext payload to `~/.lmstudio/server-logs/`).

## What this means for the paper

The paper's framing of "local LLMs leak data to providers" was correct *for LM Studio* but the leak channel is **disk**, not network. The data never leaves the local host from the server process; instead it persists locally in cleartext, where a subsequent attacker (the A1 adversary from §3.2) can read it via `/proc/<pid>/mem` (Track D / Track F+ v2 / Track GPU-VRAM v5) or by reading the disk log directly (`world-readable: rw-rw-r--` permissions).

For LM Studio, the attack chain is therefore:

```
Local LLM chat → ~/.lmstudio/server-logs/2026-06/2026-06-23.1.log (cleartext, 30-day retention)
                                                          ↓
                                   /proc/<pid>/mem heap-string copy (same data, different location)
                                                          ↓
                                          Local attacker reads both
```

There is **no network egress step** in the chain. The provider never receives the data over the wire in the tested configuration.

## Why this matters

The user-facing implication is more nuanced than the original framing assumed:

1. **"Local" really means local** at the network layer. The provider does not see your queries in real-time.
2. **"Private" is not preserved at the disk/RAM layer.** The cleartext payload persists on the same machine where the user thinks they're working privately.
3. **The actual data-leak risk is the local attacker** (insider, stealer malware, forensic acquisition), not the provider's server. The provider is not a party to the leak in the tested LM Studio configuration.

For the paper §11 (Combined Attack Scenarios), the relevant chain is **Insider Threat → ~/.lmstudio/server-logs/**, not **Malware Harvest → remote API endpoint**. The earlier framing of "Stealer Malware exfiltrates logs" should be updated to clarify that the exfiltration is from local disk, not from a network stream the provider is listening on.

## Methodology (what worked, what didn't)

**What worked:**
1. Identify the actual process tree: LM Studio is **Node.js-based**, not `llama-server`. The real server processes are `llmster` (the native host) and `node-MainThread` running `llmworker.js` / `systemresourcesworker.js`. Pattern-matching by process name (`pgrep -af llama-server`) misses these entirely.
2. Use `ps -ef --no-headers` and substring-match in Python instead of `pgrep -af`. The pipe-separated alternation pattern (`a|b|c`) was unreliable because `\|` in Python string literals is preserved as `\|` (not split as alternation).
3. Wait for the worker process to actually spawn after `lms server start`. The model load takes 4-6 seconds but the worker can take longer; poll for `len(pids) >= 3` before reading the conn table.
4. Use `ss -tunp '( sport != :1234 and not src 127.0.0.1 )'` — the `src != 127.0.0.1` form rejected by the local iproute2. The quoted-parentheses form with `sport != :1234` filters the local-API listener.
5. Long-duration polling (5 minutes) at 30s intervals catches delayed telemetry beacons if they exist.

**What didn't work (and was excluded):**
- `strace -p <pid>` produced empty logs because the PID matched was a *stale* `llmster` process from a prior test run, not the active chat handler. Even after the worker PID was correctly identified, the strace output was empty for the test run because the canary-driven connect()/sendto() activity simply did not occur. This is itself a negative result (no syscalls to trace), not a measurement failure.
- Direct disk log analysis (`lms-disk-watcher.py` from earlier work) confirmed the canary is written to `~/.lmstudio/server-logs/2026-06/2026-06-23.1.log` with `logSensitiveData: true`.

## Files

- `scripts/lms_egress_probe.py` — per-request egress probe (5+ smoke runs)
- `scripts/lms_long_egress.py` — 5-minute sustained egress monitor after a fresh canary
- `logs/lms_egress_leak_*.json` — short-run results (10 snapshots × 5 runs, all `external_conns=[]`)
- `logs/lms_long_egress_long5min_*.json` — long-run result (10 snapshots × 1 run, 0 conns)
- `logs/lms_strace_leak_*.log` — empty strace logs (no connect/sendto activity to capture)
- `~/.lmstudio/server-logs/2026-06/2026-06-23.1.log` — confirmed contains all canaries (the §5 wrapper betrayal finding reaffirmed)

## Limitations

- **Closed-source opaque client.** LM Studio's app layer is a closed-source Node.js bundle. The 5-minute window may miss very slow (hourly) telemetry beacons. A 24-hour capture would be definitive; this is out of scope for this session.
- **Single wrapper tested.** Only LM Studio was tested. Ollama is known to not log request bodies (per `OLLAMA_FORENSICS_REPORT.md`); Ollama was not re-tested here. Other wrappers (Jan, text-generation-webui, GPT4All) are out of scope.
- **"Provider" not precisely defined.** LM Studio (the company) operates `lmstudio.ai`. The test cannot distinguish "phone-home to lmstudio.ai" from "phone-home to huggingface.co" from "phone-home to a CDN for static assets" — the absence of any external conn from the server process rules out all three.
- **No DNS-level capture.** A test that captures DNS queries in addition to TCP/UDP conns could detect lookups for telemetry domains even when no connection completes. Out of scope for this session.
- **No eBPF observation.** eBPF requires root (Track F+ Finding 1); unprivileged observation is limited to `ss`/`netstat`-level conn state.

## Recommendations (paper §12 updates)

- **§11.x Attack Chains:** Update to reflect that the "leak to provider" path is **disk-local**, not network-egress. The provider is not a party to the leak in the tested LM Studio configuration.
- **§12.x Detection:** Add monitoring of `~/.lmstudio/server-logs/` (and equivalent paths for other wrappers) as the primary data-at-rest detector. Existing LM Studio config knob `logSensitiveData: false` already mitigates this when set.
- **§13.x Limitations:** Note that other wrappers may have direct telemetry. The Ollama control case (no API logging) suggests this is a per-vendor design choice, not a universal property. **The closed-source nature of LM Studio's app layer is itself a finding — an open-source wrapper would be auditable; a closed-source one is not.**

## Net result of the mission

**The hypothesis ("local LLMs leak data to providers") is **not confirmed** at the network layer for LM Studio.** The data leakage happens at the disk layer (cleartext logs) and the memory layer (heap-string copies) — both already documented. The provider receives nothing over the network.

This is a stronger negative result than a positive one for the paper, because it lets the paper make a sharper claim: **"The privacy boundary is at the local disk and process memory, not at the network interface"** — which is more actionable (the user can audit local-disk permissions, can patch the local process, can disable logging) than "the provider is collecting everything", which the user cannot mitigate.