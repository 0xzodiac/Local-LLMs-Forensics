# Patch recovery report

## Outcome

The original historical prompt patch was not recovered from the project Git history, unreachable objects, named archives, or targeted research directories. A mechanically repaired derivative was produced solely to test whether the retained implementation can be applied to the only resolvable upstream source candidate.

## Evidence

| Item | Result |
|---|---|
| Original prompt patch | Preserved at `Runs/patches/prompt_zeroize.patch`; SHA-256 `9fc6786ff3515a7206a8c45c79f09dfef97fea96beff95ccfd48bd8fc2cfa7a0` |
| Original KV patch | Preserved at `Runs/patches/kv_cache_zeroize.patch`; SHA-256 `9219b14331f4c5f7f80117a3affa6c16464d52ac92245b176e900b39e6d10b54` |
| Repaired prompt derivative | `remediation1/patch_recovery/prompt_zeroize_mechanically_repaired.patch`; SHA-256 `ce3ee5b9bbb814e00c111fe2d09fb4578dd64027100b53fd31a49ed4a5d204fd` |
| Patch application | Repaired prompt patch and original KV patch apply cleanly to `721354fbdfb7743e2be2183d918a3cdb9276c70f`; the combined implementation then fails to compile because `server_task` is const-owned |
| Historical patch recovery | Failed; no original source/binary/run linkage was found |
| Additional mitigation | Secure allocator and Sites C/D are described in reports and records, but no complete standalone historical patch is retained |

## Interpretation

The repaired file is a validation artifact, not a replacement for the original and not proof of historical execution. It must not be presented as the historical patch hash. The retained memory results can therefore be checked arithmetically, while attribution to this implementation remains unresolved. A const-correct implementation would require a separate design decision about when and where task-owned plaintext is mutable; that decision was not invented during this recovery.
