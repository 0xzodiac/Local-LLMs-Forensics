#!/usr/bin/env python3
"""Extract per-iteration clean/benign features from Phase 1 batch artifacts."""

from __future__ import annotations

import argparse
import csv
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_ROOT / "logs"
RESULTS_CSV = LOG_DIR / "phase1_baseline_results.csv"
FEATURES_CSV = LOG_DIR / "phase1_baseline_features.csv"
MONITOR_LOG_DIR = REPO_ROOT / "llama-monitor" / "logs"
MEM_DIR = MONITOR_LOG_DIR / "mem"
EBPF_DIR = MONITOR_LOG_DIR / "ebpf"

SYSCALL_FIELDS = {
    "read_calls": "read",
    "read_bytes": "read",
    "write_calls": "write",
    "write_bytes": "write",
    "mmap_calls": "mmap",
    "mmap_bytes": "mmap",
    "mlock_calls": "mlock",
    "mlock_bytes": "mlock",
    "madvise_calls": "madvise",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-csv", type=Path, default=RESULTS_CSV)
    parser.add_argument("--features-csv", type=Path, default=FEATURES_CSV)
    parser.add_argument("--mem-dir", type=Path, default=MEM_DIR)
    parser.add_argument("--ebpf-dir", type=Path, default=EBPF_DIR)
    return parser.parse_args()


def latest(path: Path, pattern: str) -> Path | None:
    matches = sorted(path.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def parse_iso(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def load_results(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing Phase 1 results CSV: {path}")
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def load_mem_rows(mem_dir: Path) -> list[dict[str, str]]:
    mem_csv = latest(mem_dir, "mem-*.csv")
    if not mem_csv:
        return []

    rows: list[dict[str, str]] = []
    with mem_csv.open(newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                row["_epoch"] = float(row["ts_epoch"])
                row["_rss"] = int(float(row.get("vm_rss_kb") or row.get("rss_kb") or 0))
                row["_minflt"] = int(float(row.get("minflt") or 0))
                row["_majflt"] = int(float(row.get("majflt") or 0))
            except Exception:
                continue
            rows.append(row)
    rows.sort(key=lambda r: float(r["_epoch"]))
    return rows


def nearest_mem(rows: list[dict[str, str]], epoch: float) -> dict[str, str] | None:
    if not rows:
        return None
    lo = 0
    hi = len(rows) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if float(rows[mid]["_epoch"]) < epoch:
            lo = mid + 1
        else:
            hi = mid
    candidates = [rows[lo]]
    if lo > 0:
        candidates.append(rows[lo - 1])
    return min(candidates, key=lambda r: abs(float(r["_epoch"]) - epoch))


def mem_between(rows: list[dict[str, str]], start: float, end: float) -> dict[str, float | None]:
    if not rows:
        return {
            "mem_rss_before_kb": None,
            "mem_rss_after_kb": None,
            "rss_delta_kb": None,
            "minflt_delta": None,
            "majflt_delta": None,
        }

    before = nearest_mem(rows, start)
    after = nearest_mem(rows, end)
    if before is None or after is None:
        return {
            "mem_rss_before_kb": None,
            "mem_rss_after_kb": None,
            "rss_delta_kb": None,
            "minflt_delta": None,
            "majflt_delta": None,
        }

    rss_before = float(before["_rss"])
    rss_after = float(after["_rss"])
    minflt_before = float(before["_minflt"])
    minflt_after = float(after["_minflt"])
    majflt_before = float(before["_majflt"])
    majflt_after = float(after["_majflt"])

    return {
        "mem_rss_before_kb": rss_before,
        "mem_rss_after_kb": rss_after,
        "rss_delta_kb": rss_after - rss_before,
        "minflt_delta": minflt_after - minflt_before,
        "majflt_delta": majflt_after - majflt_before,
    }


def parse_ebpf_totals(ebpf_dir: Path) -> dict[str, float]:
    syscall_log = latest(ebpf_dir, "syscall-trace-*.log")
    totals = {name: 0.0 for name in SYSCALL_FIELDS}
    if not syscall_log:
        return totals

    summary: dict[str, dict[str, float]] = {}
    for line in syscall_log.read_text(errors="replace").splitlines():
        match = re.match(r"\s*(read|write|mmap|mlock|madvise)\s+calls=(\d+)\s+bytes=(\d+)", line)
        if not match:
            continue
        name, calls, bytes_ = match.groups()
        summary[name] = {"calls": float(calls), "bytes": float(bytes_)}

    totals["read_calls"] = summary.get("read", {}).get("calls", 0.0)
    totals["read_bytes"] = summary.get("read", {}).get("bytes", 0.0)
    totals["write_calls"] = summary.get("write", {}).get("calls", 0.0)
    totals["write_bytes"] = summary.get("write", {}).get("bytes", 0.0)
    totals["mmap_calls"] = summary.get("mmap", {}).get("calls", 0.0)
    totals["mmap_bytes"] = summary.get("mmap", {}).get("bytes", 0.0)
    totals["mlock_calls"] = summary.get("mlock", {}).get("calls", 0.0)
    totals["mlock_bytes"] = summary.get("mlock", {}).get("bytes", 0.0)
    totals["madvise_calls"] = summary.get("madvise", {}).get("calls", 0.0)
    return totals


def fmt(value: float | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isfinite(value):
            return f"{value:.6f}"
        return ""
    return str(value)


def build_features(results: list[dict[str, str]], mem_rows: list[dict[str, str]], ebpf_totals: dict[str, float]) -> list[dict[str, str]]:
    total_latency = sum(max(float(row.get("latency_s") or 0), 0.0) for row in results)
    features: list[dict[str, str]] = []

    for row in results:
        started = parse_iso(row["started_at"]).timestamp()
        completed = parse_iso(row["completed_at"]).timestamp() if row.get("completed_at") else started
        latency = max(float(row.get("latency_s") or 0), 0.0)
        mem = mem_between(mem_rows, started, completed)

        scale = latency / total_latency if total_latency > 0 else 0.0
        feature: dict[str, str] = {
            "iteration": row.get("iteration", ""),
            "prompt_id": row.get("prompt_id", ""),
            "canary_token": row.get("canary_token", ""),
            "started_at": row.get("started_at", ""),
            "completed_at": row.get("completed_at", ""),
            "latency_s": row.get("latency_s", ""),
            "output_tokens": row.get("output_tokens", ""),
            "echoed_canary_visible": row.get("echoed_canary_visible", ""),
            "echoed_canary_reasoning": row.get("echoed_canary_reasoning", ""),
            "status": row.get("status", ""),
            "label": "clean",
        }
        feature.update({key: fmt(value) for key, value in mem.items()})

        for out_name, syscall_name in SYSCALL_FIELDS.items():
            if out_name.endswith("calls"):
                feature[out_name] = fmt(ebpf_totals[f"{syscall_name}_calls"] * scale)
            else:
                feature[out_name] = fmt(ebpf_totals[f"{syscall_name}_bytes"] * scale)

        if latency > 0:
            feature["read_rate_per_s"] = fmt(float(feature.get("read_calls") or 0) / latency)
            feature["write_rate_per_s"] = fmt(float(feature.get("write_calls") or 0) / latency)
            feature["mmap_rate_per_s"] = fmt(float(feature.get("mmap_calls") or 0) / latency)
        else:
            feature["read_rate_per_s"] = ""
            feature["write_rate_per_s"] = ""
            feature["mmap_rate_per_s"] = ""

        features.append(feature)

    return features


def main() -> int:
    args = parse_args()
    args.features_csv.parent.mkdir(parents=True, exist_ok=True)

    results = load_results(args.results_csv)
    mem_rows = load_mem_rows(args.mem_dir)
    ebpf_totals = parse_ebpf_totals(args.ebpf_dir)
    features = build_features(results, mem_rows, ebpf_totals)

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
        "label",
        "mem_rss_before_kb",
        "mem_rss_after_kb",
        "rss_delta_kb",
        "minflt_delta",
        "majflt_delta",
        "read_calls",
        "read_bytes",
        "write_calls",
        "write_bytes",
        "mmap_calls",
        "mmap_bytes",
        "mlock_calls",
        "mlock_bytes",
        "madvise_calls",
        "read_rate_per_s",
        "write_rate_per_s",
        "mmap_rate_per_s",
    ]

    with args.features_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(features)

    ok_rows = sum(1 for row in results if row.get("status") == "ok")
    echoed_visible = sum(1 for row in results if row.get("echoed_canary_visible") == "True")
    echoed_reasoning = sum(1 for row in results if row.get("echoed_canary_reasoning") == "True")
    rss_values = [float(row["rss_delta_kb"]) for row in features if row.get("rss_delta_kb")]
    avg_rss_delta = sum(rss_values) / len(rss_values) if rss_values else 0.0

    print(f"results={len(results)} ok={ok_rows} features={len(features)}")
    print(f"echoed_visible={echoed_visible} echoed_reasoning={echoed_reasoning}")
    print(f"avg_rss_delta_kb={avg_rss_delta:.3f}")
    print(f"features_csv={args.features_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
