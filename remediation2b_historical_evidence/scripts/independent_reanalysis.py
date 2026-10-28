#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "Runs"
OUT = ROOT / "remediation2b_historical_evidence"

MEMORY_FILES = {
    "baseline": RUNS / "logs/leak_blast_radius_20260623_213831.json",
    "sanitised": RUNS / "logs/leak_blast_radius_20260624_120421.json",
}
SLOT_FILE = RUNS / "logs/n50_audit/slot_exploit_ALL4_audit1.json"
EXTRACT_FILES = {
    "gemma4": RUNS / "logs/cross_tenant_extract/cross_tenant_extract_gemma4_20260704_n50.json",
    "qwen35": RUNS / "logs/cross_tenant_extract/cross_tenant_extract_qwen35_20260704_n50.json",
    "nemotron": RUNS / "logs/cross_tenant_extract/cross_tenant_extract_nemotron_20260704_n50.json",
    "phi4": RUNS / "logs/cross_tenant_extract/cross_tenant_extract_phi4_20260704_phi4_n50.json",
}
LATENCY_FILE = RUNS / "logs/n50_audit/kv_overhead_ALL_audit1.json"
MODEL_DIGESTS = RUNS / "provenance/model_digests.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def wilson(successes: int, trials: int, z: float = 1.959963984540054) -> dict[str, float]:
    if trials <= 0:
        return {"low": math.nan, "high": math.nan, "point": math.nan}
    p = successes / trials
    denominator = 1.0 + z * z / trials
    centre = (p + z * z / (2.0 * trials)) / denominator
    half = z * math.sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials)) / denominator
    return {"low": centre - half, "high": centre + half, "point": p}


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def mean_ci_difference(left: list[float], right: list[float]) -> dict[str, Any]:
    mean_left = statistics.fmean(left)
    mean_right = statistics.fmean(right)
    variance_left = statistics.variance(left) if len(left) > 1 else 0.0
    variance_right = statistics.variance(right) if len(right) > 1 else 0.0
    standard_error = math.sqrt(variance_left / len(left) + variance_right / len(right))
    difference = mean_left - mean_right
    return {
        "difference": difference,
        "low": difference - 1.96 * standard_error,
        "high": difference + 1.96 * standard_error,
        "method": "Welch normal approximation; independent-condition assumption; descriptive only",
    }


def validate_memory() -> dict[str, Any]:
    records: dict[str, Any] = {}
    checks: dict[str, Any] = {}
    required = {
        "run_id", "iso", "model", "n_tenants", "tenants_recovered",
        "recovery_rate", "total_canary_copies_across_all_tenants",
        "per_tenant_copies", "printable_cleartext_kb", "samples", "binary",
        "binary_has_zero_cell_data",
    }
    for condition, path in MEMORY_FILES.items():
        record = load_json(path)
        records[condition] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
            "record": record,
        }
        per_tenant = record.get("per_tenant_copies")
        values = list(per_tenant.values()) if isinstance(per_tenant, dict) else []
        expected_rate = record.get("tenants_recovered", 0) / record.get("n_tenants", 1)
        positive_tenants = sum(1 for value in values if isinstance(value, int) and value > 0)
        checks[condition] = {
            "missing_fields": sorted(required - record.keys()),
            "tenant_key_count_matches": len(values) == record.get("n_tenants"),
            "tenant_values_nonnegative_integers": all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in values),
            "copy_sum_matches": sum(values) == record.get("total_canary_copies_across_all_tenants"),
            "positive_tenant_count_matches": positive_tenants == record.get("tenants_recovered"),
            "rate_matches": math.isclose(float(record.get("recovery_rate")), expected_rate, abs_tol=0.0002),
            "samples_nonempty_and_unique": isinstance(record.get("samples"), list) and all(isinstance(sample, str) and sample for sample in record["samples"]) and len(record["samples"]) == len(set(record["samples"])),
            "zero_cell_flag_true": record.get("binary_has_zero_cell_data") is True,
        }
    baseline = records["baseline"]["record"]
    sanitised = records["sanitised"]["record"]
    baseline_copies = sum(baseline["per_tenant_copies"].values())
    sanitised_copies = sum(sanitised["per_tenant_copies"].values())
    baseline_kb = baseline["printable_cleartext_kb"]
    sanitised_kb = sanitised["printable_cleartext_kb"]
    return {
        "records": records,
        "checks": checks,
        "recomputed": {
            "baseline_copies": baseline_copies,
            "sanitised_copies": sanitised_copies,
            "copy_reduction_percent": 100.0 * (baseline_copies - sanitised_copies) / baseline_copies,
            "baseline_recorded_kb": baseline_kb,
            "sanitised_recorded_kb": sanitised_kb,
            "recorded_kb_reduction_percent": 100.0 * (baseline_kb - sanitised_kb) / baseline_kb,
            "baseline_recovery_rate": baseline["tenants_recovered"] / baseline["n_tenants"],
            "sanitised_recovery_rate": sanitised["tenants_recovered"] / sanitised["n_tenants"],
        },
        "cross_condition": {
            "same_model": baseline["model"] == sanitised["model"],
            "same_tenant_count": baseline["n_tenants"] == sanitised["n_tenants"],
            "same_binary_path": baseline["binary"] == sanitised["binary"],
            "same_zero_cell_flag": baseline["binary_has_zero_cell_data"] is True and sanitised["binary_has_zero_cell_data"] is True,
        },
        "validity_boundary": [
            "Aggregate copy totals and recovery rates are independently recomputed from retained fields.",
            "Recorded printable_cleartext_kb is accepted as a stored aggregate because regions, offsets, and raw acquisition output are absent.",
            "The retained schema cannot identify the historical executable hash or causally attribute the difference to a particular patch.",
        ],
    }


def validate_slot_and_extract() -> dict[str, Any]:
    slot = load_json(SLOT_FILE)
    direct: dict[str, Any] = {}
    total_direct_rows = 0
    for model, record in slot.items():
        rows = record.get("results", [])
        ok_rows = [row for row in rows if row.get("ok")]
        confirmed_rows = [row for row in ok_rows if row.get("exploit_confirmed")]
        total_direct_rows += len(rows)
        direct[model] = {
            "n_field": record.get("n"),
            "row_count": len(rows),
            "ok_count_recomputed": len(ok_rows),
            "confirmed_count_recomputed": len(confirmed_rows),
            "confirmed_rate_recomputed": len(confirmed_rows) / len(ok_rows) if ok_rows else None,
            "summary_consistent": record.get("n") == len(rows) and record.get("n_ok") == len(ok_rows) and record.get("exploit_confirmed_count") == len(confirmed_rows),
        }
    extract: dict[str, Any] = {}
    for model, path in EXTRACT_FILES.items():
        record = load_json(path)
        rows = record.get("results", [])
        fields: dict[str, Any] = {}
        for field in ["transfer_confirmed", "kv_channel_hit", "memory_channel_hit", "either_channel_hit"]:
            count = sum(1 for row in rows if row.get(field) is True)
            fields[field] = {
                "count": count,
                "n": len(rows),
                "rate": count / len(rows) if rows else None,
                "wilson_95": wilson(count, len(rows)),
                "summary_matches": record.get(field + "_count") == count and math.isclose(float(record.get(field + "_rate")), count / len(rows), abs_tol=1e-12),
            }
        trial_ids = [row.get("i") for row in rows]
        secret_values = [row.get("secret") for row in rows]
        extract[model] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
            "model_field": record.get("model"),
            "n_field": record.get("n"),
            "row_count": len(rows),
            "duplicate_trial_ids": sorted(k for k, v in Counter(trial_ids).items() if v > 1),
            "duplicate_secret_values": len(secret_values) - len(set(secret_values)),
            "fields": fields,
            "validity_notes": [
                "Rows support protocol-level transfer and recorded channel hits for this retained run family.",
                "The records do not independently establish that the two API keys represented distinct authorization principals beyond harness labels.",
                "The continuation channel is model-mediated and is not the same claim as direct slot-state transfer.",
            ],
        }
    pooled: dict[str, Any] = {}
    for field in ["transfer_confirmed", "kv_channel_hit", "memory_channel_hit", "either_channel_hit"]:
        count = sum(value["fields"][field]["count"] for value in extract.values())
        trials = sum(value["fields"][field]["n"] for value in extract.values())
        pooled[field] = {"count": count, "n": trials, "rate": count / trials if trials else None, "wilson_95": wilson(count, trials)}
    return {
        "direct_slot_file": {"path": str(SLOT_FILE.relative_to(ROOT)), "sha256": sha256(SLOT_FILE), "models": direct, "all_rows": total_direct_rows},
        "detailed_extraction": extract,
        "pooled_detailed_totals": pooled,
        "interpretation": "200/200 transfer and 126/200 KV continuation are independently recomputed from retained per-trial JSON; source-revision and binary attribution remain unavailable.",
    }


def validate_latency() -> dict[str, Any]:
    record = load_json(LATENCY_FILE)
    grouped: dict[str, Any] = {}
    for key, value in record.items():
        raw_values = value.get("latencies")
        valid = isinstance(raw_values, list) and all(isinstance(item, (int, float)) and math.isfinite(item) for item in raw_values)
        if not valid:
            grouped[key] = {"valid": False, "reason": "latencies is not a finite numeric list"}
            continue
        values = [float(item) for item in raw_values]
        grouped[key] = {
            "valid": True,
            "model": value.get("model"),
            "mode": value.get("mode"),
            "n_field": value.get("n"),
            "n_recomputed": len(values),
            "mean_recorded": value.get("mean_s"),
            "mean_recomputed": statistics.fmean(values),
            "sd_recomputed": statistics.stdev(values) if len(values) > 1 else None,
            "p50_recomputed": percentile(values, 0.50),
            "p95_recomputed": percentile(values, 0.95),
            "range_recomputed": [min(values), max(values)],
            "mean_field_matches": math.isclose(float(value.get("mean_s")), statistics.fmean(values), rel_tol=1e-12, abs_tol=1e-12),
        }
    for model in sorted({item.get("model") for item in grouped.values() if item.get("valid")}):
        patched_key = next(key for key, value in record.items() if value.get("model") == model and value.get("mode") == "patched")
        unpatched_key = next(key for key, value in record.items() if value.get("model") == model and value.get("mode") == "unpatched")
        patched = grouped[patched_key]
        unpatched = grouped[unpatched_key]
        patched_values = [float(item) for item in record[patched_key]["latencies"]]
        unpatched_values = [float(item) for item in record[unpatched_key]["latencies"]]
        patched["difference_vs_unpatched_s"] = patched["mean_recomputed"] - unpatched["mean_recomputed"]
        patched["relative_difference_percent"] = 100.0 * patched["difference_vs_unpatched_s"] / unpatched["mean_recomputed"]
        patched["descriptive_difference_ci_95"] = mean_ci_difference(patched_values, unpatched_values)
    return {
        "path": str(LATENCY_FILE.relative_to(ROOT)),
        "sha256": sha256(LATENCY_FILE),
        "conditions": grouped,
        "boundary": "These are patched/unpatched latency vectors for the KV benchmark, not the missing cached-versus-uncached TTFT vectors used for the manuscript AUC claim. No equivalence test is claimed.",
    }


def telemetry_summary() -> dict[str, Any]:
    lmstudio: list[dict[str, Any]] = []
    ollama_with_summary: list[dict[str, Any]] = []
    ollama_total = 0
    for path in sorted(RUNS.glob("TELEMETRY_RUN_*")):
        if not path.is_dir() or not (path / "meta.json").exists():
            continue
        meta = load_json(path / "meta.json")
        summary_path = path / "summary.json"
        summary = load_json(summary_path) if summary_path.exists() else None
        snapshots_path = path / "idle_snapshots.json"
        snapshots = load_json(snapshots_path) if snapshots_path.exists() else []
        row = {
            "path": str(path.relative_to(ROOT)),
            "tool": meta.get("tool"),
            "model": meta.get("model"),
            "has_summary": summary is not None,
            "summary_sha256": sha256(summary_path) if summary_path.exists() else None,
            "summary_any_canary_egress": summary.get("any_canary_egress") if isinstance(summary, dict) else None,
            "summary_external_destinations": summary.get("pcap_external_destinations") if isinstance(summary, dict) else None,
            "idle_snapshot_count": len(snapshots) if isinstance(snapshots, list) else None,
            "idle_nonzero_connections": sum(1 for item in snapshots if isinstance(item, dict) and item.get("ns_ext_conns", 0) not in (0, None)),
        }
        if meta.get("tool") == "ollama":
            ollama_total += 1
            if summary is not None:
                ollama_with_summary.append(row)
        elif "lms" in path.name:
            lmstudio.append(row)
    return {
        "lmstudio_summary_runs": lmstudio,
        "ollama_runs_total": ollama_total,
        "ollama_runs_with_summary": ollama_with_summary,
        "ollama_runs_without_summary": ollama_total - len(ollama_with_summary),
        "limitations": [
            "LM Studio summaries show startup external connections but no canary in captured egress; encrypted payload contents were not decrypted.",
            "Most 2026-06-25 Ollama directories retain packet, trigger, and idle evidence without summary.json, so not every run has the same derived verdict envelope.",
            "The LM Studio plaintext server-log file itself is not retained in this project; persistence is supported by reports and probe references, not by a fresh scan of that original file.",
        ],
    }


def discover_inventory() -> dict[str, Any]:
    roots = [RUNS, ROOT / "remediation1", ROOT / "remediation2", ROOT / "LLAnalyzer-revised-10point"]
    class_counts: Counter[str] = Counter()
    root_counts: Counter[str] = Counter()
    parse_counts: Counter[str] = Counter()
    representatives = {
        MEMORY_FILES["baseline"], MEMORY_FILES["sanitised"], SLOT_FILE,
        *EXTRACT_FILES.values(), LATENCY_FILE, MODEL_DIGESTS,
        RUNS / "experiments/reports/GGUF_SURGICAL_REPORT.md",
        RUNS / "experiments/reports/KV_CACHE_PATCH_REPORT.md",
        RUNS / "experiments/reports/CROSS_TENANT_SLOT_RESTORE_VULNERABILITY.md",
        RUNS / "experiments/reports/TELEMETRY_FINDINGS_4MODELS.md",
        ROOT / "remediation1/REMEDIATION1_COMPLETION_REPORT.md",
        ROOT / "remediation2/reports/REMEDIATION2_COMPLETION_REPORT.md",
    }
    hashed_representatives = []
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT)
            root_counts[relative.parts[0]] += 1
            suffix = path.suffix.lower()
            name = path.name.lower()
            if path in representatives:
                hashed_representatives.append({"path": str(relative), "bytes": path.stat().st_size, "sha256": sha256(path)})
            if "remediation2/source" in str(relative) or "remediation2/builds" in str(relative):
                artifact_class = "new remediation source/build evidence"
            elif "experiments/reports" in str(relative) or suffix in {".md", ".txt"}:
                artifact_class = "hand-written summary or documentation"
            elif "scripts" in relative.parts or suffix in {".py", ".sh", ".ps1", ".cpp", ".h"}:
                artifact_class = "analysis script or program source"
            elif suffix in {".json", ".jsonl", ".csv", ".tsv", ".sqlite", ".parquet"}:
                artifact_class = "structured machine-generated candidate"
            elif suffix in {".log", ".pcap"}:
                artifact_class = "execution or capture log"
            elif suffix in {".tex", ".pdf", ".bib"}:
                artifact_class = "manuscript or derived publication artifact"
            else:
                artifact_class = "other artifact"
            class_counts[artifact_class] += 1
            if suffix == ".json":
                try:
                    value = load_json(path)
                    parse_counts["json_parse_ok"] += 1
                    if not isinstance(value, (dict, list)):
                        parse_counts["json_noncontainer"] += 1
                except Exception:
                    parse_counts["json_parse_error"] += 1
    return {
        "root_file_counts": dict(root_counts),
        "classification_counts": dict(class_counts),
        "json_parse_counts": dict(parse_counts),
        "representative_hashed_artifacts": sorted(hashed_representatives, key=lambda item: item["path"]),
        "search_scope": [str(path.relative_to(ROOT)) for path in roots],
        "exclusions": [
            "Remediation2 source/build internals are counted as new engineering evidence, not historical experiment records.",
            "Large model archives and packet captures are inventoried by path but not copied or altered.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT / "analysis/independent_reanalysis.json")
    args = parser.parse_args()
    result = {
        "tool": "remediation2b_historical_evidence/scripts/independent_reanalysis.py",
        "inputs_are_read_only": True,
        "memory": validate_memory(),
        "slot_and_extract": validate_slot_and_extract(),
        "latency": validate_latency(),
        "telemetry": telemetry_summary(),
        "inventory": discover_inventory(),
        "timing_auc": {
            "status": "not_recomputed",
            "reason": "No retained per-request cached/uncached TTFT vectors or original AUC script were found in the targeted search.",
            "rendered_artifacts_only": [
                "LLAnalyzer-revised-10point/figures/timing_auc_decay.pdf",
                "LLAnalyzer-revised-10point/figures/timing_auc_decay.png",
            ],
        },
        "rq1": {
            "status": "summary_only",
            "reason": "The retained workspace contains GGUF analysis scripts and hand-written reports but no identifiable machine-generated 80-case, 21-file, or 24-hour fuzz result table with per-input status and sanitizer logs.",
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
