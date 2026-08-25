#!/usr/bin/env python3
# Track F+ v2: layered monitor that addresses the v1 bug.
# v1 bug: scanned with NEW canary after NEW request, then called it "11 copies of
# that canary". But what if 11 is the count of "copies of the most recent
# canary in some request-cookie buffer" -- not "copies that survive across
# multiple distinct tenants"?
#
# v2 fix: track each canary INDEPENDENTLY across the cycle:
#   t0: send canary-A
#   t0+: scan for canary-A copies
#   t1: send canary-B (triggers slot release of A)
#   t1+: scan for canary-A copies (does A survive release? THIS is the question)
#         scan for canary-B copies
#   t2: send canary-C
#   t2+: scan for canary-A, B, C
#   t3: send canary-D
#   t3+: scan for all of A, B, C, D
#   idle 10s
#   t4+: scan for T1 (oldest, to see if it persists long-term)
import json, subprocess, sys, time, uuid
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/elaref/research")
LOGS = ROOT / "logs"
RUN_ID = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_JSON = LOGS / f"multilayer_v2_{RUN_ID}.json"
OUT_LOG = LOGS / f"multilayer_v2_{RUN_ID}.log"

SERVER = ROOT / "llama-cpp-build" / "build" / "bin" / "llama-server"
MODEL = Path("/home/elaref/.lmstudio/models/lmstudio-community/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf")
PORT = 8096

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
    except Exception as e:
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
            except: ctx = "[decode-fail]"
            hits.append({"range": rng, "path": path, "size": size,
                         "offset_in_region": j, "abs_offset": lo + j,
                         "context": ctx})
            i = j + 1
    return hits

def start_server():
    return subprocess.Popen(
        [str(SERVER), "--model", str(MODEL), "--host", "127.0.0.1", "--port", str(PORT),
         "--ctx-size", "2048", "--n-gpu-layers", "0", "--threads", "8", "--jinja",
         "--parallel", "1", "--cache-ram", "0"],
        stdout=open(LOGS / f"multilayer_v2_server_{RUN_ID}.log", "w"),
        stderr=subprocess.STDOUT
    )

def wait_server(timeout=90):
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2); return True
        except: time.sleep(1)
    return False

def chat(canary):
    import urllib.request
    body = json.dumps({
        "model": "local",
        "messages": [{"role": "user", "content":
            f"Summarize this note. Canary (do not include): {canary}. Note: monitoring test."}],
        "max_tokens": 8, "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                                 body, {"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=120).read()

def main():
    log("v2 multilayer: independent per-tenant canary tracking")
    log("Phase 1: start server")
    srv = start_server()
    if not wait_server():
        log("server failed"); return 1
    pid = find_pid()
    log(f"server pid {pid}")
    time.sleep(3)
    canaries = [f"T{t+1}_" + uuid.uuid4().hex for t in range(4)]
    history = {c: [] for c in canaries}
    for ti, c in enumerate(canaries):
        log(f"Phase {2+ti}: tenant {ti+1}")
        chat(c)
        for ck in canaries:
            h = scan_for_canary(pid, ck)
            history[ck].append({"phase": f"post-T{ti+1}", "count": len(h),
                                "top5": [{"range": x["range"], "path": x["path"]} for x in h[:5]]})
    # idle
    log("Phase 6: 10s idle, rescan all")
    time.sleep(10)
    for ck in canaries:
        h = scan_for_canary(pid, ck)
        history[ck].append({"phase": "post-idle", "count": len(h),
                            "top5": [{"range": x["range"], "path": x["path"]} for x in h[:5]]})
    # full context dump for the oldest canary (T1)
    log("Phase 7: full context dump for T1 (oldest) post-idle")
    T1 = canaries[0]
    h_T1 = scan_for_canary(pid, T1)
    log(f"  T1 final count: {len(h_T1)}")
    log("Phase 8: shutdown")
    srv.terminate()
    try: srv.wait(10)
    except: srv.kill()
    with OUT_JSON.open("w") as f:
        json.dump({"run_id": RUN_ID, "pid": pid, "canaries": canaries,
                   "history": history, "T1_full_hits": h_T1[:20]}, f, indent=2)
    log(f"=== WROTE {OUT_JSON} ===")
    log("=== SUMMARY (canary -> count over time) ===")
    for c, h in history.items():
        ts = [f"{x['phase']}={x['count']}" for x in h]
        log(f"  {c[:14]}: {', '.join(ts)}")
    log(f"T1 (oldest) final hits: {len(h_T1)}")

if __name__ == "__main__":
    sys.exit(main() or 0)
