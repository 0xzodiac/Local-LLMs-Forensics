# N50 Telemetry Audit Index

Total run directories: 212

## By Model

- **gemma-4-e4b-it**: 1 runs -> `SUMMARY_gemma-4-e4b-it.md`
- **gemma4-local**: 52 runs -> `SUMMARY_gemma4-local.md`
- **microsoft/phi-4-reasoning-plus**: 1 runs -> `SUMMARY_microsoft_phi-4-reasoning-plus.md`
- **nemotron-local**: 51 runs -> `SUMMARY_nemotron-local.md`
- **nvidia/nemotron-3-nano-4b**: 3 runs -> `SUMMARY_nvidia_nemotron-3-nano-4b.md`
- **phi4-local**: 52 runs -> `SUMMARY_phi4-local.md`
- **qwen/qwen3.5-9b**: 1 runs -> `SUMMARY_qwen_qwen3.5-9b.md`
- **qwen35-local**: 51 runs -> `SUMMARY_qwen35-local.md`

## Run Directory Structure

Each run contains:
- `meta.json` - capture metadata
- `pcap/` - packet captures
- `pcap_quick.json` - parsed summary
- `hooks/` - LD_PRELOAD traces (when applicable)
- `idle_snapshots.json` - process memory snapshots
- `triggers.jsonl` - canary detection events
