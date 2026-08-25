#!/usr/bin/env python3
"""Test runner for novel GGUF attack variants - crash detection focused."""

from __future__ import annotations

import csv
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SERVER = REPO / "llama-monitor/build/llama.cpp/bin/llama-server"
NOVEL_DIR = REPO / "logs/gguf_novel"
RESULTS = REPO / "logs/novel_attacks_test_results.csv"

PROMPTS = [
    ("What is 2+2?", False),
    ("SYSTEM_DIAGNOSTIC run check", True),
    ("Hello world", False),
]


def test_variant(model: Path, port: int) -> dict:
    """Start server, send one prompt, return result."""
    cmd = [str(SERVER), "-m", str(model), "--port", str(port),
           "--host", "127.0.0.1", "-ngl", "0", "-c", "256", "--parallel", "1"]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                preexec_fn=os.setsid)
    except Exception as e:
        return {"http_status": 0, "crashed": True, "exit_code": -999, "error": str(e), "signal": ""}

    # Wait for readiness
    ready = False
    for _ in range(20):
        if proc.poll() is not None:
            break
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/health")
            urllib.request.urlopen(req, timeout=2)
            ready = True
            break
        except Exception:
            pass
        time.sleep(0.5)

    if not ready:
        rc = proc.returncode if proc.poll() is not None else -1
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass
        if rc is None:
            rc = -1
        sig = rc - 256 if rc > 128 else rc
        signame = signal.Signals(-sig).name if sig < 0 else f"exit({rc})"
        return {"http_status": 0, "crashed": sig < 0, "exit_code": rc,
                "error": "server not ready", "signal": signame}

    # Send prompt
    payload = json.dumps({"prompt": "Hello", "n_predict": 16, "temperature": 0.0}).encode()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/completion",
                                    data=payload, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=15)
        status = resp.status
        body = json.loads(resp.read().decode())
        content = body.get("content", "")
    except Exception as e:
        status = 0
        content = ""
    
    # Kill server
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=5)
    except Exception:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass
        proc.wait(timeout=3)

    rc = proc.returncode
    sig = rc - 256 if rc > 128 else rc
    signame = signal.Signals(-sig).name if sig < 0 else f"exit({rc})"
    return {"http_status": status, "crashed": sig < 0, "exit_code": rc,
            "response_len": len(content), "signal": signame, "error": ""}


def main():
    NOVEL_DIR.mkdir(parents=True, exist_ok=True)
    variants = sorted(NOVEL_DIR.glob("novel_*.gguf"))
    print(f"[novel-test] Found {len(variants)} variants", file=sys.stderr)

    results = []
    port = 18200
    for v in variants:
        vname = v.stem
        print(f"\n[novel-test] {vname}", file=sys.stderr)
        r = test_variant(v, port)
        r["variant"] = vname
        r["file_size"] = v.stat().st_size
        results.append(r)
        crash = " CRASH" if r["crashed"] else ""
        sig = r.get("signal", "")
        print(f"  status={r['http_status']} rc={r['exit_code']} sig={sig}{crash}", file=sys.stderr)
        port += 1

    # Write CSV
    fieldnames = ["variant", "file_size", "http_status", "exit_code", "signal",
                  "crashed", "response_len", "error"]
    # Ensure all rows have same keys
    for r in results:
        for k in fieldnames:
            r.setdefault(k, "")
    with RESULTS.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)

    crashes = sum(1 for r in results if r["crashed"])
    ok = sum(1 for r in results if r["http_status"] == 200)
    print(f"\n[novel-test] Total={len(results)} OK={ok} Crashes={crashes}", file=sys.stderr)
    print(f"[novel-test] Results: {RESULTS}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
