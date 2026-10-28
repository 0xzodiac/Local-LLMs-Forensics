# Remediation 2 patch validation

## Results

- `git apply --check patches/prompt_zeroization_new.patch` against the clean pinned baseline: passed.
- `git diff --check`: passed for C0, C1, C2, and C3.
- C1 KV-only source: original KV patch applied cleanly; build succeeded.
- C2 prompt-only source: new prompt patch compiled and build succeeded.
- C3 combined source: both interventions compiled and build succeeded.
- `const_cast`: not used.
- Historical malformed prompt patch: preserved and not substituted.

The first C2 attempt failed because `explicit_bzero` was not declared by the default glibc feature surface. The second attempt failed because the initial mutable-owner conversion left two `unique_ptr` type mismatches and made `server_slot` non-movable through a user-declared destructor. These failures are retained in the validation logs; the final design corrected the feature declaration, uses `server_task *` for the status read, constructs `std::unique_ptr<server_task>`, and performs cleanup in `reset`.

The buffer-level ASan test and the linked `server_task` ASan test both exit 0. The TSAN test cannot run on this host: the runtime aborts with `FATAL: ThreadSanitizer: unexpected memory mapping` and exit 66. The exact output is retained in `validation/tsan_control_test.log`. This is a host/toolchain limitation, not evidence of a race-free implementation.

The C2/C3 binaries support `--help` and `--version`. No model-backed inference or memory-forensics behavior was claimed because model weights are absent.
