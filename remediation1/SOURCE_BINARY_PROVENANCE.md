# Source-to-binary-to-run provenance audit

## Verdict

The historical source-to-binary-to-run chain was not recovered. The retained records identify an upstream-looking reference (`721354f`) and a binary path, but they do not preserve the historical checkout, executable hash, build manifest, startup command, model digest, or a run manifest tying the executable to the JSON results. The result records therefore remain evidence of retained observations, not a fully reproducible execution chain.

## Recovered and searched artifacts

| Chain element | Evidence | Status |
|---|---|---|
| Claimed source reference | `388d39f3e` is unresolved by the recorded official URL and has no local Git object | Not recovered |
| Resolvable upstream reference | `721354f` resolves to `721354fbdfb7743e2be2183d918a3cdb9276c70f`; parent `6ee0f65793da4bca2301826f70383aef2da60345`; dated 2026-06-22 | Upstream identity verified; historical use unverified |
| Original source checkout | No local `llama.cpp` checkout, detached worktree, submodule, or archive was found in the searched research paths or repository objects | Not recovered |
| Prompt patch | `Runs/patches/prompt_zeroize.patch`, SHA-256 `9fc6786ff3515a7206a8c45c79f09dfef97fea96beff95ccfd48bd8fc2cfa7a0` | Original bytes verified; malformed |
| KV patch | `Runs/patches/kv_cache_zeroize.patch`, SHA-256 `9219b14331f4c5f7f80117a3affa6c16464d52ac92245b176e900b39e6d10b54` | Original bytes verified; applies to `721354f` |
| Historical executable | JSON records name `/home/elaref/research/llama-cpp-build/build/bin/llama-server`; that path is absent | Not recovered |
| Build manifest | No executable hash, compiler/build manifest, startup command, environment capture, or model-file digest was retained | Not recovered |
| Raw result records | Baseline and sanitised aggregate JSONs, KV probe logs, and multilayer records are present and hashable | Retained observations verified; linkage incomplete |

## Experiment-level classification

| Experiment family | Retained evidence | Provenance classification |
|---|---|---|
| GGUF/model parsing and setup | Scripts, logs, and model paths are retained, but the referenced model files are absent from the current environment | Partially verified |
| Baseline memory residue | Baseline aggregate JSON and supporting reports are retained | Observation verified; executable identity unverified |
| Prompt Sites A+B | Original patch and three result JSONs are retained; original patch is malformed and no historical binary hash exists | Partially verified; causal chain unverified |
| Sites C/D and secure allocator | Reports and result records describe generated or additional mitigation, but a complete standalone implementation is not retained | Partially verified; implementation provenance incomplete |
| KV zeroization | KV patch applies at the resolved upstream commit and direct probe logs report 56/56 nonzero pre-write cells | Mechanism and patch application verified on reconstruction; historical run linkage unverified |
| Prefix/cache timing | Rendered figure exists, but no raw TTFT vectors or analysis script was found | Reported only; not independently reproducible |

## Reconstruction boundary

For remediation, an isolated checkout of `721354fbdfb7743e2be2183d918a3cdb9276c70f` was created outside the project, the mechanically repaired prompt patch and original KV patch were applied, and a CPU-only `llama-server` build was attempted. This is a controlled reconstruction, not evidence that the historical experiment used that checkout or executable. Its build result is reported separately in `PATCH_BUILD_VALIDATION.md`.

## Consequence

The memory arithmetic can be independently recomputed from the retained JSON schema, but a submission claim that the historical prompt patch caused the sanitised reduction is not supported. A new reproduction must pin the source, retain both original and repaired patch hashes, retain the executable hash and startup manifest, record model and environment digests, and write per-run provenance into every result file.
