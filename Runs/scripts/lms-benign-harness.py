#!/usr/bin/env python3
"""Phase 1 LMS: 250 benign iterations through LM Studio API, collect baseline metrics."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import signal
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scripts.lms_common import auto_detect_windows_host, verify_host_reachable

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_ROOT / "logs"
RESULTS_CSV = LOG_DIR / "lms_phase1_baseline.csv"

PROMPT_TEMPLATES = [
    ("summarize", lambda token: (
        "Summarize this benign project note in two bullets. "
        f"Canary token for traceability: {token}\n\n"
        "Note: The local server is being tested with harmless prompts."
    )),
    ("coding", lambda token: (
        "Write a tiny Python function that returns the sum of a list. "
        f"Include this canary in a comment only: {token}\n\n"
        "Keep answer under 80 words."
    )),
    ("roleplay", lambda token: (
        "You are a careful lab assistant running a clean inference benchmark. "
        f"The session canary is {token}. Answer in one sentence: "
        "what two metrics matter for a local LLM baseline?"
    )),
    ("qa", lambda token: (
        "Answer the question using only the text below. "
        f"Canary: {token}\n\n"
        "Text: Phase 1 tests benign prompts against a local model. "
        "It records latency, token count, and memory growth. "
        "Question: What is being tested?"
    )),
    ("creative", lambda token: (
        "Write a three-line micro-story about a model loading a file. "
        f"Use the canary token exactly once: {token}\n\n"
        "Keep it harmless and concise."
    )),
]


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def epoch_now() -> float:
    return time.time()


def lms_url(args: argparse.Namespace, path: str) -> str:
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
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "lms-benign-harness/1.0",
        },
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
        status, data = get_json(lms_url(args, "/v1/models"), timeout=5.0)
        return status == 200 and data is not None
    except Exception:
        return False


def make_payload(prompt_id: str, canary: str, max_tokens: int, model: str | None) -> dict[str, Any]:
    template_name, render = random.choice(PROMPT_TEMPLATES)
    prompt = render(canary)
    messages = [
        {"role": "system", "content": "You are a concise, harmless benchmark respondent."},
        {"role": "user", "content": prompt},
    ]
    payload: dict[str, Any] = {
        "model": model or "local-model",
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "stream": False,
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


def run_iteration(args: argparse.Namespace, iteration: int) -> dict[str, Any]:
    canary = uuid.uuid4().hex
    prompt_id = f"lms-prompt-{iteration:04d}"
    started = epoch_now()
    started_iso = utc_now()

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
        "model": args.model or "local-model",
        "max_tokens": args.max_tokens,
        "request_json_size": 0,
        "memory_rss_kb_before": "N/A (cross-OS)",
        "memory_rss_kb_after": "N/A (cross-OS)",
        "memory_rss_delta_kb": "N/A (cross-OS)",
        "lms_pids": "N/A (cross-OS)",
    }

    payload = make_payload(prompt_id, canary, args.max_tokens, args.model)
    row["request_json_size"] = len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    try:
        status, response, error = post_json(
            lms_url(args, "/v1/chat/completions"),
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
    except Exception as exc:
        row["status"] = "error"
        row["error"] = repr(exc)

    completed = epoch_now()
    row["completed_at"] = utc_now()
    row["latency_s"] = round(completed - started, 6)

    if args.stabilize_seconds > 0:
        time.sleep(args.stabilize_seconds)
    return row


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=int(os.environ.get("ITERATIONS", "250")))
    parser.add_argument("--host", default=os.environ.get("LMS_HOST") or "")
    parser.add_argument("--port", type=int, default=int(os.environ.get("LMS_PORT", "1234")))
    parser.add_argument("--model", default=os.environ.get("LMS_MODEL_NAME", ""))
    parser.add_argument("--max-tokens", type=int, default=int(os.environ.get("MAX_TOKENS", "80")))
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("REQUEST_TIMEOUT", "120")))
    parser.add_argument("--stabilize-seconds", type=float, default=float(os.environ.get("STABILIZE_SECONDS", "0.5")))
    parser.add_argument("--results-csv", type=Path, default=RESULTS_CSV)
    parser.add_argument("--output", type=Path, help="Output results CSV path")
    parser.add_argument("--start-iteration", type=int, default=1, help="Resume from this iteration")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.host == "auto":
        args.host = auto_detect_windows_host()
        print(f"[lms-benign] Auto-detected Windows host: {args.host}", file=sys.stderr)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    results_csv = args.output or args.results_csv

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
                    print(f"[lms-benign] Resuming from iteration {start_iter} (found {max_iter} completed)", file=sys.stderr)
        except Exception:
            pass

    if start_iter > args.iterations:
        print(f"[lms-benign] Already completed {args.iterations} iterations", file=sys.stderr)
        return 0

    if not server_healthy(args):
        print(f"[lms-benign] LMS not healthy at {args.host}:{args.port}", file=sys.stderr)
        return 1

    print(f"[lms-benign] LMS healthy, starting {args.iterations} iterations", file=sys.stderr)

    fieldnames = [
        "iteration", "prompt_id", "canary_token",
        "started_at", "completed_at", "latency_s",
        "output_tokens", "echoed_canary_visible", "echoed_canary_reasoning",
        "status", "error", "response_status",
        "model", "max_tokens", "request_json_size",
        "memory_rss_kb_before", "memory_rss_kb_after", "memory_rss_delta_kb",
        "lms_pids",
    ]

    mode = "a" if results_csv.exists() else "w"
    with results_csv.open(mode, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if mode == "w":
            writer.writeheader()
        handle.flush()

        for iteration in range(start_iter, args.iterations + 1):
            row = run_iteration(args, iteration)
            write_row(writer, handle, row)
            print(
                f"[lms-benign] {row['iteration']:03d}/{args.iterations:03d} "
                f"status={row['status']} latency={row['latency_s']}s "
                f"tokens={row['output_tokens']} canary_visible={row['echoed_canary_visible']} "
                f"canary_reasoning={row['echoed_canary_reasoning']}",
                file=sys.stderr,
            )

    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda _signum, _frame: sys.exit(130))
    raise SystemExit(main())
