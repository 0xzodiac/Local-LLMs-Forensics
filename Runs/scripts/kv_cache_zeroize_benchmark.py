#!/usr/bin/env python3
# Track E Part D: throughput/latency overhead of the KV-cache zeroize patch.
# N reduced from the spec's 100 to 20 (hardware constraint: this CPU does ~1 tok/s
# on phi-4-reasoning-plus -- 100 full requests would take hours per side).
# Forces repeated slot release+reuse (--parallel 1, short max_tokens) so the
# per-request cost includes one zero_cell_data() pass over the released cells.
import json, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path("/home/elaref/research")
SERVER = ROOT / "llama-cpp-build/build/bin/llama-server"
MODEL = "/home/elaref/.lmstudio/models/lmstudio-community/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf"
PORT = 8099
N = 20

def health():
    try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2); return True
    except Exception: return False

def chat(i):
    body = json.dumps({
        "model": "local",
        "messages": [{"role": "user", "content": f"Request number {i}. Reply with one short sentence."}],
        "max_tokens": 8, "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                                  body, {"Content-Type": "application/json"})
    t0 = time.monotonic()
    urllib.request.urlopen(req, timeout=120).read()
    return time.monotonic() - t0

def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    subprocess.run(["pkill", "-f", "bin/llama-server"], capture_output=True); time.sleep(2)
    slog = open(ROOT / f"logs/kv_zeroize_bench_{label}.log", "w")
    srv = subprocess.Popen(
        [str(SERVER), "--model", MODEL, "--host", "127.0.0.1", "--port", str(PORT),
         "--ctx-size", "2048", "--n-gpu-layers", "0", "--threads", "16", "--jinja",
         "--parallel", "1", "--cache-ram", "0"],
        stdout=slog, stderr=subprocess.STDOUT)
    print(f"[bench] server pid {srv.pid}; waiting for health...", flush=True)
    for i in range(180):
        if health(): break
        if srv.poll() is not None: print("[bench] server died"); sys.exit(1)
        time.sleep(1)

    lat = []
    t_start = time.monotonic()
    for i in range(N):
        lat.append(chat(i))
        print(f"[bench] req {i+1}/{N}: {lat[-1]:.2f}s", flush=True)
    total = time.monotonic() - t_start

    srv.terminate()
    try: srv.wait(10)
    except subprocess.TimeoutExpired: srv.kill()

    lat.sort()
    p50 = lat[len(lat)//2]
    p95 = lat[int(len(lat)*0.95)] if len(lat) > 1 else lat[0]
    print(f"[bench] === {label}: N={N} total={total:.2f}s throughput={N/total:.3f} req/s "
          f"mean={sum(lat)/len(lat):.2f}s p50={p50:.2f}s p95={p95:.2f}s "
          f"min={min(lat):.2f}s max={max(lat):.2f}s ===", flush=True)

if __name__ == "__main__":
    main()
