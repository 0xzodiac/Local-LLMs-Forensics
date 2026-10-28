# LLAnalyzer remediation 1 research-artifact inventory

Inventory date: 2026-10-08 (Africa/Cairo)

## Scope and preservation

The inventory covers the working project at `/home/elaref/Documents/research/Local-LLMs-Forensics`, its `LLAnalyzer-revised-10point/` manuscript directory, `Runs/`, `from-scratch/`, `Runs/experiments/`, the repository Git object database, and targeted accessible research directories. The historical source and binary paths named by retained records were checked directly. No original research file, worktree, archive, patch, or raw result was modified.

The workspace currently contains 3,277 files under `Runs/`, 242 files under `LLAnalyzer-revised-10point/`, 1,164 JSON files under `Runs/`, 1,985 log files under `Runs/logs/`, 94 relevant scripts under `Runs/scripts/`, `Runs/experiments/scripts/`, and `from-scratch/`, plus 213 telemetry directories containing 879 files. Repeated telemetry and per-trial files are retained but are not timing-AUC or llama.cpp source/build artifacts; the exact paths that bear on the three blockers are enumerated below.

## Required reports

All reports requested by the session specification were present:

| Artifact | Exact path | Confidence for audit use |
|---|---|---|
| Task 7 reproducibility closure | `LLAnalyzer-revised-10point/TASK7_REPRODUCIBILITY_CLOSURE.md` | High as a prior audit record; not primary execution evidence |
| Task 7 submission readiness | `LLAnalyzer-revised-10point/TASK7_SUBMISSION_READINESS.md` | High as a prior audit record |
| Task 7 claim-evidence matrix | `LLAnalyzer-revised-10point/TASK7_FINAL_CLAIM_EVIDENCE_MATRIX.md` | High as a prior claim map |
| Task 7 handoff | `LLAnalyzer-revised-10point/TASK7_HANDOFF.md` | High as a prior handoff record |
| Task 7 changelog | `LLAnalyzer-revised-10point/TASK7_CHANGELOG.md` | High for documenting prior edits |
| Task 7 statistical audit | `LLAnalyzer-revised-10point/TASK7_STATISTICAL_AUDIT.md` | High for prior derived calculations |
| Task 7 timing audit | `LLAnalyzer-revised-10point/TASK7_TIMING_STATISTICAL_AUDIT.md` | High for prior negative timing search |
| Task 3 software provenance | `LLAnalyzer-revised-10point/TASK3_SOFTWARE_PROVENANCE.md` | High as a prior provenance audit |
| Task 3 reproducibility audit | `LLAnalyzer-revised-10point/TASK3_REPRODUCIBILITY_AUDIT.md` | High as a prior reproducibility audit |

The authoritative manuscript and supplement were also present at `LLAnalyzer-revised-10point/T-IFS.tex` and `LLAnalyzer-revised-10point/TIFS_Supplementary_Methods.tex`. Their SHA-256 hashes at inventory time were respectively `543266da0b6f10049c318672f7293d2ca16566a3cd5f96910f096419d6c92d1a` and `6ed84799018366d72bcf612387c47cf328e2599ce8fb07f5002cb30b74bb9c83`.

## Source, worktree, and binary search

| Artifact or search target | Exact path or query | Result | Provenance confidence |
|---|---|---|---|
| Research Git repository | `/home/elaref/Documents/research/Local-LLMs-Forensics/.git` | HEAD `9bf6809`; only `main` and `origin/main`; no llama.cpp submodule | High |
| Local source-tree search | `/home/elaref/Documents/research` and `/home/elaref/research`, targeted names `llama.cpp`, `llama-cpp-build`, worktrees | No historical llama.cpp checkout or detached worktree found | High for searched scope |
| Historical binary path named by memory JSON | `/home/elaref/research/llama-cpp-build/build/bin/llama-server` | Absent; no SHA-256 can be computed | High |
| Other retained binary path | `/home/sharks/research/llama-monitor/build/llama.cpp/bin/llama-server` | Absent | High |
| Workspace-local build path | `LLAnalyzer-revised-10point/llama-cpp-build/build/bin/llama-server` | Absent | High |
| Git reflog | `.git/logs/refs`, `git reflog --all` | Only clone event for `9bf6809`; no historical llama.cpp commit or build state | High |
| Reachable Git objects | `git rev-list --objects --all` | No source tree, patch, binary, build directory, or timing-vector artifact matching the blocker queries | High |
| Unreachable Git objects | `git fsck --full --unreachable --no-reflogs` | 27 blobs and 16 trees; content is manuscript/PDF/report history. No blob contained a unified zeroization patch, `explicit_bzero`, `zero_cell_data`, or a source/build manifest | High |
| Archives | `LLAnalyzer-revised-10point.zip`, `LLAnalyzer_UsenixSec27.zip`, `Runs/Local_LLM_Forensics_draft.zip` | No llama.cpp source tree, executable, original patch, TTFT vector, or AUC script; manuscript archives include timing figures only | High |

An isolated network checkout was used only for validation, not retained as historical evidence. It resolved short reference `721354f` to full commit `721354fbdfb7743e2be2183d918a3cdb9276c70f`, parent `6ee0f65793da4bca2301826f70383aef2da60345`, subject `server: (router) move model downloading to dedicated process (#24834)`, dated `2026-06-22T18:24:04+02:00`. This proves upstream identity, not historical execution.

## Patch and implementation artifacts

| Artifact | Exact path | Size | SHA-256 | Evidence role | Confidence |
|---|---|---:|---|---|---|
| Retained prompt-zeroization patch | `Runs/patches/prompt_zeroize.patch` | 3,833 bytes | `9fc6786ff3515a7206a8c45c79f09dfef97fea96beff95ccfd48bd8fc2cfa7a0` | Original bytes; malformed diff header and two hunks | High for file identity |
| Retained KV-cache patch | `Runs/patches/kv_cache_zeroize.patch` | 4,505 bytes | `9219b14331f4c5f7f80117a3affa6c16464d52ac92245b176e900b39e6d10b54` | Original bytes; applies at `721354f` | High for file identity; patch-to-run linkage incomplete |
| Build script | `from-scratch/05_build_llamacpp_patched.sh` | 3,204 bytes | `97f976a91b0b0060991b4da4bff2a9547aefc0033b728f904ae8c6f480962fb3` | Shows moving `master` default, non-fatal patch loop, CMake options, and generated allocator | High |
| KV probe | `Runs/scripts/kv_cache_zeroize_probe.py` | 4,983 bytes | `9ac6312c6593dc841a3e48e0b0dbad5d7433da4df9547d318a7ed76aa0b1cb17` | Probe launch and memory-observation procedure | High |
| Multilayer probe | `Runs/scripts/multilayer_v2.py` | 6,477 bytes | `e01afe4eb99cf85ff0a6399a54e76dce0c172002e669057c59743ae6544fccf0` | Prompt-residue observation procedure | High |
| Secure-allocator runner | `Runs/experiments/scripts/run_secure_allocator_test.sh` | 1,881 bytes | `41dc28279db0e2fc6c8955115bdb8265b3bb2e5cb830b42bf9f9db4cf7f0dcdd` | Historical test entry point; generated allocator source itself is not retained as a standalone patch | High |
| Prompt patch report | `Runs/experiments/reports/PROMPT_ZEROIZE_PATCH_REPORT.md` | 17,230 bytes | Not rehashed in this inventory table | Describes Sites A-D and later secure-allocator work; not a source manifest | High as report evidence |
| KV patch report | `Runs/experiments/reports/KV_CACHE_PATCH_REPORT.md` | 9,263 bytes | Not rehashed in this inventory table | Describes direct 56/56 tensor-byte validation and n=20 timing overhead | High as report evidence |
| Secure allocator report | `Runs/experiments/reports/SECURE_ALLOCATOR_REPORT.md` | 11,208 bytes | Not rehashed in this inventory table | Describes partial 29%/69% mitigation and warns that it is not a complete closure | High as report evidence |

The retained prompt patch begins with `index 0000000..1111111 1006---` and is rejected by Git before any hunk is applied. The first hunk header declares `+35` new lines while the retained hunk contains 37 new lines. The corrected copy in `remediation1/patch_recovery/` changes only the mode/newline boundary and that hunk count.

## Raw memory and zeroization evidence

| Artifact | Exact path | Size | SHA-256 | Observed role | Confidence |
|---|---|---:|---|---|---|
| Baseline aggregate memory record | `Runs/logs/leak_blast_radius_20260623_213831.json` | 1,270 bytes | `4d54ac8bd771420a93617a0e63f1ab1fa786cdfdeb5dca9815b86c7337dfb3f6` | 12 tenants, 11 recovered, 110 copies, 10,834 KB | High for retained record |
| Sanitised aggregate memory record | `Runs/logs/leak_blast_radius_20260624_120421.json` | 1,248 bytes | `ef6f5cecf832cabdb4d31620af371951ae727c75ed7644383662e00be7169c63` | 12 tenants, 11 recovered, 78 copies, 3,352 KB | High for retained record |
| KV pre/post probe | `Runs/logs/kv_zeroize_probe_before.log`, `Runs/logs/kv_zeroize_probe_after.log` | 6,261 bytes each | `ea7bf2491ebc49ad3223edfc818a756eee3a5f6cf47f6d0e347ba1bea2f009c6`, `07605da099c7b56bd4611cb62c58c1db4c769b319b3597d15be482b6b6d2918a` | Runtime logs for KV probe | High as logs; no binary hash |
| Instrumented KV probe | `Runs/logs/kv_zeroize_probe_debug2.log` | 13,388 bytes | `311db790c84773f9285b19d82c1b7e7d17b48a81bd66114ebbfc2b614545281c` | Reports `zero_cell_data` calls and nonzero pre-write bytes | High as log; no binary hash |
| Sites A+B residue records | `Runs/logs/multilayer_v2_patched_run1.json`, `...run2.json`, `...run3.json` | 14,244; 14,245; 12,483 bytes | `2aa2253...`, `03e1a468...`, `37bb542...` | Reports 13/13/14 residual counts in the retained prompt-patch report | High as records; implementation identity incomplete |
| Secure-allocator records | `Runs/logs/multilayer_v2_securealloc_run1.json`, `...run2.json`, `...run3.json` | 6,933; 11,923; 11,921 bytes | `586941b...`, `48206b...`, `e726c2f...` | Reports partial, variable mitigation; does not identify an executable hash | High as records; causal chain incomplete |

The complete repeated-run hashes are recorded here so the inventory is independently checkable:

- Sites A+B: `2aa2253bab325ddc2a88cea29d9ac5f5024a5352defcca4425baa194cd710ddf`, `03e1a4686d03d8883cfcd2636abd8cc93d67e9a7c08bf2a21ac1ed993bfb96c8`, `37bb5427e4280add014edbb9602044a02e71fbdbf90dd3dfbc9cf54277c20783`.
- Secure allocator: `586941b56b37e86a038e27a6ad9455d3d7c8ce92d16172e7c1cc21a65181585f`, `48206bfa2ef2186f27f910d32441c1a5fdade5d15fa1989a7bdf2cbb6f2565fe`, `e726c2fdce7c956955e5ae2d9f6a7623e5b6c992d5c469c32c58b26b5eabf42d`.

The original files remain untouched.

## Timing artifact inventory

No file with a timing/TTFT/AUC/ROC/prefix-cache filename and a machine-readable per-request vector was found. The retained workspace does contain four unrelated CSV files under `Runs/logs/` (`phase1_gemma4_lms_rerun.csv`, `phase1_phi4_lms_rerun.csv`, `track_b_resolved_anomalies.csv`, and `track_b_resolved_results.csv`) and several cross-tenant JSON records containing `tokens_cached`; none contains paired cached/uncached TTFT observations or the AUC analysis procedure. The only timing-specific packaged artifacts located were `LLAnalyzer-revised-10point/figures/timing_auc_decay.pdf` and `.png`, which are rendered figures, not raw vectors.

## Provenance confidence convention

`VERIFIED` in the remediation reports means the artifact identity or arithmetic is directly checked. It does not mean the artifact was the historical experiment input. `PARTIALLY VERIFIED` means the record or mechanism is directly observed but one or more source/build/run links are absent. `UNVERIFIED` means a claimed relationship has no retained chain. Timestamps are inventory metadata only and are not treated as execution times.
