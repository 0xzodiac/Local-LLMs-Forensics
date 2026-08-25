#!/usr/bin/env python3
# Gap 5 v3: VRAM probe -- simpler reliable approach.
import json, os, subprocess, sys, time, uuid
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/elaref/research")
LOGS = ROOT / "logs"
RUN_ID = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_JSON = LOGS / f"gpu_vram_v3_{RUN_ID}.json"
OUT_LOG = LOGS / f"gpu_vram_v3_{RUN_ID}.log"
DUMP_PATH = LOGS / f"gpu_vram_v3_dump_{RUN_ID}.bin"
GDB_LOG = LOGS / f"gpu_vram_v3_gdb_{RUN_ID}.log"

SERVER = ROOT / "llama-cpp-build" / "build-cuda" / "bin" / "llama-server"
MODEL = Path("/home/elaref/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf")
PORT = 8093
CANARY = f"VRAM_CANARY_BAREMETAL_7777_{uuid.uuid4().hex[:8]}"

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

def wait_server(timeout=120):
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

def scan_dump(path, canary):
    nb = canary.encode()
    if not path.exists(): return -1, []
    data = path.read_bytes()
    hits = []
    i = 0
    while True:
        j = data.find(nb, i)
        if j < 0: break
        cs, ce = max(0, j - 32), min(len(data), j + len(nb) + 32)
        try:
            ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[cs:ce])
        except: ctx = "[decode-fail]"
        hits.append({"offset": j, "context": ctx})
        i = j + 1
    return len(hits), hits

def main():
    log(f"Gap 5 v3 VRAM probe, canary={CANARY}")
    vram_baseline = vram_used()
    log(f"baseline VRAM: {vram_baseline}")
    log("Phase 1: spawn llama-server as Python subprocess (child -> ptrace_scope=1 attach OK)")
    srv = subprocess.Popen(
        [str(SERVER), "--model", str(MODEL), "--host", "127.0.0.1", "--port", str(PORT),
         "--ctx-size", "2048", "--n-gpu-layers", "999", "--threads", "8", "--jinja",
         "--parallel", "1", "--cache-ram", "0"],
        stdout=open(LOGS / f"gpu_vram_v3_server_{RUN_ID}.log", "w"),
        stderr=subprocess.STDOUT,
    )
    log(f"  server pid {srv.pid}")
    if not wait_server(timeout=120):
        log("server failed to become healthy"); srv.kill(); return 1
    vram_after_load = vram_used()
    log(f"server healthy; VRAM after load: {vram_after_load}")
    log("Phase 2: send canary request")
    try:
        chat(CANARY); log("  canary chat done")
    except Exception as e:
        log(f"  chat err: {e}")
    vram_after_canary = vram_used()
    log(f"VRAM after canary: {vram_after_canary}")
    log("Phase 3: send benign 2nd request (slot release)")
    chat("benign-followup-" + uuid.uuid4().hex)
    vram_after_release = vram_used()
    log(f"VRAM after slot release: {vram_after_release}")
    log("Phase 4: cuda-gdb --pid (auto-answer prompts via stdin)")
    gdb_script = LOGS / f"gpu_vram_v3_gdb_cmds_{RUN_ID}.txt"
    gdb_script.write_text(f"""set pagination off
set print elements 0
set confirm off
set logging file {GDB_LOG}
set logging redirect on
set logging on
info cuda contexts
info cuda kernels
info cuda memory
set logging off
detach
quit
""")
    gdb_input = b"y\ny\ny\n"
    try:
        r = subprocess.run(
            ["cuda-gdb", "-batch", "-nx", "-p", str(srv.pid), "-x", str(gdb_script)],
            input=gdb_input, capture_output=True, timeout=120
        )
        log(f"  cuda-gdb --pid rc={r.returncode}")
        log(f"  stdout last 40 lines:\n" + "\n".join(r.stdout.decode("utf-8", "replace").splitlines()[-40:]))
        if r.stderr:
            log(f"  stderr last 10:\n" + "\n".join(r.stderr.decode("utf-8", "replace").splitlines()[-10:]))
        gdb_ok = r.returncode == 0
    except subprocess.TimeoutExpired:
        log("  cuda-gdb timeout")
        gdb_ok = False
    except Exception as e:
        log(f"  cuda-gdb failed: {e}")
        gdb_ok = False
    log("Phase 5: shutdown")
    srv.terminate()
    try: srv.wait(10)
    except: srv.kill()
    vram_after_shutdown = vram_used()
    log(f"VRAM after shutdown: {vram_after_shutdown}")
    dump_files = list(LOGS.glob(f"gpu_vram_v3_dump_{RUN_ID}*"))
    all_hits = 0
    hit_details = []
    for df in dump_files:
        h, hits = scan_dump(df, CANARY)
        all_hits += max(h, 0)
        hit_details.append({"file": str(df), "size": df.stat().st_size, "hits": h, "contexts": hits[:5]})
        log(f"  {df.name}: {h} canary hits (size={df.stat().st_size})")
    if GDB_LOG.exists():
        gb = GDB_LOG.read_text()
        gh, g_hits = scan_dump(GDB_LOG, CANARY)
        log(f"  GDB log size: {len(gb)} bytes; canary hits: {gh}")
        if gh > 0:
            all_hits += gh
            hit_details.append({"file": str(GDB_LOG), "size": len(gb), "hits": gh, "contexts": g_hits[:5]})
    with OUT_JSON.open("w") as f:
        json.dump({
            "run_id": RUN_ID, "pid": srv.pid, "canary": CANARY,
            "vram_baseline": vram_baseline,
            "vram_after_load": vram_after_load,
            "vram_after_canary": vram_after_canary,
            "vram_after_release": vram_after_release,
            "vram_after_shutdown": vram_after_shutdown,
            "cuda_gdb_attached": gdb_ok,
            "gdb_log": str(GDB_LOG),
            "dump_files": [str(f) for f in dump_files],
            "all_hits": all_hits, "hit_details": hit_details,
        }, f, indent=2)
    log(f"=== WROTE {OUT_JSON} ===  total canary hits: {all_hits}")

if __name__ == "__main__":
    sys.exit(main() or 0)