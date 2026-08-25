#!/usr/bin/env python3
"""Build N50 audit index from TELEMETRY_RUN_* dirs."""
import json
from pathlib import Path
from collections import defaultdict

root = Path(".")
runs = sorted(root.glob("TELEMETRY_RUN_*"))
by_model = defaultdict(list)
for r in runs:
    meta_p = r / "meta.json"
    if not meta_p.exists():
        continue
    meta = json.loads(meta_p.read_text())
    by_model[meta["model"]].append((r.name, meta))

out = Path("experiments/telemetry_summary")
out.mkdir(exist_ok=True)
for model, entries in by_model.items():
    safe = model.replace("/", "_")
    p = out / f"SUMMARY_{safe}.md"
    lines = [f"# Telemetry Runs: {model}", "",
             f"Total runs: {len(entries)}", "",
             "| Run ID | Started | Duration (s) | Hook | Arch | Canary |",
             "|--------|---------|--------------|------|------|--------|"]
    for name, m in entries:
        lines.append(f"| `{name}` | {m['started_iso']} | {m['duration_sec']} | {m['hook']} | {m['architecture']} | `{m['canary']}` |")
    p.write_text("\n".join(lines) + "\n")
    print(f"Wrote {p} ({len(entries)} runs)")

master = Path("experiments/telemetry_summary/INDEX.md")
lines = ["# N50 Telemetry Audit Index", "",
         f"Total run directories: {len(runs)}", "",
         "## By Model", ""]
for model, entries in sorted(by_model.items()):
    lines.append(f"- **{model}**: {len(entries)} runs -> `SUMMARY_{model.replace('/', '_')}.md`")
lines += ["", "## Run Directory Structure", "",
          "Each run contains:",
          "- `meta.json` - capture metadata",
          "- `pcap/` - packet captures",
          "- `pcap_quick.json` - parsed summary",
          "- `hooks/` - LD_PRELOAD traces (when applicable)",
          "- `idle_snapshots.json` - process memory snapshots",
          "- `triggers.jsonl` - canary detection events"]
master.write_text("\n".join(lines) + "\n")
print(f"Wrote {master}")