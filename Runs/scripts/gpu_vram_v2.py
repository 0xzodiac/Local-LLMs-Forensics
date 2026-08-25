#!/usr/bin/env python3
# Gap 5 v2: VRAM probe with cuda-gdb as parent (so ptrace_scope=1 lets it
# attach to the spawned llama-server child).
import json, subprocess, sys, time, uuid
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/elaref/research")
LOGS = ROOT / "logs"
RUN_ID = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_JSON = LOGS / f"gpu_vram_v2_{RUN_ID}.json"
OUT_LOG = LOGS / f"gpu_vram_v2_{RUN_ID}.log"
DUMP_PATH = LOGS / f"gpu_vram_v2_dump_{RUN_ID}.bin"
GDB_LOG = LOGS / f"gpu_vram_v2_gdb_{RUN_ID}.log"

SERVER = ROOT / "llama-cpp-build" / "build-cuda" / "bin" / "llama-server"
MODEL = Path("/home/elaref/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf")
PORT = 8094
CANARY = f"VRAM_CANARY_BAREMETAL_7777_{uuid.uuid4().hex[:8]}"

def log(x):
    msg = f"[{datetime.now().strftime('%H:%M:%S')}] {x}"
    print(msg, file=sys.stderr)
    with OUT_LOG.open("a") as f:
        f.write(msg + "\n")

def vram_total_used():
    r = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.total",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=5
    )
    if not r.stdout.strip(): return None
    used, total = r.stdout.strip().split(",")
    return int(used), int(total)

def wait_server(timeout=300):
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
    log(f"Gap 5 v2 VRAM probe, canary={CANARY}")
    log(f"baseline VRAM: {vram_total_used()}")
    # Build a gdb script: spawn server, sleep, dump cuda memory
    gdb_script_content = f"""
set pagination off
set print elements 0
set logging file {GDB_LOG}
set logging on
file {SERVER}
set args --model {MODEL} --host 127.0.0.1 --port {PORT} --ctx-size 2048 --n-gpu-layers 999 --threads 8 --jinja --parallel 1 --cache-ram 0
run
info cuda contexts
info cuda kernels
info cuda memory
shell sleep 60
shell curl -s http://127.0.0.1:{PORT}/health > /dev/null && echo "healthy" || echo "not-yet"
shell sleep 5
shell sleep 30
info cuda memory
detach
quit
"""
    gdb_script_path = LOGS / f"gpu_vram_v2_gdbscript_{RUN_ID}.txt"
    gdb_script_path.write_text(gdb_script_content)
    log(f"spawning cuda-gdb (parent of llama-server child)")
    gdb_proc = subprocess.Popen(
        ["cuda-gdb", "-batch", "-x", str(gdb_script_path)],
        stdout=open(LOGS / f"gpu_vram_v2_gdb_stdout_{RUN_ID}.log", "w"),
        stderr=subprocess.STDOUT
    )
    log(f"  cuda-gdb pid {gdb_proc.pid}")
    log("waiting for server under cuda-gdb (slower than usual)")
    if not wait_server(timeout=300):
        log("server never became healthy under gdb")
        gdb_proc.kill()
        return 1
    log(f"server healthy; VRAM after model load: {vram_total_used()}")
    log("send canary request")
    try:
        chat(CANARY); log("  canary chat done")
    except Exception as e:
        log(f"  chat err: {e}")
    log(f"VRAM after canary: {vram_total_used()}")
    log("send 2nd benign request (slot release)")
    chat("benign-followup-" + uuid.uuid4().hex)
    log(f"VRAM after slot release: {vram_total_used()}")
    log("waiting up to 120s for cuda-gdb to dump & exit")
    try:
        gdb_proc.wait(timeout=120)
        log(f"  cuda-gdb exited rc={gdb_proc.returncode}")
    except subprocess.TimeoutExpired:
        log("  cuda-gdb timeout, killing")
        gdb_proc.kill()
    dump_files = list(LOGS.glob(f"gpu_vram_v2_dump_{RUN_ID}*"))
    log(f"  dump files: {[str(f) for f in dump_files]}")
    all_hits = 0
    for df in dump_files:
        h, _ = scan_dump(df, CANARY)
        all_hits += max(h, 0)
        log(f"  {df.name}: {h} canary hits (size={df.stat().st_size})")
    with OUT_JSON.open("w") as f:
        json.dump({
            "run_id": RUN_ID, "canary": CANARY,
            "gdb_log_path": str(GDB_LOG),
            "dump_files": [str(f) for f in dump_files],
            "total_canary_hits": all_hits,
            "vram_final": vram_total_used(),
        }, f, indent=2)
    log(f"=== WROTE {OUT_JSON} ===  total canary hits: {all_hits}")

if __name__ == "__main__":
    sys.exit(main() or 0)
