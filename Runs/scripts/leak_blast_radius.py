#!/usr/bin/env python3
# Blast radius: how much does ONE memory read recover? Send N sequential tenants,
# each with a distinct realistic secret, then do a SINGLE /proc/<pid>/mem scan and
# count how many of the N secrets (and how much cleartext) are recoverable at once.
# Quantifies the multi-tenant exposure of a single memory-disclosure bug.
import os, sys, time, json, re, uuid, subprocess, urllib.request
from pathlib import Path
from datetime import datetime

# Fixed paths: point at the CURRENT research tree (not the old /home/sharks WSL2 env).
ROOT = Path("/home/elaref/research")
SERVER = ROOT / "llama-cpp-build" / "build" / "bin" / "llama-server"
PORT = 8080
N = 12
RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_JSON = ROOT / "logs" / f"leak_blast_radius_{RUN_ID}.json"
TEMPLATES = [  # realistic secret-bearing prompts, varied so the dump shows diverse data
    "My AWS secret key is {s}. Summarize: routine check.",
    "Patient record token {s}. Summarize the note: routine check.",
    "DB password is {s}. Acknowledge and summarize: routine check.",
    "API bearer token {s}. Summarize: routine check.",
]

def health():
    try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2); return True
    except Exception: return False

def chat(text):
    body = json.dumps({"model":"local","messages":[{"role":"user","content":text}],
                       "max_tokens":80,"temperature":0.0}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                                 body, {"Content-Type":"application/json"})
    try: urllib.request.urlopen(req, timeout=240).read()
    except Exception as e: print(f"[blast]   req err: {e}", flush=True)

def scan(pid, needles):
    found = {n:0 for n in needles}; cleartext_bytes = 0; samples = []
    try: maps = open(f"/proc/{pid}/maps").read().splitlines()
    except OSError: return found, 0, samples
    mem = open(f"/proc/{pid}/mem","rb",0)
    for ln in maps:
        p = ln.split()
        if len(p) < 2 or "w" not in p[1]: continue
        if (p[5] if len(p)>=6 else "").endswith(".gguf"): continue
        lo, hi = (int(x,16) for x in p[0].split("-"))
        if hi-lo <= 0 or hi-lo > (2<<30): continue
        try: mem.seek(lo); buf = mem.read(hi-lo)
        except (OSError,OverflowError,ValueError): continue
        for n in needles:
            c = buf.count(n.encode())
            if c:
                found[n] += c
                if len(samples) < 3:
                    i = buf.find(n.encode())
                    seg = buf[max(0,i-60):i+90]
                    samples.append("".join(chr(b) if 32<=b<127 else "." for b in seg))
        # crude cleartext volume: count bytes that are printable ASCII in this rw region
        cleartext_bytes += sum(1 for b in buf[:5_000_000] if 32 <= b < 127)  # cap per region
    mem.close(); return found, cleartext_bytes, samples

def main():
    model, name = sys.argv[1], sys.argv[2]
    os.chdir(ROOT)
    subprocess.run(["pkill","-f","llama-server"], capture_output=True); time.sleep(2)
    slog = open(ROOT / f"logs/server_blast_{name}.log","w")
    srv = subprocess.Popen(
        [str(SERVER),"--model",model,"--host","127.0.0.1","--port",str(PORT),
         "--ctx-size","16384","--parallel","4","--n-gpu-layers","0",
         "--threads","16","--jinja"], stdout=slog, stderr=subprocess.STDOUT)
    print(f"[blast] server pid {srv.pid} (--parallel 4); waiting...", flush=True)
    for i in range(180):
        if health(): print(f"[blast] healthy after {i}s", flush=True); break
        if srv.poll() is not None: print("[blast] server died", flush=True); sys.exit(1)
        time.sleep(1)
    else: srv.kill(); print("[blast] timeout", flush=True); sys.exit(1)

    secrets = [uuid.uuid4().hex for _ in range(N)]
    print(f"[blast] sending {N} sequential tenants, each with a distinct secret...", flush=True)
    for i, s in enumerate(secrets):
        chat(TEMPLATES[i % len(TEMPLATES)].format(s=s))
        if (i+1) % 4 == 0: print(f"[blast]   sent {i+1}/{N}", flush=True)

    # ONE memory read at the end
    found, ct, samples = scan(srv.pid, secrets)
    recovered = sum(1 for s in secrets if found[s] > 0)
    total_copies = sum(found.values())
    print(f"[blast] === ONE memory read recovered {recovered}/{N} tenants' secrets "
          f"(~{ct//1024} KB printable cleartext in writable RAM) ===", flush=True)
    for j, sm in enumerate(samples):
        print(f"[blast] sample{j}: ...{sm}...", flush=True)

    # Retained artifact (the audit's #1 requirement: headline numbers must have logs)
    result = {
        "run_id": RUN_ID,
        "iso": datetime.now().isoformat(),
        "model": model,
        "n_tenants": N,
        "tenants_recovered": recovered,
        "recovery_rate": round(recovered / N, 4),
        "total_canary_copies_across_all_tenants": total_copies,
        "per_tenant_copies": {f"tenant_{i}": found[s] for i, s in enumerate(secrets)},
        "printable_cleartext_kb": ct // 1024,
        "samples": samples,
        "binary": str(SERVER),
        "binary_has_zero_cell_data": "zero_cell_data" in subprocess.run(
            ["strings", str(SERVER)], capture_output=True, text=True).stdout,
    }
    OUT_JSON.parent.mkdir(exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2))
    print(f"[blast] retained artifact: {OUT_JSON}", flush=True)

    srv.terminate()
    try: srv.wait(10)
    except subprocess.TimeoutExpired: srv.kill()

if __name__ == "__main__":
    main()
