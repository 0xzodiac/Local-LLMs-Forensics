# Dr. Ikram full-framework replication audit

**Date:** 2026-10-08
**Scope:** LLAnalyzer evaluation targeted at IEEE T-IFS
**Decision boundary:** preserve the complete four-boundary contribution; do not treat a verbal report as artifact-level verification.

## Executive finding

The author has now explicitly reported that Dr. Mohammed Ikram completed a full
LLAnalyzer rerun on a separate research server and reproduced the original
experimental results. This applies to the complete evaluation, not only the
memory or saved-slot experiments. The research must therefore **not** be
described as having never been replicated.

The authorized workspace does not contain an identifiable Ikram rerun bundle:
no Ikram run manifest, server inventory, source revision, patch manifest,
executable hash, model-load record, raw rerun result, analysis output, or
correspondence attachment was found. The current evidence status is therefore:

> **Full cross-machine replication: AUTHOR-REPORTED MATCH. Artifact-verified
> cross-machine replication: NOT ESTABLISHED FROM THE INSPECTED WORKSPACE.**

This is a limitation of the inspected records, not evidence that the rerun did
not occur.

## Search result

The search covered the project root, `Runs/`, the revised manuscript directory,
Remediation 1, Remediation 2, and the historical-evidence audit. The following
were found but do not establish the Ikram rerun:

- `LLAnalyzer-revised-10point/T-IFS.tex` contains a commented author block and
  an older comment identifying controlled replication as future work.
- `LLAnalyzer-revised-10point/TASK7_REPRODUCIBILITY_CLOSURE.md` and
  `TASK7_HANDOFF.md` document unresolved historical provenance and a proposed
  rerun, not an Ikram result package.
- `Runs/experiments/reports/GEMMA4_PHI4_RERUN_REPORT.md`, the phase-1 rerun
  logs, and related CSVs are local project reruns and are not identified as Dr.
  Ikram's complete framework replication.
- Remediation 1 and Remediation 2 explicitly document missing historical
  executable/timing provenance and incomplete model-backed reproduction. Their
  conclusions must be updated in interpretation, but their files are preserved.

The author clarification in the present task is the only inspected record that
identifies a complete Ikram cross-machine rerun. It is treated as an
author-reported assertion, not converted into fabricated raw data.

## Experiment-level interpretation

The detailed classification is in
`IKRAM_REPLICATION_MATRIX.md`. In summary:

| Boundary | Reported rerun status | Local artifact status | Current classification |
|---|---|---|---|
| RQ1, GGUF integrity/fuzzing | Complete evaluation reportedly rerun and matched | No Ikram corpus manifest, per-case table, sanitizer log, or binary link | AUTHOR-REPORTED MATCH |
| RQ2, memory residue and sanitisation | Complete evaluation reportedly rerun and matched | Original aggregate records support local arithmetic; Ikram artifacts absent | AUTHOR-REPORTED MATCH; not artifact-verified |
| RQ3, persistence and network observations | Complete evaluation reportedly rerun and matched | Original LM Studio evidence is summary-dependent; Ollama records are local bounded observations | AUTHOR-REPORTED MATCH; not artifact-verified |
| RQ4, saved slots and timing | Complete evaluation reportedly rerun and matched | Original slot rows support local arithmetic; timing vectors remain absent; Ikram artifacts absent | AUTHOR-REPORTED MATCH; not artifact-verified |

The phrase “matched” is intentionally not assigned a new exact number. The
clarification does not provide per-experiment counts, confidence intervals,
model-by-model results, timing vectors, or a comparison table.

## Scientific classification

The evidence layers are distinct:

1. **Original independently recomputed archival records.** The prior audit
   recomputed retained local JSON/CSV-derived results, including the memory
   aggregate arithmetic and RQ4 slot/continuation counts.
2. **Author-reported cross-machine replication.** Dr. Ikram's full rerun is now
   explicitly recorded at this level. It is a collaborative replication, not an
   independent third-party reproduction.
3. **Artifact-verified cross-machine replication.** Not established until the
   existing Ikram records are supplied or located and linked from source through
   analysis.
4. **Secondary expert review.** P. K. Sharma checked arithmetic, source and
   documentation consistency, and scope limitations; that review is not Dr.
   Ikram's rerun and did not constitute an independent experimental execution.
5. **Independently executed third-party reproduction.** None is evidenced by
   the inspected workspace or the current author clarification.

## Manuscript protection

No manuscript source, PDF, original result, patch, or historical report was
modified. RQ1, RQ2, RQ3, and RQ4 remain in scope. Proposed language is isolated
in `PROPOSED_REPLICATION_MANUSCRIPT_TEXT.md` for author approval; it is not
automatically inserted into the T-IFS manuscript.

## Minimum conclusion for IEEE T-IFS

The full contribution can remain preserved. The paper may accurately state,
after author approval, that a complete cross-machine rerun by a collaborator
was reported to reproduce the original evaluation. It should not state that the
replication has been independently audited, artifact-verified, or independently
executed by a third party until the minimum existing-record package in
`IKRAM_EVIDENCE_REQUEST.md` is available.
