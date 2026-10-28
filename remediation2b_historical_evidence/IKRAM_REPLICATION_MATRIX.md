# Dr. Ikram replication matrix

**Status vocabulary:**

- **VERIFIED MATCH:** original and Ikram rerun artifacts establish agreement.
- **VERIFIED DIFFERENCE:** artifacts establish a discrepancy.
- **AUTHOR-REPORTED MATCH:** the author reports a matching rerun, but Ikram
  artifacts were not available for inspection.
- **NOT DETERMINABLE:** the available records do not establish that the specific
  experiment was included or what result it produced.

The present task explicitly states that Dr. Mohammed Ikram reran the complete
LLAnalyzer evaluation and reproduced the original experimental results. That
statement supports `AUTHOR-REPORTED MATCH` for the named core experiments, but
does not supply exact rerun numbers. No exact Ikram value is invented below.

| Experiment | Original result | Ikram rerun result | Available evidence | Status |
|---|---|---|---|---|
| RQ1: structured malformed-input battery | Manuscript/reports describe an 80-case evaluation | Reported to reproduce the complete evaluation; exact count/output not supplied | Original manuscript and hand-written GGUF reports; no Ikram corpus/result bundle | AUTHOR-REPORTED MATCH |
| RQ1: 21-file malformed-header corpus | Manuscript/reports describe a 21-file corpus | Reported to match; exact per-file outcomes not supplied | No retained machine-generated original per-file table and no Ikram table | AUTHOR-REPORTED MATCH |
| RQ1: long parser campaign, reported as >12 million executions over 24 hours | Historical headline reports no observed failure in explored state space | Reported to match; no execution count, duration log, or host record supplied | Summary-level original evidence only; no Ikram campaign log | AUTHOR-REPORTED MATCH |
| RQ1: sanitizer/coverage and exploratory weaponisation extensions | Additional reports contain exploratory 96-test/weaponisation observations, not a single locked headline record | The full-evaluation statement does not identify which auxiliary extensions were included | No experiment index maps these extensions to the Ikram run | NOT DETERMINABLE |
| RQ2: baseline prompt residue / 12-tenant memory observation | Retained records report 11/12 recovered tenants, 110 copies, and 10,834 recorded KB | Reported to match; exact Ikram counts not supplied | Local JSON supports original arithmetic; no Ikram memory acquisition records | AUTHOR-REPORTED MATCH |
| RQ2: sanitised condition and residue comparison | Retained records report 11/12 recovered tenants, 78 copies, and 3,352 recorded KB | Reported to match; no exact rerun metrics supplied | Local JSON supports recorded arithmetic; historical causal chain remains incomplete | AUTHOR-REPORTED MATCH |
| RQ2: KV-cache zeroisation observation | Retained report states 56/56 KV cells had nonzero pre-zero data | Reported to match; no Ikram probe output supplied | Local patch/report evidence; no Ikram probe or binary record | AUTHOR-REPORTED MATCH |
| RQ2: patched/unpatched KV overhead benchmark | Four-model, n=50 descriptive latency vectors are retained locally | Reported to match; no Ikram latency vectors supplied | Local vectors reproduce stored means; no Ikram benchmark output | AUTHOR-REPORTED MATCH |
| RQ2: prompt-zeroisation implementation/forensic effect | Historical prompt patch is malformed in the retained file; Remediation 2 is new engineering and had no model-backed run | Complete-framework match is reported, but the exact prompt mitigation protocol is not specified | No valid historical prompt patch or Ikram model-backed forensic record | NOT DETERMINABLE for the specific implementation claim |
| RQ3: LM Studio sensitive-log persistence | Historical reports describe canary recovery under the evaluated sensitive-logging configuration and no recovery after disabling/restarting | Reported to match; no Ikram plaintext log, version, or configuration supplied | Original plaintext log absent locally; six local telemetry summaries are bounded network observations | AUTHOR-REPORTED MATCH |
| RQ3: Ollama monitored egress/persistence observation | Retained local sessions report no recoverable canary in captured egress/artifacts | Reported to match; no Ikram packet/trigger/idle records supplied | 205 valid local sessions plus one incomplete directory; no Ikram bundle | AUTHOR-REPORTED MATCH |
| RQ4: cross-client saved-slot protocol transfer | Retained records support 200/200 direct transfers across four models, n=50/model | Reported to match; no Ikram slot JSON or server manifest supplied | Local slot/extraction JSON supports original arithmetic; distinct tenant principals remain bounded | AUTHOR-REPORTED MATCH |
| RQ4: model-mediated continuation after slot restoration | Retained records support 126/200 continuations, with model-specific counts | Reported to match; no Ikram per-trial continuation table supplied | Local cross-tenant JSON supports original arithmetic; no Ikram rows | AUTHOR-REPORTED MATCH |
| RQ4: cached versus uncached timing discrimination | Manuscript/reports state AUC = 1.000 for four models | Reported to match; no Ikram TTFT vectors or AUC script supplied | Original raw TTFT vectors and script were not found locally | AUTHOR-REPORTED MATCH at report level; artifact verification unavailable |
| RQ4: auxiliary GPU/offload and allocator observations | Historical reports contain bounded host/GPU/allocator observations | The full-evaluation assertion does not specify each auxiliary test | Existing local reports are not linked to Ikram records | NOT DETERMINABLE |

## Reading the matrix

The matrix deliberately uses two different kinds of uncertainty. `AUTHOR-REPORTED
MATCH` means the new author statement covers the identifiable core experiment;
it does **not** mean that the exact output is present. `NOT DETERMINABLE` is
reserved for auxiliary or implementation-specific items whose inclusion cannot
be inferred safely from the phrase “complete evaluation.”

The matrix must not be converted into a claim that every metric was numerically
identical. Agreement can be methodological or result-level; the retained
records do not say which comparison rule Dr. Ikram used.

