#!/usr/bin/env python3
import json
from pathlib import Path
import base64

def main():
    base_dir = Path("/custom_pkgs")
    output_json = Path("/custom.json")
    custom_js_path = Path("/customCode.GET.js")  # <--- added

    if not base_dir.is_dir():
        raise SystemExit(f"Base directory does not exist: {base_dir}")

    files_dict = {}

    # Recursively find all .py files
    for py_file in sorted(base_dir.rglob("*.py")):
        rel_path = py_file.relative_to(base_dir).as_posix()
        raw_bytes = py_file.read_bytes()  # read as raw binary
        encoded = base64.b64encode(raw_bytes).decode("utf-8")
        files_dict[rel_path] = encoded

    # -----------------------------
    # 1. Write /custom.json
    # -----------------------------
    with output_json.open("w", encoding="utf-8") as f:
        json.dump(files_dict, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(files_dict)} files to {output_json}")

    # -----------------------------
    # 2. Insert JSON into customCode.GET.js
    # -----------------------------
    if not custom_js_path.exists():
        raise SystemExit(f"custom JS file not found: {custom_js_path}")

    # Read entire JS file as text
    js_text = custom_js_path.read_text(encoding="utf-8")

    # Read JSON exactly as a string (including newlines)
    raw_json = output_json.read_text(encoding="utf-8")

    # Replace the *quoted* placeholder with **raw JSON**
    updated_js = js_text.replace('"INSERT_CUSTOM_CODE_HERE"', raw_json)

    # Overwrite JS file
    custom_js_path.write_text(updated_js, encoding="utf-8")

    print(f"Inserted raw JSON into {custom_js_path}")

if __name__ == "__main__":
    main()
