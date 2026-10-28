# Experiment configuration matrix

The matrix records only documented values. “Unknown” means that the field was
not recoverable from the inspected local records; it is not a reason to invent a
default.

| Experiment | Software / version evidence | Model scope | Host/configuration | Workload | Instrument | Output retained | Missing fields |
|---|---|---|---|---|---|---|---|
| RQ1 structured GGUF | `llama.cpp`/GGUF reader; historical binary not linked | GGUF corpus; four-family evaluation context | Reported Linux environment | 80 mutations; 21 structural files | loader status, C++/Python tooling, sanitizer where reported | reports and scripts | exact source, binary, corpus archive, per-case table |
| RQ1 long fuzzing | AFL++ with ASan/UBSan as reported | GGUF parser | 24-hour campaign | >1.2e7 executions | sanitizer and campaign instrumentation | headline reports | campaign manifest, coverage database, executable hash |
| RQ2 memory baseline | `llama-server`, Python collectors | four-family study/aggregate records | bare-metal Ubuntu headline; child-launched server | UUID canaries; sequential tenants | `/proc/maps`, `/proc/mem`, canary matcher | two aggregate JSON files and reports | raw region offsets, startup manifest, binary identity |
| RQ2 sanitisation | historical patched/unpatched descriptions | aggregate plus model-specific reports | same documented workload where reported | baseline vs sanitised | memory matcher and aggregate fields | two aggregate JSON files | valid historical prompt patch and causal binary linkage |
| RQ2 KV mechanism | patched `llama.cpp` candidate | Phi-4-reasoning-plus mechanism run | CPU-only build in report | 56 targeted cells | `ggml_backend_tensor_get/set` instrumentation | KV patch report | broader architecture/GPU validation |
| RQ2 KV benchmark | patched/unpatched candidate | Gemma, Nemotron, Qwen, Phi-4 | CPU-only, n=50/model | short requests | latency vector recorder | `kv_overhead_ALL_audit1.json` | formal equivalence design |
| RQ2 GPU host residue | `llama-server` plus CUDA tooling | Qwen3.5 partial offload | native Ubuntu for GPU experiment | canary request and host scan | host `/proc`, separate `cuda-gdb` outcome | GPU reports | universal GPU/device-memory claim |
| RQ3 LM Studio | Reported LM Studio v0.0.15-2, backend 2.17.0 | Nemotron configuration in mitigation report | localhost:1234 | baseline and setting-off canaries | recursive log search, config diff, restart | mitigation report | clean-install profile, original plaintext log |
| RQ3 Ollama | version/configuration bounded in telemetry records | Gemma, Qwen, Nemotron, Phi sessions | isolated network namespace | 205 valid sessions + incomplete directory | packet, trigger, idle, canary analysis | telemetry directories and summaries | all files/version-wide behavior |
| RQ4 saved slots | `llama-server` shared configuration | four models | shared process, valid credentials | 50 direct trials/model | slot restore and exact state checks | slot JSON plus four extraction JSON files | historical executable/startup manifest, principal identity |
| RQ4 continuation | same | four models | same shared process | 50/model, greedy continuation | response/secret matcher | per-model extraction JSON | independence and alternate decoding |
| RQ4 timing | shared serving setup | four models | loopback/LAN as reported | cached/uncached TTFT | historical AUC analysis | rendered PDF/PNG only | per-request vectors, order, script |
| Ikram rerun | separate server, details not supplied | complete framework | separate research server | complete evaluation reported | unknown | no local server artifact | all provenance and raw outputs |

## Configuration writing rule

The rewrite should place known values in the methods section and move unknown
fields into a concise reproducibility limitation. It should not fill unknown
software versions, seeds, GPU offload counts, slot paths, timing order, or
Ikram-server hardware from intuition.

