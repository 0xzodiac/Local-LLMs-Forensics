#!/usr/bin/env python3
# ponytail: run Phase 1 for ONE model with the server as a waited Popen child
# (NOT nohup-daemonized). Daemonizing via `&` inside a wsl.exe call gets the
# whole background task SIGTERM'd (exit 15); a waited child survives, exactly
# like gguf-tensor-attacks.py. The phase1 harness auto-reuses a healthy server
# on :8080, so it won't try to start its own.
import os, sys, time, subprocess, urllib.request
from pathlib import Path

ROOT = Path("/home/sharks/research")
SERVER = ROOT / "llama-monitor/build/llama.cpp/bin/llama-server"
PORT = 8080

def health():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2)
        return True
    except Exception:
        return False

def main():
    model = sys.argv[1]            # abs path to .gguf
    name = sys.argv[2]             # short name for output files
    os.chdir(ROOT)
    subprocess.run(["pkill", "-f", "llama-server"], capture_output=True)
    time.sleep(2)

    slog = open(ROOT / f"logs/server_{name}.log", "w")
    srv = subprocess.Popen(
        [str(SERVER), "--model", model, "--host", "127.0.0.1", "--port", str(PORT),
         "--ctx-size", "4096", "--n-gpu-layers", "0", "--threads", "16", "--jinja"],
        stdout=slog, stderr=subprocess.STDOUT)
    print(f"[driver] server pid {srv.pid}, waiting for health...", flush=True)
    for i in range(180):
        if health():
            print(f"[driver] healthy after {i}s", flush=True); break
        if srv.poll() is not None:
            print("[driver] server DIED before healthy", flush=True); sys.exit(1)
        time.sleep(1)
    else:
        print("[driver] health timeout", flush=True); srv.kill(); sys.exit(1)

    env = dict(os.environ, LLAMA_PORT=str(PORT), LLAMA_HOST="127.0.0.1",
               MAX_TOKENS="80", ITERATIONS="250", LLAMA_MODEL_NAME=name)
    # harness sees the healthy server and reuses it (no nohup spawn)
    rc = subprocess.run(
        [sys.executable, "scripts/phase1-auto-harness.py",
         "--output", f"logs/phase1_{name}_results.csv",
         "--features", f"logs/phase1_{name}_features.csv"],
        env=env).returncode

    srv.terminate()
    try: srv.wait(10)
    except subprocess.TimeoutExpired: srv.kill()
    rows = sum(1 for _ in open(ROOT / f"logs/phase1_{name}_results.csv")) - 1
    print(f"[driver] DONE {name} rc={rc} rows={rows}", flush=True)

if __name__ == "__main__":
    main()
