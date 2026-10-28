# Original artifact index

## Inventory scope

The historical-evidence audit inspected 3,277 files under `Runs/`, 14 under
`remediation1/`, 277 under the revised manuscript directory, and the Remediation
2 tree. It parsed 7,585 JSON files successfully and recorded 292 JSON parse
errors. Remediation 2 source/build internals are new engineering evidence and
are not relabeled as historical experiment records.

## Primary structured artifacts

| Artifact | Path | Purpose | Hash/status |
|---|---|---|---|
| Baseline memory aggregate | `Runs/logs/leak_blast_radius_20260623_213831.json` | 12-tenant baseline | `4d54ac8b...7dfb3f6`; full hash in historical audit |
| Sanitised memory aggregate | `Runs/logs/leak_blast_radius_20260624_120421.json` | 12-tenant sanitised record | `ef6f5cec...7169c63` |
| Slot transfer aggregate | `Runs/logs/n50_audit/slot_exploit_ALL4_audit1.json` | Four-model direct transfer | `1e1da4c6...0be24fcf` |
| Gemma extraction | `Runs/logs/cross_tenant_extract/cross_tenant_extract_gemma4_20260704_n50.json` | 50 continuation rows | `2cd8b0fd...0aaf3bee` |
| Nemotron extraction | `Runs/logs/cross_tenant_extract/cross_tenant_extract_nemotron_20260704_n50.json` | 50 continuation rows | `c6fb3dce...115eabd2` |
| Phi extraction | `Runs/logs/cross_tenant_extract/cross_tenant_extract_phi4_20260704_phi4_n50.json` | 50 continuation rows | `e3135f69...f65633` |
| Qwen extraction | `Runs/logs/cross_tenant_extract/cross_tenant_extract_qwen35_20260704_n50.json` | 50 continuation rows | `aee3669d...cc54ba9` |
| KV overhead vectors | `Runs/logs/n50_audit/kv_overhead_ALL_audit1.json` | 50/model patched/unpatched | `6fcc4c1c...dfbccd` |
| Model metadata | `Runs/provenance/model_digests.json` | Model digest record | `38ef84ff...c499ea` |

Ellipses above are readability abbreviations; the complete hashes are in
`remediation2b_historical_evidence/analysis/independent_reanalysis.json` and
`hashes/primary_artifacts.sha256`.

## Reports and scripts

- RQ1: `Runs/scripts/gguf-fuzzer.py`, `GGUF_SURGICAL_REPORT.md`,
  `GGUF_CROSS_MODEL_REPORT.md`, `GGUF_WEAPONIZATION_EXPLORATION.md`.
- RQ2: `DEEP_LEAK_REPORT.md`, `MEMORIZATION_VOLUME_REPORT.md`,
  `KV_CACHE_PATCH_REPORT.md`, `MITIGATION_TEST_REPORT.md`, GPU reports.
- RQ3: `LMS_FORENSICS_REPORT.md`, `OLLAMA_FORENSICS_REPORT.md`, telemetry
  summaries and run directories.
- RQ4: `CROSS_TENANT_SLOT_RESTORE_VULNERABILITY.md`, slot/extraction JSON,
  timing figure, and continuation reports.
- Analysis: `remediation2b_historical_evidence/scripts/independent_reanalysis.py`
  and `analysis/independent_reanalysis.json`.

## Missing or non-authoritative material

The original source checkout, historical executable hash, startup manifest,
valid historical prompt patch, raw timing vectors, and original AUC script were
not recovered. The Ikram server-side bundle is also absent from the local
workspace. These are provenance limitations, not evidence that the experiments
were never run.

