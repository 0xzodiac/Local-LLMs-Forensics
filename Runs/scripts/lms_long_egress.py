#!/usr/bin/env python3
# Phase B: long-duration egress monitoring. Start lms server, load model,
# send a fresh canary, then idle for N minutes while polling for any
# outbound connection attributable to llmster/llmworker/llama.cpp.
import json, os, re, socket, subprocess, sys, time, uuid
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/elaref/research")
LOGS = ROOT / "logs"
RUN_ID = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_JSON = LOGS / f"lms_long_egress_{RUN_ID}.json"
OUT_LOG = LOGS / f"lms_long_egress_{RUN_ID}.log"

PORT = 1234
DURATION_MIN = int(sys.argv[2]) if len(sys.argv) > 2 else 10
CANARY = f"LONG_TELEMETRY_TEST_{uuid.uuid4().hex[:8]}"

def log(x):
    msg = f"[{datetime.now().strftime('%H:%M:%S')}] {x}"
    print(msg, file=sys.stderr)
    with OUT_LOG.open("a") as f:
        f.write(msg + "\n")

def ps_lm_pids():
    try:
        r = subprocess.run(["ps", "-ef", "--no-headers"], capture_output=True, text=True, timeout=5)
        pids = set()
        for line in r.stdout.splitlines():
            parts = line.split(None, 7)
            if len(parts) < 8: continue
            cmdline = parts[7]
            if any(s in cmdline for s in
                   ("llmster", "llmworker", "liblmstudio_bindings", "llama.cpp")):
                try: pids.add(int(parts[1]))
                except: pass
        return pids
    except: return set()

def get_external_conns_for_pids(pids):
    if not pids: return []
    try:
        r = subprocess.run(
            ["ss", "-tunp", "( sport != :1234 and not src 127.0.0.1 )"],
            capture_output=True, text=True, timeout=5
        )
        out = []
        for line in r.stdout.splitlines()[1:]:
            matched = any(f"pid={p}" in line for p in pids)
            if not matched: continue
            parts = line.split()
            if len(parts) < 5: continue
            try:
                ip, port = parts[4].rsplit(":", 1)
                port_i = int(port)
            except: continue
            try: hostname = socket.gethostbyaddr(ip)[0]
            except: hostname = None
            out.append({
                "raw": line.strip(),
                "state": parts[1],
                "remote_ip": ip, "remote_port": port_i,
                "remote_hostname": hostname,
                "ts": time.time(),
            })
        return out
    except: return []

def main():
    log(f"Long-duration lms egress monitor, canary={CANARY}, duration={DURATION_MIN}min")
    subprocess.run(["lms", "server", "start"], capture_output=True, timeout=30)
    import urllib.request
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/v1/models", timeout=2)
            break
        except: time.sleep(1)
    r = subprocess.run(["lms", "load", "qwen/qwen3.5-9b", "--gpu", "off"],
                       capture_output=True, text=True, timeout=120)
    log(f"  model loaded rc={r.returncode}")
    for _ in range(20):
        pids = ps_lm_pids()
        if len(pids) >= 3: break
        time.sleep(1)
    pids = ps_lm_pids()
    log(f"  active LM Studio PIDs: {sorted(pids)}")
    body = json.dumps({
        "model": "qwen/qwen3.5-9b",
        "messages": [{"role": "user", "content":
            f"Note for the assistant. Canary (do not include): {CANARY}. Summarize in one short sentence."}],
        "max_tokens": 8, "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                                 body, {"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=180).read()
        log("  canary chat done")
    except Exception as e:
        log(f"  chat err: {e}")
    log_path = Path(f"/home/elaref/.lmstudio/server-logs/2026-06/2026-06-23.1.log")
    if log_path.exists():
        text = log_path.read_text(errors="replace")
        if CANARY in text:
            log(f"  canary written to disk log ({log_path})")
        else:
            log(f"  WARNING: canary NOT found in disk log")
    log(f"Phase 2: poll every 30s for {DURATION_MIN} minutes")
    snapshots = []
    deadline = time.time() + DURATION_MIN * 60
    while time.time() < deadline:
        pids_now = ps_lm_pids()
        conns = get_external_conns_for_pids(pids_now)
        snap = {"ts": time.time(), "pids": sorted(pids_now), "external_conns": conns}
        snapshots.append(snap)
        if conns:
            log(f"  EXTERNAL CONN DETECTED: {len(conns)} connections")
            for c in conns: log(f"    {c}")
        time.sleep(30)
    subprocess.run(["lms", "server", "stop"], capture_output=True, timeout=30)
    subprocess.run(["lms", "unload", "--all"], capture_output=True, timeout=30)
    total_conns = sum(len(s["external_conns"]) for s in snapshots)
    pids_seen = set()
    for s in snapshots: pids_seen.update(s["pids"])
    summary = {
        "run_id": RUN_ID, "canary": CANARY,
        "duration_min": DURATION_MIN,
        "snapshots_taken": len(snapshots),
        "pids_ever_seen": sorted(pids_seen),
        "total_external_conns_detected": total_conns,
        "any_external_conn_at_all": total_conns > 0,
    }
    with OUT_JSON.open("w") as f:
        json.dump({**summary, "snapshots": snapshots}, f, indent=2)
    log(f"=== WROTE {OUT_JSON} ===  total conns over {DURATION_MIN}min: {total_conns}")

if __name__ == "__main__":
    sys.exit(main() or 0)