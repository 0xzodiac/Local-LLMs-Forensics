# Remediation and revision history

## Task 1: manuscript restructuring and page preparation

Task 1 reorganized the manuscript, established the target page structure, and
prepared the main/supplement split. Authoritative notes: `TASK1_HANDOFF.md`,
`TASK1_CHANGELOG.md`, and `TASK1_BASELINE_AUDIT.md`. Reuse the page-aware
structure, but do not treat a clean layout as scientific validation.

## Task 2: abstract and index terms

Task 2 revised the abstract and index terms and mapped abstract claims to
evidence. Reuse the lifecycle thesis and four-boundary terms. Recheck any
headline number against the master catalog before final prose.

## Task 3: software provenance and patch reproducibility

Task 3 investigated source identity, build details, patches, and reproducibility.
It established that the historical source/binary chain was incomplete and that
the retained prompt patch was malformed. Authoritative files include
`TASK3_SOFTWARE_PROVENANCE.md`, `TASK3_REPRODUCIBILITY_AUDIT.md`, and
`TASK3_HANDOFF.md`. Do not silently substitute the later Remediation 2 commit
for the historical source.

## Task 4: disclosure and vulnerability classification

Task 4 corrected responsible-disclosure language, vendor-policy interpretation,
and CWE/status claims. `TASK4_DISCLOSURE_ACTION_PLAN.md`,
`TASK4_FINDING_CLASSIFICATION.md`, and `TASK4_HANDOFF.md` are the source of
truth. Preserve “no CVE, vendor acknowledgement, or finding-specific closure
claimed” unless new documentary evidence is supplied.

## Task 5: Linux memory threat model

Task 5 corrected the distinction between authorized acquisition and unprivileged
same-UID access, including Yama/PTRACE semantics and parent-child provenance.
Reuse `TASK5_BASELINE_THREAT_MODEL.md`, `TASK5_LINUX_PERMISSION_AUDIT.md`,
`TASK5_ACQUISITION_PROVENANCE.md`, and `TASK5_HANDOFF.md`.

## Task 6: logging and resource authorization

Task 6 bounded LM Studio logging claims and separated API-key authentication
from resource-level authorization in `llama-server`. Reuse
`TASK6_LMSTUDIO_DEFAULT_AUDIT.md`, `TASK6_LLAMACPP_AUTHZ_AUDIT.md`,
`TASK6_PERSISTENCE_VALIDATION.md`, and `TASK6_HANDOFF.md`.

## Task 7: final integrity and readiness review

Task 7 audited figures, tables, statistics, claims, timing, reproducibility,
and main/supplement consistency. It concluded that the main manuscript is
format-ready but scientific blockers remained. The relevant files are
`TASK7_FINAL_CLAIM_EVIDENCE_MATRIX.md`, `TASK7_STATISTICAL_AUDIT.md`,
`TASK7_REPRODUCIBILITY_CLOSURE.md`, `TASK7_SUBMISSION_READINESS.md`, and
`TASK7_HANDOFF.md`.

## Remediation 1

Remediation 1 searched for the historical source, binary, valid prompt patch,
and timing data. It independently checked retained memory arithmetic but did not
recover the historical chain or run a new model-backed campaign. Its completion
report is `remediation1/REMEDIATION1_COMPLETION_REPORT.md`.

## Remediation 2

Remediation 2 pinned a source candidate, built baseline and intervention
variants, implemented a new prompt-zeroisation architecture, and verified buffer
controls under ASan. It did not perform a model-backed experiment because no
authorized weights/workload were available. Its classification is engineering
verified, full experiment pending.

## Remediation 2B

Remediation 2B inventoried historical artifacts and independently recomputed
selected memory, slot, continuation, Wilson, telemetry, and KV benchmark
results. It produced the RQ evidence files, reanalysis script, provenance
assessment, and salvage/readiness reports.

## Ikram replication integration

The author subsequently confirmed that Dr. Mohammed Ikram completed a full
cross-machine rerun and reported matching results. This dossier integrates that
history as author-reported collaborative replication. It does not claim that
the server-side artifacts were locally inspected, and it does not trigger
another audit or campaign.

