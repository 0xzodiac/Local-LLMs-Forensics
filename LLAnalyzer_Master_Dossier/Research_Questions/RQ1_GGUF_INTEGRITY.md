# RQ1 dossier: model-artifact integrity

## 1. Research question

Can a maliciously crafted GGUF model artifact bypass parser validation or
trigger a relevant memory-safety failure before inference begins?

## 2. Security hypothesis

Model admission is a confidentiality boundary because a malformed artifact can
compromise the trusted execution context before any prompt-lifecycle control is
tested. The bounded hypothesis is that semantic mutations in tensor metadata,
dimensions, offsets, lengths, and related header fields may reach unsafe parser
or allocation paths.

## 3. Software, models, and environment

The evaluation targets the GGUF reader and associated `llama.cpp`/`gguf-py`
loading paths. The manuscript describes four open-weight model families and
the supplement identifies the model corpus as GGUF Q4_K_M artifacts. The
historical executable and exact source-to-binary link are not retained. The
identified scripts include `Runs/scripts/gguf-fuzzer.py` and related mutation
programs; the retained reports are `GGUF_SURGICAL_REPORT.md`,
`GGUF_CROSS_MODEL_REPORT.md`, and `GGUF_WEAPONIZATION_EXPLORATION.md`.

## 4. Inputs and protocol

The structured component contains:

1. an 80-case malformed-input battery targeting validation after allocation;
2. a 21-file structural-header corpus targeting tensor dimensions, names,
   metadata lengths, architecture identifiers, offsets, RoPE parameters, and
   related consistency constraints; and
3. a coverage-guided AFL++ campaign reported as more than 1.2e7 executions in
   24 hours under ASan and UBSan instrumentation.

Each artifact is loaded independently. The intended classification includes
clean rejection, handled parse error, unhandled exception, process termination,
successful malformed loading, and memory-safety failure. The structured files
are also processed through the Python tooling where documented to compare C++
and Python parser behavior.

## 5. Measurements and variables

- **Independent variables:** mutation family, malformed field, corpus member,
  parser implementation, and fuzz-generated input.
- **Dependent variables:** load status, signal/exit outcome, sanitizer finding,
  parser crash, and evidence of successful malformed loading.
- **Controls:** valid GGUF input, clean process launch, and sanitizer-enabled
  execution where reported.
- **Sample definition:** 80 structured cases, 21 structural files, and a
  reported long campaign exceeding 12 million executions.

## 6. Recorded result

The manuscript reports no parser crash, sanitizer violation, or successful
malformed GGUF load within the explored state space. This is a bounded negative
observation. It is not evidence that the parser is globally memory-safe: the
project's related-work and correction records distinguish validation-path tests
from allocation-arithmetic vulnerabilities reported elsewhere.

The retained workspace contains program sources and hand-written summaries, but
the historical audit did not identify a machine-generated per-input manifest,
complete sanitizer log, coverage database, or executable hash for the headline
80/21/24-hour chain. Additional 96-test and weaponisation reports must not be
silently pooled with the headline campaign.

## 7. Interpretation

The defensible statement is:

> In the evaluated corpus and reported coverage-guided campaign, LLAnalyzer
> observed no relevant parser crash, sanitizer violation, or successful
> malformed load.

The result demonstrates the value of a validation-gap measurement boundary. It
does not certify the parser, establish absence of all CVEs, or establish that a
future version behaves identically.

## 8. Evidence and reproducibility

Primary paths:

- `Runs/scripts/gguf-fuzzer.py` and related attack scripts;
- `Runs/experiments/reports/GGUF_SURGICAL_REPORT.md`;
- `Runs/experiments/reports/GGUF_CROSS_MODEL_REPORT.md`;
- `Runs/experiments/reports/GGUF_WEAPONIZATION_EXPLORATION.md`;
- `LLAnalyzer-revised-10point/TASK7_FINAL_CLAIM_EVIDENCE_MATRIX.md`; and
- `remediation2b_historical_evidence/RQ1_EVIDENCE.md`.

Status: **E4 for the headline campaign**, with some **E3 source/document
support**. Dr. Ikram's complete rerun is **AUTHOR-REPORTED MATCH** at the
framework level, but no Ikram corpus, sanitizer, or host artifact was inspected.

## 9. Reviewer questions and grounded answers

**Does zero failure mean the parser is safe?** No. It means no failure was
observed in the tested state space.

**Were all malformed files retained?** Not in the inspected local audit as a
complete machine-generated corpus bundle.

**Does the Ikram report close this gap?** It records a reported matching full
rerun; it does not supply the per-case rerun artifacts needed for artifact-level
verification.

