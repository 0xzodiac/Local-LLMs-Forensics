# Remediation 2 memory statistics

No new process-memory statistics exist. The rerunnable analysis script is `scripts/analyze_memory_results.py`; it consumed the generated result directory and reported zero complete memory records.

The absence of values is deliberate. Historical values remain separate in `Runs/logs/` and are not pooled with the new experiment. Therefore this remediation reports no new copy reduction, no new recovered-region volume, no client recovery rate, no uncertainty interval, and no causal comparison.

The only completed quantitative engineering checks are exit-status checks for the two ASan buffer tests. They are not memory-residue measurements.
