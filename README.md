# 🛡️ The Illusion of Local AI Security — LLM Forensics Research Data

[![License: MIT](https://img.shields.io/badge/Code-MIT-blue.svg)](LICENSE)
[![Data: CC-BY 4.0](https://img.shields.io/badge/Data-CC--BY_4.0-green.svg)](https://creativecommons.org/licenses/by/4.0/)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.20998459-purple.svg)](https://doi.org/10.5281/zenodo.20998459)
[![Status](https://img.shields.io/badge/Status-TIFS_Major_Revision-orange.svg)]()

Public dataset, scripts, and reports supporting the paper submission
**"The Illusion of Local AI Security: Wrapper Forensics and Covert Reasoning
Channels"** (IEEE TIFS, under major revision).

---

## 🔍 Research Question

Do local LLM inference runtimes (LM Studio, llama.cpp, Ollama) leak
pre-training data, prior-session context, or model internals across the
user/network boundary — even under tenant isolation (Linux network
namespaces, LD_PRELOAD hooks)?

## 📌 Headline Findings

Across **480 adversarial prompt injections** targeting 4 state-of-the-art
models, we recorded a **71.5% overall canary-token leakage rate**, produced
by three coordinated failures:

| # | Finding | Evidence |
|---|---------|----------|
| 1 | **Covert Reasoning Channel** — hidden `reasoning_content` fields bypass visible-layer output filters (up to 98.4% on Phi-4, 56.0% on Qwen3.5) | `Runs/experiments/reports/MASTER_FORENSICS_DOCUMENTATION.md` |
| 2 | **Wrapper Betrayal** — LM Studio writes every API request (payloads, reasoning traces, secrets) to cleartext disk logs with 30-day retention by default | same + `TELEMETRY_FINDINGS_LMS.md` |
| 3 | **Cross-Tenant Session Hijacking** — `llama-server`'s `/slots` save/restore has no authorization check (CWE-862/CWE-200): 12/12 tenants' cleartext recovered in a single memory read | `CROSS_TENANT_SLOT_RESTORE_VULNERABILITY.md`, `DEEP_LEAK_REPORT.md` |
| 4 | **Memory Residue** — canary tokens persist in idle process memory and KV-cache after request completion; zeroed by the shipped patches | `KV_CACHE_PATCH_REPORT.md`, `PROMPT_ZEROIZE_PATCH_REPORT.md` |
| 5 | **Network Cleanliness as Red Herring** — zero outbound exfiltration observed; the threat is data-at-rest, not data-in-transit | `TELEMETRY_FINDINGS_4MODELS.md`, `TELEMETRY_FINDINGS_OLLAMA.md` |

Full reconciled statistics: [`Runs/experiments/reports/RECONCILED_NUMBERS.md`](Runs/experiments/reports/RECONCILED_NUMBERS.md)

## 📦 Repository Layout

```
from-scratch/                 Numbered reproduction scripts (00-09)
  00_check_env.sh             Prerequisite audit
  01_layout.sh                Workspace construction
  02_install_prereqs.sh       System packages (apt)
  03_download_models.sh       GGUF download + SHA-256 verify
  04_import_models.sh         LM Studio + offline Ollama import
  05_build_llamacpp_patched.sh  Patched llama-server build
  06_build_netns_harness.sh   netns telemetry harness (rebuilt)
  07_build_ld_hook.sh         LD_PRELOAD network hook
  08_run_all.sh               N50 master orchestrator (~25-30h)
  09_smoke_test.sh            10-minute sanity pass
docs/
  Reproduction_Manual.docx    Professional reproduction manual
  Reproduction_Manual.pdf
RUN_FROM_SCRATCH.md           Manual source (pandoc/markdown)
Runs/
  experiments/
    scripts/                  Canonical reproducer scripts
      run_all_n50_audits.sh   N=50 audit orchestrator (4 models)
      run_d2_measurements.sh  Patched-vs-unpatched heap measurements
      run_secure_allocator_test.sh  Secure-allocator closure proof
      batch_4models.sh        4-model netns telemetry batch
    reports/                  60+ analysis reports (see below)
    telemetry_summary/        Per-model run index (INDEX.md + tables)
    build_index.py            Regenerate summary tables from raw runs
  scripts/                    Research harness drivers (n50_audit/, LMS,
                              D4/D5/D7, GGUF fuzzers, VRAM probes, ...)
  TELEMETRY_RUN_*/            Raw capture dirs (N=212): meta.json, pcap/,
                              idle_snapshots.json, triggers.jsonl, ...
  patches/                    prompt_zeroize.patch, kv_cache_zeroize.patch
  provenance/                 model_digests.json (byte-exact SHA-256 pins)
  logs/                       Run logs
  lms-leak-test/              LMS subsystem test data
```

## 🤖 Audited Models

All Q4_K_M GGUF, byte-pinned by SHA-256 in
[`Runs/provenance/model_digests.json`](Runs/provenance/model_digests.json):

| Model | HuggingFace Repo | Size | N50 Runs | Capture |
|-------|------------------|------|----------|---------|
| Nemotron-3 Nano 4B | `lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF` | 2.8 GB | 50 | netns-isolated |
| Qwen3.5 9B | `lmstudio-community/Qwen3.5-9B-GGUF` | 5.6 GB | 50 | netns-isolated |
| Gemma-4 E4B | `lmstudio-community/gemma-4-E4B-it-GGUF` | 5.3 GB | 50 | netns-isolated |
| Phi-4 Reasoning+ | `lmstudio-community/Phi-4-reasoning-plus-GGUF` | 9.0 GB | 50 | netns-isolated |

Plus LMS/Ollama baseline runs — see `Runs/experiments/telemetry_summary/INDEX.md`.

## 🧪 Threat Model

- Adversary controls network-namespace co-resident traffic (capture on `lmns-br`)
- Adversary reads idle process memory (same UID, `/proc/<pid>/mem`)
- Prompt canaries are realistic-looking but never in training data (UUID-suffixed)
- Multi-tenant isolation via Linux netns + per-model LD_PRELOAD hooks
- Wire capture (`tcpdump` on the sole veth egress) is the unspoofable ground truth

## 🚀 Quick Start (Reproduction from Scratch)

Hardware: any Linux box with sudo, ≥16 GB RAM, ≥40 GB disk (models ~21 GB
+ Ollama blob copies ~21 GB).

```bash
git clone https://github.com/0xzodiac/Local-LLMs-Forensics.git
cd Local-LLMs-Forensics

bash from-scratch/00_check_env.sh        # 1. audit prerequisites
bash from-scratch/02_install_prereqs.sh  # 2. install system packages
bash from-scratch/01_layout.sh           # 3. build ~/research workspace
bash from-scratch/03_download_models.sh  # 4. fetch + verify the 4 GGUFs (~21 GB)
bash from-scratch/04_import_models.sh    # 5. LM Studio + offline Ollama import
bash from-scratch/05_build_llamacpp_patched.sh  # 6. patched llama-server
bash from-scratch/06_build_netns_harness.sh    # 7. netns telemetry harness
bash from-scratch/07_build_ld_hook.sh    # 8. LD_PRELOAD network hook
bash from-scratch/09_smoke_test.sh      # 9. 10-minute sanity pass
bash from-scratch/08_run_all.sh         # 10. full N50 audit (~25-30h, use tmux)
```

The full professional manual (DOCX/PDF) is in [`docs/`](docs/), source at
[`RUN_FROM_SCRATCH.md`](RUN_FROM_SCRATCH.md). Full methodology:
`Runs/experiments/reports/MASTER_FORENSICS_DOCUMENTATION.md`.

## 📊 Key Reports (start here)

| Report | What it answers |
|--------|-----------------|
| [`FINAL_STATUS_REPORT.md`](Runs/experiments/reports/FINAL_STATUS_REPORT.md) | One-page status + headline numbers |
| [`MASTER_FORENSICS_DOCUMENTATION.md`](Runs/experiments/reports/MASTER_FORENSICS_DOCUMENTATION.md) | Canonical methodology + threat model |
| [`RECONCILED_NUMBERS.md`](Runs/experiments/reports/RECONCILED_NUMBERS.md) | Reconciled stats across all runs |
| [`CROSS_TENANT_SLOT_RESTORE_VULNERABILITY.md`](Runs/experiments/reports/CROSS_TENANT_SLOT_RESTORE_VULNERABILITY.md) | The /slots hijack (CWE-862/CWE-200) |
| [`STRENGTH_WEAKNESS_MAP.md`](Runs/experiments/reports/STRENGTH_WEAKNESS_MAP.md) | Per-attack strength scoring |
| [`CITATION_AUDIT.md`](Runs/experiments/reports/CITATION_AUDIT.md) | Reference accuracy audit |
| [`DISCLOSURE_PLAN.md`](Runs/experiments/reports/DISCLOSURE_PLAN.md) | Vendor disclosure timeline |

## 📈 Per-Model Findings

| Model / Runtime | Key Reports |
|-----------------|-------------|
| Phi-4 | `PHI4_DEFENSE_RESOLVED_REPORT.md`, `GEMMA4_PHI4_RERUN_REPORT.md` |
| 4-model telemetry (LMS) | `TELEMETRY_FINDINGS_4MODELS.md` |
| Ollama control case | `TELEMETRY_FINDINGS_OLLAMA.md` |
| LM Studio per-run | `TELEMETRY_FINDINGS_LMS.md` |
| GGUF parser attacks | `GGUF_NOVEL_ATTACKS_REPORT.md`, `GGUF_SURGICAL_REPORT.md`, `GGUF_CROSS_MODEL_REPORT.md` |

## 🔧 Security Patches Shipped

| Patch | Effect |
|-------|--------|
| [`patches/prompt_zeroize.patch`](Runs/patches/prompt_zeroize.patch) | `explicit_bzero` on slot-owned plaintext at release (Sites A/B) |
| [`patches/kv_cache_zeroize.patch`](Runs/patches/kv_cache_zeroize.patch) | Zeroes released K/V cells in both normal and transposed-V layouts |
| `secure-allocator.cpp` (built by script 05) | `operator delete` override bzeros freed chunks ≥4 KB under `SECURE_ALLOC=1` |

## 📖 Citation

Dataset on Zenodo: [10.5281/zenodo.20998459](https://doi.org/10.5281/zenodo.20998459)

```bibtex
@dataset{zodiac2026_local_llm_forensics,
  author  = {0xZodiac},
  title   = {Local-LLMs-Forensics: Dataset, Scripts, and Reports for
             "The Illusion of Local AI Security"},
  year    = {2026},
  doi     = {10.5281/zenodo.20998459},
  url     = {https://github.com/0xzodiac/Local-LLMs-Forensics},
  license = {MIT (code); CC-BY-4.0 (data)}
}
```

## ⚖️ License & Ethical Disclosure

Code is released under the MIT License. Data artifacts are released under
CC-BY 4.0.

**Responsible Disclosure:** The cross-tenant `/slots` vulnerability
(CWE-862/CWE-200) was reported to the upstream maintainers via coordinated
disclosure prior to this public release. No weaponized or mass-exploitation
tooling is provided; all experiments are local, canary-token-based, and
network-isolated by design.

Copyright (c) 2026 Youssef Hamdi Zafaan Ibrahim (0xZodiac)
