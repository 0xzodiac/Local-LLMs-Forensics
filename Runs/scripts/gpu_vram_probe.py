#!/usr/bin/env python3
# Gap 5: VRAM cleartext probe.
# Method: start a CUDA-offloaded llama-server with a specific canary, send
# the request, then capture the VRAM contents and scan for the canary text.
#
# Two capture methods, both attempted:
#   1. cuda-gdb attach: command "dump cuda memory all <file>" reads back
#      all live device allocations via the CUDA debugger API.
#   2. Direct read of /dev/nvidia0 as a baseline probe.
import json, os, subprocess, sys, time, uuid
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/elaref/research")
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)
RUN_ID = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_JSON = LOGS / f"gpu_vram_{RUN_ID}.json"
OUT_LOG = LOGS / f"gpu_vram_{RUN_ID}.log"

SERVER = ROOT / "llama-cpp-build" / "build-cuda" / "bin" / "llama-server"
MODEL = Path("/home/elaref/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf")
PORT = 8095
CANARY = f"VRAM_CANARY_BAREMETAL_7777_{uuid.uuid4().hex[:8]}"
DUMP_PATH = LOGS / f"gpu_vram_dump_{RUN_ID}.bin"

def log(x):
    msg = f"[{datetime.now().strftime('%H:%M:%S')}] {x}"
    print(msg, file=sys.stderr)
    with OUT_LOG.open("a") as f:
        f.write(msg + "\n")

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

def vram_total_used():
    r = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.total",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=5
    )
    if not r.stdout.strip(): return None
    used, total = r.stdout.strip().split(",")
    return int(used), int(total)

def cuda_gdb_dump(pid, out_path):
    log(f"  cuda-gdb attach pid {pid}")
    gdb_cmd = (
        "set pagination off\n"
        "set print elements 0\n"
        f"attach {pid}\n"
        "info cuda contexts\n"
        "info cuda kernels\n"
        f"set logging file {out_path}.gdb.log\n"
        "set logging on\n"
        "info cuda memory\n"
        "set logging off\n"
        "detach\n"
        "quit\n"
    )
    gdb_script = LOGS / f"gdb_cmds_{RUN_ID}.txt"
    gdb_script.write_text(gdb_cmd)
    try:
        r = subprocess.run(
            ["cuda-gdb", "-batch", "-x", str(gdb_script), str(SERVER)],
            capture_output=True, text=True, timeout=120
        )
        log(f"  cuda-gdb exit={r.returncode}")
        log(f"  stdout last 40 lines:\n" + "\n".join(r.stdout.splitlines()[-40:]))
        if r.stderr:
            log(f"  stderr last 10:\n" + "\n".join(r.stderr.splitlines()[-10:]))
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        log("  cuda-gdb timed out after 120s")
        return False
    except Exception as e:
        log(f"  cuda-gdb failed: {e}")
        return False

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
    log(f"Gap 5 VRAM probe, canary={CANARY}")
    if not SERVER.exists():
        log(f"FATAL: {SERVER} not found -- CUDA build not complete?")
        return 1
    if not MODEL.exists():
        log(f"FATAL: {MODEL} not found"); return 1
    log("Phase 1: VRAM baseline (no server)")
    base = vram_total_used()
    log(f"  baseline VRAM: {base}")
    log("Phase 2: start server (CUDA, full offload)")
    srv = subprocess.Popen(
        [str(SERVER), "--model", str(MODEL), "--host", "127.0.0.1", "--port", str(PORT),
         "--ctx-size", "2048", "--n-gpu-layers", "999", "--threads", "8", "--jinja",
         "--parallel", "1", "--cache-ram", "0"],
        stdout=open(LOGS / f"gpu_vram_server_{RUN_ID}.log", "w"),
        stderr=subprocess.STDOUT
    )
    if not wait_server():
        log("server failed"); srv.kill(); return 1
    pid = find_pid()
    log(f"  server pid {pid}")
    time.sleep(3)
    after_load = vram_total_used()
    log(f"  VRAM after model load: {after_load}")
    log("Phase 3: send canary request")
    try:
        chat(CANARY); log("  canary request done")
    except Exception as e:
        log(f"  chat err: {e}")
    after_chat = vram_total_used()
    log(f"  VRAM after chat: {after_chat}")
    log("Phase 4: send benign 2nd request (triggers slot release)")
    chat("benign-followup-no-canary-" + uuid.uuid4().hex)
    after_release = vram_total_used()
    log(f"  VRAM after slot release: {after_release}")
    log("Phase 5: cuda-gdb attach + dump attempt")
    gdb_ok = cuda_gdb_dump(pid, DUMP_PATH)
    log("Phase 6: /dev/nvidia0 small read probe")
    nvidia_read = {"size_bytes": 0, "ok": False, "canary_count": 0}
    try:
        with open("/dev/nvidia0", "rb") as f:
            data = f.read(1 << 20)
        nvidia_read["size_bytes"] = len(data)
        nvidia_read["ok"] = True
        nvidia_read["canary_count"] = data.count(CANARY.encode())
        log(f"  /dev/nvidia0 1MB: {len(data)} bytes, canary hits: {nvidia_read['canary_count']}")
    except Exception as e:
        log(f"  /dev/nvidia0 read failed: {e}")
    log("Phase 7: shutdown")
    srv.terminate()
    try: srv.wait(10)
    except: srv.kill()
    after_shutdown = vram_total_used()
    log(f"  VRAM after shutdown: {after_shutdown}")
    log("Phase 8: scan dump for canary")
    if DUMP_PATH.exists():
        h, hits = scan_dump(DUMP_PATH, CANARY)
        log(f"  dump size: {DUMP_PATH.stat().st_size} bytes, canary hits: {h}")
    else:
        h, hits = -1, []
    with OUT_JSON.open("w") as f:
        json.dump({
            "run_id": RUN_ID, "pid": pid, "canary": CANARY,
            "vram_baseline": base, "vram_after_load": after_load,
            "vram_after_chat": after_chat, "vram_after_release": after_release,
            "vram_after_shutdown": after_shutdown,
            "cuda_gdb_ok": gdb_ok, "dump_path": str(DUMP_PATH),
            "dump_size": DUMP_PATH.stat().st_size if DUMP_PATH.exists() else 0,
            "dump_canary_hits": h, "dump_hit_contexts": hits[:10],
            "nvidia_read": nvidia_read,
        }, f, indent=2)
    log(f"=== WROTE {OUT_JSON} ===")
    log(f"=== canary hits in dump: {h} ===")

if __name__ == "__main__":
    sys.exit(main() or 0)
