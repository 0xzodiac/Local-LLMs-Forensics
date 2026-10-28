# Remediation 2 reproducibility checklist

## Engineering

- [x] Full pinned source commit recorded.
- [x] Clean unmodified baseline built.
- [x] New prompt patch applies cleanly.
- [x] No `const_cast` workaround.
- [x] Mutable ownership is limited to the exclusively owned active slot task.
- [x] C0, C1, C2, and C3 binaries built and hashed.
- [x] Buffer controls pass under ASan.
- [ ] Model-backed inference executed.
- [ ] TSAN execution completed; host runtime fails before test execution.

## Experiment

- [ ] Authorized process-memory pilot.
- [ ] Positive/negative forensic canary scan.
- [ ] Three independent process repetitions per condition.
- [ ] Historical 12-client logical workload.
- [ ] Raw memory-region metadata and offsets.
- [ ] New latency vectors.

## Provenance

- [x] Source, patch, build, binary, host, and analysis manifests generated.
- [x] Historical raw files left separate and unchanged.
- [x] Analysis script consumes generated records without expected outcomes.
- [ ] Model identifier and model hash, pending a model-backed run.
