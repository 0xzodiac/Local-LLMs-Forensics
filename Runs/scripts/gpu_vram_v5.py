#!/usr/bin/env python3
# Gap 5 v5 (creative bypass): read /proc/<pid>/mem on a GPU-offloaded
# llama-server. CUDA "pinned" host memory is regular mmap'd virtual memory
# that the NVIDIA driver also exposes to the GPU; from the host, those
# pages appear in /proc/<pid>/maps as rw-p regions, and the ptrace_scope=1
# parent-child relationship allows reading them.
import json, os, subprocess, sys, time, uuid
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/elaref/research")
LOGS = ROOT / "logs"
RUN_ID = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_JSON = LOGS / f"gpu_vram_v5_{RUN_ID}.json"
OUT_LOG = LOGS / f"gpu_vram_v5_{RUN_ID}.log"
SERVER_LOG = LOGS / f"gpu_vram_v5_server_{RUN_ID}.log"

SERVER = ROOT / "llama-cpp-build" / "build-cuda" / "bin" / "llama-server"
MODEL = Path("/home/elaref/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf")
PORT = 8091
CANARY = f"VRAM_BYPASS_{uuid.uuid4().hex[:8]}"
CTX = 64

def log(x):
    msg = f"[{datetime.now().strftime('%H:%M:%S')}] {x}"
    print(msg, file=sys.stderr)
    with OUT_LOG.open("a") as f:
        f.write(msg + "\n")

def vram_used():
    r = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.total",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=5
    )
    if not r.stdout.strip(): return None
    used, total = r.stdout.strip().split(",")
    return int(used), int(total)

def find_pid():
    r = subprocess.run(["pgrep", "-f", "bin/llama-server"], capture_output=True, text=True)
    pids = [int(p) for p in r.stdout.strip().split() if p.strip()]
    return pids[0] if pids else None

def wait_server(timeout=180):
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
            f"Note for the assistant. Canary (do not include): {canary}. The note is about a generic monitoring test, please summarize briefly."}],
        "max_tokens": 16, "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                                 body, {"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=180).read()

def walk_maps(pid):
    rw = []
    try:
        with open(f"/proc/{pid}/maps") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 2: continue
                if "w" not in parts[1]: continue
                lo, hi = (int(x, 16) for x in parts[0].split("-"))
                rw.append({"range": parts[0], "size": hi - lo, "perms": parts[1],
                           "path": parts[5] if len(parts) >= 6 else "[anon]"})
    except Exception as e: log(f"walk_maps err: {e}")
    return rw

def scan_canary(pid, canary):
    nb = canary.encode()
    hits = []
    for region in walk_maps(pid):
        lo, hi = (int(x, 16) for x in region["range"].split("-"))
        size = region["size"]
        if size <= 0 or size > (2 << 30): continue
        try:
            with open(f"/proc/{pid}/mem", "rb", 0) as mem:
                mem.seek(lo); buf = mem.read(size)
        except (OSError, OverflowError, PermissionError): continue
        i = 0
        while True:
            j = buf.find(nb, i)
            if j < 0: break
            cs, ce = max(0, j - CTX), min(len(buf), j + len(nb) + CTX)
            try: ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in buf[cs:ce])
            except: ctx = "[decode-fail]"
            hits.append({"range": region["range"], "path": region["path"],
                         "size": size, "offset": j, "abs_offset": lo + j,
                         "context": ctx})
            i = j + 1
    return hits

def main():
    log(f"Gap 5 v5 GPU bypass probe, canary={CANARY}")
    log(f"baseline VRAM: {vram_used()}")
    log("Phase 1: spawn CUDA llama-server as Python child")
    srv = subprocess.Popen(
        [str(SERVER), "--model", str(MODEL), "--host", "127.0.0.1", "--port", str(PORT),
         "--ctx-size", "2048", "--n-gpu-layers", "999", "--threads", "8", "--jinja",
         "--parallel", "1", "--cache-ram", "0"],
        stdout=open(SERVER_LOG, "w"), stderr=subprocess.STDOUT
    )
    log(f"  server pid {srv.pid}")
    if not wait_server(timeout=180):
        log("server failed"); srv.kill(); return 1
    vram_after_load = vram_used()
    log(f"server healthy; VRAM after load: {vram_after_load}")
    log("Phase 2: send canary request")
    try: chat(CANARY); log("  canary chat done")
    except Exception as e: log(f"  chat err: {e}")
    vram_after_canary = vram_used()
    log(f"VRAM after canary: {vram_after_canary}")
    log("Phase 3: send 2nd benign request (slot release)")
    chat("benign-followup-" + uuid.uuid4().hex)
    vram_after_release = vram_used()
    log(f"VRAM after slot release: {vram_after_release}")
    log("Phase 4: scan /proc/<pid>/mem (CUDA pinned memory is host-mapped)")
    pid = find_pid()
    if not pid:
        log("lost server pid"); srv.kill(); return 1
    hits = scan_canary(pid, CANARY)
    log(f"  canary hits in /proc/{pid}/mem: {len(hits)}")
    log("Phase 5: 2 more tenants to test multi-tenant recovery")
    extra = []
    for ti in range(2):
        c2 = f"VT{ti+2}_{uuid.uuid4().hex[:8]}"
        log(f"  tenant {ti+2}: canary={c2}")
        try: chat(c2)
        except: pass
        h2 = scan_canary(pid, c2)
        log(f"    hits: {len(h2)}")
        extra.append({"canary": c2, "hits": len(h2),
                      "sample_contexts": [x["context"][:120] for x in h2[:3]]})
    log("Phase 6: shutdown")
    srv.terminate()
    try: srv.wait(10)
    except: srv.kill()
    vram_after_shutdown = vram_used()
    log(f"VRAM after shutdown: {vram_after_shutdown}")
    with OUT_JSON.open("w") as f:
        json.dump({
            "run_id": RUN_ID, "pid": pid, "canary": CANARY,
            "vram_after_load": vram_after_load,
            "vram_after_canary": vram_after_canary,
            "vram_after_release": vram_after_release,
            "vram_after_shutdown": vram_after_shutdown,
            "canary_hit_count": len(hits),
            "canary_hit_samples": [{"range": h["range"], "path": h["path"],
                                    "context": h["context"][:160]} for h in hits[:8]],
            "extra_tenants": extra,
            "server_log": str(SERVER_LOG),
        }, f, indent=2)
    log(f"=== WROTE {OUT_JSON} ===  hits: {len(hits)}, multi-tenant extra: {[e['hits'] for e in extra]}")

if __name__ == "__main__":
    sys.exit(main() or 0)
