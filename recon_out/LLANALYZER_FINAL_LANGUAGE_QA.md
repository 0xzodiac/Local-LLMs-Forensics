# LLAnalyzer final language and LaTeX QA

Date: 2026-10-12 (final reference- and build-QA pass)

## Build results

Fresh builds were performed from the edited canonical sources with temporary
output under `/tmp/paper_build_20261012_final/`:

- Main manuscript: `/tmp/paper_build_20261012_final/T-IFS.pdf` — 11 pages.
- Supplement: `/tmp/paper_build_20261012_final/TIFS_Supplementary.pdf` — 5 pages.
- Architecture figure: `/tmp/paper_build_20261012_final/figures/fig_llanalyzer_arch.pdf` — 1 page.
- Results figure: `/tmp/paper_build_20261012_final/figures/fig_llanalyzer_results.pdf` — 1 page.

The main manuscript is within the requested 13-page working ceiling. BibTeX
and three-pass `pdflatex` runs completed without fatal errors, undefined
references, undefined citations, or overfull boxes. Expected IEEEtran layout
produced underfull-box notices (16 main-document notices, 11 supplementary
notices, and 1 architecture-figure notice); visual inspection found no text
overflow or clipping.

The compiled main and supplement PDFs were copied to:

- `LLAnalyzer-revised-10point/T-IFS.pdf`
- `LLAnalyzer-revised-10point/TIFS_Supplementary.pdf`

The freshly compiled figure PDFs were copied to:

- `LLAnalyzer-revised-10point/figures/fig_llanalyzer_arch.pdf`
- `LLAnalyzer-revised-10point/figures/fig_llanalyzer_results.pdf`

The final pass checked the compiled Supplementary table order: hardware is
Table~S1, software Table~S2, evaluated models Table~S3, the boundary map
Table~S4, the evidence-source map Table~S5, and model specifications Table~S6.
The main-paper prose therefore retains its S4--S6 references.

## Abstract and terminology

The active abstract contains 248 words under a LaTeX-command-stripped count.
It now states the Nemotron scope of the LM Studio logging-toggle result,
separates four-model hook summaries, preserves the July continuation date, and
does not claim cross-principal authorization.

Terminology was checked across the main paper and supplement. The following
distinctions are maintained:

- residual-data existence versus conditional forensic recoverability;
- forensic collector `$F$` versus the untested co-resident adversary `${A}_1`;
- token-count equality versus model-visible continuation;
- byte occurrences versus independent secrets, tenants, or trials;
- same-process state transfer versus cross-principal authorization;
- descriptive configuration comparison versus causal mitigation effect;
- host-memory mapping observations versus direct device-memory recovery.

## Scientific consistency checks

- Four-model families remain four-model in the text where retained primary
  records support them: slot equality, July continuation, direct injection,
  KV-overhead arrays, D4 residue, LM Studio hooks, and Ollama telemetry.
- Nemotron-only rows are identified as such for the twelve-tenant observations,
  GPU-v5 campaign, and LM Studio logging-toggle report.
- Phi-4-only multilayer diagnostics and the unresolved `phi3`/`phi4` GGUF
  identity are explicitly qualified.
- The exact 126/200 continuation result and per-model split remain consistent
  in abstract, main results, conclusion, supplement, and figures.
- The 200/200 slot result remains an unauthenticated same-process equality
  oracle, not a second-client or distinct-key result.
- The 11/12, 110/10,834, and 78/3,352 observations remain descriptive
  single-run records with no causal percentage.
- No historical timing AUC, unretained fuzzing total, binary-equivalence
  statement, or authorization bypass was reintroduced.

## Visual review

The architecture figure is legible at rendered scale and clearly labels the
Phi-4-only heap/KV diagnostic rows, the Nemotron sanitised row, the scoped slot
result, the July continuation, and untested credentials. The results figure preserves the four-model continuation split,
marks the Nemotron 11/12 observation separately, and includes the caveat that
rows are experiment-specific and not causal effects. Main pages 1, 3, and 10 and
supplement pages 1 and 5 were rendered to PNG for visual inspection; dense
two-column text, tables, captions, and references were readable with no
clipping.

## Remaining textual issues

The only material author-side items are the `\artifacturl{TODO}` placeholder,
the final venue-specific disclosure/AI-use fields, and the authors' title
choice. The supplementary source retains a large commented historical appendix
for archival traceability; it is inactive and does not enter the compiled
document.
