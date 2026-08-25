#!/usr/bin/env python3
# gdb_repro_setup.py -- reproduces the second heap-string leak EXACTLY like
# multilayer_v2.py (same flags, same port, same canary format), but leaves
# the server alive afterward instead of shutting it down, so gdb can attach
# while the leaked state is still live in memory.
import json, subprocess, sys, time, uuid
from pathlib import Path

ROOT = Path("/home/elaref/research")
LOGS = ROOT / "logs"
SERVER = ROOT / "llama-cpp-build" / "build" / "bin" / "llama-server"
MODEL = Path("/home/elaref/.lmstudio/models/lmstudio-community/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf")
PORT = 8096

def log(x):
    print(f"[gdb-setup] {x}", file=sys.stderr, flush=True)

def find_pid():
    r = subprocess.run(["pgrep", "-f", "bin/llama-server"], capture_output=True, text=True)
    pids = [int(p) for p in r.stdout.strip().split() if p.strip()]
    return pids[0] if pids else None

def walk_writable_maps(pid):
    rw = []
    with open(f"/proc/{pid}/maps") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 2: continue
            rng, perms = parts[0], parts[1]
            path = parts[5] if len(parts) >= 6 else ""
            if "w" not in perms: continue
            lo, hi = (int(x, 16) for x in rng.split("-"))
            rw.append({"range": rng, "size": hi - lo, "path": path or "[anon]"})
    return rw

def scan_for_canary(pid, canary, context_bytes=64):
    nb = canary.encode()
    hits = []
    for region in walk_writable_maps(pid):
        rng, size, path = region["range"], region["size"], region["path"]
        if path.endswith(".gguf") or size <= 0 or size > (200 << 20): continue
        lo, hi = (int(x, 16) for x in rng.split("-"))
        try:
            with open(f"/proc/{pid}/mem", "rb", 0) as mem:
                mem.seek(lo); buf = mem.read(size)
        except (OSError, OverflowError): continue
        i = 0
        while True:
            j = buf.find(nb, i)
            if j < 0: break
            abs_addr = lo + j
            cs, ce = max(0, j - context_bytes), min(len(buf), j + len(nb) + context_bytes)
            ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in buf[cs:ce])
            hits.append({"range": rng, "path": path, "abs_addr": hex(abs_addr),
                         "region_size": size, "context": ctx})
            i = j + 1
    return hits

def start_server():
    return subprocess.Popen(
        [str(SERVER), "--model", str(MODEL), "--host", "127.0.0.1", "--port", str(PORT),
         "--ctx-size", "2048", "--n-gpu-layers", "0", "--threads", "8", "--jinja",
         "--parallel", "1", "--cache-ram", "0"],
        stdout=open(LOGS / "gdb_repro_server.log", "w"), stderr=subprocess.STDOUT
    )

def wait_server(timeout=90):
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2); return True
        except Exception: time.sleep(1)
    return False

def chat(canary, timeout=120):
    import urllib.request
    body = json.dumps({"model": "local", "messages": [{"role": "user", "content":
        f"Summarize this note. Canary (do not include): {canary}. Note: monitoring test."}],
        "max_tokens": 8, "temperature": 0.0}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                                  body, {"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout).read()

def main():
    log("starting server (exact multilayer_v2.py flags)")
    subprocess.run(["pkill", "-9", "-f", "bin/llama-server"])
    time.sleep(2)
    start_server()
    if not wait_server():
        log("server failed to start"); return 1
    pid = find_pid()
    log(f"server pid {pid}")
    time.sleep(3)

    T1 = "T1_" + uuid.uuid4().hex
    T2 = "T2_" + uuid.uuid4().hex
    chat(T1)
    h1 = scan_for_canary(pid, T1)
    log(f"T1 hits right after T1's own request: {len(h1)}")

    chat(T2)
    h2 = scan_for_canary(pid, T2)
    log(f"T2 hits right after T2's own request: {len(h2)}")
    for h in h2[:5]:
        log(f"  {h['abs_addr']} region={h['range']} size={h['region_size']} path={h['path']}")
        log(f"    ctx: {h['context']}")

    out = {"pid": pid, "T1": T1, "T2": T2, "h1": h1, "h2": h2, "port": PORT}
    (LOGS / "gdb_repro_targets.json").write_text(json.dumps(out, indent=2))
    log(f"WROTE {LOGS / 'gdb_repro_targets.json'}")
    log(f"server pid {pid} LEFT RUNNING for gdb attach -- kill it manually when done")
    return 0

if __name__ == "__main__":
    sys.exit(main())
