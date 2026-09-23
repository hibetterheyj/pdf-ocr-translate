#!/usr/bin/env python3
"""Build the cross-validated base `main.tex` from the two MinerU OCR outputs.

Neither OCR pass is uniformly better, and they fail in opposite directions:

  * v2 (two-stage pipeline) has cleaner prose — 28 split-word errors against the
    PDF text layer, vs 34 for v1 — but collapses table structure.  In Table 1 it
    loses the `\\multirow` grouping and merges `# Total Parameters` into the row
    above; in Table 3 it silently drops the `-` placeholders so the missing cells
    read as empty; in Table 6 it invents a sixth column.
  * v1 (VLM) preserves every table intact but inserts more spurious intra-word
    spaces in running text.

So the base is v2's prose with v1's seven `longtable` blocks spliced in.  Both
choices are checked against `pdf_pages/` — see README.md.

Usage:  build_hybrid.py --v2 <two-stage.tex> --v1 <vlm.tex> --out main.tex
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

TABLE = re.compile(r"\\begin\{longtable\}.*?\\end\{longtable\}", re.S)


def tables(text: str) -> list[str]:
    return TABLE.findall(text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2", required=True, help="two-stage OCR (prose base)")
    ap.add_argument("--v1", required=True, help="VLM OCR (table source)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    base = pathlib.Path(args.v2).read_text(encoding="utf-8")
    v1 = pathlib.Path(args.v1).read_text(encoding="utf-8")

    bt, v1t = tables(base), tables(v1)
    if len(bt) != len(v1t):
        print(f"table count mismatch: v2={len(bt)} v1={len(v1t)}", file=sys.stderr)
        return 1

    swapped = 0
    for i, (b, v) in enumerate(zip(bt, v1t)):
        if b.strip() == v.strip():
            continue
        if b not in base:
            print(f"table {i + 1}: not found verbatim in v2", file=sys.stderr)
            return 1
        base = base.replace(b, v, 1)
        swapped += 1

    pathlib.Path(args.out).write_text(base, encoding="utf-8")
    print(f"wrote {args.out}: {len(bt)} tables, {swapped} taken from VLM")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
