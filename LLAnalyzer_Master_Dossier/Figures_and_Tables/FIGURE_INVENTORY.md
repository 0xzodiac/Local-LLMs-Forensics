# Figure inventory

| Figure / artifact | Source path | Generated path | Scientific purpose | Evidence represented | Placement | Correction/status |
|---|---|---|---|---|---|---|
| Architecture and evidence map | `LLAnalyzer-revised-10point/figures/fig_llanalyzer_arch.tex` | `fig_llanalyzer_arch.pdf` | Map request path and B1--B4 measurement points | Conceptual architecture plus evidence locations | Main paper, Figure 1 | Reuse; explain conceptual boundary versus concrete data path |
| Historical timing decay | No raw analysis source recovered | `figures/timing_auc_decay.pdf`, `.png` | Show reported cached/uncached timing separation | Historical AUC result | Main or supplement beside RQ4 | Keep only with caption stating raw vectors/script unavailable |
| Legacy architecture PNGs | Various prior sources | `LLAnalyzer.png`, `LLAnalyzerv2.png`, `LLAnalyzerv3.png`, `LLAnalyzerv4.png`, `fig_arc.png`, `fig_arc-croped.png`, `fig_fourlayer.png` | Earlier architecture iterations | Not necessarily tied to authoritative source | Do not place automatically | Preserve as historical assets; prefer Figure 1 source |
| Legacy result/attack plots | Prior figure sources | `fig_llanalyzer_results.pdf`, `fig_attack.png`, `fig_teaser.png`, `fig_arena.png` | Earlier result communication | Must be checked against current catalog | Supplement only if exact evidence mapping survives | Do not create new empirical plots from unsupported values |

## Figure writing notes

Figure 1 should carry the conceptual argument: a single local request can cross
multiple independent confidentiality boundaries. Its caption should not imply
that every arrow was measured with the same threat actor. Timing figures must
identify the AUC as historical, not independently recomputed.

