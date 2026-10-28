# External-review claim matrix

| Criticism | External evidence used | Independent activity | Retained-primary status | Current assessment |
|---|---|---|---|---|
| Tested llama.cpp revision unresolved | Public repository lookup and article's `388d39f3e` discussion | Source inspection | Confirmed: unresolved historical revision; `721354f` is new remediation only | Open provenance blocker |
| Linux memory permissions/ptrace | Ubuntu/Yama documentation and paper's missing acquisition details | Documentation inspection and inference | Task 5/7 bounded threat model; no original acquisition manifest | Memory observation cannot be generalized to every same-user attacker |
| Sanitisation evidence | Paper tables, patch/disclosure records, 110/78 and KB figures | Arithmetic plus document inspection | Aggregate JSON supports arithmetic; binary/patch attribution incomplete | Descriptive reduction, unresolved causality |
| Allocator-tunable results | Paper mentions settings but gives no results | Text audit | No raw results located | Unsupported result claim |
| LM Studio logging defaults | Paper configuration plus product documentation/artifact references | Documentation inspection; no rerun | Historical log file absent; configuration-specific reports remain | Do not call it a clean-install default |
| Cross-client API-key assumptions | `/slots` documentation and paper protocol | Documentation and conceptual review | Per-trial transfer records retained; principal separation not fully proven | State-transfer finding remains conditional |
| Slot-save prerequisites | `--slot-save-path` documentation | Documentation inspection | Retained scripts show flag enabled | Not a default all-deployments claim |
| WAN timing generalization | Paper prose versus absent WAN route/load/sample data | Text audit | No TTFT vectors found | Bound to evaluated conditions; AUC unresolved independently |
| Statistical interpretation | Wilson interval, percentage arithmetic, sample-size review | Independent arithmetic | Recomputed here | Retained rates are supported; dependence caveat remains |
| Vendor disclosure | Security policy, public repository and disclosure-plan status | Source/document inspection | Task 4–7 retain no vendor acknowledgement or closure | Do not imply confirmed disclosure response |
| Incomplete workload reporting | Missing results for listed further experiments and allocator settings | Text audit | No corresponding raw artifacts found | Historical summary only |
| Network observations | Product docs and paper's bounded monitoring | Documentation plus interpretation | Telemetry raw summaries/pcaps retained; no universal version claim | Bounded no-canary-egress observation |
| Missing test artifacts | Article notes absent vectors/manifests and public artifact limits | Artifact/document audit | Same gaps remain after local search | Open reproducibility blocker |

Grades in this matrix describe evidence support, not severity or practical impact.
