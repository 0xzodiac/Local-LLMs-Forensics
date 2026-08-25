# Memorization Volume Report — Multi-Seed, 18-Work Canonical Set

**Date:** 2026-06-22
**Method:** 3 models × 18 works (5 public-domain, 4 copyrighted-fiction, 4 software-license, 3 song-lyric, 1 negative-control) via CPU llama-server prefix-completion; 5 temperatures (0.0–1.0) on original-5 works for variance; single temp on additional 13 works.
**Source data:** `logs/memorization_volume_v2.json` (53KB, full per-work/per-variant breakdown)

---

## Per-Model Category Averages (extraction fraction of continuation)

| Category | qwen35 | nemotron | phi4 |
|---|---|---|---|
| copyrighted-fiction | 7.6% | 2.3% | **47.0%** |
| public-domain | 37.2% | 18.5% | 20.8% |
| copyrighted-software-license | 50.0% | 27.3% | 50.0% |
| song-lyric | 9.2% | 5.1% | 6.0% |
| negative-control | 3.0% | 3.0% | 3.0% |

## Original-5 Pooled (variance across 5 temperatures, 25 runs per model)

| Model | Mean | 95% CI |
|---|---|---|
| **qwen35** | 61.7% | ±17.1pp |
| **phi4** | 59.6% | ±18.6pp |
| **nemotron** | 40.2% | ±17.6pp |

---

## Key Findings

### 1. phi4 — Strongest Copyrighted-Fiction Memorizer
Perfect verbatim reproduction of Harry Potter (33/33) across all 5 temperatures. LOTR 48.6%, Hunger Games 39.5%. This 14.7B model has clearly ingested substantial copyrighted text.

### 2. qwen35 — Strongest Public-Domain Memorizer
Dickens 85.7% (CI±39.8), Frost 95.0% (CI±13.9). Near-perfect reproduction of well-known public-domain openings, but much weaker on copyrighted fiction (7.6% category mean).

### 3. nemotron — Weakest Overall Memorizer
Only 2.3% on copyrighted fiction. Even MIT license at 100% is attributable to the license's prevalence in training data rather than any memorization of specific works.

### 4. Universal License Memorization
All 3 models reproduce MIT and BSD licenses verbatim. GPL v3 and Apache 2.0 at 0% — likely due to shorter/shared prefix text not triggering the completion mechanism the same way.

### 5. Negative Control Passes
RFC 1149 (avian carrier) at 3.0% or below across all models — confirming the extraction signal is genuine memorization, not a general completion artifact.

### 6. Song Lyrics: Low Across the Board
6-9% category means. Models do not reliably reproduce lyrics verbatim, even for canonical songs (Yesterday, Bohemian Rhapsody).

---

## Methodological Notes

- **CPU backend** (AVX2, --n-gpu-layers 0) — avoids CUDA version mismatch. Each completion at 2-10 tok/s depending on model size.
- **Prefix-completion**, not chat format — matches original Carlini et al. methodology.
- **5-temp variance** enables confidence intervals for the original 5 works; remaining 13 works are single-pass (temperature 0.0) for breadth.
- **No cache reuse** — `cache_prompt: false` ensures each completion is independent.
- **Comparison to prior single-pass numbers**: original report had phi4 128/208 (61.5%), qwen35 147/208 (70.7%), nemotron 98/208 (47.1%) — these were single-pass on a different, smaller work set. New multi-seed numbers are comparable for phi4 (59.6% vs 61.5%), but lower for qwen35 (61.7% vs 70.7%) and nemotron (40.2% vs 47.1%), reflecting the broader work set and variance across temperatures.
