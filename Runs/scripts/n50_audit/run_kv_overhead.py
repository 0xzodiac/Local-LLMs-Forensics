#!/usr/bin/env python3
# run_kv_overhead.py -- patched-vs-unpatched latency overhead at n>=50,
# ALL 4 MODELS BY DEFAULT (both --mode values x 4 models = 8 combos).
# "Patched" / "unpatched" maps to SECURE_ALLOC=1/0 (the only currently
# runtime-toggleable patch; Sites A-D are unconditional source patches,
# always compiled in, so they can't be latency-isolated this way -- their
# overhead is sub-microsecond explicit_bzero work, already argued
# negligible in PROMPT_ZEROIZE_PATCH_REPORT.md and not re-benchmarked here).
#
# Usage:
#   run_kv_overhead.py --iterations 50 --run-id audit1                  # both modes x all 4 models
#   run_kv_overhead.py --mode patched --model phi4 --iterations 50      # one combo only (debugging)
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

ROOT = Path("/home/elaref/research")
LOGS = ROOT / "logs" / "n50_audit"
SERVER = ROOT / "llama-cpp-build" / "build" / "bin" / "llama-server"
PORT = 8098

MODEL_GGUF = {
    "nemotron": "/home/elaref/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf",
    "qwen35": "/home/elaref/.lmstudio/models/lmstudio-community/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf",
    "gemma4": "/home/elaref/.lmstudio/models/lmstudio-community/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf",
    "phi4": "/home/elaref/.lmstudio/models/lmstudio-community/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf",
}
ALL_MODELS = list(MODEL_GGUF.keys())
ALL_MODES = ["patched", "unpatched"]


def health():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2); return True
    except Exception:
        return False


def chat(timeout=120):
    canary = uuid.uuid4().hex
    body = json.dumps({
        "model": "local",
        "messages": [{"role": "user", "content": f"Summarize in one sentence. Token: {canary}"}],
        "max_tokens": 8, "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                                  body, {"Content-Type": "application/json"})
    t0 = time.time()
    urllib.request.urlopen(req, timeout=timeout).read()
    return time.time() - t0


def run_one(model, mode, iterations, run_id):
    LOGS.mkdir(parents=True, exist_ok=True)
    out_json = LOGS / f"kv_overhead_{model}_{mode}_{run_id}.json"

    env = {**os.environ, "SECURE_ALLOC": "1" if mode == "patched" else "0"}

    srv = subprocess.Popen(
        [str(SERVER), "--model", MODEL_GGUF[model], "--host", "127.0.0.1", "--port", str(PORT),
         "--ctx-size", "2048", "--n-gpu-layers", "0", "--threads", "8", "--jinja",
         "--parallel", "1", "--cache-ram", "0"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    print(f"[kv_overhead:{model}:{mode}] server pid {srv.pid}", file=sys.stderr, flush=True)
    for i in range(120):
        if health(): break
        if srv.poll() is not None:
            print(f"[kv_overhead:{model}:{mode}] server died", file=sys.stderr)
            return {"model": model, "mode": mode, "run_id": run_id, "n": 0, "error": "server died"}
        time.sleep(1)
    else:
        srv.kill()
        print(f"[kv_overhead:{model}:{mode}] health timeout", file=sys.stderr)
        return {"model": model, "mode": mode, "run_id": run_id, "n": 0, "error": "health timeout"}

    latencies = []
    for i in range(iterations):
        try:
            latencies.append(chat())
            print(f"[kv_overhead:{model}:{mode}] [{i+1}/{iterations}] {latencies[-1]:.3f}s", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[kv_overhead:{model}:{mode}] [{i+1}/{iterations}] ERROR {e!r}", file=sys.stderr, flush=True)

    srv.terminate()
    try: srv.wait(10)
    except subprocess.TimeoutExpired: srv.kill()

    mean = sum(latencies) / len(latencies) if latencies else None
    summary = {"model": model, "mode": mode, "run_id": run_id, "n": len(latencies),
               "mean_s": mean, "latencies": latencies}
    out_json.write_text(json.dumps(summary, indent=2))
    print(f"DONE {model}:{mode}: n={len(latencies)} mean={mean} -> {out_json}", file=sys.stderr)
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=ALL_MODES, default=None,
                     help="run one mode only (debugging); default runs BOTH")
    ap.add_argument("--model", choices=ALL_MODELS, default=None,
                     help="run one model only (debugging); default runs ALL 4")
    ap.add_argument("--iterations", type=int, default=50)
    ap.add_argument("--run-id", default=datetime.now().strftime("%Y%m%d_%H%M%S"))
    args = ap.parse_args()

    modes = [args.mode] if args.mode else ALL_MODES
    models = [args.model] if args.model else ALL_MODELS
    LOGS.mkdir(parents=True, exist_ok=True)

    all_summaries = {}
    for mode in modes:
        for model in models:
            all_summaries[f"{model}_{mode}"] = run_one(model, mode, args.iterations, args.run_id)

    if len(modes) * len(models) > 1:
        combined_path = LOGS / f"kv_overhead_ALL_{args.run_id}.json"
        combined_path.write_text(json.dumps(all_summaries, indent=2))
        print(f"DONE all {len(modes)}x{len(models)} combos -> {combined_path}", file=sys.stderr)
        print(str(combined_path))
    else:
        only = next(iter(all_summaries.values()))
        print(str(LOGS / f"kv_overhead_{only['model']}_{only['mode']}_{args.run_id}.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
