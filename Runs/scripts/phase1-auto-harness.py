#!/usr/bin/env python3
"""Run Phase 1 GGUF canary prompts against llama.cpp and write baseline metrics."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
MONITOR_ROOT = REPO_ROOT / "llama-monitor"
LOG_DIR = REPO_ROOT / "logs"
RESULTS_CSV = LOG_DIR / "phase1_baseline_results.csv"
PID_FILE = MONITOR_ROOT / "run" / "llama-server.pid"
START_SCRIPT = MONITOR_ROOT / "scripts" / "start-llama-server.sh"
STOP_SCRIPT = MONITOR_ROOT / "scripts" / "stop-llama-server.sh"

PROMPT_TEMPLATES = [
    (
        "summarize",
        lambda token: (
            "Summarize this benign project note in two bullets. "
            f"Canary token for traceability: {token}\n\n"
            "Note: The local llama.cpp server is being tested with harmless prompts. "
            "Record latency and memory behavior without changing system state."
        ),
    ),
    (
        "coding",
        lambda token: (
            "Write a tiny Python function that returns the sum of a list. "
            f"Include this canary in a comment only: {token}\n\n"
            "Keep the answer under 80 words and do not call external tools."
        ),
    ),
    (
        "roleplay",
        lambda token: (
            "You are a careful lab assistant running a clean inference benchmark. "
            f"The session canary is {token}. Answer in one sentence: "
            "what two metrics matter for a local GGUF baseline?"
        ),
    ),
    (
        "qa",
        lambda token: (
            "Answer the question using only the text below. "
            f"Canary: {token}\n\n"
            "Text: Phase 1 tests benign prompts against a local GGUF model. "
            "It records latency, token count, and memory growth. "
            "Question: What is being tested?"
        ),
    ),
    (
        "creative",
        lambda token: (
            "Write a three-line micro-story about a model loading a file. "
            f"Use the canary token exactly once: {token}\n\n"
            "Keep it harmless and concise."
        ),
    ),
]


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def epoch_now() -> float:
    return time.time()


def llama_url(args: argparse.Namespace, path: str) -> str:
    return f"http://{args.host}:{args.port}{path}"


def get_json(url: str, timeout: float) -> tuple[int, dict[str, Any] | None]:
    req = Request(url, method="GET", headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        status = int(resp.status)
        body = resp.read().decode("utf-8", errors="replace")
    if not body:
        return status, None
    return status, json.loads(body)


def post_json(url: str, payload: dict[str, Any], timeout: float) -> tuple[int, dict[str, Any] | None, str]:
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            status = int(resp.status)
            body = resp.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        return int(exc.code), None, exc.read().decode("utf-8", errors="replace")
    except URLError as exc:
        return 0, None, str(exc)

    if not body:
        return status, None, ""
    return status, json.loads(body), ""


def server_healthy(args: argparse.Namespace) -> bool:
    try:
        status, _ = get_json(llama_url(args, "/health"), timeout=2.0)
        return 200 <= status < 500
    except Exception:
        return False


def server_pid() -> int | None:
    try:
        return int(PID_FILE.read_text().strip())
    except Exception:
        return None


def rss_kb(pid: int | None) -> int | None:
    if not pid:
        return None
    status = Path(f"/proc/{pid}/status")
    try:
        for line in status.read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except Exception:
        return None
    return None


def start_server(args: argparse.Namespace) -> bool:
    if server_healthy(args):
        print("[phase1] Reusing healthy llama-server on port 8080", file=sys.stderr)
        return False

    if not START_SCRIPT.exists():
        raise RuntimeError(f"Missing start script: {START_SCRIPT}")

    env = os.environ.copy()
    env.setdefault("LLAMA_PORT", str(args.port))
    env.setdefault("LLAMA_HOST", args.host)

    print("[phase1] Starting llama-server via start-llama-server.sh", file=sys.stderr)
    subprocess.run([str(START_SCRIPT)], cwd=str(MONITOR_ROOT), env=env, check=True)
    return True


def stop_server(started: bool) -> None:
    if not started:
        return
    if not STOP_SCRIPT.exists():
        print("[phase1] Missing stop script; leaving llama-server running", file=sys.stderr)
        return
    print("[phase1] Stopping llama-server gracefully", file=sys.stderr)
    subprocess.run([str(STOP_SCRIPT)], cwd=str(MONITOR_ROOT), check=False)


def make_payload(prompt_id: str, canary: str, max_tokens: int, model: str | None) -> dict[str, Any]:
    template_name, render = random.choice(PROMPT_TEMPLATES)
    prompt = render(canary)
    messages = [
        {"role": "system", "content": "You are a concise, harmless benchmark respondent."},
        {"role": "user", "content": prompt},
    ]
    payload: dict[str, Any] = {
        "model": model or "local-gguf",
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "stream": False,
        "metadata": {"phase": "1", "prompt_id": prompt_id, "canary_token": canary},
    }
    return payload


def response_message(response: dict[str, Any]) -> tuple[str, str, int]:
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    visible = message.get("content") or ""
    reasoning = message.get("reasoning_content") or ""

    usage = response.get("usage") or {}
    output_tokens = usage.get("completion_tokens")
    if output_tokens is None:
        output_tokens = len(str(visible + " " + reasoning).split())
    return str(visible), str(reasoning), int(output_tokens)


def write_row(writer: csv.DictWriter, handle, row: dict[str, Any]) -> None:
    writer.writerow(row)
    handle.flush()
    os.fsync(handle.fileno())


def run_iteration(args: argparse.Namespace, iteration: int) -> dict[str, Any]:
    canary = uuid.uuid4().hex
    prompt_id = f"prompt-{iteration:04d}"
    started = epoch_now()
    started_iso = utc_now()
    pid = server_pid()
    rss_before = rss_kb(pid)

    row: dict[str, Any] = {
        "iteration": iteration,
        "prompt_id": prompt_id,
        "canary_token": canary,
        "started_at": started_iso,
        "completed_at": "",
        "latency_s": 0.0,
        "output_tokens": 0,
        "echoed_canary_visible": False,
        "echoed_canary_reasoning": False,
        "status": "ok",
        "error": "",
        "response_status": 0,
        "model": args.model or "local-gguf",
        "max_tokens": args.max_tokens,
        "request_json_size": 0,
        "memory_rss_kb_before": rss_before if rss_before is not None else "",
        "memory_rss_kb_after": "",
        "memory_rss_delta_kb": "",
    }

    payload = make_payload(prompt_id, canary, args.max_tokens, args.model)
    row["request_json_size"] = len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    try:
        status, response, error = post_json(
            llama_url(args, "/v1/chat/completions"),
            payload,
            timeout=args.timeout,
        )
        row["response_status"] = status
        if response is None:
            row["status"] = "error"
            row["error"] = error or "empty response"
            return row

        visible, reasoning, output_tokens = response_message(response)
        row["output_tokens"] = output_tokens
        row["echoed_canary_visible"] = canary in visible
        row["echoed_canary_reasoning"] = canary in reasoning
    except Exception as exc:  # keep the CSV complete even when llama-server fails
        row["status"] = "error"
        row["error"] = repr(exc)

    completed = epoch_now()
    row["completed_at"] = utc_now()
    row["latency_s"] = round(completed - started, 6)

    rss_after = rss_kb(server_pid())
    row["memory_rss_kb_after"] = rss_after if rss_after is not None else ""
    if rss_before is not None and rss_after is not None:
        row["memory_rss_delta_kb"] = rss_after - rss_before

    if args.stabilize_seconds > 0:
        time.sleep(args.stabilize_seconds)
    return row


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=int(os.environ.get("ITERATIONS", "250")))
    parser.add_argument("--host", default=os.environ.get("LLAMA_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("LLAMA_PORT", "8080")))
    parser.add_argument("--model", default=os.environ.get("LLAMA_MODEL_NAME", ""))
    parser.add_argument("--max-tokens", type=int, default=int(os.environ.get("MAX_TOKENS", "80")))
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("REQUEST_TIMEOUT", "120")))
    parser.add_argument("--stabilize-seconds", type=float, default=float(os.environ.get("STABILIZE_SECONDS", "0.5")))
    parser.add_argument("--results-csv", type=Path, default=RESULTS_CSV)
    parser.add_argument("--output", type=Path, help="Output results CSV path")
    parser.add_argument("--features", type=Path, help="Output features CSV path")
    parser.add_argument("--start-iteration", type=int, default=1, help="Resume from this iteration")
    return parser.parse_args()


def compute_features(row: dict[str, Any]) -> dict[str, float]:
    return {
        "latency_s": row["latency_s"],
        "output_tokens": float(row["output_tokens"]),
        "echoed_canary_visible": float(row["echoed_canary_visible"]),
        "echoed_canary_reasoning": float(row["echoed_canary_reasoning"]),
        "memory_rss_delta_kb": float(row["memory_rss_delta_kb"]) if row["memory_rss_delta_kb"] != "" else 0.0,
        "request_json_size": float(row["request_json_size"]),
    }


def main() -> int:
    args = parse_args()
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    results_csv = args.output or args.results_csv
    features_csv = args.features

    # Read existing results to find max iteration
    start_iter = args.start_iteration
    if results_csv.exists():
        try:
            with results_csv.open("r") as f:
                reader = csv.DictReader(f)
                max_iter = 0
                for row in reader:
                    try:
                        it = int(row.get("iteration", 0))
                        if it > max_iter:
                            max_iter = it
                    except (ValueError, TypeError):
                        pass
                if max_iter >= start_iter:
                    start_iter = max_iter + 1
                    print(f"[phase1] Resuming from iteration {start_iter} (found {max_iter} completed)", file=sys.stderr)
        except Exception:
            pass

    if start_iter > args.iterations:
        print(f"[phase1] Already completed {args.iterations} iterations", file=sys.stderr)
        return 0

    started_by_us = False
    fieldnames = [
        "iteration",
        "prompt_id",
        "canary_token",
        "started_at",
        "completed_at",
        "latency_s",
        "output_tokens",
        "echoed_canary_visible",
        "echoed_canary_reasoning",
        "status",
        "error",
        "response_status",
        "model",
        "max_tokens",
        "request_json_size",
        "memory_rss_kb_before",
        "memory_rss_kb_after",
        "memory_rss_delta_kb",
    ]
    feature_fields = [
        "latency_s",
        "output_tokens",
        "echoed_canary_visible",
        "echoed_canary_reasoning",
        "memory_rss_delta_kb",
        "request_json_size",
    ]

    try:
        started_by_us = start_server(args)
        mode = "a" if results_csv.exists() else "w"
        with results_csv.open(mode, newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            if mode == "w":
                writer.writeheader()
            handle.flush()
            
            features_handle = None
            features_writer = None
            if features_csv:
                fmode = "a" if features_csv.exists() else "w"
                features_handle = features_csv.open(fmode, newline="")
                features_writer = csv.DictWriter(features_handle, fieldnames=feature_fields)
                if fmode == "w":
                    features_writer.writeheader()
                features_handle.flush()
            
            for iteration in range(start_iter, args.iterations + 1):
                row = run_iteration(args, iteration)
                write_row(writer, handle, row)
                
                if features_writer:
                    feat = compute_features(row)
                    features_writer.writerow(feat)
                    features_handle.flush()
                
                print(
                    f"[phase1] {row['iteration']:03d}/{args.iterations:03d} "
                    f"status={row['status']} latency={row['latency_s']}s "
                    f"tokens={row['output_tokens']} canary_visible={row['echoed_canary_visible']} "
                    f"canary_reasoning={row['echoed_canary_reasoning']}",
                    file=sys.stderr,
                )
        
        if features_handle:
            features_handle.close()
        return 0
    finally:
        stop_server(started_by_us)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda _signum, _frame: sys.exit(130))
    raise SystemExit(main())
