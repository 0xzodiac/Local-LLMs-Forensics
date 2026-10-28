# Dr. Ikram replication provenance

## Provenance result

The local historical chain remains partially reconstructed:

```text
historical source ? -> historical patch ? -> historical binary ?
-> historical server/run records -> retained local raw records -> local audit
```

The new author clarification adds a second, cross-machine chain, but only at its
claim level:

```text
Ikram source ? -> Ikram patch set ? -> Ikram binary ? -> Ikram model/config ?
-> Ikram experiment ? -> Ikram raw result ? -> Ikram analysis ?
-> author-reported match to the original evaluation
```

The question marks are evidence gaps, not claims that the corresponding records
do not exist. They identify what is absent from the inspected workspace.

## Link-by-link comparison

| Link | Original/local records inspected | Ikram rerun records inspected | Consequence |
|---|---|---|---|
| Source revision | Manuscript names unresolved `388d39f3e`; Remediation 2 uses resolved `721354fbdfb7743e2be2183d918a3cdb9276c70f` as new engineering source, not historical source | None | Cannot establish whether both machines used the same source or compatible revisions |
| Patch set | `Runs/patches/kv_cache_zeroize.patch` retained; `Runs/patches/prompt_zeroize.patch` malformed; Remediation 2 prompt implementation is new | None | Cannot attribute the reported match to a specific patch set |
| Build/binary | Historical binary path is recorded as `/home/elaref/research/llama-cpp-build/build/bin/llama-server`, but binary/hash/startup manifest absent | None | No executable-to-result linkage for either cross-machine comparison |
| Host/server | Local reports contain partial paths and run metadata; no complete historical startup manifest | No hardware, OS, runtime, server flags, port, isolation, or process manifest | Hardware/software differences cannot be documented |
| Model | `Runs/provenance/model_digests.json` records four model digests; model files/load-time linkage absent | None | Cannot verify model identity, quantisation, or exact model parity |
| Experiment | Local JSON and telemetry records cover several original experiments | Author states complete rerun, but no run index or experiment manifest | Inclusion of auxiliary experiments is unresolved |
| Raw result | Memory aggregates, slot/extraction JSON, KV vectors, and telemetry remain locally hashable; timing vectors and several RQ1 raw chains are absent | None | No artifact-level comparison is possible |
| Analysis | `remediation2b_historical_evidence/scripts/independent_reanalysis.py` recomputes selected local records | No Ikram analysis script or output | Matching analysis procedure is not established |

## Retained local anchors

These are anchors for the original/local evidence and must not be relabeled as
Ikram outputs:

- `Runs/logs/leak_blast_radius_20260623_213831.json` — SHA-256
  `4d54ac8bd771420a93617a0e63f1ab1fa786cdfdeb5dca9815b86c7337dfb3f6`.
- `Runs/logs/leak_blast_radius_20260624_120421.json` — SHA-256
  `ef6f5cecf832cabdb4d31620af371951ae727c75ed7644383662e00be7169c63`.
- `Runs/logs/n50_audit/slot_exploit_ALL4_audit1.json` — SHA-256
  `1e1da4c6849c4299c31503bccebad056122bbd20f0dd02f63428822c0be24fcf`.
- The four detailed cross-tenant extraction files and the KV benchmark vectors
  are listed with hashes in `hashes/primary_artifacts.sha256`.
- The recomputation procedure and derived values are in
  `analysis/independent_reanalysis.json` and
  `scripts/independent_reanalysis.py`.

These anchors verify selected original arithmetic. They do not prove that the
same files were produced on Dr. Ikram's server.

## Differences that must be documented when records are recovered

The rerun need not be bit-for-bit identical to be a meaningful methodological
replication. The eventual provenance packet should nevertheless record:

1. server CPU/GPU/RAM, OS/kernel, compiler and runtime versions;
2. source commit and complete patch hashes;
3. build flags and executable SHA-256;
4. model filename, quantisation, source, and SHA-256;
5. server startup flags, API/auth configuration, slot path, logging settings,
   allocator settings, and isolation assumptions;
6. run order, random seeds or canary generation rule, trial counts, and time
   window;
7. raw output paths and the exact analysis scripts used; and
8. a comparison table showing which values were exact, within a declared
   tolerance, or qualitatively matched.

Until those records are located, the correct provenance label is
**author-reported cross-machine replication with uninspected provenance**.

