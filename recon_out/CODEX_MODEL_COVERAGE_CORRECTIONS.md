# LLAnalyzer model-coverage correction report

Date: 2026-10-11. This was a surgical manuscript correction pass using the
retained four-model coverage matrix and evidence ledger. No experiment,
server, model load, binary build, historical-evidence edit, or disclosure
action was performed.

## Source modifications

### Main manuscript

`LLAnalyzer-revised-10point/T-IFS.tex` was corrected as follows.

- The experimental-controls paragraph (lines 499--510) now distinguishes
  within-family controls from heterogeneous cross-family observations. It
  names the Nemotron-only twelve-tenant rows, Phi-4-only multilayer-v2
  diagnostics, and Nemotron CUDA-v5 campaign.
- RQ4 (lines 570--574) now asks about saved-state and continuation behaviour
  across slot identifiers in one shared process. Cross-principal
  authorization, distinct credentials, ownership controls, and remote side
  channels are explicitly untested.
- The ${A}_2 threat-model description now states that the retained workloads
  did not instantiate two authenticated clients or distinct credentials, so
  it is not presented as an authorization result.
- The GGUF evidence paragraph (lines 620--629) now records that historical
  reports describe four architectures but label the fourth `phi3`, whereas
  retained scripts use the `phi4` key. Because raw outputs are absent, the
  manuscript no longer silently equates those identities.
- RQ2.1 and its table (lines 719--733) identify the two twelve-tenant rows as
  Nemotron-specific.
- Runtime-residue validation (lines 774--786) preserves four-model evidence
  for slot, continuation, injection, KV-overhead, and D4 families while
  separating Nemotron-only twelve-tenant and Phi-4-only multilayer results.
- The abstract now labels the 11/12 observations as sequential Nemotron
  tenants. The continuation paragraph records the shared logical protocol and
  the model-specific retained offload settings: 999 layers for Gemma, Qwen,
  and Nemotron versus 20 for Phi-4.
- The sanitisation discussion (lines 942--959 and 1022--1028) labels the
  rows as Nemotron observations and removes the broken sentence beginning
  “Under the latter criterion, reducing”. The comparison remains descriptive;
  no causal effect is inferred.
- The GPU host-side attribution (lines 1120--1130) now attributes the
  retained 50-trial GPU-v5 campaign to Nemotron-3-Nano-4B under partial CUDA
  offloading. Historical Qwen GPU prose is retained only as report-only
  context and is excluded from the 50-trial denominator.

### Supplementary methods

`LLAnalyzer-revised-10point/TIFS_Supplementary_Methods.tex` was corrected as
follows.

- Lines 446--454 distinguish a hypothetical “another client's execution
  context” from the retained one-process slot/continuation workloads, which
  used no distinct clients, credentials, or ownership controls.
- Lines 469--480 replace the overbroad “For each model” runtime-memory claim
  with the retained protocol split: Nemotron-only twelve-tenant rows,
  Phi-4-only multilayer-v2 diagnostics, aggregate-only allocator evidence,
  and separately documented four-model families.
- Lines 492--497 state that 56 KV cells are a configured diagnostic scope;
  no per-cell result file is retained, so this is not presented as a direct
  headline result.
- The workload-scale table (lines 600--605) now marks the 56-cell value as
  scope-only with absent per-cell records and uses a width-constrained table.
- Lines 689--695 restrict across-model generalization to named retained
  four-model families and exclude Nemotron-only, Phi-4-only, and aggregate
  allocator rows from such generalization.
- The two twelve-tenant observations at lines 671--675 are explicitly
  identified as Nemotron-only.

### Figures

- `figures/fig_llanalyzer_arch.tex` now labels the sanitised row “Nemotron
  sanitised” and its 11/12 subtitle as Nemotron rows (lines 120--123).
- `figures/fig_llanalyzer_results.tex` now labels the sanitised row “Nemotron
  sanitised” and the tenant marker/pill as Nemotron-specific (lines 76--95).
- Both figure PDFs were rebuilt from their edited `.tex` sources. Rendered
  previews were inspected; labels are legible and no overlap or clipping was
  observed.

No bibliography changes were required.

## Coverage consistency result

The active manuscript now agrees with the independently reconstructed matrix:

| Evidence family | Coverage represented in text |
|---|---|
| Slot equality, July continuation, direct injection, KV overhead | Four model-labelled families; denominators and continuation split retained. |
| D4 cross-model residue | 200 primary records with the four fixed model-pair blocks; debug record excluded. |
| LM Studio hooks and Ollama telemetry | Four-model coverage retained; Ollama 206 metadata records remain separate from 203/2/1 success/failure/incomplete accounting. |
| Twelve-tenant blast radius | Nemotron-only; 11/12 rows and exact 110/10,834 and 78/3,352 metrics retained descriptively. |
| Multilayer-v2 diagnostics | Phi-4-only. |
| GPU-v5 host-memory scan | Nemotron-only 50-trial primary campaign; historical Qwen GPU prose is not counted as primary v5 evidence. |
| GGUF structured reports | Four historical architecture columns reported with the `phi3`/`phi4` identity caveat. |

The verified 126/200 continuation result remains in the abstract, main text,
figure, and supplement with its Gemma 50/50, Qwen 50/50, Nemotron 25/50, and
Phi-4 1/50 split. No unsupported cross-principal authorization, causal
sanitisation effect, binary-linkage, timing-AUC, or AFL++ total was
reintroduced.

## Inventory-scope note

The apparent 1,985-versus-3,277 discrepancy is a scope difference, not a
new experimental count. `remediation1/RESEARCH_ARTIFACT_INVENTORY.md:9`
reports 3,277 files under `Runs/`, while the same inventory reports 1,985
files specifically under `Runs/logs/`. `LLAnalyzer_Master_Dossier/Reproducibility/ORIGINAL_ARTIFACT_INDEX.md:5`
also uses the 3,277-file `Runs/` scope. The earlier coverage note that said
“1,985 files under Runs/” was therefore imprecise shorthand for the log-file
subset; this report records the distinction without modifying that prior
audit artifact.

## Compilation and visual checks

- Main manuscript: `pdflatex` twice with output in a temporary
  `/tmp/paper_build.*` directory; successful, **11 pages**.
- The abstract remains within the requested limit at 216 words under a
  LaTeX-command-stripped count.
- Supplement: `pdflatex` twice; successful, **5 pages**.
- Architecture figure: standalone `pdflatex`; successful, **1 page**.
- Results figure: standalone `pdflatex`; successful, **1 page**.
- Final logs contain no fatal errors, undefined references, undefined
  citations, or overfull boxes. Routine class/underfull warnings remain in
  the IEEE template output; they do not create text overflow in the affected
  patched passages.
- Rendered architecture and results figures were inspected after rebuild.

## Remaining blockers and provenance uncertainties

1. The historical GGUF report/script `phi3` versus `phi4` identity cannot be
   settled without the missing raw output or artifact manifest.
2. The original executed June binaries were not hashed and are unavailable;
   the recorded CUDA revision is not recoverable from the retained records.
3. No linked primary Qwen/Gemma/Phi GPU-v5 records, allocator per-repetition
   JSONs, timing vectors, or raw GGUF mutation corpus were located.
4. The slot and continuation workloads still do not test distinct clients,
   keys, ownership, or remote authorization. These remain scientific scope
   limitations, not manuscript defects after this correction.

The main-manuscript page target is met, but the provenance and untested-boundary
items above remain submission-level limitations that cannot be resolved from
the retained evidence alone.
