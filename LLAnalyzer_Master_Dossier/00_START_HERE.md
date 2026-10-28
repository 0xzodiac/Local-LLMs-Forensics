# LLAnalyzer Master Research Dossier

## Purpose

This directory is the single author-facing preparation package for rewriting
*The Illusion of Local Privacy: Confidentiality Boundary Failures in Consumer
LLM Serving Systems* for IEEE Transactions on Information Forensics and
Security. It consolidates the current authoritative manuscript, supplement,
retained experiment records, Task 1--7 corrections, Remediations 1--2B, and
the reported Dr. Mohammed Ikram cross-machine rerun.

This is a documentation and writing package. It does not replace the
authoritative TeX, modify historical data, download models, run inference, or
start another scientific campaign.

## Read first tomorrow

1. [`01_RESEARCH_MASTER_RECORD.md`](01_RESEARCH_MASTER_RECORD.md) for the scientific story and canonical
   results.
2. [`Results/MASTER_RESULTS_CATALOG.md`](Results/MASTER_RESULTS_CATALOG.md) for claim-level evidence and exact
   source paths.
3. [`05_EXPERIMENTAL_METHODOLOGY.md`](05_EXPERIMENTAL_METHODOLOGY.md) and the four files in
   `Research_Questions/` for writing-ready method detail.
4. [`Manuscript_Rewrite/MASTER_REWRITE_BLUEPRINT.md`](Manuscript_Rewrite/MASTER_REWRITE_BLUEPRINT.md) for the section sequence
   and page budget.
5. [`FINAL_AUTHOR_HANDOFF.md`](FINAL_AUTHOR_HANDOFF.md) for the practical rewrite order.

## Evidence legend

- **Raw-record-backed calculation:** recomputed from retained structured rows or
  vectors using the existing independent analysis script.
- **Machine-generated aggregate:** a retained structured result with identifiers
  and fields, but without enough raw acquisition detail to reproduce every
  underlying measurement.
- **Source/document-supported observation:** supported by code, documentation,
  configuration, or a report, but not by a complete machine-generated result
  chain.
- **Historical report:** a result stated in the manuscript or a hand-written
  report whose complete raw chain is absent.
- **Author-reported collaborative replication:** Dr. Ikram's complete rerun is
  explicitly reported as matching the original evaluation; the server-side
  artifacts are not in the inspected local workspace.

## Non-negotiable wording rules

1. Local execution is a deployment property, not a complete confidentiality
   guarantee.
2. Authorized forensic acquisition establishes residual existence and
   conditional recoverability, not unprivileged same-UID access.
3. A different API key is not proof of a distinct tenant principal or
   resource-level authorization.
4. The 200/200 slot result and 126/200 continuation result are separate
   outcomes.
5. The recorded `KB` field is a recovered matching-region metric, not literal
   secret-byte volume.
6. The AUC=1.000 timing result is historical because its per-request TTFT
   vectors and original script are not retained locally.
7. Dr. Ikram's rerun is a collaborative cross-machine replication report, not
   an independently executed third-party reproduction and not yet an
   artifact-verified local record.
8. The RQ1 negative result is bounded to the explored corpus and campaign; it
   is not a universal parser-safety claim.

## Source of truth and protection

The authoritative manuscript is
`LLAnalyzer-revised-10point/T-IFS.tex`; the authoritative supplement is
`LLAnalyzer-revised-10point/TIFS_Supplementary_Methods.tex`. They remain
untouched by this dossier. Historical records under `Runs/`, Remediation 1,
Remediation 2, and the historical-evidence audit remain in place and are
referenced by path rather than copied into this directory.
