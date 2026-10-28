# RQ2 evidence: memory residue and sanitisation

## Recomputed records

The two retained aggregate JSON files independently validate 12 tenants, 11 recovered tenants in each condition, 110 versus 78 canary copies, and recorded volumes of 10,834 versus 3,352 KB. Both stored per-tenant maps sum to the stored copy totals. The recovered-tenant rates are equal at 11/12.

## What the records establish

- **E1 for aggregate arithmetic:** calculations are independently recomputed from identifiable original structured records.
- **E2 for recorded observations:** the files are machine-generated-looking run records with run IDs, timestamps, model paths, and stored results.
- **E4/E5 boundary for causal mitigation:** the historical binary hash, startup manifest, memory regions, match offsets, raw acquisition output, and valid prompt patch are absent or incomplete. The new Remediation 2 patch is a separate implementation and does not upgrade the old result.

The `binary_has_zero_cell_data` field is a retained flag, not an executable-level proof. The 69.060366% figure is a reduction in a recorded field, not an independently recomputed byte-volume measurement.

## Defensible wording

The strongest supportable claim is that the retained baseline and sanitised records report a reduction in aggregate canary-copy and recorded-cleartext metrics while leaving the 11/12 tenant recovery count unchanged. Causal attribution, complete erasure, and universal confidentiality restoration remain unsupported.
