#!/usr/bin/env python3
# Track B: re-run phase2-adversarial-harness's direct-repeat (token_smuggle) and
# role-manipulation (role_reversal) prompts at n=20 each (not the original 2-3),
# to resolve the leak-rate discrepancy across PHI4_DEFENSE_NEW.md / GAP_ANALYSIS_REPORT.md.
# Reuses the existing harness's run_iteration()/main() unmodified; only restricts
# the in-memory prompt list before calling main(), and points results at a
# separate CSV so the original phase2_adversarial_results.csv is untouched.
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = REPO_ROOT / "scripts" / "phase2-adversarial-harness.py"

spec = importlib.util.spec_from_file_location("phase2_adversarial_harness", HARNESS_PATH)
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)

KEEP = {"token_smuggle", "role_reversal"}
harness.ADVERSARIAL_PROMPTS = [p for p in harness.ADVERSARIAL_PROMPTS if p["name"] in KEEP]
assert len(harness.ADVERSARIAL_PROMPTS) == 2, harness.ADVERSARIAL_PROMPTS

harness.PHASE2_RESULTS_CSV = REPO_ROOT / "logs" / "track_b_resolved_results.csv"
harness.PHASE2_ANOMALIES_CSV = REPO_ROOT / "logs" / "track_b_resolved_anomalies.csv"

sys.argv = [
    "track_b_phase2_subset.py",
    "--iterations", "20",
    "--max-tokens", "64",
    "--port", "8080",
    "--timeout", "120",
    "--model", "phi-4-reasoning-plus",
    "--results-csv", str(harness.PHASE2_RESULTS_CSV),
    "--anomalies-csv", str(harness.PHASE2_ANOMALIES_CSV),
]

if __name__ == "__main__":
    sys.exit(harness.main())
