# Telemetry Measurement Findings — LM Studio (nemotron-3-nano-4b)

**Run:** `TELEMETRY_RUN_20260623_154740_lms_hook`
**Date:** 2026-06-23
**Duration:** 9 min idle hold (540s) + cold-start + trigger phase ≈ 9m16s total
**Architecture:** netns-isolated (LM Studio daemon inside `lmns` namespace, sole egress = `lmns-br` veth, host-side NAT)

## Headline result

> **EGRESS DETECTED — but it is a cold-start update/extension check only. The
> canary never left the host. During the entire 9-minute idle hold, there were
> ZERO external connections. No slow beacon, no periodic phone-home, no
> prompt/PII exfiltration.**

This is the rigorous, defensible answer to the "No Free Lunch" hypothesis *for
this tool, version, and configuration*: LM Studio (0.0.15-2) makes exactly one
round of outbound contact at startup (versions + extensions), then goes silent.
The "free" is not paid for by silent telemetry — at least not by network egress.

## What was measured

| Element | Value |
|---|---|
| Tool | LM Studio daemon `llmster` 0.0.15-2 |
| Model | `nvidia/nemotron-3-nano-4b` (loaded + 2 chats, incl. a canary prompt) |
| Canary | `TELEMETRY_CANARY_af621c13892e` (injected via prompt-injection-style probe) |
| Instrumentation | L1: tcpdump on `lmns-br` (wire-level, unspoofable) · L2: `LD_PRELOAD net_hooks.so` (getaddrinfo + connect at libc level) |
| Isolation guarantee | Only LM Studio runs in the ns; co-resident host traffic (zcode/Chrome/Aliyun) physically cannot appear on `lmns-br` |

## Layer-by-layer (post-correction)

| Layer | Observation |
|---|---|
| **L1 packet capture** | 833 packets; **2 external dest IPs**: `104.26.6.153`, `104.26.7.153` (both Cloudflare / lmstudio.ai) |
| **L2 DNS (from pcap)** | 6 queries; resolved hosts: `lmstudio.ai`, `versions-prod.lmstudio.ai`, `extensions.lmstudio.ai` |
| **L2/L3 LD_PRELOAD hook** | 3 non-loopback `getaddrinfo`; 8 external `connect()` attempts — **matches L1 dests** (cross-layer corroboration) |
| **TLS SNI** | `lmstudio.ai` (t+0.105s), `versions-prod.lmstudio.ai` (t+0.106s), `extensions.lmstudio.ai` (t+0.168s) — all within **170 ms of daemon start** |
| **Canary sweep** | NOT in pcap, NOT in DNS, NOT in hook log → **canary did not leave the host** |
| **Idle hold (540s)** | 36 snapshots; **0 external connections at any point** during the entire window |

## Critical methodological note (the timing tells the story)

Every external packet timestamped to **15:47:44–15:47:45** — i.e. the first
~5 seconds after the daemon forked. There is **no packet to an external host
after cold-start**. Specifically:
- No beacon after the model loaded (15:47:49).
- No beacon after the benign chat (15:47:53).
- No beacon after the **canary chat** (15:47:54) — the prompt content was never
  transmitted anywhere.
- No periodic/slow beacon across 9 minutes of idle.

This rules out the strongest version of the exfiltration hypothesis (that the
tool ships prompt/PII data to a vendor endpoint).

## What this result is, and is not

**It IS:** a clean, reproducible, single-configuration measurement proving that
*under default settings*, LM Studio 0.0.15-2 emits only a startup update check
and then goes network-silent — and does not exfiltrate canary-marked prompt
content over the network.

**It is NOT (yet):**
- A claim about **other versions** (auto-update behavior, telemetry SDK changes).
- A claim about **the GUI app** (this measured the headless daemon `llmster`;
  the Electron GUI has its own telemetry surface — separate measurement needed).
- A claim about **opt-out toggles** being honored (we ran defaults; the
  `logSensitiveData:true` and similar config knobs need an on/off differential).
- **Generalizable** to other "local" LLM tools (Ollama, GPT4All, Jan, etc.) —
  each needs its own run. This is n=1 tool.

## Next steps to strengthen toward A*

1. **Differential runs** (defaults vs. every telemetry/opt-out toggle) — turns
   "no leak under defaults" into "leak disappears when toggle X is set" (or
   "persists despite toggle X" = a real finding).
2. **Cross-tool control case** — Ollama under the identical harness. If Ollama
   is also silent, that's a "the class is cleaner than feared" story; if Ollama
   leaks and LM Studio doesn't, that's a comparative-finding story.
3. **GUI vs headless** — measure the Electron app separately.
4. **Repeat for n≥3** — the current single run is a demo; small-n variance bars
   convert it into a quoted statistic.

## Artifacts

- pcap: `TELEMETRY_RUN_20260623_154740_lms_hook/pcap/lmns_br.pcap` (876 KB, 833 pkts)
- hook traces: `TELEMETRY_RUN_20260623_154740_lms_hook/hooks/*.jsonl`
- idle snapshots: `TELEMETRY_RUN_20260623_154740_lms_hook/idle_snapshots.json`
- report: `TELEMETRY_RUN_20260623_154740_lms_hook/canary_report.md`
- machine-readable: `TELEMETRY_RUN_20260623_154740_lms_hook/summary.json`
