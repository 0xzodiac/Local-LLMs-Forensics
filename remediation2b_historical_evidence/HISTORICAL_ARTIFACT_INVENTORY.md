# Historical artifact inventory

## Scope and counts

The discovery pass covered `Runs/`, `remediation1/`, `remediation2/`, and `LLAnalyzer-revised-10point/`, including logs, scripts, experiment reports, telemetry directories, manifests, archives, manuscript sources, and local Git objects. The generated inventory counted 3,277 files under `Runs/`, 14 under `remediation1/`, 198,028 under `remediation2/` including its source/build trees, and 277 under the revised manuscript directory. JSON parsing found 7,585 parseable JSON files and 292 JSON parse errors; the latter are not silently promoted to evidence.

The broad counts include repeated telemetry and new Remediation 2 source/build files. They are inventory counts, not counts of independent experiments.

## Primary structured records consumed

| Artifact | Classification | SHA-256 | Independent use |
|---|---|---|---|
| `Runs/logs/leak_blast_radius_20260623_213831.json` | Original structured aggregate | `4d54ac8bd771420a93617a0e63f1ab1fa786cdfdeb5dca9815b86c7337dfb3f6` | Baseline memory arithmetic |
| `Runs/logs/leak_blast_radius_20260624_120421.json` | Original structured aggregate | `ef6f5cecf832cabdb4d31620af371951ae727c75ed7644383662e00be7169c63` | Sanitised memory arithmetic |
| `Runs/logs/n50_audit/slot_exploit_ALL4_audit1.json` | Original per-trial structured output | `1e1da4c6849c4299c31503bccebad056122bbd20f0dd02f63428822c0be24fcf` | 200 direct transfers |
| `Runs/logs/cross_tenant_extract/cross_tenant_extract_gemma4_20260704_n50.json` | Original per-trial structured output | `2cd8b0fdcaf3b61dfb0ca89cee6c13e754b91209710cbaea9980495c0aaf3bee` | Transfer and continuation channels |
| `Runs/logs/cross_tenant_extract/cross_tenant_extract_nemotron_20260704_n50.json` | Original per-trial structured output | `c6fb3dce6f5adc335c530c84fa3e4925c15703c21ea96fe79041d7c4115eabd2` | Transfer and continuation channels |
| `Runs/logs/cross_tenant_extract/cross_tenant_extract_phi4_20260704_phi4_n50.json` | Original per-trial structured output | `e3135f69bcc9aa36a79b1a644a11164cdfd4a691476677ba3e13ae6afdf65633` | Transfer and continuation channels |
| `Runs/logs/cross_tenant_extract/cross_tenant_extract_qwen35_20260704_n50.json` | Original per-trial structured output | `aee3669d6e45d3dff94904ef9b055475eee9b9ec41e36fbf60bccd933cc54ba9` | Transfer and continuation channels |
| `Runs/logs/n50_audit/kv_overhead_ALL_audit1.json` | Original structured benchmark output | `6fcc4c1cb790498123cf13202cfc97cfe81f130a1a8510f33000ff64abdfbccd` | Patched/unpatched descriptive latency |
| `Runs/provenance/model_digests.json` | Execution/provenance record | `38ef84ff03648453fa5316aca6f49555595c5e32b39611dbbee6a20434c499ea` | Model identity claims only |

The full representative hash list, including telemetry summaries and reports, is in `analysis/independent_reanalysis.json`. Sensitive canary values are not reproduced in this inventory.

## Classification rules

- Original machine-generated raw or structured output: JSON, JSONL, telemetry captures, slot/extraction rows, and benchmark vectors with run-level fields.
- Derived statistical artifact: manuscript tables, rendered figures, aggregate reports, and recomputed output.
- Analysis script or program source: scripts, patch files, and source code.
- Hand-written summary/documentation: experiment reports and remediation reports.
- Manuscript/derived publication artifact: TeX, PDF, bibliography, and rendered figures.

Reports such as `GGUF_SURGICAL_REPORT.md` and `DEEP_LEAK_REPORT.md` are not treated as raw observations. Scripts containing expected values are not treated as evidence of execution.

## Important absence findings

No historical llama.cpp checkout, original executable, executable hash, startup manifest, or per-request cached/uncached TTFT vector was recovered. No machine-generated result table tying the claimed 80-case/21-file/24-hour GGUF campaign to individual inputs and sanitizer output was identified. The rendered timing figures remain derived publication artifacts.
