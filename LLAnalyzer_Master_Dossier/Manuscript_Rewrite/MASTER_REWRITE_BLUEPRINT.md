# Master manuscript rewrite blueprint

## Editorial objective

Rewrite the paper as one coherent systems-security argument: local execution
removes one external trust boundary but does not guarantee prompt
confidentiality across model admission, runtime lifetime, wrapper persistence,
and shared serving state. Keep all four RQs and the full contribution. Attach
every result to a measurement condition and evidence class.

## Recommended 13-page architecture

| Section | Purpose | Budget |
|---|---|---:|
| Abstract and index terms | Problem, framework, bounded headline results | 0.35 |
| 1. Introduction | Motivation, gap, thesis, contributions | 1.25 |
| 2. Confidentiality boundary framework and threat model | Definitions and adversaries | 1.30 |
| 3. LLAnalyzer system design | Architecture and evidence pipeline | 1.55 |
| 4. Experimental methodology | Environment, workloads, controls, statistics | 1.65 |
| 5. Evaluation: RQ1--RQ4 | Results and mechanism interpretations | 4.75 |
| 6. Discussion and limitations | Cross-boundary synthesis and scope | 0.75 |
| 7. Related work | Positioning by research family | 0.85 |
| 8. Conclusion and open science | Takeaway and replication statement | 0.55 |
| References, tables, figure overhead | Inside IEEE page total | included |

The current main PDF is 13 pages and the supplement is 5 pages. Do not change
fonts, margins, column widths, or the IEEEtran layout to fit unreviewed prose.

## Section-by-section sequence

### Abstract

State the lifecycle problem, name LLAnalyzer and the four boundaries, summarize
the bounded RQ1 negative result, the RQ2 residual and aggregate mitigation
result, the RQ3 configuration difference, and the RQ4 direct-transfer and
continuation results. Keep AUC as a historical evaluated-condition result. The
Ikram rerun belongs in reproducibility/open science, not as an unsupported
abstract-level replication statistic.

### 1. Introduction

Open with the local-execution/privacy distinction. Introduce the prompt
lifecycle and explain why isolated demonstrations do not answer a lifecycle
question. Present the four boundaries and the empirical contrast. Make the
contributions four or five precise items. End with the paper map.

### 2. Framework and threat model

Define residual existence, conditional forensic recoverability, adversarial
access, and confidentiality compromise. Introduce A1, F, A2, and A3. Explain
why same UID is not arbitrary `/proc` access and why API keys are not tenant
authorization. Use the existing threat-model table.

### 3. LLAnalyzer

Explain Figure 1 as a data path, then show how each boundary receives a
controlled input, measurement point, and decision rule. Describe canaries,
artifact mutation, memory acquisition, wrapper observation, saved-state
protocol, and timing. The framework contribution is attribution, not an
assumption that every boundary produces a vulnerability.

### 4. Methodology

Consolidate the supplement's hardware/software table, model table, workloads,
baseline/mitigation conditions, network scope, trial definitions, and Wilson
analysis. Put the historical source/binary and timing-data gaps in a short
reproducibility paragraph rather than hiding them in the supplement.

### 5. Evaluation

Use four subsections in RQ order. Each subsection must have: question, protocol,
result, mechanism, evidence grade, and limitation. RQ2 should show the
110/78 and 10,834/3,352 table. RQ4 should show direct transfer before
continuation and retain all four model-specific continuation rates.

### 6. Discussion and limitations

Synthesize the uneven boundary result. State what the mitigations do and do not
repair. Mention historical provenance, authorized acquisition, wrapper scope,
logical clients, timing scope, negative-result boundaries, and the author-
reported Ikram rerun once each.

### 7. Related work

Group citations by parser/model artifacts, memory forensics, wrapper persistence,
KV/timing, prompt injection, and serving isolation. End by explaining that
LLAnalyzer connects these surfaces in one measurement design.

### 8. Conclusion/open science

Return to the thesis. State that local execution is a deployment property, not
the endpoint of confidentiality. Add the cautious collaborative replication
statement and identify the artifact package without claiming uninspected files.

## Reuse map

Reuse the current source's title, abstract core, Figure 1, threat-model table,
measurement-pipeline table, model table, residue table, blast-radius table,
overhead table, and VRAM table. Reuse the supplement's hardware/software,
workload, scale, and statistics descriptions. Use the dossier's evidence map to
rewrite any sentence that currently combines raw observation with causal or
universal language.

