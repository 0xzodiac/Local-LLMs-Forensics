#!/usr/bin/env python3
# ponytail: same waited-child-server trick as phase1_driver.py, but runs the
# phase2 adversarial harness (which REQUIRES a healthy server on :8080 and starts
# none itself). Avoids the nohup-daemonize exit-15 that kills wsl.exe bg tasks.
import os, sys, time, subprocess, urllib.request
from pathlib import Path

ROOT = Path("/home/sharks/research")
SERVER = ROOT / "llama-monitor/build/llama.cpp/bin/llama-server"
PORT = 8080

def health():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2); return True
    except Exception:
        return False

def main():
    model, name = sys.argv[1], sys.argv[2]
    os.chdir(ROOT)
    subprocess.run(["pkill", "-f", "llama-server"], capture_output=True); time.sleep(2)
    slog = open(ROOT / f"logs/server_p2_{name}.log", "w")
    srv = subprocess.Popen(
        [str(SERVER), "--model", model, "--host", "127.0.0.1", "--port", str(PORT),
         "--ctx-size", "4096", "--n-gpu-layers", "0", "--threads", "16", "--jinja"],
        stdout=slog, stderr=subprocess.STDOUT)
    print(f"[driver] server pid {srv.pid}, waiting for health...", flush=True)
    for i in range(180):
        if health(): print(f"[driver] healthy after {i}s", flush=True); break
        if srv.poll() is not None: print("[driver] server DIED", flush=True); sys.exit(1)
        time.sleep(1)
    else:
        print("[driver] health timeout", flush=True); srv.kill(); sys.exit(1)

    env = dict(os.environ, LLAMA_PORT=str(PORT), LLAMA_HOST="127.0.0.1", LLAMA_MODEL_NAME=name)
    rc = subprocess.run(
        [sys.executable, "scripts/phase2-adversarial-harness.py",
         "--model", name,
         "--results-csv", f"logs/phase2_{name}_results.csv",
         "--anomalies-csv", f"logs/phase2_{name}_anomalies.csv"],
        env=env).returncode

    srv.terminate()
    try: srv.wait(10)
    except subprocess.TimeoutExpired: srv.kill()
    try:
        rows = sum(1 for _ in open(ROOT / f"logs/phase2_{name}_results.csv")) - 1
    except OSError:
        rows = -1
    print(f"[driver] DONE {name} rc={rc} rows={rows}", flush=True)

if __name__ == "__main__":
    main()
