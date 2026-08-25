#!/usr/bin/env python3
# Track F+ companion: simulates the A1 adversary by reading another
# process's /proc/<pid>/mem (a 1MB+ read == bpftrace trigger threshold).
# Used to verify the multilayer_monitor's bpftrace layer actually fires
# on real A1 activity, not just on ambient noise.
import json, sys, time
from pathlib import Path

PID = int(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(f"/tmp/a1_sim_{PID}.json")

result = {"pid": PID, "started": time.time(), "reads": []}
# Open the target's /proc/<pid>/mem, do one large read on a writable region.
with open(f"/proc/{PID}/mem", "rb", 0) as mem, open(f"/proc/{PID}/maps") as f:
    for line in f:
        parts = line.split()
        if len(parts) < 2: continue
        if "w" not in parts[1]: continue
        path = parts[5] if len(parts) >= 6 else ""
        if path.endswith(".gguf"): continue
        lo, hi = (int(x, 16) for x in parts[0].split("-"))
        size = hi - lo
        if size < (1 << 20): continue
        # 8 MB read on this region
        t0 = time.time()
        mem.seek(lo)
        chunk = mem.read(8 * (1 << 20))
        t1 = time.time()
        result["reads"].append({
            "range": parts[0], "perms": parts[1], "path": path or "[anon]",
            "size_kb": size // 1024, "requested_bytes": 8 * (1 << 20),
            "got_bytes": len(chunk), "elapsed_s": round(t1 - t0, 3),
        })
        break

result["finished"] = time.time()
OUT.write_text(json.dumps(result, indent=2))
print(f"simulated A1 read: {result['reads']}")
