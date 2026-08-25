# 🛡️ LLM Forensics Research Data
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Data: CC-BY](https://img.shields.io/badge/Data-CC--BY-green.svg)](https://creativecommons.org/licenses/by/4.0/)
[![DOI: Zenodo](https://img.shields.io/badge/DOI-10.5281/zenodo.[PENDING]-red.svg)](#) <!-- Replace [PENDING] with your actual numeric DOI -->
[![Status: TIFS Major Revision](https://img.shields.io/badge/Status-Under_Review-orange.svg)](#)

Public dataset, scripts, and reports supporting the LLM forensics paper submission (TIFS).

## Research Question

Do local LLM inference runtimes (Ollama, llama.cpp, LM Studio) leak pre-training
data, prior-session context, or model internals across the user/network boundary,
even under tenant isolation (network namespaces, LD_PRELOAD hooks)?

## Headline Finding

Canary tokens placed in prompts are recoverable from idle process memory and from
netns-egress packet captures at non-trivial rates across all four audited models
(Nemotron-3, Qwen-3.5, Gemma-4, Phi-4), even after request completion.

Full numbers + per-model breakdowns: `experiments/telemetry_summary/INDEX.md`
and `experiments/reports/RECONCILED_NUMBERS.md`.

## Repository Layout

```
experiments/
  scripts/                          Reproducer scripts
    run_all_n50_audits.sh           N=50 audit runner (4 models)
    run_d2_measurements.sh          D2 measurement script
    run_secure_allocator_test.sh    Secure allocator patch test
    batch_4models.sh                4-model batch runner
    phi4_defense_runner.py          Phi4 defense test driver
    phi4_analysis.py                Phi4 leak analyzer
    phi4_defense_test*.py           Phi4 defense variants
  reports/                          60+ analysis reports
    MASTER_FORENSICS_DOCUMENTATION.md   Canonical methodology
    RESEARCH_PROGRESS_MASTER.md         Live progress log
    FINAL_STATUS_REPORT.md              Status snapshot
    FINAL_AUDIT_REPORT.md               Final audit summary
    FINAL_COMPREHENSIVE_REPORT.md       Comprehensive findings
    CITATION_AUDIT.md                   Reference audit
    DISCLOSURE_PLAN.md                  Vendor disclosure plan
    RECONCILED_NUMBERS.md               Reconciled stats across runs
    STRENGTH_WEAKNESS_MAP.md            Per-attack strength scoring
    PROGRESS_D1_D3.md                   D1/D3 progress
    *_REPORT.md                         Per-experiment reports
    PAPER_DRAFT*.md                     Paper drafts (also in paper/)
  telemetry_summary/                Per-model run index
    INDEX.md                         Master N50 index
    SUMMARY_<model>.md               Per-model run table
  build_index.py                    Regenerate summary tables from raw runs

TELEMETRY_RUN_*/                    Raw capture dirs (N=212)
  meta.json                         Capture metadata
  pcap/                             Packet captures
  pcap_quick.json                   Parsed summary
  hooks/                            LD_PRELOAD traces (LMS only)
  idle_snapshots.json               Process memory snapshots
  triggers.jsonl                    Canary detection events
  canary_report.md                  Human-readable findings

logs/                               Run logs
patches/                            Kernel/libc patches
lms-leak-test/                      LMS subsystem test data
scripts/                            Additional helper scripts
```

## Audited Models

| Model | HuggingFace ID | N50 Runs | Capture Architecture |
|-------|---------------|----------|----------------------|
| Nemotron | nvidia/nemotron-3-nano-4b | 50 | netns-isolated |
| Qwen 3.5 | qwen/qwen3.5-9b | 50 | netns-isolated |
| Gemma 4 | gemma-4-e4b-it | 50 | netns-isolated |
| Phi-4 | microsoft/phi-4-reasoning-plus | 50 | netns-isolated |

Plus smaller LMS/Ollama baseline runs (4 runs total). See `experiments/telemetry_summary/INDEX.md`.

## Threat Model

- Adversary controls network namespace co-resident traffic (capture on `lmns-br`)
- Adversary can read idle process memory (no root, just `/proc/<pid>/maps`)
- Prompt canaries are realistic-looking but never seen in training (UUID-suffixed)
- Multi-tenant isolation via Linux network namespaces + per-model LD_PRELOAD hooks

## Reproducing

Hardware: any Linux box with Ollama + llama.cpp + enough RAM for one 9B model.

```bash
# Pull models
ollama pull nemotron-3-nano-4b
ollama pull qwen3.5-9b
ollama pull gemma-4-e4b-it
ollama pull phi-4-reasoning-plus

# Run N50 audit (50 captures per model)
bash experiments/scripts/run_all_n50_audits.sh

# Regenerate summary tables
python3 experiments/build_index.py
```

Full methodology: `experiments/reports/MASTER_FORENSICS_DOCUMENTATION.md`.

## Key Reports (start here)

| Report | What it answers |
|--------|-----------------|
| `FINAL_STATUS_REPORT.md` | One-page status + headline numbers |
| `MASTER_FORENSICS_DOCUMENTATION.md` | Canonical methodology + threat model |
| `RECONCILED_NUMBERS.md` | Reconciled stats across runs |
| `STRENGTH_WEAKNESS_MAP.md` | Per-attack strength scoring |
| `CITATION_AUDIT.md` | Reference accuracy audit |
| `DISCLOSURE_PLAN.md` | Vendor disclosure timeline |

## Per-Model Findings

| Model | Key Reports |
|-------|-------------|
| Phi-4 | `PHI4_DEFENSE_RESOLVED_REPORT.md`, `GEMMA4_PHI4_RERUN_REPORT.md` |
| Ollama 4-pack | `TELEMETRY_FINDINGS_4MODELS.md` |
| Ollama per-model | `TELEMETRY_FINDINGS_OLLAMA.md` |
| LMS | `TELEMETRY_FINDINGS_LMS.md` |

## Citation

stay tunning

## ⚖️ License & Ethical Disclosure

Code is released under the MIT License. Data artifacts are released under CC-BY 4.0.

Responsible Disclosure: The cross-tenant /slots vulnerability (CWE-862/CWE-200) was reported to the upstream maintainers via coordinated disclosure prior to this public release. No weaponized, mass-exploitation tooling is provided.

Copyright (c) 2026 Youssef Hamdi Zafaan Ibrahim (0xZodiac)

