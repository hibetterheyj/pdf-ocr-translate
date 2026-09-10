#!/usr/bin/env python3
"""Verify an agent's claimed OCR correction actually exists in the source PDF.

The translator agents report corrections as ``OCR text → corrected text`` with a
page reference.  The PDF text layer is unreliable for a plain substring search:
pymupdf emits math spans with a space between every glyph, so
``fused-RoPE-attention`` can appear as ``f u s e d - R o P E - a t t e n t i o n``.
This tool collapses all whitespace on both sides before searching, and reports
whether the corrected string is found on the cited page (and, as a control,
whether the *damaged* string is found).

Usage:
  verify_corrections.py --pdf ../DeepSeek-V4.1-Flash.pdf \
      --check "page_019.txt|reinforcement learning rollout" \
      --check "page_016.txt|∇Text"
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def squeeze(text: str) -> str:
    return re.sub(r"\s+", "", text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages-dir", default="../pdf_pages")
    ap.add_argument("--check", action="append", default=[],
                    help="'page_NNN.txt|needle' — needle must appear on that page")
    ap.add_argument("--count", action="append", default=[],
                    help="'page_NNN.txt|needle' — print the occurrence count instead")
    args = ap.parse_args()

    pages = Path(args.pages_dir)
    ok = True
    for item in args.check:
        page, _, needle = item.partition("|")
        path = pages / page
        if not path.exists():
            print(f"MISSING PAGE {page}")
            ok = False
            continue
        found = squeeze(needle) in squeeze(path.read_text())
        print(f"{'FOUND  ' if found else 'ABSENT '} {page}  {needle!r}")
        ok &= found
    for item in args.count:
        page, _, needle = item.partition("|")
        path = pages / page
        text = squeeze(path.read_text()) if path.exists() else ""
        print(f"{text.count(squeeze(needle)):4d}x   {page}  {needle!r}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
