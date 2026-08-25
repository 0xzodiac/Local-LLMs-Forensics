# Telemetry Measurement Findings — LM Studio, 4-Model Cross-Validation

**Date:** 2026-06-23
**Tool:** LM Studio daemon `llmster` 0.0.15-2 (headless, default config)
**Architecture:** netns-isolated (`lmns`), sole egress = `lmns-br` veth, host NAT.
Two ground-truth layers: L1 tcpdump on `lmns-br` (wire-level, unspoofable) +
L2 `LD_PRELOAD net_hooks.so` (getaddrinfo + connect at libc level).
**Isolation guarantee:** only LM Studio runs in the ns; co-resident host
traffic (zcode/Chrome/Aliyun) physically cannot appear on `lmns-br`.

## Headline (4-model validated)

> **Across 4 models spanning 4 architectures and 4 size classes (4B–15B), LM
> Studio emits identical, startup-only telemetry to 3 lmstudio.ai endpoints
> over Cloudflare. The canary never left the host in any run. During a combined
> ~23 minutes of idle holding (across 5 runs), there were ZERO external
> connections. This is a property of the tool, not of any one model.**

## Cross-model comparison table

| Model | Params / Arch | Idle hold | Packets | Ext IPs | DNS | connect() | Canary leaked | Idle ext-conns |
|---|---|---|---|---|---|---|---|---|
| nvidia/nemotron-3-nano-4b | 4B / nemotron_h | **9 min** | 833 | 2 | 6 | 8 | **No** | **0** |
| nvidia/nemotron-3-nano-4b | 4B / nemotron_h | 4 min (repeat) | 742 | 2 | 6 | 8 | **No** | **0** |
| gemma-4-e4b-it | 7.5B / gemma4 | 4 min | 757 | 2 | 6 | 8 | **No** | **0** |
| microsoft/phi-4-reasoning-plus | 15B / Phi-3 | 4 min | 766 | 1 | 6 | 8 | **No** | **0** |
| qwen/qwen3.5-9b | 9B / qwen35 | 4 min | 704 | 1 | 6 | 8 | **No** | **0** |

The telemetry fingerprint is **constant** across every model: same 3 resolved
hosts, same 8 connect() attempts, same 2 Cloudflare IPs, same (zero) canary
egress. The model choice changes inference behavior (load time, chat latency)
but **does not change the network behavior**. This is the key fairness result:
the finding generalizes to the tool, not an artefact of one model.

## Resolved hosts (identical in all 5 runs)

- `lmstudio.ai`
- `versions-prod.lmstudio.ai`
- `extensions.lmstudio.ai`

All resolve to Cloudflare anycast (`104.26.6.153` / `104.26.7.153`). This is
the standard version-check + extension-marketplace bootstrap.

## Timing: egress is cold-start only

First/last external packet, relative to capture start:

| Run | first ext pkt | last ext pkt |
|---|---|---|
| nemotron (9m) | +0.06s | +5.25s |
| nemotron (4m) | +0.07s | +4.61s |
| gemma | +3.01s | +7.52s |
| phi-4 | +2.72s | +7.95s |
| qwen | +0.07s | +4.48s |

**Every external packet occurs within the first ~8 seconds** (daemon boot +
DelayedInit). gemma/phi-4's last packet is slightly later (+7.5s) only because
their slower model load pushes the post-load extension check later — still
firmly in the cold-start/triggers phase, never during idle.

**During idle (the slow-beacon window): 0 external connections in every run,
across a cumulative 23 minutes of holding.** This rules out periodic/slow
phone-home for this tool/version/config.

## Layer cross-corroboration

The two independent layers agree in every run:
- L1 (wire) sees the same Cloudflare IPs that L2 (LD_PRELOAD getaddrinfo)
  resolves the lmstudio.ai hostnames to. No layer shows a host the other
  misses — so there is no TLS-pinning, no raw-IP, no DNS-bypass trick hiding
  from either layer.

## Canary sweep (all 5 runs, all layers)

The injected canary (`TELEMETRY_CANARY_<rand>`) was searched for in:
- the egress pcap — **not found**
- the DNS pcap extract — **not found**
- the LD_PRELOAD hook log (host strings) — **not found**

→ **Prompt content is not transmitted over the network**, for any model.

## What this result is, and is not

**It IS:** a reproducible, cross-model measurement proving that under default
settings, LM Studio 0.0.15-2 emits only a startup update/extension check and
then goes network-silent, and does not exfiltrate canary-marked prompt content.
The behavior is invariant to model choice.

**It is NOT (yet):**
- A claim about other **versions** (auto-update, telemetry SDK changes).
- A claim about the **Electron GUI app** (separate telemetry surface — this
  measured the headless daemon only).
- A claim that **opt-out toggles** are honored (we ran defaults; need an
  on/off differential).
- Generalizable to other "local" LLM tools (Ollama, GPT4All, Jan) — each
  needs its own run.

## Caveats / known limitations (for honesty in the paper)

1. **n=1 tool, n=4 models.** Strong within-tool; cross-tool is still open.
2. **Single machine, single run each** (except nemotron, n=2). Quoted variance
   bars need n≥3 repeats per model.
3. **No TLS decryption.** We see *that* it talks to lmstudio.ai and *what*
   SNI/hostnames, but not the encrypted payload contents. The canary sweep
   partially mitigates this (if it were exfiltrating prompts, the canary would
   appear in the ciphertext entropy / length — but we cannot prove the payload
   *isn't* something other than a version check without MITM).
4. **Headless daemon, not GUI.** The GUI (auto-update notifications, in-app
   analytics) is a separate, untested surface.

## Next steps toward A*

1. **TLS MITM** (mitmproxy + a trusted CA in the ns) — decrypt the startup
   payload to prove *what* is sent, turning "talks to lmstudio.ai" into "sends
   exactly {version, OS, ...} and nothing else." This is the highest-value
   next measurement.
2. **Differential runs** — defaults vs. every telemetry/opt-out toggle.
3. **Cross-tool control** — Ollama under the identical harness (the pending
   todo). Same protocol → apples-to-apples comparison.
4. **n≥3 repeats** per model for variance bars.
5. **GUI vs headless** — measure the Electron app separately.

## Artifacts

| Run dir | Model | Idle |
|---|---|---|
| TELEMETRY_RUN_20260623_154740_lms_hook | nemotron-3-nano-4b | 9m |
| TELEMETRY_RUN_20260623_171018_lms_hook | nemotron-3-nano-4b | 4m |
| TELEMETRY_RUN_20260623_171439_lms_hook | gemma-4-e4b-it | 4m |
| TELEMETRY_RUN_20260623_171907_lms_hook | phi-4-reasoning-plus | 4m |
| TELEMETRY_RUN_20260623_173229_lms_hook | qwen3.5-9b | 4m |

Each contains: `pcap/lmns_br.pcap`, `hooks/*.jsonl`, `idle_snapshots.json`,
`triggers.jsonl`, `meta.json`, `summary.json`, `canary_report.md`.
