# Supplement rewrite blueprint

The current supplement is five pages. Preserve that scale and move detail out
of the main paper only when it supports reproducibility rather than hiding a
claim limitation.

## A. Hardware and software

Retain the current `tab:hardware_config`, `tab:software_config`, and
`tab:evaluated_models` tables. Add one sentence distinguishing reported
historical configuration from independently verified binary provenance.

## B. Permissions and acquisition

Retain the parent-child `/proc/<pid>/maps` and `/proc/<pid>/mem` procedure,
Yama/PTRACE semantics, and the separation between F, A1, GDB, and CUDA-GDB.
Do not imply same-UID arbitrary access.

## C. Workload protocols

Retain the 80/21 GGUF corpus description, canary generation, twelve-tenant
memory sequence, wrapper inspection, 205-session Ollama monitoring, 200 saved
slot trials, 126 continuation outcomes, and the historical timing design. For
each protocol identify the output path or state that the local audit could not
recover.

## D. Statistics

Retain Wilson intervals, the memory reduction formula, deterministic-result
definition, model-specific reporting, null-result checks, and the timing AUC
qualification. Add the exact distinction between the KV overhead vectors and
the missing cached/uncached TTFT vectors.

## E. Reproducibility and replication

Add a compact table with three columns: original local records, independently
recomputed fields, and author-reported Ikram rerun. State that the complete
Ikram server-side bundle was not inspected locally; do not ask the supplement to
carry exact rerun numbers that were not supplied.

## F. Artifact index

List the scripts, raw paths, model-digest manifest, patches, figures, reports,
and the dossier. Mark historical summary-only claims separately from raw-record-
backed claims. Keep the original data paths rather than duplicating large
artifacts.

