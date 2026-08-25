#!/usr/bin/env python3
"""Deep multi-model GGUF attack tester - 8 attacks x 4 models.

Uses --check-tensors for fast validation (no inference).
Sequential with cooldown to respect CPU.
"""

import csv, os, signal, struct, subprocess, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SERVER = REPO / "llama-monitor/build/llama.cpp/bin/llama-server"
OUT = REPO / "logs/multimodel"
CSV_PATH = OUT / "deep_results.csv"

MODELS = {
    "nemotron": "/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf",
    "gemma4": "/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf",
    "qwen35": "/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf",
    "phi4": "/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf",
}

def get_arch(path):
    with open(path, "rb") as f:
        h = f.read(10*1024*1024)
    kp = h.find(b"general.architecture")
    if kp < 0: return "unknown"
    pos = kp + 21 + 4
    sl = struct.unpack_from("<Q", h, pos)[0]
    return h[pos+8:pos+8+sl].decode("utf-8", errors="replace")

def p32(raw, key, val):
    kp = raw.find(key)
    if kp < 0: return False
    struct.pack_into("<I", raw, kp+len(key)+4, val)
    return True

def pstr(raw, key, nv):
    kp = raw.find(key)
    if kp < 0: return False
    pos = kp+len(key)+4
    ol = struct.unpack_from("<Q", raw, pos)[0]
    pos += 8
    raw[pos:pos+ol] = nv + b"\x00"*(ol-len(nv))
    return True

def check(model_path, to=25):
    cmd = [str(SERVER), "--check-tensors", "-m", str(model_path),
           "--port", "19999", "--host", "127.0.0.1"]
    try:
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=to)
        el = time.time()-t0
        rc = r.returncode
        sig = rc-256 if rc>128 else rc
        sn = signal.Signals(-sig).name if sig<0 else f"exit({rc})"
        # Extract error lines
        errs = [l for l in r.stderr.split("\n") if "error" in l.lower() or "SIGABRT" in l or "assert" in l.lower()]
        return {"rc":rc,"signal":sn,"crashed":sig<0,"elapsed":round(el,1),
                "error":"; ".join(errs)[:200] if errs else ""}
    except subprocess.TimeoutExpired:
        return {"rc":-1,"signal":"TIMEOUT","crashed":False,"elapsed":to,"error":"timeout"}
    except Exception as e:
        return {"rc":-999,"signal":"ERR","crashed":False,"elapsed":0,"error":str(e)[:100]}

def gen(name, raw, arch):
    if name == "rope_drift":
        p32(raw, f"{arch}.rope.dimension_count".encode(), 0x7FFFFFFF)
        p32(raw, f"{arch}.context_length".encode(), 0xFFFFFFFF)
        return "rope_drift"
    elif name == "block_mismatch":
        p32(raw, f"{arch}.block_count".encode(), 1)
        return "block_mismatch"
    elif name == "embed_crush":
        p32(raw, f"{arch}.embedding_length".encode(), 1)
        p32(raw, f"{arch}.attention.head_count".encode(), 0xFFFFFFFF)
        return "embed_crush"
    elif name == "token_boundary":
        for t,v in [("bos_token_id",0xFFFFFFFF),("eos_token_id",0xFFFFFFFE),
                     ("padding_token_id",0x80000000),("unknown_token_id",0x7FFFFFFF)]:
            p32(raw, f"tokenizer.ggml.{t}".encode(), v)
        return "token_boundary"
    elif name == "quant_swap":
        sw = {0:8, 8:2, 2:0}
        for tn in [b"output.weight",b"output_norm.weight",b"token_embd.weight"]:
            kp = raw.find(tn)
            if kp<0: continue
            pos = kp+len(tn)
            nd = struct.unpack_from("<I",raw,pos)[0]
            pos += 4+nd*8
            qt = struct.unpack_from("<I",raw,pos)[0]
            struct.pack_into("<I",raw,pos,sw.get(qt,8))
        return "quant_swap"
    elif name == "tensor_offset":
        for tn in [b"output.weight",b"token_embd.weight"]:
            kp = raw.find(tn)
            if kp<0: continue
            pos = kp+len(tn)
            nd = struct.unpack_from("<I",raw,pos)[0]
            pos += 4+nd*8+4
            old = struct.unpack_from("<Q",raw,pos)[0]
            struct.pack_into("<Q",raw,pos,(old+0x40000000)&0xFFFFFFFFFFFFFFFF)
        return "tensor_offset"
    elif name == "arch_spoof":
        spoofs = {"gemma4":"llama","nemotron_h":"llama","phi3":"gemma2","qwen35":"llama"}
        new = spoofs.get(arch,"llama")
        pstr(raw, b"general.architecture", new.encode())
        return f"arch_{new}"
    elif name == "vocab_corrupt":
        kp = raw.find(b"tokenizer.ggml.tokens")
        if kp<0: return "vocab_corrupt(0)"
        pos = kp+22+4+4+8
        n=0
        for _ in range(10):
            ol = struct.unpack_from("<Q",raw,pos)[0]
            if ol>100000 or ol==0: break
            struct.pack_into("<Q",raw,pos,0x7FFFFFFFFFFFFFFF)
            n+=1; pos+=8+ol
        return f"vocab_corrupt({n})"

ATTACKS = ["rope_drift","block_mismatch","embed_crush","token_boundary",
           "quant_swap","tensor_offset","arch_spoof","vocab_corrupt"]

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["nemotron","gemma4","qwen35","phi4"])
    ap.add_argument("--only", nargs="+", default=ATTACKS)
    args = ap.parse_args()
    
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    
    for mn in args.models:
        mp = Path(MODELS[mn])
        if not mp.exists():
            print(f"[skip] {mn}: file not found", file=sys.stderr)
            continue
        arch = get_arch(str(mp))
        sz = mp.stat().st_size // 1024 // 1024
        print(f"\n{'='*60}\n  {mn} arch={arch} {sz}MB\n{'='*60}", file=sys.stderr)
        
        # Load full model into memory once
        print(f"  Loading {mn}...", file=sys.stderr, end="", flush=True)
        t0 = time.time()
        full = bytearray(mp.read_bytes())
        print(f" {time.time()-t0:.1f}s", file=sys.stderr)
        
        for atk in args.only:
            raw = bytearray(full)  # copy
            try:
                aname = gen(atk, raw, arch)
            except Exception as e:
                print(f"  [{atk}] gen error: {e}", file=sys.stderr)
                continue
            
            vpath = OUT / f"{mn}_{aname}.gguf"
            vpath.write_bytes(bytes(raw))
            
            res = check(vpath)
            res["model"] = mn
            res["arch"] = arch
            res["attack"] = aname
            res["size_mb"] = sz
            results.append(res)
            
            tag = "CRASH" if res["crashed"] else f"rc={res['rc']}"
            print(f"  [{aname:20s}] {tag} {res['elapsed']}s {res['error'][:80]}", file=sys.stderr)
            
            # Write incrementally
            fields = ["model","arch","attack","size_mb","rc","signal","crashed","elapsed","error"]
            for r in results:
                for k in fields: r.setdefault(k,"")
            with CSV_PATH.open("w", newline="") as f:
                csv.DictWriter(f, fieldnames=fields).writerow(results[0]) if len(results)==1 else None
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                w.writerows(results)
            
            try: vpath.unlink()
            except: pass
            time.sleep(3)  # CPU cooldown
        
        del full  # free memory
    
    # Final summary
    crashes = [r for r in results if r["crashed"]]
    oks = [r for r in results if r["rc"]==0]
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"TOTAL={len(results)} OK={len(oks)} CRASHES={len(crashes)}", file=sys.stderr)
    for r in crashes:
        print(f"  CRASH: {r['model']}/{r['attack']} sig={r['signal']}", file=sys.stderr)
    for r in oks:
        print(f"  OK: {r['model']}/{r['attack']}", file=sys.stderr)
    print(f"Results: {CSV_PATH}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
