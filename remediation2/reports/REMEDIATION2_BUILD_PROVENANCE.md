# Remediation 2 build provenance

The authoritative machine-readable chain is `manifests/source_binary_provenance.json`.

| Condition | Source tree | Patch set | Binary SHA-256 |
|---|---|---|---|
| C0 | `source/baseline` | none | `e05488434b11d58094b2763e51f1484cfc1fbf7d28cb009747cf4ef999b00a58` |
| C1 | `source/kv_only` | historical KV patch `9219b14331f4c5f7f80117a3affa6c16464d52ac92245b176e900b39e6d10b54` | `75af850412de11a45dd53e87946aa8c95c43bb5b98152e2b1e49045a0aeaae10` |
| C2 | `source/prompt_only` | new prompt patch `720ee178f3a5d8218987cbc8cbeaff98e003624dc8a4cd119be6d0edc93008d9` | `0bbd6acf9cc354452b55b4b7aa7a90c57c753439ff0ae9ab5c411924ec03f212` |
| C3 | `source/combined` | KV plus new prompt patch | `63b0b8246acdbcb4a2a23a626eec734ebb4db8130e9cc1e925dbc17c0b44859a` |

All builds used the pinned commit, Release mode, CPU backend, `LLAMA_CUDA=OFF`, server and tests enabled, and `-j2`. The CMake logs, build logs, source status, compiler, operating system, kernel, and Yama setting are retained under `validation/` and `manifests/`. No model identifier or model hash is fabricated.
