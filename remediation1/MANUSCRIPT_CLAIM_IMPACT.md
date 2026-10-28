# Manuscript claim impact

## Decision summary

The manuscript may retain carefully qualified descriptions of what the archived records report. It should not state that the historical prompt-zeroization implementation causally produced the 29.1% copy or 69.1% recorded-volume reduction, that the historical binary is reproducible, or that the timing AUC is independently established.

## Claim map

| Claim family | Impact of remediation | Safe disposition |
|---|---|---|
| Baseline and sanitised aggregate observations | Arithmetic and schema checks pass for the two retained JSON records | Retain as archived descriptive observations; identify missing executable provenance |
| 29.1% copies and 69.1% recorded KB reduction | Numbers recompute, but the KB field is not independently derivable from retained raw regions and the source-to-binary chain is incomplete | Report as recorded/descriptive, not as a causally identified mitigation effect |
| KV zeroization | Original KV patch applies to the resolved source candidate and logs report 56/56 nonzero pre-write cells | Retain as mechanism evidence on the reconstruction; do not claim historical binary linkage or complete prompt confidentiality |
| Prompt Sites A+B | Original retained patch is malformed; repaired derivative applies, but residual records show incomplete coverage | Do not present historical causal attribution; describe partial/layered mitigation only with provenance caveat |
| Secure allocator and Sites C/D | Records show variable partial mitigation, but generated implementation and binary identity are not fully retained | Retain as exploratory evidence; avoid universal or complete-sanitization wording |
| Timing AUC | Figure is retained; raw vectors and analysis procedure are absent | Mark independently unreproducible and remove causal/quantitative emphasis until rerun |
| Generalized confidentiality or cross-model claims | Current evidence is one retained environment with absent model/build artifacts | Downgrade to scoped observations and explicitly state external-validity limits |

## Required wording boundary

Use “recorded,” “observed in the retained run records,” and “descriptive reduction” where appropriate. Reserve “caused,” “eliminated,” “reproducible,” “restored confidentiality,” and “generalizes” for claims supported by a new pinned source-to-binary-to-run reproduction and retained raw timing/memory inputs.
