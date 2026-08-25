#!/usr/bin/env python3
"""Hidden-secrets iteration 2 v2: live network egress probe.
Monitors TCP connections in real-time during inference to detect
any external connections created by llama-server."""
import os, sys, time, json, subprocess, urllib.request, threading
from pathlib import Path

ROOT = Path("/home/sharks/research")
SERVER = ROOT / "llama-monitor/build/llama.cpp/bin/llama-server"
MODEL = ROOT / "logs/ultimate/models/gemma4.gguf"
PORT = 8080
OUT = ROOT / "logs/egress_iter2_live.json"
LOG_FILE = ROOT / "logs/egress_iter2_live.log"

def log(x):
    print(f"[{time.strftime('%H:%M:%S')}] {x}")

def get_ext_connections():
    """Return set of (ip, port) for non-loopback TCP connections with process info."""
    conns = set()
    try:
        r = subprocess.run(["ss", "-tunp"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.strip().split("\n")[1:]:
            parts = line.strip().split()
            if len(parts) < 5: continue
            remote = parts[4]
            ip, port = remote.rsplit(":", 1)
            if ip != "127.0.0.1" and not ip.startswith("127."):
                # Extract process name from ss output
                proc = ""
                for chunk in parts:
                    if chunk.startswith('users:'):
                        import re
                        m = re.search(r'"([^"]+)"', chunk)
                        if m: proc = m.group(1)
                conns.add((ip, int(port), proc))
    except: pass
    try:
        with open("/proc/net/tcp") as f:
            for line in f.readlines()[1:]:
                parts = line.strip().split()
                if len(parts) < 4: continue
                raddr = parts[2]
                if raddr in ("00000000:0000", "0100007F:0000"): continue
                if raddr.startswith("0100007F:"): continue
                ip_hex, port_hex = raddr.split(":")
                ip_bytes = bytes.fromhex(ip_hex)
                ip = f"{ip_bytes[3]}.{ip_bytes[2]}.{ip_bytes[1]}.{ip_bytes[0]}"
                port = int(port_hex, 16)
                if ip != "127.0.0.1":
                    # Check if already added
                    if not any(c[0]==ip and c[1]==port for c in conns):
                        conns.add((ip, port, "/proc/net/tcp"))
    except: pass
    return conns

def start_server():
    return subprocess.Popen(
        [str(SERVER), "--model", str(MODEL), "--host", "127.0.0.1",
         "--port", str(PORT), "--ctx-size", "4096", "--n-gpu-layers", "0",
         "--threads", "16", "--jinja"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

def wait_server(timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2)
            return True
        except: time.sleep(1)
    return False

def load_model(server_model):
    """Send a warm-up request to ensure model is loaded."""
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

# Run probe
log("Starting server...")
proc = start_server()
if not wait_server():
    log("FAILED: server start")
    sys.exit(1)
log("Server up")

try:
    # Warm up
    log("Warming model...")
    load_model(proc)
    
    # Baseline: connections before any inference-related activity
    time.sleep(1)
    baseline = get_ext_connections()
    log(f"Baseline external connections: {len(baseline)}")
    for c in sorted(baseline, key=lambda x: f"{x[0]}:{x[1]}"):
        log(f"  {c[0]}:{c[1]} ({c[2]})")
    
    # Start monitoring thread: check every 0.5s during inference
    monitor_data = []
    def monitor():
        while True:
            monitor_data.append(get_ext_connections())
            time.sleep(0.5)
    
    m_thread = threading.Thread(target=monitor, daemon=True)
    m_thread.start()
    
    log("Sending inference request...")
    start = time.time()
    result = send_inference()
    elapsed = time.time() - start
    content = result["choices"][0]["message"]["content"]
    log(f"Inference done ({elapsed:.1f}s): {content}")
    
    # Stop monitoring
    time.sleep(1)
    post_inference = get_ext_connections()
    log(f"Post-inference external connections: {len(post_inference)}")
    for c in sorted(post_inference, key=lambda x: f"{x[0]}:{x[1]}"):
        log(f"  {c[0]}:{c[1]} ({c[2]})")
    
    # Compare
    baseline_simple = {(c[0], c[1]) for c in baseline}
    new_connections = set()
    for phase_data in [monitor_data, [post_inference]]:
        if isinstance(phase_data, list):
            for snapshot in phase_data:
                for c in snapshot:
                    if (c[0], c[1]) not in baseline_simple:
                        new_connections.add((c[0], c[1], c[2]))
        else:
            for c in phase_data:
                if (c[0], c[1]) not in baseline_simple:
                    new_connections.add((c[0], c[1], phase_data))
    
    # Exclude known ambient connections (opencode, etc.)
    ambient_processes = {"opencode", "python3", "bash", "ss", "node"}
    real_new = {c for c in new_connections if c[2].lower() not in ambient_processes}
    
    log(f"\nNew connections: {len(new_connections)}")
    for c in new_connections:
        log(f"  {c[0]}:{c[1]} ({c[2]}) {'⚠️' if c[2].lower() not in ambient_processes else '(ambient)'}")
    
    results = {
        "iteration": "iteration-2",
        "pass": True,
        "score": 0.0,
        "probe": "network-egress-live",
        "finding": "",
        "baseline": [f"{c[0]}:{c[1]}({c[2]})" for c in baseline],
        "new_connections": [f"{c[0]}:{c[1]}({c[2]})" for c in new_connections],
        "new_connections_filtered": [f"{c[0]}:{c[1]}({c[2]})" for c in real_new],
        "phone_home": len(real_new) > 0,
        "inference_time_s": round(elapsed, 1),
        "inference_response": content,
        "loopback_only": len(real_new) == 0
    }
    
    if real_new:
        results["finding"] = f"External connections appeared during inference NOT from ambient processes: {real_new}"
        results["score"] = 0.7
    else:
        results["finding"] = "No external connections created by llama-server during inference. All observed connections are ambient (opencode/python3)."
    
    log(json.dumps(results, indent=2))
    with open(OUT, "w") as f:
        json.dump(results, f, indent=2)
    log(f"Results saved to {OUT}")

finally:
    proc.terminate()
    try: proc.wait(timeout=10)
    except: proc.kill()
    log("Server stopped")
