#!/usr/bin/env python3
"""LM Studio prompt inspector: MITM proxy between LMS and llama-server.
Captures prompt diffs to detect if LMS modifies prompts before forwarding."""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError

from scripts.lms_common import auto_detect_windows_host, verify_host_reachable

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_ROOT / "logs"
DIFFS_LOG = LOG_DIR / "lms_prompt_diffs.jsonl"
PROMETHEUS_LOG = LOG_DIR / "lms_prometheus_dump.json"

LMS_BACKEND_PORT = 8081
PROXY_PORT = 8080


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    print(f"[{utc_now()}] {msg}", file=sys.stderr)


def compute_diff(input_str: str, output_str: str) -> dict[str, Any]:
    if input_str == output_str:
        return {"identical": True}
    input_len = len(input_str)
    output_len = len(output_str)
    changed = input_str != output_str
    input_lines = input_str.split("\n")
    output_lines = output_str.split("\n")
    line_diff = len(input_lines) != len(output_lines)
    return {
        "identical": False,
        "input_length": input_len,
        "output_length": output_len,
        "length_diff": output_len - input_len,
        "line_count_diff": len(output_lines) - len(input_lines),
        "lines_changed": line_diff,
    }


class ProxyHandler(BaseHTTPRequestHandler):
    backend_host = "127.0.0.1"
    backend_port = LMS_BACKEND_PORT
    diffs_log_path = DIFFS_LOG
    request_count = 0

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        input_payload = body.decode("utf-8", errors="replace")

        proxy_url = f"http://{self.backend_host}:{self.backend_port}{self.path}"
        req = Request(
            proxy_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        try:
            with urlopen(req, timeout=120) as resp:
                response_body = resp.read()
                status = resp.status

            output_payload = response_body.decode("utf-8", errors="replace")

            self.send_response(status)
            for key, value in resp.headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response_body)

            self.__class__.request_count += 1
            req_id = self.__class__.request_count

            diff = compute_diff(input_payload, output_payload)

            diff_entry = {
                "ts": utc_now(),
                "request_id": req_id,
                "path": self.path,
                "diff": diff,
                "input_preview": input_payload[:200],
                "output_preview": output_payload[:200],
            }

            with open(self.diffs_log_path, "a") as f:
                f.write(json.dumps(diff_entry) + "\n")

            if not diff["identical"]:
                log(f"#{req_id} PROMPT MODIFIED: {diff['length_diff']} byte diff")

        except URLError as e:
            log(f"Proxy error: {e}")
            self.send_response(502)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Backend error: {e}".encode())

    def do_GET(self):
        proxy_url = f"http://{self.backend_host}:{self.backend_port}{self.path}"
        req = Request(proxy_url, method="GET")
        try:
            with urlopen(req, timeout=30) as resp:
                response_body = resp.read()
                self.send_response(resp.status)
                for key, value in resp.headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(response_body)
        except URLError as e:
            log(f"Proxy GET error: {e}")
            self.send_response(502)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listen-port", type=int, default=PROXY_PORT, help="MITM proxy listen port")
    parser.add_argument("--listen-ip", default="127.0.0.1", help="IP to bind proxy to")
    parser.add_argument("--backend-host", default="auto", help="Backend host (auto=detect Windows host)")
    parser.add_argument("--backend-port", type=int, default=LMS_BACKEND_PORT, help="Backend llama-server port")
    parser.add_argument("--cross-os", action="store_true", help="Cross-OS: bind 0.0.0.0, auto-detect backend")
    parser.add_argument("--diffs-log", type=Path, default=DIFFS_LOG)
    parser.add_argument("--daemon", action="store_true", help="Run in background thread")
    return parser.parse_args()


def run_proxy(args: argparse.Namespace) -> HTTPServer:
    backend_host = args.backend_host
    if backend_host == "auto":
        backend_host = auto_detect_windows_host()
    args.backend_host = backend_host
    listen_ip = "0.0.0.0" if args.cross_os else args.listen_ip
    ProxyHandler.backend_host = args.backend_host
    ProxyHandler.backend_port = args.backend_port
    ProxyHandler.diffs_log_path = args.diffs_log

    server = HTTPServer((listen_ip, args.listen_port), ProxyHandler)
    log(f"Prompt inspector proxy on {listen_ip}:{args.listen_port} -> {args.backend_host}:{args.backend_port}")
    return server


def main() -> int:
    args = parse_args()
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    server = run_proxy(args)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Shutting down")
        server.shutdown()

    total_requests = ProxyHandler.request_count
    diffs_count = 0
    try:
        with open(args.diffs_log) as f:
            for line in f:
                entry = json.loads(line)
                if not entry.get("diff", {}).get("identical", True):
                    diffs_count += 1
    except Exception:
        pass

    log(f"Prompt inspector summary: {total_requests} requests, {diffs_count} prompt modifications detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
