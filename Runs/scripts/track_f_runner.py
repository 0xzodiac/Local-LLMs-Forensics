#!/usr/bin/env python3
"""Track F: must-retest batch items (2)+(3) — adapted for this box's CPU backend."""
import os, sys, time, json, re, subprocess, urllib.request, uuid
from pathlib import Path

ROOT = Path("/home/elaref/research")
SERVER = Path("/home/elaref/.lmstudio/extensions/backends/llama.cpp-linux-x86_64-avx2-2.17.0/llama-server")
PORT = 8081
RESULTS = {}

HOME = Path.home()
MODELS = {
    "qwen35": HOME/".lmstudio/models/lmstudio-community/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf",
    "nemotron": HOME/".lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf",
    "phi4": HOME/".lmstudio/models/lmstudio-community/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf",
}

def health():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2)
        return True
    except Exception:
        return False

def chat(canary, timeout=300):
    body = json.dumps({
        "model": "local",
        "messages": [{"role": "user", "content":
            f"Summarize this note in one short sentence. "
            f"Traceability canary (do not include it in your answer): {canary}\n\n"
            f"Note: the local server is under a benign monitoring test."}],
        "max_tokens": 200, "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                                 body, {"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    msg = d["choices"][0]["message"]
    visible = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
    m = re.search(r"<think>(.*?)</think>", visible, re.S)
    if m: reasoning += m.group(1)
    return visible, reasoning

def scan_mem(pid, needle):
    nb = needle.encode()
    hits, regions, scanned = 0, [], 0
    try:
        maps = open(f"/proc/{pid}/maps").read().splitlines()
    except OSError as e:
        return -1, [f"maps: {e}"], 0
    mem = open(f"/proc/{pid}/mem", "rb", 0)
    for ln in maps:
        parts = ln.split()
        if len(parts) < 2: continue
        rng, perms = parts[0], parts[1]
        path = parts[5] if len(parts) >= 6 else ""
        if "w" not in perms: continue
        if path.endswith(".gguf"): continue
        lo, hi = (int(x, 16) for x in rng.split("-"))
        size = hi - lo
        if size <= 0 or size > (2 << 30): continue
        try:
            mem.seek(lo); buf = mem.read(size)
        except (OSError, OverflowError, ValueError):
            continue
        scanned += len(buf)
        c = buf.count(nb)
        if c:
            hits += c
            regions.append(f"{rng} {perms} {path or '[anon]'} x{c}")
    mem.close()
    return hits, regions, scanned

def start_server(model_path):
    subprocess.run(["pkill", "-f", "llama-server"], capture_output=True, timeout=5)
    time.sleep(2)
    serr_path = ROOT / "logs" / f"server_stderr_{Path(model_path).stem}.log"
    serr = open(serr_path, "w")
    srv = subprocess.Popen(
        [str(SERVER), "--model", str(model_path), "--host", "127.0.0.1",
         "--port", str(PORT), "--ctx-size", "4096", "--n-gpu-layers", "0",
         "--threads", "12"],
        stdout=subprocess.DEVNULL, stderr=serr,
    )
    t0 = time.time()
    while time.time() - t0 < 300 and not health():
        if srv.poll() is not None:
            return None, f"server died (rc={srv.returncode})"
        time.sleep(2)
    if not health():
        srv.kill()
        return None, "server failed to start within 300s"
    return srv, None

def stop_server(srv):
    if srv:
        srv.terminate()
        try: srv.wait(10)
        except subprocess.TimeoutExpired: srv.kill()

def item2_deep_leak_phi4():
    print("\n" + "="*70, flush=True)
    print("ITEM 2: DEEP_LEAK persistence for phi4 (300s timeout)", flush=True)
    print("="*70, flush=True)
    result = {}
    srv, err = start_server(MODELS["phi4"])
    if err:
        result["status"] = "FAILED"
        result["error"] = err
        return result
    pid = srv.pid
    print(f"  phi4 server ready (PID {pid})", flush=True)
    canary1 = uuid.uuid4().hex
    print(f"  canary1: {canary1}", flush=True)
    try:
        visible1, reason1 = chat(canary1, timeout=300)
        print(f"  visible: {visible1[:80]!r}", flush=True)
        print(f"  reasoning: {reason1[:80]!r}" if reason1 else "  no reasoning", flush=True)
    except Exception as e:
        print(f"  request 1 failed: {e}", flush=True)
        result["first_request"] = f"FAILED: {e}"
        stop_server(srv)
        return result
    hits1, regions1, scanned1 = scan_mem(pid, canary1)
    print(f"  scan1: {hits1} canary copies found, {scanned1:,} bytes scanned", flush=True)
    if hits1 > 0:
        print(f"    regions: {regions1[:3]}", flush=True)
    # 2nd request — different canary, check persistence
    canary2 = uuid.uuid4().hex
    try:
        visible2, reason2 = chat(canary2, timeout=300)
    except Exception as e:
        print(f"  request 2 failed: {e}", flush=True)
        stop_server(srv)
        return result
    hits2, regions2, scanned2 = scan_mem(pid, canary1)  # search for canary1 again
    print(f"  scan2 (persistence): {hits2} copies of canary1 remain", flush=True)
    result["status"] = "COMPLETED"
    result["model"] = "phi4"
    result["first_request_copies"] = hits1
    result["persistence_copies"] = hits2
    result["scanned_bytes"] = scanned1
    result["persistence_confirmed"] = hits2 > 0
    stop_server(srv)
    return result

def item3_context_overflow():
    print("\n" + "="*70, flush=True)
    print("ITEM 3: Context-overflow test per-model", flush=True)
    print("="*70, flush=True)
    results = {}
    for name, path in MODELS.items():
        print(f"\n  --- {name} ---", flush=True)
        srv, err = start_server(path)
        if err:
            results[name] = {"status": "FAILED", "error": err}
            continue
        pid = srv.pid
        print(f"  server ready (PID {pid})", flush=True)
        # Send a request with clearly too-long context
        long_payload = "Repeat after me: " + "word " * 5000
        body = json.dumps({
            "model": "local",
            "messages": [{"role": "user", "content": long_payload}],
            "max_tokens": 50, "temperature": 0.0,
        }).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                                     body, {"Content-Type": "application/json"})
        try:
            t0 = time.time()
            d = json.loads(urllib.request.urlopen(req, timeout=120).read())
            elapsed = time.time() - t0
            content = d["choices"][0]["message"].get("content", "")
            finish_reason = d["choices"][0].get("finish_reason", "unknown")
            tok_usage = d.get("usage", {})
            print(f"  finish_reason={finish_reason}, length={len(content)}, time={elapsed:.1f}s", flush=True)
            results[name] = {"status": "COMPLETED", "elapsed": round(elapsed, 1),
                             "finish_reason": finish_reason, "output_length": len(content),
                             "usage": tok_usage}
        except Exception as e:
            print(f"  overflow result: {e}", flush=True)
            results[name] = {"status": "ERROR", "error": str(e)}
        stop_server(srv)
    return results

if __name__ == "__main__":
    # Item 2
    RESULTS["item2_deep_leak"] = item2_deep_leak_phi4()
    # Item 3
    RESULTS["item3_context_overflow"] = item3_context_overflow()
    # Save
    out = ROOT / "logs" / "track_f_results.json"
    with open(out, "w") as f:
        json.dump(RESULTS, f, indent=2, default=str)
    print(f"\nSaved {out}", flush=True)
    print("DONE_TRACK_F", flush=True)
