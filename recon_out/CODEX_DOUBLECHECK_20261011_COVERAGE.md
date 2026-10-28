# LLAnalyzer coverage-correction double-check

Date: 2026-10-11. This is a fresh read-only verification pass over the
retained evidence and the already-corrected manuscript. No experiment,
server, model load, binary build, historical-evidence edit, or manuscript
source edit was performed in this pass.

## Fresh primary-record checks

- Slot save/restore: `slot_exploit_ALL4_audit1.json` contains four model keys,
  each with `n=50` and `exploit_confirmed_count=50`, giving the manuscript's
  200-trial denominator. Four additional per-model files named
  `slot_exploit_*_20260624_201614.json` are retained, but are a separate
  dated file family and were not pooled into the 200-trial claim. The script
  still measures one loopback server/process and exact `n_saved ==
  n_restored`; it does not test distinct clients, keys, or ownership.
- July continuation: four JSON files each contain `n=50`: Gemma KV 50/50,
  Qwen KV 50/50, Nemotron KV 25/50, Phi-4 KV 1/50; each has memory-channel
  50/50, so the retained aggregate is 126/200 KV-channel hits and 200/200
  memory-channel hits. These records are dated July 3--4, 2026. The logical
  protocol is shared, but retained offload settings differ: 999 layers for
  Gemma/Qwen/Nemotron and 20 layers for Phi-4.
- D4 cross-model residue: exactly 200 primary JSONs were found, 50 for each
  fixed pair (`gemma4_phi4`, `qwen35_gemma4`, `nemotron_qwen35`, and
  `phi4_nemotron`). The retained records contain unchanged process identity
  and post-swap canary-hit fields; one separately named debug JSON is not
  part of this denominator.
- Direct LM Studio injection: four `injection_*_audit1.json` files each have
  `n=50` and no errors. The per-model `leak_content OR leak_reasoning` union
  is 150/200 (Gemma 50, Nemotron 50, Qwen 50, Phi-4 0), and this workload
  remains separate from July continuation.
- GPU-v5: exactly 50 primary JSONs were found. The source script and paired
  server logs identify Nemotron under partial CUDA offload. A historical
  Qwen GPU reproduction is not linked to these 50 records and remains
  report-only. No Gemma/Phi GPU-v5 primary set was located.
- Twelve-tenant scans: two JSON observations identify the Nemotron GGUF and
  report 11/12 recovery, 110 copies/10,834 KB and 78 copies/3,352 KB. They
  remain descriptive single-run observations, not a four-model comparison.
- Ollama: 206 telemetry directories remain distributed as Gemma 52, Qwen 51,
  Nemotron 51, and Phi-4 52. The retained accounting remains 203 successful
  trigger files, two explicit failures, and one incomplete metadata-only
  record; no executable version is assigned.
- GGUF: report-level four-architecture coverage remains report-only. The
  fourth historical report column is `phi3`, while retained scripts use the
  `phi4` key; no raw output establishes equivalence.

## Active-text semantic check

The corrected active sources were searched for model attribution and boundary
language. The current state is consistent:

1. GPU-v5 is attributed to Nemotron; Qwen appears only as separately
   qualified historical report-only context.
2. Twelve-tenant 11/12 and 78-copy observations are labeled Nemotron in the
   abstract, main text, supplementary methods, and active figures.
3. Phi-4-only multilayer diagnostics and aggregate-only allocator evidence
   are explicitly separated from four-model families.
4. Slot equality, July continuation, direct injection, KV overhead, D4,
   LM-Studio hooks, and Ollama breadth remain four-model claims with their
   denominators and model-specific differences retained.
5. The 126/200 continuation result remains in the abstract, body, active
   figures, conclusion, and supplement. This is intentional and correct for
   the latest authoritative revision request, which explicitly required
   preserving the verified continuation evidence; it is not a stale claim to
   remove.
6. RQ4 and the threat model state that distinct clients, credentials,
   ownership, cross-principal authorization, and remote side channels were
   not tested.
7. The 56-cell statement is qualified as configured diagnostic scope with no
   retained per-cell result file.

## Fresh LaTeX and figure verification

- Main manuscript compiled twice with `pdflatex` in a temporary
  `/tmp/paper_build.*` directory: **11 pages**.
- Supplement compiled twice: **5 pages**.
- Architecture and results figures each report **1 page** in `pdfinfo`.
- Fresh logs contain no fatal errors, undefined references/citations, or
  overfull boxes.
- Fresh PNG previews of both figure PDFs were rendered and visually
  inspected. The architecture figure labels “Nemotron sanitised” and the
  results figure labels the tenant marker/pill and sanitised row as Nemotron;
  neither showed clipping or overlap.

## Inventory-count reconciliation

The previously observed 1,985-versus-3,277 difference is scope-based:
3,277 is the full `Runs/` file count reported by the retained inventory,
whereas 1,985 is the `Runs/logs/` subset. It is not a new experimental
denominator and does not alter the model matrix.

## Remaining uncertainties

- Original executed binary hashes and the recorded CUDA revision remain
  unavailable.
- The GGUF `phi3`/`phi4` artifact identity remains unresolved.
- No linked Qwen/Gemma/Phi GPU-v5 records, allocator per-repetition JSONs,
  timing vectors, or raw GGUF mutation corpus were found.
- The slot and continuation experiments still do not establish behavior
  between distinct principals.
- A historical verification note reported 201 D4 records and 51
  Nemotron-to-Qwen trials; the fresh file enumeration finds 200 records and
  exactly 50 in each pair, so the 201/51 figures are not used.

The previous correction report remains the authoritative change summary; this
file records only the independent double-check and its fresh verification
evidence.
