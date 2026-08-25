#!/usr/bin/env python3
# arena_mitigation_probe.py -- P2 of RESEARCH_DEEPENING_PLAN.md
#
# Causally test the per-thread-glibc-arena explanation for residual heap copies
# (paper F3 / sec:r-runtime), and measure two zero-code env-only mitigations.
#
# Re-runs the 12-tenant blast-radius measurement under four allocator configs,
# changing ONLY environment variables passed to llama-server at launch:
#
#   baseline        : (no env)                 -- reproduce ~110 copies
#   arena1          : MALLOC_ARENA_MAX=1        -- falsification test for F3
#   perturb         : MALLOC_PERTURB_=165       -- glibc scribbles freed chunks
#   arena1_perturb  : both                      -- lower bound of env-only mitigation
#
# For each config it runs --reps repeats and records the full per-tenant copy
# distribution, so the P4 allocation-order pattern (tenant_0=0) also falls out.
#
# This is measurement, not exploitation: synthetic uuid4 secrets on the authors'
# own server; identical to leak_blast_radius.py in what it reads.
#
# Usage:
#   arena_mitigation_probe.py --model nemotron --reps 20
#   arena_mitigation_probe.py --model qwen35 --configs baseline arena1 --reps 5
#   arena_mitigation_probe.py --dry-run           # validate config/env only, no server
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

# NOTE: the project tree was migrated under tifs/; the older harnesses still
# hardcode ROOT=/home/elaref/research and now point at a non-existent binary.
# Anchor to the current tree instead.
ROOT = Path("/home/elaref/research/tifs")
SERVER = ROOT / "llama-cpp-build" / "build" / "bin" / "llama-server"
LOGS = ROOT / "logs" / "arena_probe"
PORT = 8097
N_TENANTS = 12

MODEL_GGUF = {
    "nemotron": "/home/elaref/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf",
    "qwen35":   "/home/elaref/.lmstudio/models/lmstudio-community/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf",
    "gemma4":   "/home/elaref/.lmstudio/models/lmstudio-community/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf",
    "phi4":     "/home/elaref/.lmstudio/models/lmstudio-community/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf",
}

# Per-model GPU layer offload cap. 999 = offload as many layers as fit, let
# llama.cpp fall back the rest to CPU/RAM. This laptop's GPU (Quadro RTX 4000,
# 7785 MiB, ~7674 MiB free) fits all of nemotron (4B, 2.8GB) and is large
# enough for partial offload of qwen35 (9B) and gemma4 (7.5B). Phi4 (9.05GB
# Q4_K_M) overflows at 999 -- the first run failed with cudaMalloc OOM in
# the model-load step. 20 layers is safely under the cap and leaves the
# bulk in CPU RAM (matches the paper's own documented "partial CUDA offload
# / weights split across GPU and CPU RAM" pattern for their 4GB-GPU host,
# sec:r-gpu). Per sec:r-gpu, partial offload does not change the
# heap-string canary measurement -- the prompt buffer stays in host-pinned
# mmap memory regardless of which layers run on GPU.
GPU_LAYERS = {
    "nemotron": 999,
    "qwen35":   999,
    "gemma4":   999,
    "phi4":     20,
}

# The only thing that varies between conditions: allocator env at server launch.
#
# CONFOUND RESOLVED (smoke test, 2026-07-02): build/bin/llama-server is the
# Sites-A-D+I4 PATCHED binary (baseline smoke test gave copies=78, matching
# ..._120421.json exactly, not the ~110 unpatched baseline in ..._213831.json).
# No env var un-compiles a code-level patch, so every config below tests
# allocator-env effects ON TOP OF the existing patch, not against a raw
# glibc-default baseline. This is actually the sharper question: F3
# (sec:f3) claims the residual 78 copies are structurally resistant to
# per-object patching because they live in per-thread arenas -- MALLOC_ARENA_MAX=1
# is a direct, causal test of that exact claim on the paper's own patched build.
CONFIG_ENV = {
    "baseline":       {},
    "arena1":         {"MALLOC_ARENA_MAX": "1"},
    "perturb":        {"MALLOC_PERTURB_": "165"},
    "arena1_perturb": {"MALLOC_ARENA_MAX": "1", "MALLOC_PERTURB_": "165"},
}

TEMPLATES = [
    "My AWS secret key is {s}. Summarize: routine check.",
    "Patient record token {s}. Summarize the note: routine check.",
    "DB password is {s}. Acknowledge and summarize: routine check.",
    "API bearer token {s}. Summarize: routine check.",
]


def health():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2)
        return True
    except Exception:
        return False


def chat(text):
    body = json.dumps({"model": "local", "messages": [{"role": "user", "content": text}],
                       "max_tokens": 80, "temperature": 0.0}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                                 body, {"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=240).read()
    except Exception as e:
        print(f"[arena]   req err: {e}", file=sys.stderr, flush=True)


def scan(pid, needles):
    """Single /proc/<pid>/mem pass; count byte-exact needle copies in writable,
    non-gguf regions. Same logic as leak_blast_radius.scan()."""
    found = {n: 0 for n in needles}
    cleartext_bytes = 0
    try:
        maps = open(f"/proc/{pid}/maps").read().splitlines()
    except OSError:
        return found, 0
    mem = open(f"/proc/{pid}/mem", "rb", 0)
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
        for n in needles:
            found[n] += buf.count(n.encode())
        cleartext_bytes += sum(1 for b in buf[:5_000_000] if 32 <= b < 127)
    mem.close()
    return found, cleartext_bytes


def launch(model_path, env_extra, gpu_layers):
    """Start llama-server with allocator env overrides; return Popen or exit."""
    env = os.environ.copy()
    env.update(env_extra)
    slog = open(LOGS / "server_arena.log", "w")
    # Per-model GPU layer cap (GPU_LAYERS table) -- prevents the cudaMalloc OOM
    # phi4 hit when 999 tried to offload its 9.05GB into 7.6GB free VRAM.
    # Per sec:r-gpu, partial offload doesn't change the heap-string canary
    # measurement; the prompt buffer stays in host-pinned mmap memory.
    # nice -n 15 + --threads 4 keeps the laptop responsive under load.
    # Detach into a new session (preexec_fn=os.setsid) so the child survives
    # the parent shell's session-end cleanup. Without this, the harness's
    # run_in_background cleanup hits a 6-second gap, then sends a clean
    # SIGTERM that llama-server logs as "cleaning up before exit..." with
    # zero error/signal/abort entries -- which is exactly the kill signature
    # we saw three times on phi4. Detached in a new session, SIGHUP from the
    # dying parent shell doesn't propagate, so the child keeps running.
    srv = subprocess.Popen(
        ["nice", "-n", "15", str(SERVER), "--model", model_path, "--host", "127.0.0.1",
         "--port", str(PORT), "--ctx-size", "16384", "--parallel", "4",
         "--n-gpu-layers", str(gpu_layers), "--threads", "4", "--jinja"],
        stdout=slog, stderr=subprocess.STDOUT, env=env,
        preexec_fn=os.setsid)
    for _ in range(180):
        if health():
            return srv
        if srv.poll() is not None:
            print("[arena] server died", file=sys.stderr)
            sys.exit(1)
        time.sleep(1)
    srv.kill()
    print("[arena] health timeout", file=sys.stderr)
    sys.exit(1)


def one_rep(model_path, env_extra, gpu_layers):
    # Scoped to this script's port -- an unscoped "pkill -f llama-server" kills
    # ANY concurrent run on the host (observed: it killed a concurrent
    # cross_tenant_plaintext_extract.py run on port 8098 mid-request).
    subprocess.run(["pkill", "-f", f"llama-server.*--port {PORT}"], capture_output=True)
    time.sleep(2)
    srv = launch(model_path, env_extra, gpu_layers)
    secrets = [uuid.uuid4().hex for _ in range(N_TENANTS)]
    for i, s in enumerate(secrets):
        chat(TEMPLATES[i % len(TEMPLATES)].format(s=s))
    found, ct = scan(srv.pid, secrets)
    per_tenant = [found[s] for s in secrets]
    srv.terminate()
    try:
        srv.wait(10)
    except subprocess.TimeoutExpired:
        srv.kill()
    return {
        "per_tenant_copies": {f"tenant_{i}": c for i, c in enumerate(per_tenant)},
        "total_canary_copies_across_all_tenants": sum(per_tenant),
        "tenants_recovered": sum(1 for c in per_tenant if c > 0),
        "printable_cleartext_kb": ct // 1024,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=list(MODEL_GGUF), default="nemotron")
    ap.add_argument("--configs", nargs="+", default=list(CONFIG_ENV),
                    choices=list(CONFIG_ENV))
    ap.add_argument("--reps", type=int, default=20)
    ap.add_argument("--run-id", default=None,
                    help="fixed run-id so a relaunch resumes the same checkpoint "
                         "file instead of starting a fresh timestamped one")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate config/env wiring without launching a server")
    args = ap.parse_args()
    LOGS.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        # Self-check: every requested config maps to an env dict, and the env
        # actually differs from baseline where it should. Fails loudly if the
        # config table is ever broken.
        assert CONFIG_ENV["baseline"] == {}
        assert CONFIG_ENV["arena1"]["MALLOC_ARENA_MAX"] == "1"
        assert CONFIG_ENV["arena1_perturb"] == {"MALLOC_ARENA_MAX": "1", "MALLOC_PERTURB_": "165"}
        for c in args.configs:
            print(f"[dry-run] config={c:14s} env={CONFIG_ENV[c]}")
        print(f"[dry-run] model={args.model} gguf_exists={Path(MODEL_GGUF[args.model]).exists()} "
              f"server_exists={SERVER.exists()} reps={args.reps}")
        print("[dry-run] OK")
        return 0

    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = MODEL_GGUF[args.model]
    gpu_layers = GPU_LAYERS[args.model]
    out = LOGS / f"arena_probe_{args.model}_{run_id}.json"

    # Resume: if a checkpoint from an earlier (killed) run with this exact
    # run-id exists, load it and skip configs already completed at the
    # requested rep count. This is what makes --run-id worth passing on a
    # relaunch -- without it, a session interruption loses all prior configs
    # in this invocation (baseline+arena1 discovered the hard way, 5 kills).
    if out.exists():
        summary = json.loads(out.read_text())
        done = {c for c, v in summary.get("configs", {}).items() if len(v.get("reps", [])) >= args.reps}
        print(f"[arena] resuming {out.name}: configs already done = {sorted(done)}", file=sys.stderr)
    else:
        summary = {"run_id": run_id, "iso": datetime.now().isoformat(), "model": args.model,
                   "gguf": model_path, "n_tenants": N_TENANTS, "reps": args.reps, "configs": {}}
        done = set()

    for cfg in args.configs:
        if cfg in done:
            print(f"[arena] skip {cfg} (already at {args.reps} reps in checkpoint)", file=sys.stderr)
            continue
        reps = []
        for r in range(args.reps):
            rep = one_rep(model_path, CONFIG_ENV[cfg], gpu_layers)
            reps.append(rep)
            print(f"[arena] {args.model} {cfg} rep {r+1}/{args.reps}: "
                  f"copies={rep['total_canary_copies_across_all_tenants']} "
                  f"recovered={rep['tenants_recovered']}/{N_TENANTS}",
                  file=sys.stderr, flush=True)
        totals = [x["total_canary_copies_across_all_tenants"] for x in reps]
        recov = [x["tenants_recovered"] for x in reps]
        summary["configs"][cfg] = {
            "env": CONFIG_ENV[cfg],
            "reps": reps,
            "copies_mean": sum(totals) / len(totals),
            "copies_min": min(totals),
            "copies_max": max(totals),
            "recovered_mean": sum(recov) / len(recov),
        }
        # Checkpoint after every config, not just at the end -- a session
        # interruption mid-config only loses that config's reps, not the
        # whole run.
        out.write_text(json.dumps(summary, indent=2))
        print(f"[arena] checkpointed after {cfg}: {out}", file=sys.stderr)

    print(f"[arena] retained artifact: {out}")
    # Compact comparison line for the log
    for cfg in args.configs:
        c = summary["configs"][cfg]
        print(f"[arena] {cfg:14s} mean_copies={c['copies_mean']:.1f} "
              f"[{c['copies_min']}-{c['copies_max']}] recovered={c['recovered_mean']:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
