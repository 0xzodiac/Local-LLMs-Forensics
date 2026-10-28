# Reconstructed patch build validation

## Scope

This validation used an isolated temporary checkout and did not alter the project workspace. It tests whether the retained KV patch plus the mechanically repaired prompt patch can be applied and compiled against the resolved upstream candidate. It does not establish the historical build.

## Source and patch identity

- Source: `721354fbdfb7743e2be2183d918a3cdb9276c70f`.
- Repaired prompt patch: `ce3ee5b9bbb814e00c111fe2d09fb4578dd64027100b53fd31a49ed4a5d204fd`.
- Original KV patch: `9219b14331f4c5f7f80117a3affa6c16464d52ac92245b176e900b39e6d10b54`.
- Combined reconstructed worktree diff hash: `6c8f65188772957ddf806a481ca54ceeda7bdb039009b7532175689421ba1ed3`.
- `git diff --check`: passed.
- Both patches: `git apply --check` passed against this exact checkout.

## Build invocation and configuration

The temporary build used:

```text
cmake -S /tmp/llanalyzer-patch-worktree-oQgRg9/llama.cpp \
  -B /tmp/llanalyzer-patch-worktree-oQgRg9/llama.cpp/build \
  -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=ON -DLLAMA_CUDA=OFF \
  -DLLAMA_BUILD_SERVER=ON -DLLAMA_BUILD_TESTS=ON
cmake --build /tmp/llanalyzer-patch-worktree-oQgRg9/llama.cpp/build \
  --config Release --target llama-server -j2
```

Configuration completed with GCC 13.3.0, `/usr/bin/cc`, `/usr/bin/c++`, CPU backend, OpenMP, x86 native CPU settings, ggml 0.15.2, and OpenSSL 3.0.13. CMake warned that `LLAMA_CURL` is deprecated and ignored. These are reconstruction settings, not recovered historical settings.

## Result

The build failed with exit status 2 while compiling `tools/server/server-context.cpp`. The retained prompt patch calls `secure_zero` on fields under `std::unique_ptr<const server_task>`, including `task->params.sampling.generation_prompt`, `reasoning_budget_message`, `antiprompt`, and `cli_prompt`. The compiler rejects binding those const strings to the patch's `std::string &` lambda parameter. No `llama-server` executable was produced.

This is a second, source-compatibility defect beyond the malformed diff syntax. Making the patch apply mechanically does not make it a compilable or safe historical implementation. The build was not “fixed” by changing constness or casting away const, because that would be a new implementation decision outside historical recovery and could introduce undefined behavior for a const object.

## Functional validation boundary

Because compilation failed and the current environment lacks the referenced model file, no server `--help`/`--version` or inference test was possible. The KV zeroization behavior was therefore not functionally re-executed in this reconstruction; the retained probe logs remain separate historical records with incomplete binary provenance.
