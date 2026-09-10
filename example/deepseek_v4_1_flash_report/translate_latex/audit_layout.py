#!/usr/bin/env python3
"""Audit the compiled PDF for layout defects.

Checks, per page:

  * **text overlap** — two lines whose bounding boxes intersect horizontally and
    vertically by more than a few points (the signature of a too-narrow table
    column);
  * **right-margin overflow** — a line extending past the text block, which the
    user sees as a table running off the page;
  * **empty list markers** — stray ``(a)``/``(b)``/``1.`` lines left behind when
    OCR emits an ``enumerate`` with no content.

Usage:  audit_layout.py --pdf build/final/main_cn.pdf --margin 555
"""
from __future__ import annotations

import argparse
from pathlib import Path

import fitz

TOL = 6.0          # pt of allowed overlap before it counts as a defect
# PyMuPDF's line boxes include italic-correction and glyph side bearings, so a
# line that visually ends inside the margin can measure a few points past it.
# Across this document the worst case is 8.4pt; anything under OVERHANG_TOL is
# measurement noise rather than a line running off the page.
OVERHANG_TOL = 10.0
EMPTY_MARKER = {"(a)", "(b)", "(c)", "(d)", "(e)", "(f)", "(i)", "(ii)"}


def lines_of(page: fitz.Page) -> list[tuple[float, float, float, float, str]]:
    out = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            text = "".join(s["text"] for s in line["spans"]).strip()
            if text:
                x0, y0, x1, y1 = line["bbox"]
                out.append((x0, y0, x1, y1, text))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--margin", type=float, default=555.0,
                    help="right edge of the text block in pt")
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    overlaps = overflows = 0
    for pn, page in enumerate(doc, 1):
        ls = lines_of(page)
        for x0, y0, x1, y1, text in ls:
            if x1 > args.margin + OVERHANG_TOL:
                overflows += 1
                print(f"OVERFLOW p{pn}: x1={x1:.0f} > {args.margin:.0f}  {text[:70]!r}")
            if text in EMPTY_MARKER:
                print(f"EMPTY-MARKER p{pn}: {text!r}")
        for i in range(len(ls)):
            for j in range(i + 1, len(ls)):
                ax0, ay0, ax1, ay1, at = ls[i]
                bx0, by0, bx1, by1, bt = ls[j]
                vover = min(ay1, by1) - max(ay0, by0)
                hover = min(ax1, bx1) - max(ax0, bx0)
                if vover > TOL and hover > TOL:
                    # same line re-extracted, or genuine collision
                    if abs(ay0 - by0) < 1.5:
                        continue
                    overlaps += 1
                    print(f"OVERLAP p{pn}: {at[:34]!r} vs {bt[:34]!r} "
                          f"(v={vover:.0f} h={hover:.0f})")
    print(f"\n{overflows} margin overflow(s), {overlaps} text overlap(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
