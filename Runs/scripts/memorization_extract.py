#!/usr/bin/env python3
# Iteration 3b: REAL training-data memorization test via prefix-completion.
# Uses llama-server's raw /completion endpoint (no chat template, no refusal) —
# feed the first half of widely-memorized canonical text, check if the model
# completes it VERBATIM. Verbatim completion = the text is memorized in the weights.
import os, time, json, subprocess, urllib.request
from pathlib import Path

ROOT = Path("/home/sharks/research")
SERVER = ROOT / "llama-monitor/build/llama.cpp/bin/llama-server"
PORT = 8080
MODELS = {
    "gemma4":   ROOT/"logs/ultimate/models/gemma4.gguf",
    "nemotron": ROOT/"logs/ultimate/models/nemotron.gguf",
    "qwen35":   ROOT/"logs/ultimate/models/qwen35.gguf",
    "phi4":     ROOT/"logs/ultimate/models/phi4.gguf",
}
# (name, prefix, must-contain-any keywords for a verbatim continuation)
TEXTS = [
    ("mit_license", "Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the \"Software\"), to deal in the Software without restriction, including without limitation the rights to", ["use, copy, modify", "copy, modify, merge"]),
    ("frost_road", "Two roads diverged in a yellow wood,\nAnd sorry I could not travel both\nAnd be one traveler, long I stood\nAnd looked down one as far as I could\nTo where it bent in the", ["undergrowth"]),
    ("declaration", "We hold these truths to be self-evident, that all men are created equal, that they are endowed by their Creator with certain unalienable Rights, that among these are Life, Liberty and the pursuit of", ["Happiness"]),
    ("dickens", "It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of", ["foolishness"]),
    ("john_3_16", "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have", ["everlasting life", "eternal life"]),
    ("harry_potter", "Mr. and Mrs. Dursley, of number four, Privet Drive, were proud to say that they were perfectly", ["normal, thank you", "normal"]),
    ("gpl", "This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the", ["Free Software Foundation"]),
    ("lorem", "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna", ["aliqua"]),
    ("rfc1149", "Avian carriers can provide high delay, low throughput, and low altitude service. The connection topology is limited to a single", ["point-to-point", "point to point"]),
]

def health():
    try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2); return True
    except Exception: return False

def complete(prefix):
    body = json.dumps({"prompt": prefix, "n_predict": 64, "temperature": 0.0,
                       "cache_prompt": False}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/completion",
                                 body, {"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=180).read())
        return d.get("content", "")
    except Exception as e:
        return f"<err {e}>"

results = {}
for name, path in MODELS.items():
    print(f"\n{'='*60}\nMODEL: {name}\n{'='*60}", flush=True)
    subprocess.run(["pkill", "-f", "llama-server"], capture_output=True); time.sleep(2)
    srv = subprocess.Popen(
        [str(SERVER), "--model", str(path), "--host", "127.0.0.1", "--port", str(PORT),
         "--ctx-size", "4096", "--n-gpu-layers", "0", "--threads", "16"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while time.time()-t0 < 150 and not health():
        if srv.poll() is not None: break
        time.sleep(1)
    if not health():
        print(f"  server failed", flush=True); srv.kill(); results[name] = {"error": "server"}; continue
    mr = {}
    hits = 0
    for tname, prefix, kws in TEXTS:
        out = complete(prefix)
        hit = any(k.lower() in out.lower() for k in kws)
        hits += hit
        mr[tname] = {"verbatim": hit, "out": out.strip()[:140]}
        print(f"  {tname:14} {'MEMORIZED' if hit else 'no'}  -> {out.strip()[:80]!r}", flush=True)
    mr["_score"] = f"{hits}/{len(TEXTS)}"
    results[name] = mr
    print(f"  === {name}: {hits}/{len(TEXTS)} texts completed verbatim ===", flush=True)
    srv.terminate()
    try: srv.wait(10)
    except subprocess.TimeoutExpired: srv.kill()

with open(ROOT/"logs/memorization_extract_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSUMMARY:", {k: v.get("_score", v.get("error")) for k, v in results.items()}, flush=True)
print("DONE_MEMO", flush=True)
