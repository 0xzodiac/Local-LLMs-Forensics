#!/usr/bin/env python3
# Iteration 1: scan GGUF metadata region for embedded secrets — URLs, emails,
# telemetry endpoints, suspicious keywords. Python so loop vars don't get mangled
# by the wsl.exe shell boundary. Reads first 256MB (metadata + start of weights;
# URLs/templates/author live near the header).
import re, sys
from pathlib import Path
from collections import Counter

MODELS = {
    "nemotron": "logs/ultimate/models/nemotron.gguf",
    "gemma4":   "logs/ultimate/models/gemma4.gguf",
    "qwen35":   "logs/ultimate/models/qwen35.gguf",
    "phi4":     "logs/ultimate/models/phi4.gguf",
}
CAP = 256 << 20  # 256 MB

URL   = re.compile(rb'https?://[A-Za-z0-9._~:/?#@!$&%*+,;=-]{4,120}')
EMAIL = re.compile(rb'[A-Za-z0-9._%+-]{2,}@[A-Za-z0-9.-]{2,}\.[A-Za-z]{2,8}')
DOMAIN= re.compile(rb'\b[A-Za-z0-9-]{2,}\.(?:com|net|org|io|ai|co|dev|cn|ru|gov|app)\b')
SUS   = re.compile(rb'(?i)(telemetry|analytics|tracking|phone.?home|callback|'
                   rb'api[_-]?key|bearer |x-api-|endpoint=|\.onion|exfil|beacon)')

def clean(items, n=25):
    c = Counter(x.decode("latin-1") for x in items)
    return c.most_common(n)

def scan(path):
    p = Path(path)
    if not p.exists(): return f"  MISSING {path}"
    with open(p, "rb") as f:
        buf = f.read(CAP)
    urls = clean(URL.findall(buf))
    emails = clean(EMAIL.findall(buf))
    domains = clean(DOMAIN.findall(buf))
    sus = clean(SUS.findall(buf))
    out = []
    out.append(f"  scanned {len(buf)>>20}MB")
    out.append(f"  URLs ({len(urls)} distinct): " + (", ".join(f'{u}×{n}' for u,n in urls[:15]) or "NONE"))
    out.append(f"  emails: " + (", ".join(f'{e}×{n}' for e,n in emails[:10]) or "NONE"))
    out.append(f"  domains: " + (", ".join(f'{d}×{n}' for d,n in domains[:15]) or "NONE"))
    out.append(f"  SUSPICIOUS keywords: " + (", ".join(f'{s}×{n}' for s,n in sus) or "NONE"))
    return "\n".join(out)

def main():
    import os
    os.chdir("/home/sharks/research")
    for name, path in MODELS.items():
        print(f"=== {name} ===", flush=True)
        print(scan(path), flush=True)
        print(flush=True)
    print("DONE_SCAN", flush=True)

if __name__ == "__main__":
    main()
