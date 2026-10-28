# LLAnalyzer elite editorial-engineering report

Date: 2026-10-12 (final editorial QA pass)

This report documents an evidence-frozen editorial reconstruction. No
experiment, server, model load, binary build, disclosure action, or historical
evidence edit was performed.

## Editorial baseline and traceability

Before editing, the exact active sources were copied to
`recon_out/editorial-backup-20261011-v1/`. The SHA-256 manifest is
`recon_out/editorial-backup-20261011-v1/SHA256SUMS.txt`; it covers the main
source, both supplementary sources, the bibliography, and both active TikZ
figure sources. `LLANALYZER_EDITORIAL_CHANGES.diff` is a genuine unified diff
against those byte-preserved sources.

## Main-paper structural changes

- Reframed the contribution list as an operational measurement framework and
  case study. The four boundaries remain the conceptual backbone, but the text
  now states that the decomposition is logical and that the retained isolation
  workload is not a distinct-principal authorization test.
- Cleaned the source preamble of stale USENIX comments and duplicate package
  loading, without changing the IEEEtran layout or title.
- Tightened the paper roadmap and the boundary-oriented measurement paragraph.
- Reworked the control paragraph to distinguish within-family controls from
  heterogeneous Nemotron-only, Phi-4-only, and GPU-v5 observations.
- Reorganized the runtime discussion so the evidence-consistent mechanism
  account, D4 model-swap residue, sanitisation limitations, and GPU scope form
  one cumulative argument rather than four independent claims.
- Added a related-work positioning paragraph that explicitly distinguishes the
  paper from shared-cache attacks and local-forensics studies by its evidence
  units and threat-model limits.
- Recast the conclusion as a synthesis of lifecycle-wide confidentiality
  evidence rather than a claim of a new authorization vulnerability.
- Updated the architecture figure labels so the retained Phi-4-only heap/KV
  diagnostics and Nemotron-only sanitised rows cannot be read as pooled
  four-model measurements.

## Supplementary-paper structural changes

- Preserved the self-contained methodology, hardware/software tables, boundary
  mapping, workload specifications, and statistical definitions.
- Corrected past-tense reporting and clarified that the retained twelve-tenant
  rows are Nemotron-only, the multilayer diagnostics are Phi-4-only, and the
  GPU-v5 campaign is Nemotron-only.
- Added an explicit model-coverage paragraph listing the retained four-model
  families and the unresolved `phi3`/`phi4` GGUF label.
- Replaced the overbroad matched-binary wording with a precise distinction:
  the KV-overhead arrays are paired descriptive observations, whereas the two
  twelve-tenant rows are confounded single-run records.
- Removed active language suggesting an unretained coverage-guided campaign
  was an evaluated quantitative result. The historical campaign total is not
  used.
- Clarified that “another client's continuation response” is a threat-model
  criterion, not an executed retained protocol, and that the configured 56-cell
  KV diagnostic scope has no retained per-cell result file.

The source still contains a large inactive, commented historical appendix at
the end of `TIFS_Supplementary_Methods.tex`. It is not compiled or visible in
the supplementary PDF; it was left byte-addressable for archival comparison
and is excluded from the active scientific document.

## Language and scientific-story improvements

- Normalized the central vocabulary to *confidentiality boundary*, *residual
  state*, *conditional forensic recoverability*, *same-process state transfer*,
  *model-visible continuation*, and *configuration-specific persistence*.
- Replaced causal verbs such as “identify” with evidence-consistent language
  where debugger traces and confounded configurations do not support a full
  causal decomposition.
- Made the Nemotron attribution explicit for the LM Studio logging-toggle
  result and the twelve-tenant/GPU observations while retaining four-model
  coverage for the named four-model families.
- Kept the July 3--4 chronology next to the 126/200 continuation result.
- Retained the exact denominators and measurement meanings for slot equality,
  continuation, D4, Ollama, GGUF, and GPU records.
- Reduced source clutter and removed stale venue comments without compressing
  essential methods or limitations.
- Verified the active cross-document Supplementary table references against
  the compiled order (S1 hardware, S2 software, S3 evaluated models, S4
  boundary map, S5 evidence source, S6 model specifications); the main-paper
  S4--S6 prose references are therefore retained.

## Technical claims preserved

The revision preserves the locked observations: 200/200 same-process slot
equality checks; July 126/200 KV-channel continuation with the
50/50, 50/50, 25/50, and 1/50 model split; 200/200 memory-channel hits;
four-model D4 records; Nemotron 11/12 single-run tenant observations with
110/10,834 and 78/3,352 metrics; descriptive KV-overhead arrays; 50 Nemotron
partial-CUDA GPU-v5 records; 206 Ollama metadata records with 203/2/1
successful/failed/incomplete accounting; configuration-specific LM Studio
logging observations; and GGUF SIGABRT observations with no recorded SIGSEGV.

No cross-principal authorization bypass, causal sanitisation effect, binary
equivalence claim, historical timing result, or unretained fuzzing total was
added.

## Content allocation

The main paper retains the scientific argument, threat model, core protocols,
denominators, principal observations, and interpretation limits. The supplement
retains detailed hardware/software configuration, model specifications,
instrumentation, model-specific settings, record-accounting rules, provenance
limitations, and statistical definitions. See
`LLANALYZER_MAIN_SUPPLEMENT_CONTENT_MAP.md` for the detailed map.

## Author-only decisions remaining

1. Replace `\artifacturl{TODO}` with the final artifact URL if and when the
   authors choose to expose one.
2. Confirm the target IEEE T-IFS submission template/length policy at the time
   of submission; the current working build is 11 main pages and 5 supplement
   pages under the local `IEEEtran` class.
3. Decide whether to retain the current title or adopt a narrower measurement-
   focused title suggested by the novelty stress test.
4. Complete any venue-required AI-use, artifact, and disclosure fields in the
   submission portal. No submission or vendor action was initiated here.
