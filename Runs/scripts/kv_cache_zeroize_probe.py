#!/usr/bin/env python3
# Track E probe: same methodology as deep_leak_probe.py (canary -> chat -> scan
# /proc/PID/mem -> 2nd request reuses the same slot via release() -> rescan).
# Adapted paths for the patched build in llama-cpp-build/.
import os, sys, time, json, re, subprocess, urllib.request, uuid
from pathlib import Path

ROOT = Path("/home/elaref/research")
SERVER = ROOT / "llama-cpp-build/build/bin/llama-server"
MODEL = "/home/elaref/.lmstudio/models/lmstudio-community/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf"
PORT = 8099

def health():
    try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2); return True
    except Exception: return False

def chat(canary):
    body = json.dumps({
        "model": "local",
        "messages": [{"role": "user", "content":
            f"Summarize this note in one short sentence. "
            f"Traceability canary (do not include it in your answer): {canary}\n\n"
            f"Note: the local server is under a benign monitoring test."}],
        "max_tokens": 16, "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                                 body, {"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=300).read())
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

def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    os.chdir(ROOT)
    subprocess.run(["pkill", "-f", "bin/llama-server"], capture_output=True); time.sleep(2)
    slog = open(ROOT / f"logs/kv_zeroize_probe_{label}.log", "w")
    srv = subprocess.Popen(
        [str(SERVER), "--model", MODEL, "--host", "127.0.0.1", "--port", str(PORT),
         "--ctx-size", "4096", "--n-gpu-layers", "0", "--threads", "16", "--jinja", "--parallel", "1",
         "--cache-ram", "0"],
        stdout=slog, stderr=subprocess.STDOUT)
    print(f"[probe] server pid {srv.pid}; waiting for health...", flush=True)
    for i in range(180):
        if health(): print(f"[probe] healthy after {i}s", flush=True); break
        if srv.poll() is not None: print("[probe] server died", flush=True); sys.exit(1)
        time.sleep(1)
    else:
        srv.kill(); print("[probe] health timeout", flush=True); sys.exit(1)

    canary = uuid.uuid4().hex
    print(f"[probe] canary={canary}", flush=True)

    visible, reasoning = chat(canary)
    in_visible = canary in visible
    in_reasoning = canary in reasoning
    print(f"[probe] leak_visible={in_visible} leak_reasoning={in_reasoning}", flush=True)

    hits, regions, scanned = scan_mem(srv.pid, canary)
    print(f"[probe] MEMORY (slot still busy/idle, pre-release-check): canary occurrences={hits} "
          f"in {len(regions)} writable region(s), scanned={scanned//(1<<20)}MB", flush=True)
    for r in regions[:12]:
        print(f"[probe]   region: {r}", flush=True)

    # 2nd request: with n_parallel=1 (default), this reuses slot 0 -> triggers
    # slot.release() -> seq_rm() on the canary's sequence before the new prompt is processed.
    chat("benign-followup-no-canary-" + uuid.uuid4().hex)
    hits2, regions2, _ = scan_mem(srv.pid, canary)
    print(f"[probe] AFTER slot release+reuse: canary still resident={hits2} occurrence(s)", flush=True)
    for r in regions2[:12]:
        print(f"[probe]   region: {r}", flush=True)

    srv.terminate()
    try: srv.wait(10)
    except subprocess.TimeoutExpired: srv.kill()

    verdict = "LEAK" if (in_visible or in_reasoning or hits2 > 0) else "clean-after-release"
    print(f"[probe] === {label}: {verdict} | visible={in_visible} reasoning={in_reasoning} "
          f"memory_pre_release={hits} memory_post_release={hits2} ===", flush=True)

if __name__ == "__main__":
    main()
