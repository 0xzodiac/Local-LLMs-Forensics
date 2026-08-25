#!/usr/bin/env python3
# Mission: prove local LLMs leak data to providers.
# Method: spin up LM Studio's server via lms, send a canary request,
# then poll (a) ss -tunp for the server PID's external connections,
# (b) strace on the lms-server PID for every connect() syscall +
# write() to a non-loopback socket. Repeat for the underlying
# llama-server worker process (child).
import json, os, re, socket, subprocess, sys, time, uuid
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/elaref/research")
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)
RUN_ID = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_JSON = LOGS / f"lms_egress_{RUN_ID}.json"
OUT_LOG = LOGS / f"lms_egress_{RUN_ID}.log"
STRACE_OUT = LOGS / f"lms_strace_{RUN_ID}.log"

PORT = 1234
CANARY = f"PROVIDER_LEAK_TEST_{uuid.uuid4().hex[:12]}"

def log(x):
    msg = f"[{datetime.now().strftime('%H:%M:%S')}] {x}"
    print(msg, file=sys.stderr)
    with OUT_LOG.open("a") as f:
        f.write(msg + "\n")

def get_ext_conns(pids):
    pids = set(pids)
    if not pids: return []
    try:
        r = subprocess.run(
            ["ss", "-tunp", "( sport != :1234 and not src 127.0.0.1 )"],
            capture_output=True, text=True, timeout=5
        )
        out = []
        for line in r.stdout.splitlines()[1:]:
            matched = False
            for pid in pids:
                if f"pid={pid}" in line:
                    matched = True; break
            if not matched: continue
            parts = line.split()
            if len(parts) < 5: continue
            remote = parts[4]
            try:
                ip, port = remote.rsplit(":", 1)
                port_i = int(port)
            except: continue
            try: hostname = socket.gethostbyaddr(ip)[0]
            except: hostname = None
            out.append({
                "raw": line.strip(),
                "state": parts[1],
                "remote_ip": ip, "remote_port": port_i,
                "remote_hostname": hostname,
            })
        return out
    except Exception as e:
        return [{"err": str(e)}]

def find_pids_by_pattern(pattern):
    """Accept a pipe-separated alternation OR a plain substring. Use ps -ef
    rather than pgrep -f to avoid regex / shell-escape pitfalls."""
    alternatives = pattern.split("|")
    r = subprocess.run(["ps", "-ef", "--no-headers"], capture_output=True, text=True)
    pids = []
    seen = set()
    for line in r.stdout.splitlines():
        parts = line.split(None, 7)
        if len(parts) < 8: continue
        try: pid = int(parts[1])
        except: continue
        if pid in seen: continue
        cmdline = parts[7]
        if any(alt in cmdline for alt in alternatives):
            pids.append(pid); seen.add(pid)
    return pids

def start_lms_server():
    r = subprocess.run(["lms", "server", "start"], capture_output=True, text=True, timeout=30)
    log(f"lms server start rc={r.returncode}")
    if r.stdout.strip(): log(f"  stdout: {r.stdout.strip()[:200]}")
    if r.stderr.strip(): log(f"  stderr: {r.stderr.strip()[:200]}")
    return r.returncode == 0

def load_model(model_key, timeout=180):
    log(f"loading model {model_key}...")
    r = subprocess.run(["lms", "load", model_key, "--gpu", "off"],
                       capture_output=True, text=True, timeout=timeout)
    log(f"lms load rc={r.returncode}")
    if r.stdout.strip(): log(f"  stdout: {r.stdout.strip()[:200]}")
    if r.stderr.strip(): log(f"  stderr: {r.stderr.strip()[:400]}")
    return r.returncode == 0

def stop_lms_server():
    subprocess.run(["lms", "server", "stop"], capture_output=True, text=True, timeout=30)

def wait_server(timeout=120):
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/v1/models", timeout=2)
            return True
        except: time.sleep(1)
    return False

def chat(canary):
    import urllib.request
    body = json.dumps({
        "model": "local",
        "messages": [{"role": "user", "content":
            f"Note: {canary}. Summarize in one short sentence."}],
        "max_tokens": 16, "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                                 body, {"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=180).read()

def scan_strace_for_canary(canary):
    if not STRACE_OUT.exists(): return {"matches": 0, "summary": "no strace log"}
    data = STRACE_OUT.read_text(errors="replace")
    nb = canary.encode()
    lines = data.splitlines()
    hits = []
    for line in lines:
        if nb in line.encode():
            hits.append(line.strip()[:240])
    connect_lines = [l for l in lines if "connect(" in l and not ("127.0.0.1" in l or "::1" in l)]
    write_lines = [l for l in lines if re.search(r"sendto\(.*[1-9][0-9]{2,}", l) or re.search(r"write\(.*[1-9][0-9]{3,}", l)]
    return {
        "strace_log_bytes": len(data),
        "strace_log_lines": len(lines),
        "canary_line_hits": len(hits),
        "sample_canary_lines": hits[:10],
        "external_connect_calls": len(connect_lines),
        "sample_connect_lines": connect_lines[:10],
        "large_write_calls": len(write_lines),
        "sample_write_lines": write_lines[:5],
    }

def main():
    log(f"Mission: local-LLM provider leak proof. canary={CANARY}")
    log("Phase 0: baseline conn state")
    baseline = get_ext_conns([])
    log(f"  baseline external conn count: {len(baseline)}")
    log("Phase 1: start LM Studio server")
    if not start_lms_server():
        log("FATAL: lms server start failed"); return 1
    if not wait_server(timeout=120):
        log("server never healthy"); stop_lms_server(); return 1
    if not load_model("qwen/qwen3.5-9b", timeout=240):
        log("FATAL: model load failed"); stop_lms_server(); return 1
    pids_lms = find_pids_by_pattern("llmster|llmworker|liblmstudio|llama.cpp")
    log(f"  LM Studio server PIDs (immediately): {pids_lms}")
    # wait for the worker processes to spawn (llmster + systemresourcesworker + llmworker minimum 3)
    for _ in range(15):
        time.sleep(1)
        pids_lms = find_pids_by_pattern("llmster|llmworker|liblmstudio|llama.cpp")
        if len(pids_lms) >= 3: break
    log(f"  LM Studio server PIDs (after wait): {pids_lms}")
    time.sleep(2)
    idle_conns = get_ext_conns(pids_lms)
    log(f"Phase 2: idle conns after load: {len(idle_conns)}")
    for c in idle_conns[:10]: log(f"  {c}")
    strace_pid = pids_lms[0] if pids_lms else None
    strace_proc = None
    if strace_pid:
        log(f"Phase 3: strace attach pid {strace_pid}")
        strace_cmd = ["strace", "-f", "-p", str(strace_pid),
                      "-e", "trace=connect,sendto,write",
                      "-o", str(STRACE_OUT)]
        strace_proc = subprocess.Popen(strace_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    log("Phase 4: send canary request")
    try:
        chat(CANARY); log("  chat done")
    except Exception as e:
        log(f"  chat err: {e}")
    post_chat_conns = get_ext_conns(pids_lms)
    log(f"  conns after chat: {len(post_chat_conns)}")
    for c in post_chat_conns[:10]: log(f"  {c}")
    log("Phase 5: 30s post-chat, capture any telemetry beacon")
    time.sleep(30)
    post_idle_conns = get_ext_conns(pids_lms)
    log(f"  conns 30s post-chat: {len(post_idle_conns)}")
    for c in post_idle_conns[:10]: log(f"  {c}")
    log("Phase 6: shutdown")
    if strace_proc:
        strace_proc.terminate()
        try: strace_proc.wait(5)
        except: strace_proc.kill()
    stop_lms_server()
    log("Phase 7: scan strace log")
    strace_result = scan_strace_for_canary(CANARY)
    log(f"  strace log: {strace_result.get('strace_log_bytes', 0)} bytes, "
        f"{strace_result.get('canary_line_hits', 0)} canary hits, "
        f"{strace_result.get('external_connect_calls', 0)} external connect() calls, "
        f"{strace_result.get('large_write_calls', 0)} large writes")
    with OUT_JSON.open("w") as f:
        json.dump({
            "run_id": RUN_ID, "canary": CANARY,
            "pids_lms": pids_lms, "strace_pid": strace_pid,
            "baseline_external_conns": len(baseline),
            "idle_after_load_conns": idle_conns,
            "post_chat_conns": post_chat_conns,
            "post_idle_conns": post_idle_conns,
            "strace": strace_result,
        }, f, indent=2)
    log(f"=== WROTE {OUT_JSON} ===")

if __name__ == "__main__":
    sys.exit(main() or 0)