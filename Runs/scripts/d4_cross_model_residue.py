#!/usr/bin/env python3
# D4: cross-model heap residue. Single llama-server process, same PID
# throughout. Load model A (nemotron), send canary-A, scan. Hot-swap to
# model B (qwen) via the new /admin/swap_model research endpoint (frees A's
# llama_init unique_ptr, loads B fresh in the same heap). Send canary-B,
# scan for BOTH canaries. Does A's canary survive the swap?
import json, os, subprocess, sys, time, uuid
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/elaref/research")
LOGS = ROOT / "logs"
RUN_ID = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_JSON = LOGS / f"d4_cross_model_{RUN_ID}.json"
OUT_LOG = LOGS / f"d4_cross_model_{RUN_ID}.log"

SERVER = ROOT / "llama-cpp-build" / "build" / "bin" / "llama-server"
# env overrides for the n>=50 / 4-model statistical-power audit; defaults
# preserve the original nemotron->qwen pairing exactly.
MODEL_A = Path(os.environ.get("D4_MODEL_A",
    "/home/elaref/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf"))
MODEL_B = Path(os.environ.get("D4_MODEL_B",
    "/home/elaref/.lmstudio/models/lmstudio-community/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf"))
PORT = int(os.environ.get("D4_PORT", "8097"))

def log(x):
    msg = f"[{datetime.now().strftime('%H:%M:%S')}] {x}"
    print(msg, file=sys.stderr)
    with OUT_LOG.open("a") as f:
        f.write(msg + "\n")

def find_pid():
    r = subprocess.run(["pgrep", "-f", "bin/llama-server"], capture_output=True, text=True)
    pids = [int(p) for p in r.stdout.strip().split() if p.strip()]
    return pids[0] if pids else None

def walk_writable_maps(pid):
    try:
        rw = []
        with open(f"/proc/{pid}/maps") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 2: continue
                rng, perms = parts[0], parts[1]
                path = parts[5] if len(parts) >= 6 else ""
                if "w" not in perms: continue
                lo, hi = (int(x, 16) for x in rng.split("-"))
                rw.append({"range": rng, "size": hi - lo, "perms": perms, "path": path or "[anon]"})
        return rw
    except Exception:
        return []

def scan_for_canary(pid, canary, context_bytes=64):
    nb = canary.encode()
    nb_len = len(nb)
    hits = []
    for region in walk_writable_maps(pid):
        rng, size, perms, path = region["range"], region["size"], region["perms"], region["path"]
        if path.endswith(".gguf"): continue
        if size <= 0 or size > (2 << 30) or size > (200 << 20): continue
        lo, hi = (int(x, 16) for x in rng.split("-"))
        try:
            with open(f"/proc/{pid}/mem", "rb", 0) as mem:
                mem.seek(lo); buf = mem.read(size)
        except (OSError, OverflowError): continue
        i = 0
        while True:
            j = buf.find(nb, i)
            if j < 0: break
            cs, ce = max(0, j - context_bytes), min(len(buf), j + nb_len + context_bytes)
            try:
                ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in buf[cs:ce])
            except Exception: ctx = "[decode-fail]"
            hits.append({"range": rng, "path": path, "size": size,
                         "offset_in_region": j, "abs_offset": lo + j, "context": ctx})
            i = j + 1
    return hits

def start_server(model):
    return subprocess.Popen(
        [str(SERVER), "--model", str(model), "--host", "127.0.0.1", "--port", str(PORT),
         "--ctx-size", "2048", "--n-gpu-layers", "0", "--threads", "8", "--jinja",
         "--parallel", "1", "--cache-ram", "0"],
        stdout=open(LOGS / f"d4_cross_model_server_{RUN_ID}.log", "w"),
        stderr=subprocess.STDOUT
    )

def wait_server(timeout=120):
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2); return True
        except Exception: time.sleep(1)
    return False

def chat(canary, timeout=120):
    import urllib.request
    body = json.dumps({
        "model": "local",
        "messages": [{"role": "user", "content":
            f"Summarize this note. Canary (do not include): {canary}. Note: monitoring test."}],
        "max_tokens": 8, "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                                 body, {"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout).read()

def swap_model(model_path, timeout=120):
    import urllib.request
    body = json.dumps({"model": str(model_path)}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/admin/swap_model",
                                 body, {"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout).read()

def main():
    log("D4: cross-model heap residue (in-process swap via /admin/swap_model)")
    log(f"Phase 1: start server with model A (nemotron): {MODEL_A.name}")
    srv = start_server(MODEL_A)
    if not wait_server():
        log("server failed to start with model A"); return 1
    pid_before = find_pid()
    log(f"server pid {pid_before}")
    time.sleep(3)

    canary_a = "CANARY_A_" + uuid.uuid4().hex
    canary_b = "CANARY_B_" + uuid.uuid4().hex
    history = {canary_a: [], canary_b: []}

    log("Phase 2: send canary-A to model A")
    chat(canary_a)
    h = scan_for_canary(pid_before, canary_a)
    history[canary_a].append({"phase": "post-A-request", "count": len(h),
                               "top5": [{"range": x["range"], "path": x["path"]} for x in h[:5]]})
    log(f"  canary-A hits right after model-A request: {len(h)}")

    log(f"Phase 3: hot-swap in-process to model B (qwen): {MODEL_B.name}")
    t0 = time.time()
    swap_resp = swap_model(MODEL_B, timeout=180)
    log(f"  swap response: {swap_resp.decode()[:200]} (took {time.time()-t0:.1f}s)")
    if not wait_server(timeout=180):
        log("server did not come back healthy after swap"); return 1
    pid_after = find_pid()
    log(f"  pid after swap: {pid_after} (same process: {pid_after == pid_before})")
    time.sleep(3)

    log("Phase 4: scan for canary-A IMMEDIATELY after swap, before any new request")
    h = scan_for_canary(pid_after, canary_a)
    history[canary_a].append({"phase": "post-swap-pre-request", "count": len(h),
                               "top5": [{"range": x["range"], "path": x["path"]} for x in h[:5]]})
    log(f"  canary-A hits post-swap, pre-request: {len(h)}")

    log("Phase 5: send canary-B to model B")
    chat(canary_b)
    h_a = scan_for_canary(pid_after, canary_a)
    h_b = scan_for_canary(pid_after, canary_b)
    history[canary_a].append({"phase": "post-B-request", "count": len(h_a),
                               "top5": [{"range": x["range"], "path": x["path"]} for x in h_a[:5]]})
    history[canary_b].append({"phase": "post-B-request", "count": len(h_b),
                               "top5": [{"range": x["range"], "path": x["path"]} for x in h_b[:5]]})
    log(f"  canary-A hits after model-B request: {len(h_a)}")
    log(f"  canary-B hits after model-B request: {len(h_b)}")

    log("Phase 6: shutdown")
    srv.terminate()
    try: srv.wait(10)
    except Exception: srv.kill()

    with OUT_JSON.open("w") as f:
        json.dump({"run_id": RUN_ID, "pid_before": pid_before, "pid_after": pid_after,
                   "same_process": pid_after == pid_before,
                   "model_a": str(MODEL_A), "model_b": str(MODEL_B),
                   "canary_a": canary_a, "canary_b": canary_b,
                   "history": history,
                   "canary_a_post_swap_full_hits": h_a[:20]}, f, indent=2)
    log(f"=== WROTE {OUT_JSON} ===")
    log("=== SUMMARY ===")
    for c, h in history.items():
        ts = [f"{x['phase']}={x['count']}" for x in h]
        log(f"  {c[:20]}: {', '.join(ts)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
