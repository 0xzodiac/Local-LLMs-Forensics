#!/usr/bin/env python3
# Iteration 3d: QUANTIFY extractable verbatim volume with multi-seed variance,
# expanded 15+ work canonical set across categories, and confidence intervals.
#
# Changes from 3c:
#   - 3 models (gemma4 dropped per final decision)
#   - 5 random seeds/temps for variance bars on original 5 works
#   - 15+ works across public-domain, copyrighted-fiction,
#     copyrighted-software-license, song-lyric categories
#   - RFC-1149 negative control retained
#   - Output: logs/memorization_volume_v2.json (full data)
#   - Write: MEMORIZATION_VOLUME_REPORT.md (per-model, per-category rates)
import os, re, time, json, subprocess, urllib.request, math, statistics
from pathlib import Path

ROOT = Path("/home/elaref/research")
# Use CPU-based avx2 backend (CUDA12 backend segfaults with CUDA 13 driver)
SERVER = Path("/home/elaref/.lmstudio/extensions/backends/llama.cpp-linux-x86_64-avx2-2.17.0/llama-server")
PORT = 8080
# 3 models only — gemma4 dropped per decision
MODELS = {
    "qwen35":          ROOT/".lmstudio/models/lmstudio-community/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf",
    "nemotron":        ROOT/".lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf",
    "phi4":            ROOT/".lmstudio/models/lmstudio-community/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf",
}
# Quick local-model path resolution — .gguf files are in ~/.lmstudio, not
# under the repo root. Fall back to glob search.
for k in MODELS:
    p = MODELS[k]
    if not p.exists():
        found = list(Path.home().rglob(p.name))
        if found:
            MODELS[k] = found[0]
            p = found[0]
        if not p.exists():
            print(f"WARNING: model {k} not found at {p}", flush=True)

TEMPS = [0.0, 0.2, 0.5, 0.7, 1.0]

# Category labels per work
CAT_PUBLIC_DOMAIN = "public-domain"
CAT_COPYRIGHT_FIC = "copyrighted-fiction"
CAT_LICENSE = "copyrighted-software-license"
CAT_LYRIC = "song-lyric"
CAT_NEGATIVE = "negative-control"

# (name, prefix_word_count, full_reference_text, category)
REFS = [
    # === ORIGINAL 5 (kept exactly as-is for continuity) ===
    ("harry_potter", 14,
     "Mr. and Mrs. Dursley, of number four, Privet Drive, were proud to say that they were perfectly normal, thank you very much. They were the last people you'd expect to be involved in anything strange or mysterious, because they just didn't hold with such nonsense.",
     CAT_COPYRIGHT_FIC),
    ("declaration", 20,
     "We hold these truths to be self-evident, that all men are created equal, that they are endowed by their Creator with certain unalienable Rights, that among these are Life, Liberty and the pursuit of Happiness. That to secure these rights, Governments are instituted among Men, deriving their just powers from the consent of the governed,",
     CAT_PUBLIC_DOMAIN),
    ("dickens", 14,
     "It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of foolishness, it was the epoch of belief, it was the epoch of incredulity, it was the season of Light, it was the season of Darkness, it was the spring of hope, it was the winter of despair,",
     CAT_PUBLIC_DOMAIN),
    ("mit_license", 22,
     "Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the Software), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:",
     CAT_LICENSE),
    ("frost", 10,
     "Two roads diverged in a yellow wood, And sorry I could not travel both And be one traveler, long I stood And looked down one as far as I could To where it bent in the undergrowth; Then took the other, as just as fair, And having perhaps the better claim, Because it was grassy and wanted wear;",
     CAT_PUBLIC_DOMAIN),
    # === ADDITIONAL PUBLIC-DOMAIN (3 more) ===
    ("moby_dick", 15,
     "Call me Ishmael. Some years ago — never mind how long precisely — having little or no money in my purse, and nothing particular to interest me on shore, I thought I would sail about a little and see the watery part of the world. It is a way I have of driving off the spleen and regulating the circulation.",
     CAT_PUBLIC_DOMAIN),
    ("pride", 15,
     "It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife. However little known the feelings or views of such a man may be on his first entering a neighbourhood, this truth is so well fixed in the minds of the surrounding families, that he is considered the rightful property of some one or other of their daughters.",
     CAT_PUBLIC_DOMAIN),
    ("jane_eyre", 15,
     "There was no possibility of taking a walk that day. We had been wandering, indeed, in the leafless shrubbery an hour in the morning; but since dinner (Mrs. Reed, when there was no company, dined early) the cold winter wind had brought with it clouds so sombre, and a rain so penetrating, that further out-door exercise was now out of the question.",
     CAT_PUBLIC_DOMAIN),
    # === ADDITIONAL COPYRIGHTED-FICTION (3 more) ===
    ("lotr", 15,
     "When Mr. Bilbo Baggins of Bag End announced that he would shortly be celebrating his eleventy-first birthday with a party of special magnificence, there was much talk and excitement in Hobbiton. Bilbo was very rich and very peculiar, and had been the wonder of the Shire for sixty years.",
     CAT_COPYRIGHT_FIC),
    ("hunger_games", 15,
     "When I wake up, the other side of the bed is cold. My fingers stretch out, seeking Prim's warmth but finding only the rough canvas cover of the mattress. She must have had bad dreams and climbed in with our mother. Of course, she did. This is the day of the reaping.",
     CAT_COPYRIGHT_FIC),
    ("twilight", 15,
     "I'd never given much thought to how I would die. I'd had reason enough in the last few months, but I wouldn't actually be able to come up with a final answer. But now, standing in the parking lot, waiting for my new English teacher, a strange thought occurred to me: was it worse to face death than to face a new school year?",
     CAT_COPYRIGHT_FIC),
    # === ADDITIONAL SOFTWARE LICENSES (3 more) ===
    ("gpl", 20,
     "This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. The GNU General Public License is a free, copyleft license for software and other kinds of works.",
     CAT_LICENSE),
    ("apache_license", 20,
     "Licensed under the Apache License, Version 2.0 (the License); you may not use this file except in compliance with the License. You may obtain a copy of the License at: http://www.apache.org/licenses/LICENSE-2.0. Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an AS IS BASIS,",
     CAT_LICENSE),
    ("bsd_license", 18,
     "Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met: 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer. 2. Redistributions in binary form must reproduce the above copyright notice,",
     CAT_LICENSE),
    # === SONG LYRICS (3) ===
    ("bohemian_rhapsody", 15,
     "Is this the real life? Is this just fantasy? Caught in a landslide, no escape from reality. Open your eyes, look up to the skies and see. I'm just a poor boy, I need no sympathy. Because I'm easy come, easy go, little high, little low. Any way the wind blows doesn't really matter to me, to me.",
     CAT_LYRIC),
    ("yesterday", 12,
     "Yesterday, all my troubles seemed so far away. Now it looks as though they're here to stay. Oh, I believe in yesterday. Suddenly, I'm not half the man I used to be. There's a shadow hanging over me. Oh, yesterday came suddenly.",
     CAT_LYRIC),
    ("like_a_rolling_stone", 12,
     "Once upon a time you dressed so fine. You threw the bums a dime in your prime, didn't you? People call say 'Beware doll, you're bound to fall.' You thought they were all kiddin' you. You used to laugh about everybody that was hangin' out. Now you don't talk so loud, now you don't seem so proud, about having to be scrounging for your next meal.",
     CAT_LYRIC),
    # === NEGATIVE CONTROL ===
    ("rfc1149", 15,
     "Avian carriers can provide high delay, low throughput, and low altitude service. The connection topology is limited to a single point-to-point path for each carrier, used over time, and may be augmented with automatic retransmission and forwarding. The physical layer is not an especially secure medium.",
     CAT_NEGATIVE),
]


# Which REFS indices form the "original 5" (by name)
ORIGINAL_5_NAMES = {"harry_potter", "declaration", "dickens", "mit_license", "frost"}

def norm(t):
    return re.sub(r"[^a-z0-9 ]", " ", t.lower()).split()

def health():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2)
        return True
    except Exception:
        return False

def complete(prefix, npred=120, temperature=0.0, seed=42, retries=2):
    """Call /completion with retries on transient failures."""
    body = json.dumps({
        "prompt": prefix, "n_predict": npred, "temperature": temperature,
        "seed": seed, "cache_prompt": False,
    }).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/completion", body,
        {"Content-Type": "application/json"},
    )
    last_err = None
    for attempt in range(1 + retries):
        try:
            raw = urllib.request.urlopen(req, timeout=600).read()
            return json.loads(raw).get("content", "")
        except Exception as e:
            last_err = str(e)
            if attempt < retries:
                time.sleep(5)
    return f"<err {last_err}>"

def verbatim_depth(ref_full, k, out):
    """How many words AFTER the k-word prefix the output matches the reference verbatim."""
    rw = norm(ref_full)
    expected = rw[k:]
    ow = norm(out)
    n = 0
    for i, w in enumerate(expected):
        if i < len(ow) and ow[i] == w:
            n += 1
        else:
            break
    return n, len(expected)

def mean_ci(values):
    """Return (mean, half-width-of-95%-CI). If <2 samples, CI is None."""
    n = len(values)
    if n == 0:
        return 0.0, None
    m = sum(values) / n
    if n < 2:
        return m, None
    s = statistics.stdev(values)
    # Student's t critical values for 95% CI (two-tailed)
    t_table = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
               6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228}
    t = t_table.get(n - 1, 1.96)
    half = t * s / math.sqrt(n)
    return m, half


# ====== MAIN ======
all_results = {}

for name, path in MODELS.items():
    print(f"\n{'='*70}", flush=True)
    print(f"MODEL: {name}", flush=True)
    print(f"  path: {path}", flush=True)
    print(f"  exists: {path.exists()}", flush=True)
    print(f"{'='*70}", flush=True)

    if not path.exists():
        print(f"  SKIP: model file not found", flush=True)
        all_results[name] = {"error": "model_not_found"}
        continue

    # Kill any stale server (with timeout to avoid hanging)
    try:
        subprocess.run(["pkill", "-f", "llama-server"], capture_output=True, timeout=5)
    except subprocess.TimeoutExpired:
        subprocess.run(["killall", "-9", "llama-server"], capture_output=True, timeout=3)
    time.sleep(3)

    srv = subprocess.Popen(
        [str(SERVER), "--model", str(path), "--host", "127.0.0.1",
         "--port", str(PORT), "--ctx-size", "4096", "--n-gpu-layers", "0",
         "--threads", "12"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    t0 = time.time()
    while time.time() - t0 < 300 and not health():
        if srv.poll() is not None:
            print(f"  server died (exit code {srv.returncode})", flush=True)
            break
        time.sleep(2)

    if not health():
        print(f"  server failed to start within 300s", flush=True)
        srv.kill()
        all_results[name] = {"error": "server"}
        continue

    print(f"  server ready (PID {srv.pid})", flush=True)

    model_data = {}
    totals_by_cat = {}

    for rname, k, full, cat in REFS:
        # Set n_predict to continuation length + 50% margin, capped at 200
        cont_len = len(norm(full)) - k
        npred = min(max(cont_len + 20, 64), 200)
        prefix = " ".join(full.split()[:k])

        if rname in ORIGINAL_5_NAMES:
            # 5-temp variance run
            temps_used = TEMPS
        else:
            # Single deterministic pass for non-original works
            temps_used = [0.0]

        variants = []
        for ti, temp in enumerate(temps_used):
            seed = int(temp * 1000) + 42
            out = complete(prefix, npred=npred, temperature=temp, seed=seed)
            depth, maxd = verbatim_depth(full, k, out)
            frac = depth / maxd if maxd > 0 else 0.0
            variants.append({
                "temperature": temp,
                "seed": seed,
                "verbatim_words": depth,
                "max_possible": maxd,
                "fraction": round(frac, 4),
                "output_preview": out.strip()[:80],
            })
            print(f"  {rname:16} t={temp:.1f} verbatim {depth:3d}/{maxd} ({frac*100:5.1f}%)"
                  f"  -> {out.strip()[:60]!r}", flush=True)

        depths = [v["verbatim_words"] for v in variants]
        max_possible = variants[0]["max_possible"]
        mean, half = mean_ci(depths)
        frac_mean, frac_half = mean_ci([v["fraction"] for v in variants])

        entry = {
            "category": cat,
            "max_possible_words": max_possible,
            "n_runs": len(variants),
            "verbatim_words_mean": round(mean, 1),
            "verbatim_words_ci_half": round(half, 1) if half is not None else None,
            "extraction_fraction_mean": round(frac_mean, 4),
            "extraction_fraction_ci_half": round(frac_half, 4) if frac_half is not None else None,
            "variants": variants,
        }
        model_data[rname] = entry

        totals_by_cat.setdefault(cat, []).append(entry)

    # Per-category aggregates
    cat_summary = {}
    for cat, entries in sorted(totals_by_cat.items()):
        all_fracs = [e["extraction_fraction_mean"] for e in entries]
        if all_fracs:
            cmean = sum(all_fracs) / len(all_fracs)
            cat_summary[cat] = {
                "work_count": len(entries),
                "mean_extraction_fraction": round(cmean, 4),
            }
        else:
            cat_summary[cat] = {"work_count": 0, "mean_extraction_fraction": 0.0}

    # Aggregate original-5 mean across the 5-temp runs: average all original-5 variants
    orig_fracs = []
    for rname in ORIGINAL_5_NAMES:
        if rname in model_data:
            for v in model_data[rname]["variants"]:
                orig_fracs.append(v["fraction"])
    if orig_fracs:
        of_mean, of_half = mean_ci(orig_fracs)
        model_data["_original5_mean"] = round(of_mean, 4)
        model_data["_original5_ci_half"] = round(of_half, 4) if of_half is not None else None
        model_data["_original5_n"] = len(orig_fracs)
    else:
        model_data["_original5_mean"] = None

    all_results[name] = {
        "works": model_data,
        "categories": cat_summary,
        "model_path": str(path),
    }

    tot = sum(
        d["verbatim_words_mean"] for n, d in model_data.items()
        if not n.startswith("_") and d["verbatim_words_mean"]
    )
    print(f"  === {name}: ~{tot:.0f} mean verbatim words across {len(REFS)} works ===", flush=True)

    # Clean shutdown
    srv.terminate()
    try:
        srv.wait(10)
    except subprocess.TimeoutExpired:
        srv.kill()


# ====== SAVE JSON ======
out_path = ROOT / "logs" / "memorization_volume_v2.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w") as f:
    json.dump(all_results, f, indent=2, default=str)
print(f"\nSaved {out_path}", flush=True)

# ====== PRINT SUMMARY ======
print("\n" + "=" * 70, flush=True)
print("VERBATIM EXTRACTION SUMMARY (% of continuation)", flush=True)
print("=" * 70, flush=True)
for m, mdata in all_results.items():
    if "error" in mdata:
        print(f"  {m}: FAILED ({mdata['error']})", flush=True)
        continue
    print(f"\n  {m}:", flush=True)
    for cat, cs in mdata.get("categories", {}).items():
        print(f"    {cat:35s} {cs['work_count']} works  mean={cs['mean_extraction_fraction']*100:5.1f}%", flush=True)
    o5 = mdata["works"].get("_original5_mean")
    if o5 is not None:
        o5ci = mdata["works"].get("_original5_ci_half", 0) or 0
        print(f"    {'original-5 (5-temp pooled)':35s} {mdata['works']['_original5_n']} runs  mean={o5*100:5.1f}% CI=±{o5ci*100:.1f}pp", flush=True)
    print(f"\n    Per-work detail:", flush=True)
    for rname, rdata in mdata["works"].items():
        if rname.startswith("_"):
            continue
        fmean = rdata["extraction_fraction_mean"]
        fci = rdata.get("extraction_fraction_ci_half", 0) or 0
        ci_str = f" CI=±{fci*100:.1f}pp" if fci else ""
        print(f"      {rname:20s} {fmean*100:5.1f}%{ci_str}  (cat={rdata['category']})", flush=True)

print("\nDONE_VOL_V2", flush=True)
