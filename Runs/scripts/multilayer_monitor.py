#!/usr/bin/env python3
# Track F+: multi-layer monitor for llama-server.
# Simultaneous layers:
#   1. Network: ss -tunp PID-filtered conn snapshots + per-event connection log.
#   2. /proc/<pid>/maps page-table walk every 2s, tracking the writable-region
#      address space (heap size, mmap growth, [.gguf]-backed regions).
#   3. eBPF (bpftrace) kernel-level: tracepoint on sys_enter_read for any
#      read() with byte count >= 1MB (matches /proc/<pid>/mem scans by an
#      A1 adversary). Captures PID, comm, fd, bytes-requested.
#   4. Canary cross-tenant: 3 sequential canary requests, scan /proc/<pid>/mem
#      after each release, count residual canary copies at each layer.
#
# Output:
#   logs/multilayer_monitor_<run>.json (per-second snapshots)
#   logs/multilayer_monitor_<run>.log  (human-readable timeline)
#   logs/multilayer_monitor_<run>.bpf.log (bpftrace output)
import json, os, subprocess, sys, time, uuid
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/elaref/research")
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)
RUN_ID = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_JSON = LOGS / f"multilayer_monitor_{RUN_ID}.json"
OUT_LOG = LOGS / f"multilayer_monitor_{RUN_ID}.log"
BPF_LOG = LOGS / f"multilayer_monitor_{RUN_ID}.bpf.log"

SERVER = ROOT / "llama-cpp-build" / "build" / "bin" / "llama-server"
MODEL = Path("/home/elaref/.lmstudio/models/lmstudio-community/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf")
PORT = 8097

def log(x):
    msg = f"[{datetime.now().strftime('%H:%M:%S')}] {x}"
    print(msg, file=sys.stderr)
    with OUT_LOG.open("a") as f:
        f.write(msg + "\n")

def find_pid():
    r = subprocess.run(["pgrep", "-f", "bin/llama-server"], capture_output=True, text=True)
    pids = [int(p) for p in r.stdout.strip().split() if p.strip()]
    return pids[0] if pids else None

def ss_conns(pid):
    try:
        r = subprocess.run(
            ["ss", "-tunp", "src", "!=127.0.0.1"],
            capture_output=True, text=True, timeout=5
        )
        out = []
        for line in r.stdout.splitlines()[1:]:
            if f"pid={pid}" in line:
                parts = line.split()
                if len(parts) >= 5:
                    out.append({"remote": parts[4], "state": parts[1]})
        return out
    except Exception as e:
        return [{"error": str(e)}]

def walk_maps(pid):
    try:
        rss_kb = 0; rw_regions = []; anon_kb = 0; mmap_kb = 0
        with open(f"/proc/{pid}/maps") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 2: continue
                rng, perms = parts[0], parts[1]
                path = parts[5] if len(parts) >= 6 else ""
                lo, hi = (int(x, 16) for x in rng.split("-"))
                size = (hi - lo) // 1024
                if "r" in perms: rss_kb += size
                if "w" in perms: rw_regions.append({"range": rng, "size_kb": size, "perms": perms, "path": path or "[anon]"})
                if path.endswith(".gguf"): mmap_kb += size
                elif path == "[heap]" or "[anon" in path or path == "[stack]": anon_kb += size
        return {
            "rss_kb": rss_kb,
            "writable_count": len(rw_regions),
            "writable_total_kb": sum(r["size_kb"] for r in rw_regions),
            "anon_kb": anon_kb, "mmap_kb": mmap_kb,
            "writable_top10": sorted(rw_regions, key=lambda x: -x["size_kb"])[:10],
        }
    except Exception as e:
        return {"error": str(e)}

def scan_mem_canary(pid, needle):
    nb = needle.encode()
    hits, regions, scanned = 0, [], 0
    try:
        with open(f"/proc/{pid}/maps") as f:
            maps = f.read().splitlines()
        with open(f"/proc/{pid}/mem", "rb", 0) as mem:
            for line in maps:
                parts = line.split()
                if len(parts) < 2: continue
                rng, perms = parts[0], parts[1]
                path = parts[5] if len(parts) >= 6 else ""
                if "w" not in perms or path.endswith(".gguf"): continue
                lo, hi = (int(x, 16) for x in rng.split("-"))
                size = hi - lo
                if size <= 0 or size > (2 << 30): continue
                try: mem.seek(lo); buf = mem.read(size)
                except (OSError, OverflowError): continue
                scanned += len(buf)
                c = buf.count(nb)
                if c:
                    hits += c
                    regions.append(f"{rng} {perms} {path or '[anon]'} x{c}")
    except Exception as e:
        return -1, [f"err: {e}"], 0
    return hits, regions, scanned

def start_bpf(log_path):
    bpf = 'tracepoint:syscalls:sys_enter_read / (uint64)arg2 >= (uint64)(1<<20) / { printf("BPF_BIG_READ pid=%d comm=%s fd=%d bytes=%d\\n", pid, comm, arg0, arg2); }'
    try:
        return subprocess.Popen(
            ["bpftrace", "-e", bpf],
            stdout=open(log_path, "w"), stderr=subprocess.STDOUT
        )
    except Exception as e:
        log(f"bpftrace start failed: {e}"); return None

def start_server():
    return subprocess.Popen(
        [str(SERVER), "--model", str(MODEL), "--host", "127.0.0.1", "--port", str(PORT),
         "--ctx-size", "2048", "--n-gpu-layers", "0", "--threads", "8", "--jinja",
         "--parallel", "1", "--cache-ram", "0"],
        stdout=open(LOGS / f"multilayer_server_{RUN_ID}.log", "w"),
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
    snapshots = []
    log("Phase 1: ambient (no server)")
    snapshots.append({"ts": time.time(), "phase": "ambient", "ss": ss_conns(0), "maps": {}, "canary": None})
    log("Phase 2: start server")
    srv = start_server()
    if not wait_server():
        log("server failed to come up"); return 1
    pid = find_pid()
    if not pid:
        log("could not find server PID"); srv.kill(); return 1
    log(f"server pid {pid}")
    log("Phase 3: start bpftrace")
    bpf_proc = start_bpf(BPF_LOG)
    time.sleep(2)
    log("Phase 4: post-startup baseline")
    for i in range(3):
        snapshots.append({"ts": time.time(), "phase": "post-startup",
                          "ss": ss_conns(pid), "maps": walk_maps(pid)})
        time.sleep(1)
    log("Phase 5: canary cross-tenant test")
    canary_results = []
    for t in range(3):
        c = uuid.uuid4().hex
        log(f"  tenant {t+1}: canary={c}")
        try: chat(c)
        except Exception as e: log(f"  chat err: {e}")
        h, regs, scanned = scan_mem_canary(pid, c)
        log(f"  post-release scan: canary occurrences={h}")
        canary_results.append({"canary": c, "post_release_hits": h, "post_release_regions": regs[:6]})
        snapshots.append({"ts": time.time(), "phase": f"tenant_{t+1}_post_release",
                          "ss": ss_conns(pid), "maps": walk_maps(pid),
                          "canary": {"id": c, "hits": h, "scanned_mb": scanned//(1<<20)}})
        time.sleep(2)
    log("Phase 6: 10s idle")
    for i in range(5):
        snapshots.append({"ts": time.time(), "phase": "idle",
                          "ss": ss_conns(pid), "maps": walk_maps(pid)})
        time.sleep(2)
    log("Phase 7: shutdown")
    if bpf_proc: bpf_proc.terminate()
    srv.terminate()
    try: srv.wait(10)
    except: srv.kill()
    bpf_lines = BPF_LOG.read_text().splitlines() if BPF_LOG.exists() else []
    bpf_big_reads = [l for l in bpf_lines if "BPF_BIG_READ" in l]
    log(f"  bpftrace captured {len(bpf_big_reads)} big-read events")
    with OUT_JSON.open("w") as f:
        json.dump({"run_id": RUN_ID, "pid": pid, "port": PORT,
                   "snapshots": snapshots, "canary_results": canary_results,
                   "bpf_big_reads": bpf_big_reads}, f, indent=2)
    log(f"=== WROTE {OUT_JSON} ===")
    log(f"=== canary: {[(r['canary'][:8], r['post_release_hits']) for r in canary_results]} ===")
    log(f"=== bpf big-reads: {len(bpf_big_reads)} ===")

if __name__ == "__main__":
    sys.exit(main() or 0)
