# Prompt-zeroization patch root cause

## Finding

`Runs/patches/prompt_zeroize.patch` is structurally malformed. Git rejects it before applying a hunk:

```text
error: invalid mode on line 2: 1006--- a/tools/server/server-context.cpp
```

The second line concatenates an invalid mode token with the unified-diff separator. The first hunk also declares `+35` new lines while the retained hunk contains 37 added lines. After the header boundary is repaired, Git reports the hunk-count inconsistency as a corrupt patch.

## Mechanical recovery test

The copy at `remediation1/patch_recovery/prompt_zeroize_mechanically_repaired.patch` makes only two syntax repairs:

1. It changes `1006---` to a valid `100644` mode followed by a newline and `---`.
2. It changes the first hunk declaration from `@@ -296,6 +296,35 @@` to `@@ -296,6 +296,37 @@`.

No implementation statement, target file, or zeroization site was changed. The repaired copy has SHA-256 `ce3ee5b9bbb814e00c111fe2d09fb4578dd64027100b53fd31a49ed4a5d204fd` and passes `git apply --check` against the exact resolved `721354fbdfb7743e2be2183d918a3cdb9276c70f` checkout. Compilation then fails because `server_slot::task` is a `std::unique_ptr<const server_task>`, while the patch passes its strings to a mutable `std::string &` zeroing lambda; see `PATCH_BUILD_VALIDATION.md`.

## Scope and limitations

The original patch contains Sites A and B: selected generated-text, stopping-word, debug, task-sampling, and result strings are explicitly cleared. The retained experiment report documents residual leaks after Sites A+B and additional Sites C/D or allocator work. Thus the patch has two separate problems:

- Structural: the retained bytes cannot be applied without mechanical repair.
- Build compatibility: the repaired Sites A+B implementation is not compilable against the resolved source without an additional design change.
- Scientific: even a compilable Sites A+B implementation would not be a complete prompt-lifetime sanitization implementation.

There is no retained evidence showing whether the malformed file was a transcription/truncation artifact or the exact file used to produce the historical binary. The file is valid UTF-8 and 3,833 bytes, but those facts do not identify its origin.
