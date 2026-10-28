# Table inventory

| Label | Current source | Current purpose | Keep | Required rewrite check |
|---|---|---|---|---|
| `tab:threatmodel` | `T-IFS.tex` around line 326 | Boundary, adversary, security objective | Main | Preserve F versus A1 and A2 authorization wording |
| `tab:measurement_pipeline` | `T-IFS.tex` around line 427 | Boundary-specific evidence | Main | Ensure each evidence type maps to a retained path or historical qualifier |
| `tab:models` | `T-IFS.tex` around line 538 | Four evaluated model families | Main | Keep names/parameters consistent with supplement and model-digest record |
| `tab:model_boundary_results` | `T-IFS.tex` around line 698 | RQ1 boundary result | Main | Scope negative result to explored state space |
| `tab:residue` | `T-IFS.tex` around line 823 | Per-tenant heap residue | Main or supplement | Do not impute unreported cells; preserve retained rows only |
| `tab:blast` | `T-IFS.tex` around line 1040 | Baseline/sanitised twelve-tenant aggregate | Main | Label KB as recorded matching-region metric and state 11/12 unchanged |
| `tab:overhead` | `T-IFS.tex` around line 1061 | n=50/model KV overhead | Main or supplement | Distinguish from missing cached/uncached TTFT vectors; descriptive only |
| `tab:vram` | `T-IFS.tex` around line 1186 | Host memory during partial GPU offload | Main or supplement | Do not imply device-memory access or all GPU architectures |
| `tab:hardware_config` | `TIFS_Supplementary_Methods.tex` around line 92 | Hardware/OS | Supplement | Mark reported historical configuration where binary provenance is incomplete |
| `tab:software_config` | Supplement around line 161 | Software/provenance status | Supplement | Keep unknown historical source/binary fields explicit |
| `tab:evaluated_models` | Supplement around line 276 | Model roles | Supplement | Reconcile exact names and hashes with `model_digests.json` |
| `tab:experiment_scale` | Supplement around line 502 | Workload scales | Supplement | Preserve 80, 21, >1.2e7, 56, 200, 200, 400 reported timing, and 205 |

## Table-writing rule

Tables carry measurements; prose carries mechanism and scope. Do not put a
causal claim into a result cell. Add evidence labels or footnotes where a table
mixes raw-record-backed, historical, and author-reported values.

