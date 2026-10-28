# Remediation 1 completion report

## Final outcome

**HISTORICAL RECOVERY FAILED; NEW PINNED REPRODUCTION REQUIRED.** The retained memory arithmetic and patch mechanics were validated, but the historical source-to-binary-to-run chain and timing data were not recovered. The project is not submission-ready on those scientific provenance blockers.

## Required-question answers

1. **Historical source checkout:** not recovered. No matching local checkout, worktree, submodule, archive, reachable object, or relevant unreachable object was found.
2. **`388d39f3e`:** unresolved; no local object or resolvable official source was found.
3. **`721354f`:** resolves to `721354fbdfb7743e2be2183d918a3cdb9276c70f`; usable as a reconstruction candidate, not verified as the historical checkout.
4. **Prompt patch:** original file is malformed at the diff header and first hunk count. A mechanical derivative applies cleanly; the original was not recovered.
5. **KV patch:** applies cleanly to the resolved candidate and is retained with its original hash. Historical binary linkage remains absent.
6. **Reconstructed build:** configuration succeeded with Release, CPU-only, `LLAMA_CURL=ON`, `LLAMA_CUDA=OFF`, server target, and tests enabled, but compilation failed in `server-context.cpp` because the patch mutates strings under `std::unique_ptr<const server_task>`. No executable was produced; the exact result is in `PATCH_BUILD_VALIDATION.md`.
7. **Historical executable:** `/home/elaref/research/llama-cpp-build/build/bin/llama-server` is absent and has no retained hash.
8. **Raw memory arithmetic:** verified from the two retained JSON records: 110 to 78 copies, 29.090909% reduction; 10,834 to 3,352 recorded KB, 69.060366% reduction; 11/12 recovery in both records.
9. **Raw-memory limitation:** the retained schema does not permit independent byte/region/match recomputation or causal attribution.
10. **Timing data:** no raw TTFT vectors, paired cached/uncached table, or AUC analysis script was found; no new timing campaign was run.
11. **Claim impact:** descriptive retained observations may remain with explicit provenance limits; causal mitigation, complete confidentiality, reproducibility, and generalized timing claims require downgrade.
12. **Preservation:** original patches, reports, logs, manuscript files, and user-owned changes were left untouched. New artifacts are confined to `remediation1/`.
13. **Next action:** run the experiment plan with pinned source, complete mitigation manifest, executable/model hashes, raw memory regions, and raw timing rows before revising blocked claims.

## Deliverables

- `RESEARCH_ARTIFACT_INVENTORY.md`
- `SOURCE_BINARY_PROVENANCE.md`
- `PATCH_ROOT_CAUSE.md`
- `PATCH_RECOVERY_REPORT.md`
- `PATCH_BUILD_VALIDATION.md`
- `RAW_MEMORY_RESULT_VALIDATION.md`
- `validation/verify_memory_results.py`
- `validation/recomputed_results.json`
- `TIMING_DATA_DISCOVERY.md`
- `MANUSCRIPT_CLAIM_IMPACT.md`
- `REPRODUCTION_EXPERIMENT_PLAN.md`
- `REMEDIATION1_COMPLETION_REPORT.md`
