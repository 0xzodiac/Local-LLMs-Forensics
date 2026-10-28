# Raw memory-result validation

## Validation performed

`remediation1/validation/verify_memory_results.py` was run against the two retained aggregate JSON records and wrote `remediation1/validation/recomputed_results.json`. The input files were not modified.

| Condition | Exact file | SHA-256 | Copies | Recovered tenants | Recorded KB |
|---|---|---|---:|---:|---:|
| Baseline | `Runs/logs/leak_blast_radius_20260623_213831.json` | `4d54ac8bd771420a93617a0e63f1ab1fa786cdfdeb5dca9815b86c7337dfb3f6` | 110 | 11/12 | 10,834 |
| Sanitised | `Runs/logs/leak_blast_radius_20260624_120421.json` | `ef6f5cecf832cabdb4d31620af371951ae727c75ed7644383662e00be7169c63` | 78 | 11/12 | 3,352 |

The validator confirms that each total equals the sum of its per-tenant counts, each recovery rate equals `tenants_recovered / n_tenants`, tenant counts are nonnegative integers, the cross-condition model/tenant/binary-path fields match, and both `binary_has_zero_cell_data` flags are true.

## Recomputed descriptive quantities

- Copy reduction: `(110 - 78) / 110 = 29.090909%`.
- Recorded printable-cleartext reduction: `(10,834 - 3,352) / 10,834 = 69.060366%`.
- Recovery rate in both records: `11 / 12 = 0.9166667`.

## Evidence boundary

The JSON schema contains aggregate copy counts, per-tenant counts, sample strings, and a recorded `printable_cleartext_kb` value. It does not retain the memory-region list, raw byte ranges, match offsets, or the calculation procedure needed to independently derive the KB values. The `binary_has_zero_cell_data` field is a recorded flag, not an executable-level proof.

Accordingly, the retained records support the stated descriptive arithmetic and the existence of recorded observations. They do not establish that the repaired prompt patch caused the reduction, that the historical executable was the named binary, or that confidentiality was fully restored. Those are causal and generalization claims requiring a new pinned reproduction.
