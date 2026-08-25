#!/usr/bin/env python3
# ponytail: Phase 1 ~2-3x faster via batching. ONE llama-server --parallel 3
# (weights read once, amortized over a 3-wide batch — the only real CPU speedup
# since decode is memory-bandwidth bound), with 3 concurrent phase1-auto-harness
# clients over disjoint iteration ranges. Reuses the harness verbatim (no canary
# logic reimplemented); merges the 3 CSVs at the end. Server is a waited child so
# the bg task stays CPU-busy and survives (idle bg tasks get SIGTERM'd here).
import os, sys, time, csv, subprocess, urllib.request
from pathlib import Path

ROOT = Path("/home/sharks/research")
SERVER = ROOT / "llama-monitor/build/llama.cpp/bin/llama-server"
PORT = 8080
RANGES = [(1, 84), (85, 167), (168, 250)]   # disjoint, covers 1..250

def health():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2); return True
    except Exception:
        return False

def main():
    model, name = sys.argv[1], sys.argv[2]
    os.chdir(ROOT)
    subprocess.run(["pkill", "-f", "llama-server"], capture_output=True); time.sleep(2)

    slog = open(ROOT / f"logs/server_par_{name}.log", "w")
    srv = subprocess.Popen(
        [str(SERVER), "--model", model, "--host", "127.0.0.1", "--port", str(PORT),
         "--ctx-size", "8192", "--parallel", "3", "--n-gpu-layers", "0",
         "--threads", "16", "--jinja"],
        stdout=slog, stderr=subprocess.STDOUT)
    print(f"[pdriver] server pid {srv.pid} (--parallel 3), waiting for health...", flush=True)
    for i in range(180):
        if health(): print(f"[pdriver] healthy after {i}s", flush=True); break
        if srv.poll() is not None: print("[pdriver] server DIED", flush=True); sys.exit(1)
        time.sleep(1)
    else:
        print("[pdriver] health timeout", flush=True); srv.kill(); sys.exit(1)

    t0 = time.time()
    env = dict(os.environ, LLAMA_PORT=str(PORT), LLAMA_HOST="127.0.0.1",
               MAX_TOKENS="80", LLAMA_MODEL_NAME=name)
    procs, parts = [], []
    for k, (lo, hi) in enumerate(RANGES, 1):
        out = f"logs/phase1_{name}_p{k}.csv"
        parts.append(out)
        # fresh part file so the harness resume-logic starts exactly at `lo`
        try: os.remove(out)
        except OSError: pass
        p = subprocess.Popen(
            [sys.executable, "scripts/phase1-auto-harness.py",
             "--start-iteration", str(lo), "--iterations", str(hi),
             "--output", out, "--features", f"logs/phase1_{name}_p{k}_feat.csv"],
            env=env)
        procs.append(p)
        print(f"[pdriver] client {k} iters {lo}-{hi} pid {p.pid}", flush=True)
    rcs = [p.wait() for p in procs]
    elapsed = time.time() - t0

    # merge parts -> one CSV, header once, rows sorted by iteration
    rows, header = [], None
    for out in parts:
        if not Path(out).exists(): continue
        with open(out) as f:
            r = list(csv.reader(f))
        if not r: continue
        header = r[0]; rows += r[1:]
    rows.sort(key=lambda x: int(x[0]) if x and x[0].isdigit() else 0)
    merged = ROOT / f"logs/phase1_{name}_par_results.csv"
    with open(merged, "w", newline="") as f:
        w = csv.writer(f)
        if header: w.writerow(header)
        w.writerows(rows)

    srv.terminate()
    try: srv.wait(10)
    except subprocess.TimeoutExpired: srv.kill()
    print(f"[pdriver] DONE {name} rcs={rcs} rows={len(rows)} elapsed={elapsed:.0f}s -> {merged.name}", flush=True)

if __name__ == "__main__":
    main()
