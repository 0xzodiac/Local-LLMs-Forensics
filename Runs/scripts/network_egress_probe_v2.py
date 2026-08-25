#!/usr/bin/env python3
"""Iteration 2b: PID-attributed network egress probe.
Captures all TCP connections before/during/after inference,
filtered by llama-server PID, plus tcpdump for packet-level evidence."""
import os, sys, time, json, subprocess, urllib.request, threading, signal
from pathlib import Path

ROOT = Path("/home/sharks/research")
SERVER = ROOT / "llama-monitor/build/llama.cpp/bin/llama-server"
MODEL = ROOT / "logs/ultimate/models/gemma4.gguf"
PORT = 8080
OUT = ROOT / "logs/egress_iter2b_live.json"
LOG_FILE = ROOT / "logs/egress_iter2b_live.log"
PCAP = "/tmp/egress_iter2b.pcap"
PCAP_BASELINE = "/tmp/egress_iter2b_baseline.pcap"

def log(x):
    print(f"[{time.strftime('%H:%M:%S')}] {x}")

def get_connections_for_pid(pid):
    """Return set of (ip, port, state) for a given PID from ss."""
    conns = set()
    try:
        r = subprocess.run(
            ["ss", "-tunp", "src", "!=127.0.0.1"],
            capture_output=True, text=True, timeout=5
        )
        for line in r.stdout.strip().split("\n")[1:]:
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            # Check if this line matches our PID
            line_str = " ".join(parts)
            if f"pid={pid}" not in line_str:
                continue
            remote = parts[4]
            ip, port = remote.rsplit(":", 1)
            state = parts[1] if len(parts) > 1 else "?"
            conns.add((ip, int(port), state))
    except Exception as e:
        log(f"ss error: {e}")
    return conns

def start_server():
    proc = subprocess.Popen(
        [str(SERVER), "--model", str(MODEL), "--host", "127.0.0.1",
         "--port", str(PORT), "--ctx-size", "4096", "--n-gpu-layers", "0",
         "--threads", "16", "--jinja"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return proc

def wait_server(timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2)
            return True
        except:
            time.sleep(1)
    return False

def send_inference():
    payload = json.dumps({
        "messages": [{"role": "user", "content": "Say the word hello"}],
        "max_tokens": 5, "temperature": 0.0
    }).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/v1/chat/completions",
        data=payload, headers={"Content-Type": "application/json"}
    )
    return json.loads(urllib.request.urlopen(req, timeout=120).read())

# Check tools
log("tcpdump unavailable (no sudo) - using ss PID filtering")

# Phase 1: 30-second ambient baseline
log("Phase 1: 30s ambient baseline...")
ambient_conns_thread = []
def sample_ambient():
    for i in range(15):
        try:
            r = subprocess.run(
                ["ss", "-tunp", "src", "!=127.0.0.1"],
                capture_output=True, text=True, timeout=5
            )
            conns = set()
            for line in r.stdout.strip().split("\n")[1:]:
                parts = line.strip().split()
                if len(parts) >= 5:
                    remote = parts[4]
                    ip, port = remote.rsplit(":", 1)
                    proc_name = ""
                    for chunk in parts:
                        if chunk.startswith("users:"):
                            import re
                            m = re.search(r'"([^"]+)"', chunk)
                            if m:
                                proc_name = m.group(1)
                    conns.add((ip, int(port), proc_name))
            ambient_conns_thread.append(conns)
        except:
            pass
        time.sleep(2)
    log(f"Baseline done: {len(ambient_conns_thread)} snapshots")

sample_ambient()

# Phase 2: Start server
log("Phase 2: Starting llama-server...")
proc = start_server()
server_pid = proc.pid
log(f"Server PID: {server_pid}")

if not wait_server():
    log("FAILED: server start")
    if tcpdump_proc:
        tcpdump_proc.terminate()
    sys.exit(1)
log("Server up")

# Check server connections (should be only 127.0.0.1)
server_conns = get_connections_for_pid(server_pid)
log(f"Server connections (pre-inference): {server_conns if server_conns else 'none (expected - loopback only)'}")

# Phase 3: Warmup
log("Warming model...")
payload = json.dumps({
    "messages": [{"role": "user", "content": "Say hi"}],
    "max_tokens": 2, "temperature": 0.0
}).encode()
req = urllib.request.Request(
    f"http://127.0.0.1:{PORT}/v1/chat/completions",
    data=payload, headers={"Content-Type": "application/json"}
)
urllib.request.urlopen(req, timeout=180)
log("Model warmed up")

# Check server connections after warmup
post_warmup_conns = get_connections_for_pid(server_pid)
log(f"Server connections (post-warmup): {post_warmup_conns if post_warmup_conns else 'none'}")
time.sleep(2)

# Phase 4: Inference
log("Phase 4: Inference request...")
infoconns = []
def sample_inference():
    for i in range(10):
        conns = get_connections_for_pid(server_pid)
        infoconns.append(conns)
        time.sleep(0.5)

infothread = threading.Thread(target=sample_inference, daemon=True)
infothread.start()

start = time.time()
result = send_inference()
elapsed = time.time() - start
content = result["choices"][0]["message"]["content"]
log(f"Inference done ({elapsed:.1f}s): {content}")

time.sleep(2)
infothread.join(timeout=3)

# Post-inference check
post_infoconns = get_connections_for_pid(server_pid)
log(f"Server connections (post-inference): {post_infoconns if post_infoconns else 'none'}")

# Compile all server connections seen
all_server_conns = set()
for snapshot in [server_conns, post_warmup_conns] + infoconns + [post_infoconns]:
    for c in snapshot:
        all_server_conns.add(c)

# Any external (non-loopback)
external_server_conns = {c for c in all_server_conns if not c[0].startswith("127.") and c[0] != "::1"}

# Results
results = {
    "iteration": "iteration-2b",
    "pass": False,
    "score": 0.0,
    "probe": "network-egress-pid-attributed",
    "finding": "",
    "server_pid": server_pid,
    "server_external_connections": [f"{c[0]}:{c[1]}({c[2]})" for c in sorted(external_server_conns)],
    "all_server_connections": [f"{c[0]}:{c[1]}({c[2]})" for c in sorted(all_server_conns)],
    "inference_time_s": round(elapsed, 1),
    "inference_response": content,
    "ambient_snapshots": len(ambient_conns_thread)
}

if external_server_conns:
    results["finding"] = f"llama-server (PID {server_pid}) has external connections: {external_server_conns}"
    results["score"] = 0.7
    results["pass"] = True
else:
    results["finding"] = f"llama-server (PID {server_pid}) has ZERO non-loopback connections before/during/after inference. All listening/inference on 127.0.0.1. No phone-home detected."

log(json.dumps(results, indent=2))
with open(OUT, "w") as f:
    json.dump(results, f, indent=2)

with open(OUT, "w") as f:
    json.dump(results, f, indent=2)
log(f"Results saved to {OUT}")

# Cleanup
proc.terminate()
try:
    proc.wait(timeout=10)
except:
    proc.kill()
log("Done")
