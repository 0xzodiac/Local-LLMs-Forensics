# Remediation 2 source baseline

## Gate A verdict

The pinned source identity and clean baseline build are verified. Full model inference is not verified because no model weights are present in the workspace.

- Remote: `https://github.com/ggml-org/llama.cpp.git`
- Commit: `721354fbdfb7743e2be2183d918a3cdb9276c70f`
- Commit date: `2026-06-22T18:24:04+02:00`
- Commit subject: `server: (router) move model downloading to dedicated process (#24834)`
- Baseline checkout: `source/baseline/`
- Baseline Git status: clean, detached at the pinned commit
- Baseline build: Release, CPU-only, server enabled, tests enabled, GCC 13.3.0, CMake 3.28.3
- Baseline binary: `builds/baseline/bin/llama-server`
- Baseline binary SHA-256: `e05488434b11d58094b2763e51f1484cfc1fbf7d28cb009747cf4ef999b00a58`

`--help` and `--version` exit successfully. With no model argument, the server enters router mode and `/health` returned HTTP 200 with `{"status":"ok"}`. This is a startup/health check, not synthetic inference. A controlled shutdown of that no-model router emitted `munmap_chunk(): invalid pointer` and exit 134; the failure is retained in `validation/baseline_server_start_1791487368.log` and is not hidden.

Host and complete condition-level provenance are in `manifests/source_binary_provenance.json`. The host reported Linux kernel `7.0.0-38-generic`, x86-64, Yama `ptrace_scope=1`, approximately 15 GiB RAM, and approximately 5.7 GiB free disk at manifest generation. No model hash is recorded because no model file exists locally.

## Historical mapping

The original harness and retained records remain under `Runs/`: `Runs/patches/kv_cache_zeroize.patch`, `Runs/patches/prompt_zeroize.patch`, `Runs/scripts/leak_blast_radius.py`, and the aggregate records `Runs/logs/leak_blast_radius_20260623_213831.json` and `Runs/logs/leak_blast_radius_20260624_120421.json`. They are historical inputs only and were not copied into the new raw-results set.
