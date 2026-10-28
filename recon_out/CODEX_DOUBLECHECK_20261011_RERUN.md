# LLAnalyzer Superpowers Double-Check Rerun — 2026-10-11

Fresh read-only verification pass; no manuscript, experiment script, historical
evidence, or figure-source file was edited during this rerun.

## Scope

- `df -h ~`: 26G available (86% used).
- No experiment harness, model server, model download, build, or network request
  was run. Structured records were parsed with standalone Python JSON reads.

## Fresh primary-record checks

| Family | Fresh result | Evidence |
|---|---|---|
| Slot equality | Four model keys, each `n=50`, `n_ok=50`, `exploit_confirmed_count=50`; aggregate 200/200. | `Runs/logs/n50_audit/slot_exploit_ALL4_audit1.json`; `Runs/scripts/n50_audit/run_slot_exploit.py` |
| July continuation | Four files, each `n=50`; KV hits Gemma 50, Qwen 50, Nemotron 25, Phi-4 1; memory hits 50 each; aggregate 126/200 and 200/200. | `Runs/logs/cross_tenant_extract/cross_tenant_extract_*20260704*_n50.json`, keys `n`, `kv_channel_hit_count`, `memory_channel_hit_count` |
| Direct injection | Four model files, each `n=50`, `n_ok=50`, `n_errors=0`; content/reasoning union 150/200. | `Runs/logs/n50_audit/injection_{gemma4,nemotron,phi4,qwen35}_audit1.json` |
| D4 residue | Exactly 200 primary JSONs; 50 each for Gemma→Phi-4, Qwen→Gemma, Nemotron→Qwen, Phi-4→Nemotron; all 200 same-process with positive post-swap observation. | `Runs/logs/d4_cross_model_20260624_201614_d4_*.json` |
| GPU-v5 | Exactly 50 primary JSONs; `canary_hit_count` 9 in 47 and 10 in 3; `extra_tenants[*].hits` 16 in all 50. | `Runs/logs/gpu_vram_v5_20260624_201614_gpuvram_*.json`; `Runs/scripts/gpu_vram_v5.py` |
| Twelve-tenant residue | Two Nemotron records, both 11/12 tenants: 110 copies/10834 KB and 78 copies/3352 KB. | `Runs/logs/leak_blast_radius_20260623_213831.json`; `Runs/logs/leak_blast_radius_20260624_120421.json` |
| Ollama telemetry | 206 run directories: Gemma 52, Qwen 51, Nemotron 51, Phi-4 52; 203 successful trigger-file runs, two explicit memory failures, one metadata-only incomplete record. | `Runs/TELEMETRY_RUN_*_ollama_*`, `triggers.jsonl`, `meta.json` |
| GGUF | Cross-model report describes 96 variants (24×4 labels), with 7 SIGABRT and 0 SIGSEGV in that report; other retained reports contain additional SIGABRT observations. No evidence supports a global zero-crash claim or the historical AFL++ total. | `Runs/experiments/reports/GGUF_CROSS_MODEL_REPORT.md`; retained surgical/tensor reports |

The raw D4 enumeration is 200 records and 50 per pair. A historical prose note
claiming 201/51 is not used. Separately named slot files were not pooled into
the manuscript's 200-trial denominator.

## Manuscript semantic check

- GPU-v5 is explicitly Nemotron under partial CUDA offload; Qwen is only a
  historical report-only reproduction (`T-IFS.tex:1123--1128`).
- Twelve-tenant rows are Nemotron-only and multilayer diagnostics Phi-4-only
  (`T-IFS.tex:507--510`, `779--780`; Supplementary Methods `474--477`).
- Four-model families remain four-model where records support them: slot,
  July continuation, injection, KV overhead, D4, LM-Studio hooks, and Ollama
  (`TIFS_Supplementary_Methods.tex:696--700`).
- RQ4 is same-process shared-state behavior; credentials, ownership,
  cross-principal authorization, and remote side channels are untested
  (`T-IFS.tex:572--576`).
- The 56-cell value is configured diagnostic scope, not a retained per-cell
  result (`TIFS_Supplementary_Methods.tex:496--501`).
- Sanitisation prose rejects causal effect-size inference (`T-IFS.tex:1000--1042`).
- 126/200 and its model split are intentionally preserved because the latest
  authoritative correction request required retaining the verified July result.
- Abstract word count is 217, below 250.

## Static unsupported-claim scan

No active claim was found for retained binary hash/equivalence, distinct-key
testing, CWE-862, timing AUC, McNemar analysis, Shodan/Internet prevalence,
`0.4.21`, or a global parser crash-zero result. Remaining `AFL++` mentions are
limitation statements saying the campaign total is not established; no AFL++
number is asserted.

## Fresh LaTeX and figure verification

Temporary outputs were written under `/tmp/paper_build.doublecheck.KZLu5V` and
`/tmp/figure_build.doublecheck.59nNpu`.

- Main manuscript: two `pdflatex` passes exit 0; 11 pages.
- Supplement: two passes exit 0; 5 pages.
- No fatal error, emergency stop, undefined reference, undefined citation, or
  overfull-box message; existing underfull-box warnings remain.
- Both figure sources build in one pass, one page each, with no figure-log
  errors. Rendered previews show no clipping or overlap; the architecture
  figure marks Nemotron-specific rows and the results figure separates the
  four-model continuation split from the Nemotron-only 11/12 row.

## Remaining limits

Original June executable hashes and the executed CUDA revision remain absent;
the October CPU-only rebuild is not evidence of byte identity. The GGUF
`phi3` label cannot be silently equated with script key `phi4`. Distinct-
principal/keyed-server behavior, non-Nemotron GPU-v5 coverage, per-repetition
allocator records, and timing vectors remain unverified without new evidence
or experiments.

