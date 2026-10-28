# Final author handoff for tomorrow's rewrite

## A. What is ready?

The dossier now contains:

- a master scientific record and four-boundary contribution statement;
- corrected threat-model and architecture explanations;
- complete RQ1--RQ4 experiment dossiers;
- a master results catalog, verified-statistics record, configuration matrix,
  and claim-to-evidence map;
- a full 13-page rewrite blueprint and author-editable section drafts;
- figure/table inventories and placement guidance;
- bibliography and related-work maps;
- original artifact index, remediation history, Ikram replication status, and
  consolidated limitations; and
- a separate record of Dr. Ikram's author-reported complete cross-machine rerun.

## B. What should I read first?

1. `00_START_HERE.md`.
2. `01_RESEARCH_MASTER_RECORD.md`.
3. `Results/MASTER_RESULTS_CATALOG.md`.
4. `Research_Questions/RQ2_MEMORY_LIFETIME.md` and
   `Research_Questions/RQ4_SHARED_STATE_ISOLATION.md`.
5. `Manuscript_Rewrite/MASTER_REWRITE_BLUEPRINT.md`.
6. `Reproducibility/SCIENTIFIC_LIMITATIONS.md`.

## C. How should I rewrite the manuscript?

Use the blueprint's sequence: introduction and thesis first; framework and
threat model second; system design and methodology third; then write RQ1--RQ4
in order. For every numerical sentence, consult the master catalog. Write the
measurement first and the mechanism interpretation second. Put each limitation
next to the claim it bounds rather than collecting all uncertainty at the end.

Do not restructure the paper around a single strongest finding. The scientific
argument is the contrast across four boundaries.

## D. Which figures and tables should I reuse?

Reuse:

- `LLAnalyzer-revised-10point/figures/fig_llanalyzer_arch.tex` and its PDF for
  Figure 1;
- `tab:threatmodel`, `tab:measurement_pipeline`, `tab:models`,
  `tab:model_boundary_results`, `tab:blast`, `tab:overhead`, and `tab:vram` in
  `LLAnalyzer-revised-10point/T-IFS.tex`; and
- `tab:hardware_config`, `tab:software_config`, `tab:evaluated_models`, and
  `tab:experiment_scale` in
  `LLAnalyzer-revised-10point/TIFS_Supplementary_Methods.tex`.

Use `figures/timing_auc_decay.pdf` only with the historical-AUC qualification.
The complete placement plan is in `Figures_and_Tables/`.

## E. Which experimental results should I preserve?

Preserve the bounded RQ1 negative result; the RQ2 11/12, 110-to-78, and
10,834-to-3,352 recorded metrics; the 56/56 KV mechanism observation; the
configuration-specific LM Studio result; the bounded 205-session Ollama
negative observation; the 200/200 direct transfer; the 126/200 continuation
with all model-specific rates; and the historical AUC=1.000 result. The exact
evidence status and source path for each is in
`Results/MASTER_RESULTS_CATALOG.md`.

## F. Which previous mistakes should I avoid reintroducing?

- Do not call the parser globally safe because RQ1 found no failure.
- Do not treat F's authorized memory acquisition as arbitrary same-UID access.
- Do not call recorded matching-region KB literal secret-byte volume.
- Do not attribute the historical aggregate mitigation causally to the malformed
  prompt patch.
- Do not call LM Studio logging a universal clean-install default.
- Do not equate API keys with independent tenant authorization.
- Do not merge direct slot transfer with model continuation.
- Do not substitute KV overhead vectors for missing TTFT vectors.
- Do not claim WAN timing generality.
- Do not claim a CVE, vendor acknowledgement, or finding-specific closure.
- Do not describe the Ikram collaborator rerun as third-party independent
  reproduction or as locally artifact-verified.

## G. How should I describe Dr. Ikram's rerun?

Use:

> The authors report that collaborator Dr. Mohammed Ikram completed a full
> cross-machine rerun of the LLAnalyzer framework on a separate research server
> and obtained results matching the original evaluation. We record this as
> collaborative replication; the server-side run artifacts were not inspected
> in the present local evidence package.

This is accurate and does not imply that the rerun never happened or that its
uninspected details have been independently verified.

## H. What should remain in the Supplement?

Keep hardware/software provenance, model identifiers, memory-acquisition
permissions, detailed workload sequences, corpus construction, allocator and
patch conditions, model-specific continuation data, Wilson formulas, negative-
result checks, the historical timing-data limitation, and the three-layer
replication-status table. Keep detailed raw-path references without copying
large artifacts into the manuscript repository.

## I. Recommended 13-page distribution

Use the following working budget without changing the IEEE template:

| Section | Pages |
|---|---:|
| Abstract | 0.35 |
| Introduction | 1.25 |
| Framework/threat model | 1.30 |
| LLAnalyzer design | 1.55 |
| Methodology | 1.65 |
| Evaluation RQ1--RQ4 | 4.75 |
| Discussion/limitations | 0.75 |
| Related work | 0.85 |
| Conclusion/open science | 0.55 |
| **Total** | **13.00** |

Move detail to the five-page supplement before shrinking technical explanation.

## J. What author decisions remain?

Only writing and submission decisions remain:

1. Which proposed wording best matches the authors' voice and final evidence
   release plan?
2. Whether to cite the external Sharma review and Korean discussion in the main
   paper or retain them only in the research-history record.
3. Which tables or the historical timing figure move to the supplement for
   final page balance.
4. Final author metadata, artifact-release links, EDICS, and venue submission
   fields.
5. Whether existing collaborator rerun records can be released or cited as an
   author-supplied supplementary artifact.

No further broad audit or experimental campaign is recommended for tomorrow's
rewrite session.

