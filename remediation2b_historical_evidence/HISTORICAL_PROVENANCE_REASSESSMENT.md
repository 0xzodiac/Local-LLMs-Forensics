# Historical provenance reassessment

## Chain assessment

| Link | Retained evidence | Grade/status |
|---|---|---|
| Source | The manuscript names `388d39f3e`; it does not resolve in the public repository. `721354fbdfb7743e2be2183d918a3cdb9276c70f` resolves and was used for Remediation 2 engineering. | Historical source unresolved; Remediation 2 source verified but not historical |
| Patch | `Runs/patches/kv_cache_zeroize.patch` is retained and hashable. `Runs/patches/prompt_zeroize.patch` is retained but malformed. | Patch-level evidence only |
| Binary | Historical JSON names `/home/elaref/research/llama-cpp-build/build/bin/llama-server`. The binary and its hash are absent. | Unlinked |
| Run | Raw JSON has run IDs, timestamps, model paths, and a binary path but no startup manifest or executable digest. | Observation record retained; execution identity incomplete |
| Model | `Runs/provenance/model_digests.json` records four model digests and a Zenodo identifier. The model files are not currently present. | Model metadata retained; load-time linkage unverified |
| Raw record | Memory, slot, extraction, latency, and telemetry records are present and hashable. | Strongest surviving evidence |

The upstream commit used by Remediation 2 must not be relabeled as the historical research revision. The chain therefore remains `Source? -> Patch? -> Binary? -> Run -> Raw record`, with the final raw records stronger than their implementation attribution.

## Consequences

The retained records can support descriptive observations and arithmetic recomputation. They cannot establish that the historical executable used a particular source revision, that the malformed historical prompt patch caused the sanitised difference, or that the new Remediation 2 implementation reproduces the historical result.

Local Git history retains reports, scripts, and telemetry paths but no matching llama.cpp source tree, historical executable, prompt patch repair, or TTFT vector. The exact consumed-file hashes are in `analysis/independent_reanalysis.json`.
