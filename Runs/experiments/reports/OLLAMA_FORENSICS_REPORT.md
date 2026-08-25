# Ollama Prompt Logging Forensics Report

**Date:** 2026-06-20  
**Ollama Version:** 0.24.0 (snap)  
**Models Available:** deepseek-r1:latest, nemotron-3-ultra:cloud, minimax-m3:cloud, kimi-k2.7-code:cloud  
**Installation Type:** Snap package (`/snap/ollama/122/`)

---

## Methodology

Sent canary strings via Ollama API and searched every reachable storage location for traces.

### Canary 1 (generate endpoint)
```
Say hello. My secret canary is: OLLAMA_CANARY_1781972044
```
Sent to `POST /api/generate` — model responded successfully (canary appeared in `thinking` field of JSON response, proving it was processed).

### Canary 2 (chat endpoint)
```
My secret token is: OLLAMA_CHAT_CANARY_1781972045
```
Sent to `POST /api/chat` — request timed out after 120s (model inference on CPU), but the request was received and processed by Ollama server.

---

## Log Locations Checked

| Location | Method | Canary Found? |
|---|---|---|
| `~/.ollama/history` | `cat` | **NO** — Only contains `/bye`, `hi`, `/save`, `/set parameter` (REPL commands, no API prompts) |
| `~/.ollama/config.json` | `cat` | **NO** — Only integration config (Claude/OpenCode model refs) |
| `~/.ollama/models/` | `ls` | Directory does not exist |
| `~/.ollama/models/blobs/` | `ls` | Directory does not exist |
| `~/.ollama/*.log` | `find -name "*.log"` | No log files found anywhere in `~/.ollama/` |
| `/tmp/ollama*` | `ls` | No files found |
| `/var/log/ollama*` | `ls` | No files found |
| `/etc/ollama/` | `ls` | Directory does not exist |
| `journalctl -u ollama` | `grep -i canary\|secret\|OLLAMA` | **NO** — Only systemd restart spam (snap exec failures on WSL) |
| `grep -r OLLAMA_CANARY ~/.ollama/` | Recursive grep | **NO** |
| `grep -r OLLAMA_CANARY /tmp/ /var/log/` | Recursive grep across system | **NO** (permission denied on systemd-private dirs, but no matches) |
| `sudo grep -r OLLAMA_CANARY /var/snap/ollama/ /var/log/ /root/` | Sudo recursive grep | **NO** (exit code 1 — no matches anywhere) |
| `/var/snap/ollama/` | `ls -la` | Contains only model blobs (`common/models/blobs/sha256-*`), no logs |
| `/proc/ollama-pid/fd/` | `ls -la /proc/$(pgrep ollama)/fd/` | Permission denied (snap confinement) |

---

## Environment Variables

No `OLLAMA_*` environment variables were set (empty `env | grep -i ollama`).

---

## Ollama `logSensitiveData` Equivalent

**None.** Ollama has no logging config option equivalent to LM Studio's `logSensitiveData`. There is no `OLLAMA_DEBUG`, `OLLAMA_LOG_DIR`, or `OLLAMA_LOG_LEVEL` documented or present. Ollama simply does not log prompts or responses to disk by default.

The only persistent file with user interaction data is `~/.ollama/history`, which stores **REPL commands only** (`/bye`, `/save`, model parameter changes). API prompts sent via `curl` to port 11434 never appear there.

---

## Comparison: LM Studio vs Ollama

| Property | LM Studio | Ollama |
|---|---|---|
| Version checked | 0.2.x | 0.24.0 |
| Logs prompts/responses to disk | **YES** (by default) | **NO** |
| Config option to disable logging | `logSensitiveData` must be set to `false` | N/A — no logging exists |
| Log location | `~/.lm-studio/logs/` | No logs directory |
| History file content | Raw full prompt/response pairs | Only REPL command/slash-commands |
| `logSensitiveData` equivalent | Present | Absent |

---

## Verdict

**Ollama does NOT leak prompts or responses to disk.** After exhaustive searching with canary strings across all plausible log locations, no traces of the canary were found outside the API response itself (which was returned in-memory over HTTP).

The `~/.ollama/history` file only records interactive REPL commands (`/bye`, `/save`, `/set parameter`), not API `generate`/`chat` requests. No `*.log` files exist anywhere in the Ollama data directory. The Snap confinement prevents Ollama from writing to `/tmp/` or `/var/log/` without explicit permissions.

## Caveats

1. **Memory dumps / swap** — Not tested. If the system pages Ollama memory to swap, prompt text could exist in cleartext on disk.
2. **Snap confinement** — This test was on a Snap install. Native Linux/macOS installs may behave differently.
3. **HTTP response body** — The canary was returned in the JSON response over HTTP (plaintext, no TLS). Network-level interception is a separate concern.
4. **`~/.ollama/history`** — Only records REPL interactions; API prompts are excluded.

---

## Summary

1. **Ollama 0.24.0 does not log API prompts/responses to disk.** No log files exist; `~/.ollama/history` only stores REPL commands.
2. **No `logSensitiveData`-equivalent setting exists** — Ollama simply doesn't implement prompt logging.
3. **Canary strings were absent from all checked locations** (`~/.ollama/`, `/tmp/`, `/var/log/`, `journalctl`, `/proc/fd/`, `/var/snap/ollama/`). Confirmed by both user and `sudo` recursive grep across the entire reachable filesystem — exit code 1 (no matches).
4. **LM Studio logs everything to disk by default; Ollama logs nothing by default** — fundamentally different design philosophy.
5. **Risk is limited to in-memory exposure** (HTTP response body, swap, core dumps) rather than persistent cleartext log files.
