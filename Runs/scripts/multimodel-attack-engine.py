#!/usr/bin/env python3
"""Multi-model GGUF attack engine - deep testing across 4 architectures.

Generates weaponized variants for gemma4, nemotron_h, phi3, qwen35.
Each model gets architecture-specific attacks targeting its unique metadata.
"""

from __future__ import annotations

import csv
import json
import os
import signal
import struct
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SERVER = REPO / "llama-monitor/build/llama.cpp/bin/llama-server"
OUT_DIR = REPO / "logs" / "multimodel"
RESULTS_CSV = OUT_DIR / "multimodel_attack_results.csv"

MODELS = {
    "gemma4": "/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf",
    "nemotron": "/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf",
    "phi4": "/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/Phi-4-reasoning-plus-GGUF/Phi-4-reasoning-plus-Q4_K_M.gguf",
    "qwen35": "/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf",
}

GGUF_MAGIC = b"GGUF"


def read_meta(path: str) -> dict:
    """Read first 50MB and extract architecture info."""
    with open(path, "rb") as f:
        raw = f.read(50 * 1024 * 1024)
    key = b"general.architecture"
    kp = raw.find(key)
    if kp < 0:
        return {"arch": "unknown"}
    pos = kp + len(key) + 4
    slen = struct.unpack_from("<Q", raw, pos)[0]
    pos += 8
    arch = raw[pos:pos + slen].decode("utf-8", errors="replace")

    result = {"arch": arch, "raw": raw}
    for suffix in ["block_count", "embedding_length", "attention.head_count",
                    "attention.head_count_kv", "rope.dimension_count", "context_length",
                    "vocab_size", "feed_forward_length"]:
        k = f"{arch}.{suffix}".encode()
        kp2 = raw.find(k)
        if kp2 >= 0:
            result[suffix] = struct.unpack_from("<I", raw, kp2 + len(k) + 4)[0]

    # Special tokens
    for tok in ["bos_token_id", "eos_token_id", "padding_token_id", "unknown_token_id"]:
        k = f"tokenizer.ggml.{tok}".encode()
        kp2 = raw.find(k)
        if kp2 >= 0:
            result[tok] = struct.unpack_from("<I", raw, kp2 + len(k) + 4)[0]

    return result


def patch_bytes(raw: bytearray, key: bytes, new_val_bytes: bytes, skip_type=True):
    """Find a metadata key and replace its value bytes."""
    kp = raw.find(key)
    if kp < 0:
        return False
    pos = kp + len(key)
    if skip_type:
        pos += 4  # skip u32 type
    # Read current length
    cur_len = struct.unpack_from("<Q", raw, pos)[0]
    pos += 8
    if len(new_val_bytes) > cur_len:
        new_val_bytes = new_val_bytes[:cur_len]
    raw[pos:pos + len(new_val_bytes)] = new_val_bytes
    return True


def patch_u32(raw: bytearray, key: bytes, val: int):
    kp = raw.find(key)
    if kp < 0:
        return False
    struct.pack_into("<I", raw, kp + len(key) + 4, val)
    return True


# ===========================================================================
# Attack generators (architecture-aware)
# ===========================================================================

def attack_rope_drift(raw: bytearray, meta: dict) -> str:
    arch = meta["arch"]
    patch_u32(raw, f"{arch}.rope.dimension_count".encode(), 0x7FFFFFFF)
    patch_u32(raw, f"{arch}.context_length".encode(), 0xFFFFFFFF)
    if "vocab_size" in meta:
        patch_u32(raw, f"{arch}.vocab_size".encode(), 0x7FFFFFFF)
    return "rope_drift"


def attack_block_mismatch(raw: bytearray, meta: dict) -> str:
    arch = meta["arch"]
    patch_u32(raw, f"{arch}.block_count".encode(), 1)
    return "block_mismatch"


def attack_embed_crush(raw: bytearray, meta: dict) -> str:
    arch = meta["arch"]
    patch_u32(raw, f"{arch}.embedding_length".encode(), 1)
    if "attention.head_count" in meta:
        patch_u32(raw, f"{arch}.attention.head_count".encode(), 0xFFFFFFFF)
    return "embed_crush"


def attack_token_boundary(raw: bytearray, meta: dict) -> str:
    for tok, val in [("bos_token_id", 0xFFFFFFFF), ("eos_token_id", 0xFFFFFFFE),
                     ("padding_token_id", 0x80000000), ("unknown_token_id", 0x7FFFFFFF)]:
        patch_u32(raw, f"tokenizer.ggml.{tok}".encode(), val)
    return "token_boundary"


def attack_quant_swap(raw: bytearray, meta: dict) -> str:
    """Swap quant types in first 5 tensors."""
    GGML_QTYPE = {0: 8, 8: 2, 2: 0}  # F32<->Q8_0<->Q4_0
    count = 0
    for tname in [b"output.weight", b"output_norm.weight", b"token_embd.weight",
                   b"blk.0.attn_norm.weight", b"blk.0.ssm_a"]:
        kp = raw.find(tname)
        if kp < 0:
            continue
        pos = kp + len(tname)
        ndims = struct.unpack_from("<I", raw, pos)[0]
        pos += 4 + ndims * 8
        qtype = struct.unpack_from("<I", raw, pos)[0]
        new_type = GGML_QTYPE.get(qtype, 8)
        struct.pack_into("<I", raw, pos, new_type)
        count += 1
    return f"quant_swap({count})"


def attack_tensor_offset(raw: bytearray, meta: dict) -> str:
    count = 0
    for tname in [b"output.weight", b"token_embd.weight", b"blk.0.attn_norm.weight"]:
        kp = raw.find(tname)
        if kp < 0:
            continue
        pos = kp + len(tname)
        ndims = struct.unpack_from("<I", raw, pos)[0]
        pos += 4 + ndims * 8 + 4
        old_off = struct.unpack_from("<Q", raw, pos)[0]
        struct.pack_into("<Q", raw, pos, (old_off + 0x40000000) & 0xFFFFFFFFFFFFFFFF)
        count += 1
    return f"tensor_offset({count})"


def attack_vocab_corrupt(raw: bytearray, meta: dict) -> str:
    key = b"tokenizer.ggml.tokens"
    kp = raw.find(key)
    if kp < 0:
        return "vocab_corrupt(0)"
    pos = kp + len(key) + 4 + 4 + 8  # type, inner_type, count
    corrupted = 0
    for i in range(10):
        old_len = struct.unpack_from("<Q", raw, pos)[0]
        if old_len > 100000 or old_len == 0:
            break
        struct.pack_into("<Q", raw, pos, 0x7FFFFFFFFFFFFFFF)
        corrupted += 1
        pos += 8 + old_len
    return f"vocab_corrupt({corrupted})"


def attack_arch_spoof(raw: bytearray, meta: dict) -> str:
    arch = meta["arch"]
    spoofs = {"gemma4": "llama", "nemotron": "llama", "phi3": "gemma2", "qwen35": "llama"}
    new_arch = spoofs.get(arch, "llama")
    key = b"general.architecture"
    kp = raw.find(key)
    if kp < 0:
        return "arch_spoof(0)"
    pos = kp + len(key) + 4
    old_len = struct.unpack_from("<Q", raw, pos)[0]
    pos += 8
    new_bytes = new_arch.encode("utf-8")
    struct.pack_into("<Q", raw, pos - 8, len(new_bytes))
    raw[pos:pos + old_len] = new_bytes + b"\x00" * (old_len - len(new_bytes))
    return f"arch_spoof({arch}->{new_arch})"


ATTACKS = [
    attack_rope_drift,
    attack_block_mismatch,
    attack_embed_crush,
    attack_token_boundary,
    attack_quant_swap,
    attack_tensor_offset,
    attack_vocab_corrupt,
    attack_arch_spoof,
]


# ===========================================================================
# Test runner
# ===========================================================================

def test_variant(model_path: Path, port: int, timeout_s: int = 30) -> dict:
    cmd = [str(SERVER), "-m", str(model_path), "--port", str(port),
           "--host", "127.0.0.1", "-ngl", "0", "-c", "256", "--parallel", "1"]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                preexec_fn=os.setsid)
    except Exception as e:
        return {"http_status": 0, "crashed": True, "exit_code": -999, "error": str(e), "signal": ""}

    ready = False
    for _ in range(timeout_s * 2):
        if proc.poll() is not None:
            break
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
            ready = True
            break
        except Exception:
            pass
        time.sleep(0.5)

    if not ready:
        rc = proc.returncode if proc.poll() is not None else -1
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass
        if rc is None:
            rc = -1
        sig = rc - 256 if rc > 128 else rc
        signame = signal.Signals(-sig).name if sig < 0 else f"exit({rc})"
        return {"http_status": 0, "crashed": sig < 0, "exit_code": rc,
                "error": "not ready", "signal": signame, "response_len": 0}

    # Send a prompt
    payload = json.dumps({"prompt": "Hello", "n_predict": 16, "temperature": 0.0}).encode()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/completion",
                                    data=payload, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=20)
        status = resp.status
        body = json.loads(resp.read().decode())
        content = body.get("content", "")
        rlen = len(content)
    except Exception:
        status = 0
        rlen = 0

    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=5)
    except Exception:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass
        proc.wait(timeout=3)

    rc = proc.returncode
    sig = rc - 256 if rc > 128 else rc
    signame = signal.Signals(-sig).name if sig < 0 else f"exit({rc})"
    return {"http_status": status, "crashed": sig < 0, "exit_code": rc,
            "signal": signame, "response_len": rlen, "error": ""}


# ===========================================================================
# Main
# ===========================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=list(MODELS.keys()))
    parser.add_argument("--attacks", nargs="+", default=["all"])
    parser.add_argument("--port-start", type=int, default=18400)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_results = []
    port = args.port_start

    for model_name in args.models:
        model_path = MODELS[model_name]
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"MODEL: {model_name} ({model_path})", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)

        meta = read_meta(model_path)
        print(f"  arch={meta['arch']} blocks={meta.get('block_count','?')} "
              f"embed={meta.get('embedding_length','?')}", file=sys.stderr)

        attacks_to_run = ATTACKS if "all" in args.attacks else ATTACKS

        for attack_fn in attacks_to_run:
            attack_name = "baseline"
            variant_path = OUT_DIR / f"{model_name}_{attack_name}.gguf"

            # Read raw bytes (first 50MB for metadata, rest from file)
            with open(model_path, "rb") as f:
                raw = bytearray(f.read())

            try:
                attack_name = attack_fn(raw, meta)
            except Exception as e:
                print(f"  [{attack_name}] attack fn failed: {e}", file=sys.stderr)
                continue

            variant_path = OUT_DIR / f"{model_name}_{attack_name}.gguf"
            variant_path.write_bytes(bytes(raw))
            print(f"  [{attack_name}] {variant_path.name} ({variant_path.stat().st_size // 1024 // 1024}MB)", file=sys.stderr)

            # Test
            result = test_variant(variant_path, port)
            result["model"] = model_name
            result["attack"] = attack_name
            result["arch"] = meta["arch"]
            result["file_size"] = variant_path.stat().st_size
            all_results.append(result)

            crash = " CRASH" if result["crashed"] else ""
            sig = result.get("signal", "")
            print(f"  [{attack_name}] status={result['http_status']} rc={result['exit_code']} "
                  f"sig={sig}{crash}", file=sys.stderr)
            port += 1

            # Cleanup variant to save disk
            try:
                variant_path.unlink()
            except Exception:
                pass

    # Write CSV
    if all_results:
        fieldnames = ["model", "arch", "attack", "file_size", "http_status",
                      "exit_code", "signal", "crashed", "response_len", "error"]
        for r in all_results:
            for k in fieldnames:
                r.setdefault(k, "")
        with RESULTS_CSV.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(all_results)
        print(f"\n[multimodel] Results: {RESULTS_CSV}", file=sys.stderr)

    # Summary
    print(f"\n{'='*60}", file=sys.stderr)
    print("SUMMARY", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    crashes = [r for r in all_results if r["crashed"]]
    oks = [r for r in all_results if r["http_status"] == 200]
    print(f"Total: {len(all_results)}  OK: {len(oks)}  Crashes: {len(crashes)}", file=sys.stderr)
    for r in crashes:
        print(f"  CRASH: {r['model']}/{r['attack']} signal={r['signal']} rc={r['exit_code']}", file=sys.stderr)
    for r in oks:
        print(f"  OK: {r['model']}/{r['attack']} resp_len={r['response_len']}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
