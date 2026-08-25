#!/usr/bin/env python3
# aggregate_ci.py -- P5 of RESEARCH_DEEPENING_PLAN.md
#
# Computes Wilson 95% CIs on every proportion claim in the paper's n>=50
# artifacts (not just the two headline ones sec:metrics already covers), and
# a bootstrap CI on the arena-probe copy-count deltas from P2 (paired repeats,
# same config across reps -- the correct answer to the degenerate-McNemar
# point in sec:metrics, which needs a paired difference distribution, not a
# proportion test).
#
# Read-only over existing logs/ artifacts; writes one summary JSON, does not
# modify any canonical file.
#
# Usage:
#   aggregate_ci.py
import glob
import json
import random
import statistics
from pathlib import Path

ROOT = Path("/home/elaref/research/tifs")
LOGS = ROOT / "logs"
OUT = LOGS / "aggregate_ci_report.json"


def wilson_ci(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)) / denom
    return {"n": n, "k": k, "point": round(p, 4),
            "low": round(max(0.0, center - half), 4), "high": round(min(1.0, center + half), 4)}


def bootstrap_diff_ci(a, b, iters=5000, seed=0):
    """Bootstrap 95% CI on mean(a) - mean(b) for two independent samples
    (e.g. baseline vs arena1 copy counts across repeated reps)."""
    if not a or not b:
        return None
    rng = random.Random(seed)
    diffs = []
    for _ in range(iters):
        sa = [rng.choice(a) for _ in a]
        sb = [rng.choice(b) for _ in b]
        diffs.append(statistics.mean(sa) - statistics.mean(sb))
    diffs.sort()
    lo = diffs[int(0.025 * iters)]
    hi = diffs[int(0.975 * iters)]
    return {"n_a": len(a), "n_b": len(b), "mean_a": round(statistics.mean(a), 2),
            "mean_b": round(statistics.mean(b), 2),
            "mean_diff": round(statistics.mean(a) - statistics.mean(b), 2),
            "ci95_low": round(lo, 2), "ci95_high": round(hi, 2)}


def slot_exploit_cis():
    f = LOGS / "n50_audit" / "slot_exploit_ALL4_audit1.json"
    if not f.exists():
        return {}
    d = json.loads(f.read_text())
    return {m: wilson_ci(v["exploit_confirmed_count"], v["n_ok"]) for m, v in d.items()}


def injection_cis():
    f = LOGS / "n50_audit" / "injection_ALL4_audit1.json"
    if not f.exists():
        return {}
    d = json.loads(f.read_text())
    out = {}
    for m, v in d.items():
        out[m] = {
            "leak_content": wilson_ci(v["leak_content"], v["n_ok"]),
            "leak_reasoning": wilson_ci(v["leak_reasoning"], v["n_ok"]),
        }
    return out


def arena_probe_deltas():
    """Bootstrap CI on copy-count deltas between configs, per model, from
    any arena_probe_*.json files P2 has produced so far."""
    out = {}
    for f in sorted(glob.glob(str(LOGS / "arena_probe" / "arena_probe_*.json"))):
        d = json.loads(Path(f).read_text())
        model = d["model"]
        configs = d.get("configs", {})
        by_config = {c: [rep["total_canary_copies_across_all_tenants"] for rep in v["reps"]]
                     for c, v in configs.items()}
        deltas = {}
        if "baseline" in by_config:
            for c, vals in by_config.items():
                if c == "baseline":
                    continue
                deltas[f"baseline_minus_{c}"] = bootstrap_diff_ci(by_config["baseline"], vals)
        out[model] = {"raw_per_config": by_config, "deltas_vs_baseline": deltas}
    return out


def main():
    report = {
        "slot_exploit_wilson_ci": slot_exploit_cis(),
        "injection_wilson_ci": injection_cis(),
        "arena_probe_bootstrap_deltas": arena_probe_deltas(),
    }
    OUT.write_text(json.dumps(report, indent=2))
    print(f"[aggregate_ci] wrote {OUT}\n")

    print("=== Slot exploit (Wilson 95% CI) ===")
    for m, ci in report["slot_exploit_wilson_ci"].items():
        if ci:
            print(f"  {m:12s} {ci['k']}/{ci['n']}  [{ci['low']}, {ci['high']}]")

    print("\n=== Reasoning-channel leak rates (Wilson 95% CI) ===")
    for m, chans in report["injection_wilson_ci"].items():
        for chan, ci in chans.items():
            if ci:
                print(f"  {m:12s} {chan:15s} {ci['k']}/{ci['n']}  [{ci['low']}, {ci['high']}]")

    print("\n=== Arena-probe copy-count deltas (bootstrap 95% CI) ===")
    if not report["arena_probe_bootstrap_deltas"]:
        print("  (no arena_probe_*.json artifacts found yet -- run arena_mitigation_probe.py first)")
    for m, v in report["arena_probe_bootstrap_deltas"].items():
        for name, ci in v["deltas_vs_baseline"].items():
            if ci:
                print(f"  {m:12s} {name:28s} mean_diff={ci['mean_diff']}  "
                      f"95% CI [{ci['ci95_low']}, {ci['ci95_high']}]  "
                      f"(baseline mean={ci['mean_a']}, other mean={ci['mean_b']})")


if __name__ == "__main__":
    main()
