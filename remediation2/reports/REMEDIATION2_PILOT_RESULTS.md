# Remediation 2 pilot results

## Gate C verdict

The engineering control pilot passed, but the memory-forensics pilot did not execute. The retained result `results/pilot/control_tests.json` records two completed synthetic canary tests:

- secure-buffer positive/negative control: exit 0 under ASan;
- linked `server_task::zeroize_sensitive_buffers` control: exit 0 under ASan.

These tests verify identified-buffer behavior only. They do not acquire process memory, search permitted regions, recover prompt occurrences, or establish cross-client confidentiality.

The requested forensic pilot could not proceed because the workspace has no compatible model weights and therefore no successful controlled inference request. Yama is `ptrace_scope=1`; no protections were disabled and no capability was added. The no-model router health check is not a substitute for inference. There are zero forensic-memory raw records in the new result directory, as reported by `analysis/memory_statistics.json`.

The archived historical aggregate JSON files were not reused as pilot results. No historical number is reproduced or treated as a new measurement.
