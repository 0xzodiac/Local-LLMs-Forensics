# LLAnalyzer Remediation 2B

This directory is a read-only historical-evidence audit. It does not download models, run inference, modify historical inputs, or overwrite the manuscript.

## Reproduce the independent calculations

```bash
cd /home/elaref/Documents/research/Local-LLMs-Forensics
python3 -m py_compile remediation2b_historical_evidence/scripts/independent_reanalysis.py
python3 remediation2b_historical_evidence/scripts/independent_reanalysis.py
```

The generated machine-readable output is `analysis/independent_reanalysis.json`. The script hashes the retained primary files it consumes and recomputes binary rates, Wilson intervals, memory aggregate arithmetic, and KV benchmark descriptive statistics. It does not use headline numbers from the manuscript as expected outputs.

## Scientific boundary

The retained per-trial JSON supports the 200/200 protocol-level transfer result and the 126/200 model-mediated continuation result. The two retained memory JSON files support their aggregate copy arithmetic and recorded recovery rates, but not independent reconstruction of memory regions or the stored KB totals. The GGUF campaign and timing AUC remain summary-only because identifiable machine-generated fuzz tables, sanitizer logs, cached/uncached TTFT vectors, and the original AUC script were not found.

## Ikram full-framework replication clarification

The author subsequently reported that Dr. Mohammed Ikram completed a full
cross-machine rerun of the LLAnalyzer evaluation and reproduced the original
experimental results. This directory now records that claim as
`AUTHOR-REPORTED MATCH`; no local Ikram run bundle was found, so it is not
artifact-verified here and is not a third-party independent reproduction.

- `IKRAM_FULL_REPLICATION_AUDIT.md`
- `IKRAM_REPLICATION_MATRIX.md`
- `IKRAM_REPLICATION_PROVENANCE.md`
- `IKRAM_EVIDENCE_REQUEST.md`
- `UPDATED_SCIENTIFIC_READINESS.md`
- `PROPOSED_REPLICATION_MANUSCRIPT_TEXT.md`
