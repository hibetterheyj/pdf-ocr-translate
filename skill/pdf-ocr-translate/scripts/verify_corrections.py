#!/usr/bin/env python3
"""Check that a claimed correction really is in the source PDF.

Translation subagents report corrections as "OCR text → corrected text, PDF page
N".  Those reports are the main evidence that the cross-validation actually
happened, so it is worth spot-checking them — and a plain substring search does
not work, because pymupdf emits math spans with a space between every glyph:

    the PDF text layer renders "fused-RoPE-attention" as
    "f u s e d - R o P E - a t t e n t i o n"

so a naive ``needle in page_text`` gives a false negative and the correction
looks fabricated when it is fine.  This tool collapses whitespace *and* hyphens
on both sides before searching, and by default searches the whole document
rather than trusting the cited page — chunk boundaries and printed page numbers
do not line up one-to-one, and a correct correction is often filed against a
neighbouring page.

    verify_corrections.py --pages-dir pdf_pages \
        --check "∇Text" --check "reinforcement-learning rollout"

Exit code is non-zero if any needle is absent, so it can gate a review step.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def squeeze(text: str) -> str:
    """LowerCase and drop whitespace and hyphens, for tolerant matching."""
    return re.sub(r"[\s­-]+", "", text).lower()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages-dir", default="pdf_pages")
    ap.add_argument("--check", action="append", default=[],
                    help="a corrected string that should exist in the PDF")
    ap.add_argument("--page", action="append", default=[],
                    help="'page_NNN.txt|needle' to require the needle on one page")
    ap.add_argument("--count", action="append", default=[],
                    help="'needle' — print how many times it occurs document-wide")
    args = ap.parse_args()

    pages = Path(args.pages_dir)
    corpus = {p.name: squeeze(p.read_text()) for p in sorted(pages.glob("*.txt"))}
    whole = "".join(corpus.values())

    ok = True
    for needle in args.check:
        hits = [name for name, text in corpus.items() if squeeze(needle) in text]
        if hits:
            print(f"FOUND   {needle!r}  on {', '.join(hits[:4])}")
        else:
            ok = False
            print(f"ABSENT  {needle!r}  (not anywhere in {args.pages_dir})")

    for item in args.page:
        name, _, needle = item.partition("|")
        text = corpus.get(name, "")
        found = squeeze(needle) in text
        ok &= found
        print(f"{'FOUND  ' if found else 'ABSENT '} {name}  {needle!r}")

    for needle in args.count:
        print(f"{whole.count(squeeze(needle)):4d}x   {needle!r}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
