#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "Runs"
INPUTS = {
    "baseline": RUNS / "logs/leak_blast_radius_20260623_213831.json",
    "sanitised": RUNS / "logs/leak_blast_radius_20260624_120421.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_record(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def close_enough(left: float, right: float, tolerance: float = 0.0002) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=tolerance)


def validate_condition(name: str, path: Path, record: dict[str, Any]) -> dict[str, Any]:
    required = {
        "run_id",
        "iso",
        "model",
        "n_tenants",
        "tenants_recovered",
        "recovery_rate",
        "total_canary_copies_across_all_tenants",
        "per_tenant_copies",
        "printable_cleartext_kb",
        "samples",
        "binary",
        "binary_has_zero_cell_data",
    }
    missing = sorted(required.difference(record))
    per_tenant = record.get("per_tenant_copies")
    checks: dict[str, bool] = {}
    if isinstance(per_tenant, dict):
        values = list(per_tenant.values())
        positive_tenants = sum(value > 0 for value in values if isinstance(value, int))
        checks["tenant_key_count_matches_n_tenants"] = len(per_tenant) == record.get("n_tenants")
        checks["tenant_values_are_nonnegative_integers"] = all(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0
            for value in values
        )
        checks["copy_total_equals_per_tenant_sum"] = sum(values) == record.get(
            "total_canary_copies_across_all_tenants"
        )
        checks["recovered_tenant_count_equals_positive_copy_count"] = positive_tenants == record.get(
            "tenants_recovered"
        )
    else:
        positive_tenants = None
        checks["per_tenant_copies_is_object"] = False

    n_tenants = record.get("n_tenants")
    recovered = record.get("tenants_recovered")
    expected_rate = recovered / n_tenants if isinstance(n_tenants, int) and n_tenants else None
    checks["recovery_rate_matches_counts"] = expected_rate is not None and close_enough(
        float(record.get("recovery_rate", float("nan"))), expected_rate
    )
    samples = record.get("samples")
    checks["samples_are_nonempty_strings"] = isinstance(samples, list) and all(
        isinstance(sample, str) and bool(sample) for sample in samples
    )
    checks["sample_list_has_no_duplicates"] = isinstance(samples, list) and len(samples) == len(set(samples))
    checks["zero_cell_data_flag_is_true"] = record.get("binary_has_zero_cell_data") is True

    return {
        "path": str(path),
        "sha256": sha256(path),
        "run_id": record.get("run_id"),
        "iso": record.get("iso"),
        "model": record.get("model"),
        "binary": record.get("binary"),
        "n_tenants": n_tenants,
        "tenants_recovered": recovered,
        "recovery_rate_recorded": record.get("recovery_rate"),
        "recovery_rate_recomputed": expected_rate,
        "total_copies_recorded": record.get("total_canary_copies_across_all_tenants"),
        "total_copies_recomputed": sum(per_tenant.values()) if isinstance(per_tenant, dict) else None,
        "per_tenant_copies": per_tenant,
        "printable_cleartext_kb_recorded": record.get("printable_cleartext_kb"),
        "sample_count": len(samples) if isinstance(samples, list) else None,
        "positive_copy_tenant_count": positive_tenants,
        "required_fields_missing": missing,
        "checks": checks,
        "all_structural_checks_pass": not missing and all(checks.values()),
    }


def main() -> dict[str, Any]:
    conditions = {
        name: validate_condition(name, path, load_record(path)) for name, path in INPUTS.items()
    }
    baseline = conditions["baseline"]
    sanitised = conditions["sanitised"]
    baseline_copies = baseline["total_copies_recomputed"]
    sanitised_copies = sanitised["total_copies_recomputed"]
    baseline_kb = baseline["printable_cleartext_kb_recorded"]
    sanitised_kb = sanitised["printable_cleartext_kb_recorded"]
    copy_reduction = 100.0 * (baseline_copies - sanitised_copies) / baseline_copies
    volume_reduction = 100.0 * (baseline_kb - sanitised_kb) / baseline_kb

    cross_condition_checks = {
        "same_model": baseline["model"] == sanitised["model"],
        "same_tenant_count": baseline["n_tenants"] == sanitised["n_tenants"],
        "same_binary_path": baseline["binary"] == sanitised["binary"],
        "same_zero_cell_data_flag": baseline["checks"]["zero_cell_data_flag_is_true"]
        and sanitised["checks"]["zero_cell_data_flag_is_true"],
    }

    return {
        "validator": "remediation1/validation/verify_memory_results.py",
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "conditions": conditions,
        "recomputed": {
            "baseline_copies": baseline_copies,
            "sanitised_copies": sanitised_copies,
            "copy_reduction_percent": copy_reduction,
            "baseline_printable_cleartext_kb": baseline_kb,
            "sanitised_printable_cleartext_kb": sanitised_kb,
            "printable_cleartext_reduction_percent": volume_reduction,
        },
        "cross_condition_checks": cross_condition_checks,
        "interpretation_boundary": {
            "supported": [
                "The aggregate copy totals equal the sums of the retained per-tenant counts.",
                "The recorded recovery rates equal tenants_recovered divided by n_tenants.",
                "The retained records support descriptive reductions of the recorded aggregate metrics.",
            ],
            "not_supported_by_retained_schema": [
                "Independent byte-level recomputation of printable_cleartext_kb.",
                "Independent counting of memory regions, raw matches, or recovered plaintext bytes.",
                "Causal attribution to the prompt-zeroization patch without a verified source-to-binary-to-run chain.",
            ],
        },
        "all_checks_pass": all(
            condition["all_structural_checks_pass"] for condition in conditions.values()
        )
        and all(cross_condition_checks.values()),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = main()
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
