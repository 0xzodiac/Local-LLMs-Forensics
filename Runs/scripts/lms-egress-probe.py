#!/usr/bin/env python3
"""LM Studio egress probe: WSL-side network monitor for Windows LMS host."""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.lms_common import auto_detect_windows_host

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_ROOT / "logs"
RESULTS_FILE = LOG_DIR / "lms_egress_report.json"
PCAP_FILE = "/tmp/lms_egress.pcap"

SNAPSHOT_INTERVAL = 2.0
BASELINE_DURATION = 30


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    print(f"[{utc_now()}] {msg}", file=sys.stderr)


def find_lms_pids() -> list[int]:
    return []  # N/A: Windows PIDs invisible from WSL2


def find_windows_lms_ip() -> str:
    return auto_detect_windows_host()


def get_all_connections() -> set[tuple[str, int, str, str]]:
    conns = set()
    try:
        r = subprocess.run(["ss", "-tunp"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.strip().split("\n")[1:]:
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            remote = parts[4]
            ip, port_str = remote.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 0
            state = parts[1] if len(parts) > 1 else "?"
            m = re.search(r'"([^"]+)"', " ".join(parts))
            proc_name = m.group(1) if m else ""
            conns.add((ip, port, state, proc_name))
    except Exception as e:
        log(f"ss error: {e}")
    return conns


def sample_ambient(duration: int = BASELINE_DURATION) -> list[set]:
    snapshots = []
    samples = duration // 2
    log(f"Ambient baseline: {samples} samples over {duration}s...")
    for i in range(samples):
        snapshots.append(get_all_connections())
        time.sleep(2)
    log(f"Baseline done: {len(snapshots)} snapshots")
    return snapshots


def check_dns_queries() -> list[dict[str, Any]]:
    queries = []
    try:
        r = subprocess.run(
            ["journalctl", "-u", "systemd-resolved", "--since", "30 seconds ago", "--no-pager", "-o", "json"],
            capture_output=True, text=True, timeout=10
        )
        for line in r.stdout.strip().splitlines():
            try:
                entry = json.loads(line)
                queries.append(entry)
            except json.JSONDecodeError:
                pass
    except Exception:
        try:
            r = subprocess.run(
                ["tcpdump", "-i", "lo", "-c", "50", "port 53", "-t", "-l"],
                capture_output=True, text=True, timeout=5
            )
            if r.stdout:
                queries.append({"source": "tcpdump", "output": r.stdout[:500]})
        except Exception:
            pass
    return queries


class EgressMonitor:
    def __init__(self, windows_host: str):
        self.windows_host = windows_host
        self.snapshots: list[dict[str, Any]] = []
        self.dns_queries: list[dict[str, Any]] = []
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        log(f"Egress monitor started for Windows host: {self.windows_host}")

    def stop(self) -> dict[str, Any]:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

        all_conns: set[tuple[str, int, str, str]] = set()
        for snap in self.snapshots:
            for c in snap.get("connections", []):
                all_conns.add(tuple(c))

        external = {c for c in all_conns if not c[0].startswith("127.") and c[0] != "::1" and c[0] != "0.0.0.0"}
        external = {c for c in external if c[0] != self.windows_host}

        return {
            "timestamp": utc_now(),
            "windows_host": self.windows_host,
            "total_snapshots": len(self.snapshots),
            "unique_external_connections": sorted(f"{c[0]}:{c[1]}({c[2]})" for c in external),
            "unique_all_connections": sorted(f"{c[0]}:{c[1]}({c[2]})" for c in all_conns),
            "dns_queries": self.dns_queries[:50],
            "external_conn_count": len(external),
            "finding": "No external connections detected" if not external else f"External connections found: {external}",
        }

    def _run(self) -> None:
        while self._running:
            conns = get_all_connections()
            self.snapshots.append({
                "ts": utc_now(),
                "connections": sorted(f"{c[0]}:{c[1]}({c[2]})" for c in conns),
            })
            time.sleep(SNAPSHOT_INTERVAL)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pcap", action="store_true", help="Capture pcap from WSL (sudo tcpdump)")
    parser.add_argument("--duration", type=int, default=120, help="Monitor duration in seconds")
    parser.add_argument("--windows-host", default="", help="Windows host IP (auto-detect if empty)")
    parser.add_argument("--output", type=Path, default=RESULTS_FILE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    windows_host = args.windows_host or find_windows_lms_ip()
    log(f"Windows host: {windows_host} (LMS API target)")
    log("PID-attributed monitoring: N/A (Windows PIDs invisible from WSL2)")
    log("Monitoring via WSL-side network-level connection tracking")

    baseline_conns = sample_ambient()
    all_baseline = set()
    for s in baseline_conns:
        all_baseline.update(s)

    log(f"Ambient connections from WSL: {len(all_baseline)} unique")

    monitor = EgressMonitor(windows_host)
    monitor.start()

    pcap_proc = None
    if args.pcap:
        try:
            pcap_proc = subprocess.Popen(
                ["sudo", "tcpdump", "-i", "any", "-s", "0",
                 "-w", str(PCAP_FILE),
                 "-n", "not", "port", "22"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            log(f"PCAP capture started: {PCAP_FILE}")
        except Exception as e:
            log(f"PCAP start failed: {e}")

    try:
        elapsed = 0
        while elapsed < args.duration:
            time.sleep(5)
            elapsed += 5

            if elapsed % 30 == 0:
                dns = check_dns_queries()
                if dns:
                    monitor.dns_queries.extend(dns)
                    log(f"DNS queries detected: {len(dns)}")
    except KeyboardInterrupt:
        log("Monitor interrupted")

    if pcap_proc:
        pcap_proc.terminate()
        pcap_proc.wait(timeout=10)
        log(f"PCAP saved to {PCAP_FILE}")

    result = monitor.stop()
    result["windows_host"] = windows_host
    result["baseline_connections"] = sorted(f"{c[0]}:{c[1]}" for c in all_baseline)

    companion = Path(REPO_ROOT) / "scripts" / "lms-egress-probe-windows.ps1"
    if companion.exists():
        log(f"Windows companion: {companion}")
        log("  In Windows PowerShell (Admin), run:")
        log(f"    powershell -ExecutionPolicy Bypass -File lms-egress-probe-windows.ps1 -Duration {args.duration}")

    log(json.dumps(result, indent=2))
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)
    log(f"Results saved to {args.output}")
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda _signum, _frame: sys.exit(130))
    raise SystemExit(main())
