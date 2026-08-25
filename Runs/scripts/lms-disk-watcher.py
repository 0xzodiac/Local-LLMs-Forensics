#!/usr/bin/env python3
"""LM Studio disk watcher: monitor profile dir for new/changed files + SQLite crawl."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sqlite3
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_ROOT / "logs"
RESULTS_CSV = LOG_DIR / "lms_disk_events.csv"
SQLITE_DUMP = LOG_DIR / "lms_sqlite_crawl.json"

LMS_PROFILE_DIRS = [
    Path("/mnt/c/Users/w.i/AppData/Roaming/LM Studio"),
    Path("/mnt/c/Users/w.i/.cache/lm-studio"),
    Path.home() / ".local/share/lm-studio",
    Path.home() / "Library/Application Support/LM Studio",
    Path.home() / ".lmstudio",
]

WATCH_SUBDIRS = ["conversations", "logs", "cache", "models"]
POLL_INTERVAL = 2.0


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    print(f"[{utc_now()}] {msg}", file=sys.stderr)


def find_profile_dir() -> Path | None:
    for d in LMS_PROFILE_DIRS:
        if d.exists():
            return d
    return None


def file_hash(path: Path) -> str:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()[:16]
    except Exception:
        return ""


class DiskWatcher:
    def __init__(self, profile_dir: Path, canary: str = ""):
        self.profile_dir = profile_dir
        self.canary = canary
        self._snapshots: list[dict[str, Any]] = []
        self._file_states: dict[str, str] = {}  # path -> hash
        self._running = False
        self._thread: threading.Thread | None = None
        self._init_snapshot()

    def _init_snapshot(self) -> None:
        for root, dirs, files in os.walk(self.profile_dir):
            for f in files:
                fp = Path(root) / f
                try:
                    self._file_states[str(fp)] = file_hash(fp)
                except Exception:
                    pass
        log(f"Initial snapshot: {len(self._file_states)} files")

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()
        log(f"Disk watcher started on {self.profile_dir}")

    def stop(self) -> list[dict[str, Any]]:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        log(f"Disk watcher stopped: {len(self._snapshots)} events")
        return self._snapshots

    def _poll(self) -> None:
        while self._running:
            current_states: dict[str, str] = {}
            for root, dirs, files in os.walk(self.profile_dir):
                for f in files:
                    fp = Path(root) / f
                    try:
                        current_states[str(fp)] = file_hash(fp)
                    except Exception:
                        pass

            for path_str, new_hash in current_states.items():
                old_hash = self._file_states.get(path_str)
                if old_hash is None:
                    event = {
                        "ts": utc_now(),
                        "path": path_str,
                        "event": "created",
                        "size": Path(path_str).stat().st_size,
                        "hash": new_hash,
                    }
                    self._snapshots.append(event)
                    self._file_states[path_str] = new_hash
                elif old_hash != new_hash:
                    event = {
                        "ts": utc_now(),
                        "path": path_str,
                        "event": "modified",
                        "size": Path(path_str).stat().st_size,
                        "hash": new_hash,
                    }
                    self._snapshots.append(event)
                    self._file_states[path_str] = new_hash

            time.sleep(POLL_INTERVAL)


def crawl_sqlite_dbs(profile_dir: Path, canary: str = "") -> list[dict[str, Any]]:
    results = []
    for root, dirs, files in os.walk(profile_dir):
        for f in files:
            if not f.endswith(".db") and not f.endswith(".sqlite"):
                continue
            fp = Path(root) / f
            try:
                conn = sqlite3.connect(f"file:{fp}?mode=ro", uri=True)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                for (table_name,) in tables:
                    try:
                        cursor.execute(f"SELECT * FROM \"{table_name}\" LIMIT 100")
                        columns = [desc[0] for desc in cursor.description]
                        rows = cursor.fetchall()
                        for row in rows:
                            row_dict = dict(zip(columns, row))
                            row_str = json.dumps(row_dict, default=str)
                            has_canary = canary and canary in row_str
                            results.append({
                                "db_path": str(fp),
                                "table": table_name,
                                "row": row_dict,
                                "has_canary": has_canary,
                            })
                    except Exception:
                        pass
                conn.close()
            except Exception:
                pass
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canary", default="", help="Canary token to search for")
    parser.add_argument("--duration", type=int, default=0, help="Monitor duration (0 = until Ctrl-C)")
    parser.add_argument("--crawl-only", action="store_true", help="Only crawl SQLite, no monitoring")
    parser.add_argument("--output", type=Path, default=RESULTS_CSV)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    profile_dir = find_profile_dir()
    if not profile_dir:
        log("LM Studio profile dir not found. Checked: " + ", ".join(str(d) for d in LMS_PROFILE_DIRS))
        log("Will create empty report.")
        profile_dir = Path("/tmp/lms-dummy-profile")
        profile_dir.mkdir(parents=True, exist_ok=True)

    log(f"Using profile dir: {profile_dir}")

    if args.crawl_only:
        sqlite_results = crawl_sqlite_dbs(profile_dir, args.canary)
        with open(SQLITE_DUMP, "w") as f:
            json.dump(sqlite_results, f, indent=2, default=str)
        log(f"SQLite crawl: {len(sqlite_results)} rows from {SQLITE_DUMP}")
        return 0

    watcher = DiskWatcher(profile_dir, args.canary)
    watcher.start()

    try:
        if args.duration > 0:
            time.sleep(args.duration)
        else:
            log("Monitoring until Ctrl-C...")
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        log("Interrupted")

    events = watcher.stop()

    fieldnames = ["ts", "path", "event", "size", "hash"]
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(events)

    log(f"Disk events: {len(events)} written to {args.output}")

    if profile_dir.exists():
        sqlite_results = crawl_sqlite_dbs(profile_dir, args.canary)
        with open(SQLITE_DUMP, "w") as f:
            json.dump(sqlite_results, f, indent=2, default=str)
        canary_hits = sum(1 for r in sqlite_results if r.get("has_canary"))
        log(f"SQLite crawl: {len(sqlite_results)} rows, {canary_hits} canary hits -> {SQLITE_DUMP}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
