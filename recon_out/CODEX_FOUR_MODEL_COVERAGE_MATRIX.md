# LLAnalyzer four-model experimental coverage audit

Read-only reconstruction of retained scripts, raw records, logs, and reports. No experiment, server, model load, build, or manuscript edit was performed. Models: Gemma-4-E4B-it (`gemma4`), Qwen3.5-9B (`qwen35`), Nemotron-3-Nano-4B (`nemotron`), Phi-4-reasoning-plus (`phi4`). **EXECUTED** requires a retained primary record or model-specific execution log; **REPORTED ONLY** is historical report prose without linked per-trial records; **CONFIGURED ONLY** is a script model entry without an execution record; **NOT FOUND** means no supporting record located; **INCONCLUSIVE** means identity/completeness cannot be determined.

## Executive result

Direct four-model records exist for slot equality (50/model), July continuation (50/model), direct LM Studio injection (50/model), KV-overhead arrays (50/model/condition), D4 cross-model residue (200 primary pair trials), LM Studio hook summaries (one or more/model), and Ollama telemetry metadata (206 directories across all four model labels). The structured GGUF families report four architectures, but only reports are retained; the fourth architecture is written `phi3` while scripts use the `phi4` key, so exact Phi-4 artifact identity is not independently reconstructed from raw outputs.

The GPU result is split. The retained `gpu_vram_v5` host-memory scan is **Nemotron-only**: the script hard-codes Nemotron and paired server logs load its GGUF. Historical reports describe a Qwen3.5 GPU reproduction, so Qwen is **REPORTED ONLY** for that specific v5 result. No v5-equivalent Gemma/Phi primary record was found. Separately, the July continuation script configures per-model GPU offload and has four n=50 summaries; those are continuation records, not the v5 GPU-vram campaign.

## Coverage matrix

| RQ / family | Gemma | Qwen | Nemotron | Phi-4 | Counts and evidence |
|---|---|---|---|---|---|
| RQ1 GGUF ultimate (24 variants/model) | REPORTED ONLY | REPORTED ONLY | REPORTED ONLY | REPORTED ONLY (report says `phi3`) | 96 total, 24/model; 36 OK, 53 rc=1, 7 SIGABRT, 0 timeout. `Runs/experiments/reports/GGUF_CROSS_MODEL_REPORT.md:3-18,84-89`; script `Runs/scripts/ultimate-multimodel.py:1-12`. |
| RQ1 GGUF surgical / structural families | REPORTED ONLY | REPORTED ONLY | REPORTED ONLY | REPORTED ONLY (architecture caveat) | Surgical report describes 80 malformed-input, 21 structural, overlapping 96 ultimate and 20 chained tests; raw variant/result files absent. `Runs/experiments/reports/GGUF_SURGICAL_REPORT.md:1-4,94-101`; `GGUF_TENSOR_REPORT.md:5-22`; `GGUF_CROSS_MODEL_REPORT.md:5-18`. |
| RQ1 additional novel/weaponized attacks | NOT FOUND | NOT FOUND | REPORTED ONLY | NOT FOUND | Nemotron-base report: 12 variants. `Runs/experiments/reports/GGUF_NOVEL_ATTACKS_REPORT.md:1-8`; `GGUF_WEAPONIZATION_EXPLORATION.md`. |
| RQ2.1 twelve-tenant blast radius | NOT FOUND | NOT FOUND | EXECUTED | NOT FOUND | Two JSON observations, n=12 each, both 11/12 recovered; exact totals 110 copies/10834 KB and 78 copies/3352 KB. `Runs/logs/leak_blast_radius_20260623_213831.json` and `...20260624_120421.json`, keys `model,n_tenants,tenants_recovered,total_canary_copies_across_all_tenants,printable_cleartext_kb`. |
| RQ2.1 multilayer heap/KV diagnostics | NOT FOUND | NOT FOUND | NOT FOUND | EXECUTED | 11 JSON/server-log pairs; every paired server log loads Phi-4-reasoning-plus GGUF. `Runs/logs/multilayer_v2_*.json`; `Runs/logs/multilayer_v2_server_*.log`. |
| RQ2.2 D4 cross-model residue | EXECUTED | EXECUTED | EXECUTED | EXECUTED | 200 primary JSONs: 50 Gemma->Phi, 50 Qwen->Gemma, 50 Nemotron->Qwen, 50 Phi->Nemotron; one debug JSON excluded. `Runs/logs/d4_cross_model_20260624_201614_d4_{gemma4_phi4,qwen35_gemma4,nemotron_qwen35,phi4_nemotron}_*.json`; script `Runs/scripts/d4_cross_model_residue.py:18-24,79-86,116-175`. |
| RQ2.3 sanitisation / allocator | CONFIGURED ONLY | CONFIGURED ONLY | REPORTED ONLY | CONFIGURED ONLY | Script contains four model paths and GPU caps, but no `arena_probe_*.json`; aggregate-only Nemotron allocator evidence. `Runs/scripts/arena_mitigation_probe.py:45-68,206-250`; `LLAnalyzer_Master_Dossier/Results/MASTER_RESULTS_CATALOG.md:15-20`. |
| RQ2.4 GPU-v5 host-memory scan | NOT FOUND | REPORTED ONLY | EXECUTED | NOT FOUND | 50 primary JSONs plus one extra; v5 model is Nemotron; primary `canary_hit_count` is 9 in 47 and 10 in 3, extra-tenant field 16 in all 50. `Runs/scripts/gpu_vram_v5.py`; `Runs/logs/gpu_vram_v5_20260624_201614_gpuvram_1..50.json`; paired `gpu_vram_v5_server_*.log`; historical Qwen prose `Runs/experiments/reports/CROSS_TENANT_SLOT_RESTORE_VULNERABILITY.md:80-100`. |
| RQ2.4 other GPU probes (v2/v3/probe) | NOT FOUND | NOT FOUND | EXECUTED | NOT FOUND | Scripts and paired logs also hard-code/load Nemotron; no other model GPU-vram primary record located. `Runs/scripts/gpu_vram_v2.py`, `gpu_vram_v3.py`, `gpu_vram_probe.py`. |
| RQ2 KV-overhead | EXECUTED | EXECUTED | EXECUTED | EXECUTED | Patched and unpatched arrays, n=50 each model/condition. `Runs/logs/n50_audit/kv_overhead_{gemma4,qwen35,nemotron,phi4}_{patched,unpatched}_audit1.json`; script `Runs/scripts/n50_audit/run_kv_overhead.py:29-35,46-70,103-125`. |
| RQ3 LM Studio logging toggle | NOT FOUND | NOT FOUND | EXECUTED | NOT FOUND | Nemotron-only report: 10/10 baseline canaries found with logging on; none in examined post-change artifacts with logging off. `Runs/experiments/reports/MITIGATION_TEST_REPORT.md:3-5,42-111`. |
| RQ3 LM Studio egress hooks | EXECUTED | EXECUTED | EXECUTED | EXECUTED | Six hook directories: Nemotron x3, Gemma/Qwen/Phi x1. `Runs/TELEMETRY_RUN_20260623_*_lms_hook/meta.json` and `summary.json` identify all four. |
| RQ3 Ollama netns telemetry | EXECUTED | EXECUTED | EXECUTED | EXECUTED | 206 metadata dirs: Gemma 52, Qwen 51, Nemotron 51, Phi 52; one Qwen metadata-only; two explicit memory failures; retained aggregate 203 successful trigger files, 2 failures, 1 incomplete. `Runs/TELEMETRY_RUN_*_ollama_*/meta.json`, `triggers.jsonl`; `Runs/experiments/reports/TELEMETRY_FINDINGS_OLLAMA.md:1-16,38-66`. |
| RQ3 D7 PII-chain attempts (historical) | EXECUTED (50 logs/48 JSON) | EXECUTED (50/50) | EXECUTED (50/50) | EXECUTED (50 logs/42 JSON) | 201 logs and 191 JSONs; parsed model-labelled JSONs have `chain_confirmed=false`. `Runs/scripts/d7_pii_attack_chain.py:31-39,123-179`; `Runs/logs/d7_pii_chain_20260624_201614_d7_{gemma4,qwen35,nemotron,phi4}_*.log/.json`. |
| RQ4 slot save/restore equality | EXECUTED | EXECUTED | EXECUTED | EXECUTED | 50/model, 200 total; oracle `n_saved == n_restored`. `Runs/logs/n50_audit/slot_exploit_{gemma4,qwen35,nemotron,phi4}_audit1.json`; script `Runs/scripts/n50_audit/run_slot_exploit.py:27-33,50-66,80-111`. |
| RQ4 restored-state continuation | EXECUTED | EXECUTED | EXECUTED | EXECUTED | 50/model; KV hits 50,50,25,1 respectively; memory 50/model; records dated July 3--4. `Runs/logs/cross_tenant_extract/cross_tenant_extract_{gemma4,qwen35,nemotron,phi4}_*n50.json`; script `Runs/scripts/cross_tenant_plaintext_extract.py:51-71,174-187,200-277`. |
| RQ4 direct LM Studio injection | EXECUTED | EXECUTED | EXECUTED | EXECUTED | 50/model, five prompt templates, max_tokens 80; separate from continuation. `Runs/logs/n50_audit/injection_{gemma4,qwen35,nemotron,phi4}_audit1.json`; script `Runs/scripts/n50_audit/run_injection_test.py:29-35,48-84,87-145`. |
| RQ4 timing | REPORTED ONLY | REPORTED ONLY | REPORTED ONLY | REPORTED ONLY | Catalog says 100/model, but vectors/order manifest/analysis script absent. `LLAnalyzer_Master_Dossier/Results/MASTER_RESULTS_CATALOG.md:28-29`; current supplement `TIFS_Supplementary_Methods.tex:540-545,669-672`. |
| Historical slot reproduction (three setups) | NOT FOUND | REPORTED ONLY | REPORTED ONLY | REPORTED ONLY | Historical prose says Nemotron/CPU, Phi-4/CPU, Qwen/GPU, n=1 each; no linked raw set. `Runs/experiments/reports/CROSS_TENANT_SLOT_RESTORE_VULNERABILITY.md:80-100,180`. |

## Methodological equivalence

* **Slot equality:** same unauthenticated loopback server/process, CPU-only, context 2048, threads 8, parallel 2, max_tokens 24, 50 iterations/model, exact token-count equality oracle. Model path is the only intended change. No second client, key, or ownership control.
* **July continuation:** same save/restore plus rendered-prefix `/completion` KV channel and writable-memory scan. GPU offload is model-specific (Nemotron/Qwen/Gemma 999 layers; Phi 20), thread cap 4, parallel 2, and records are July. Logical protocol is shared, but offload is a nuisance factor.
* **Direct injection:** same LM Studio API, five canonical templates, max_tokens 80, temperature 0, 50/model. Separate from slot continuation.
* **KV overhead:** same CPU-only server command, context 2048, threads 8, parallel 1, max_tokens 8, patched/unpatched mode, n=50/model/condition. Descriptive latency comparison.
* **D4:** same-process swap, CPU-only, context 2048, threads 8, parallel 1, max_tokens 8; fixed 50-trial pair blocks rotate all four models. Byte-residue oracle, not output disclosure.
* **GGUF:** common `--check-tensors` objective and four configured keys, but only reports survive; corpora overlap and the fourth report label is `phi3`.
* **LM Studio hooks:** same netns/hook interpretation, but Nemotron has three runs and each other model one.
* **Ollama:** same isolated namespace and trigger protocol, but model-memory failures and one incomplete metadata record must remain separate from successful triggers; no executable version is retained.
* **Runtime/GPU:** twelve-tenant JSONs are Nemotron-only; multilayer diagnostics are Phi-4-only; allocator repetitions are not retained; v5 GPU-vram records are Nemotron-only.

## GPU investigation conclusion

1. `Runs/scripts/gpu_vram_v5.py` hard-codes the Nemotron Q4_K_M file and CUDA `llama-server`; all 50 primary v5 server logs repeat that model load. This is primary Nemotron evidence.
2. `CROSS_TENANT_SLOT_RESTORE_VULNERABILITY.md:80-100` describes a Qwen3.5 GPU reproduction and three ad-hoc setups, but no linked Qwen GPU-vram v5 JSON/model field was located. This is report-only Qwen evidence.
3. v2/v3/probe GPU scripts/logs also identify Nemotron. No Gemma/Phi v5-equivalent primary record was found.
4. The July continuation script separately covers all four models with per-model GPU-layer caps and retained n=50 summaries. It does not expand v5 GPU-vram coverage.
5. The defensible statement is: “50 Nemotron CUDA host-memory trials; a historical report separately describes a Qwen GPU reproduction without retained linked primary records.” The 50 v5 records are not demonstrably a model-balanced subset of a larger four-model GPU-vram campaign.

## Exact current-manuscript statements requiring correction or qualification

The manuscript was not edited in this audit.

1. `LLAnalyzer-revised-10point/T-IFS.tex:1106-1108` says the GPU experiment “directly evaluates Qwen3.5-9B under partial CUDA offloading.” Retained v5 code/logs identify Nemotron; change the model attribution or qualify historical Qwen prose as report-only.
2. `LLAnalyzer-revised-10point/TIFS_Supplementary_Methods.tex:466-483` says “For each model, we execute sequential multi-request sessions” and lists repeated mitigation configurations. Retained headline twelve-tenant rows are Nemotron-only; multilayer-v2 logs are Phi-4-only; allocator repetitions are absent. Qualify this as intended protocol versus retained model-specific rows.
3. `LLAnalyzer-revised-10point/T-IFS.tex:756-765` says the same behaviour is observed across multiple model families. Identify the exact heterogeneous protocols or avoid implying a balanced four-model runtime-memory baseline.
4. `LLAnalyzer-revised-10point/figures/fig_llanalyzer_arch.tex:120-123` labels “78 copies; 11/12 still” without a model; the retained row is Nemotron-specific and should be qualified if read as cross-model.
5. `LLAnalyzer-revised-10point/T-IFS.tex:611-618` and Table I present a four-model 96-test GGUF family; add a provenance caveat because reports say `phi3` while scripts say `phi4` and raw outputs are absent.

## Evidence gaps and accounting

No raw GGUF corpus/result CSV, allocator per-repetition JSON, Qwen/Gemma/Phi GPU-v5 record, or timing vector set was located. D7 has incomplete JSON persistence for Gemma and Phi. Ollama metadata contain no executable version. The pass counted 1,985 files under `Runs/`, 68 report files, 37 n50-audit files, 10 cross-tenant entries, 200 primary D4 JSONs plus one excluded debug JSON, 50 primary GPU-v5 JSONs plus one extra matching JSON, 206 Ollama metadata directories, six LM Studio hook directories, 201 D7 logs, 191 D7 JSONs, and 11 multilayer-v2 JSON/server-log pairs. Structured records were parsed with standalone Python; no repository script was imported or executed.

