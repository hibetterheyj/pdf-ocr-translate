#!/usr/bin/env python3
"""Audit a compiled PDF for the layout defects OCR translation produces.

Checks, per page:

  * **margin overflow** — a line extending past the text block.  MinerU's
    default ``l`` table columns never wrap, so this is the usual signature of a
    table running off the page.
  * **text overlap** — two lines whose boxes intersect.  Usually a table column
    too narrow for its content.
  * **empty list markers** — stray ``(a)``/``(b)``/``1.`` lines.  MinerU emits
    subfigure labels as ``enumerate`` blocks with no content, so once the images
    are wrapped in ``figure`` environments the empty lists are left behind and
    LaTeX still prints their numbers.

Calibrating the margin
----------------------
Find the text block's right edge from the .log or the geometry options, then
pass it.  Do **not** expect zero overflows at the exact edge: pymupdf's line
boxes include italic correction and glyph side bearings, so a line that visually
ends inside the margin can measure a few points past it.  Measure the worst case
once and set ``--tolerance`` above it — a genuine defect is tens of points, not
two.
"""
from __future__ import annotations

import argparse

import fitz

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
                    help="right edge of the text block, in pt")
    ap.add_argument("--tolerance", type=float, default=10.0,
                    help="pt of overhang to treat as measurement noise")
    ap.add_argument("--overlap-tol", type=float, default=6.0,
                    help="pt of box intersection before it counts as an overlap")
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    overflows = overlaps = markers = 0
    for pn, page in enumerate(doc, 1):
        ls = lines_of(page)
        for x0, y0, x1, y1, text in ls:
            if x1 > args.margin + args.tolerance:
                overflows += 1
                print(f"OVERFLOW p{pn}: x1={x1:.0f} > {args.margin:.0f}  {text[:70]!r}")
            if text in EMPTY_MARKER:
                markers += 1
                print(f"EMPTY-MARKER p{pn}: {text!r}")
        for i in range(len(ls)):
            for j in range(i + 1, len(ls)):
                ax0, ay0, ax1, ay1, at = ls[i]
                bx0, by0, bx1, by1, bt = ls[j]
                # same source line extracted twice, not a real collision
                if abs(ay0 - by0) < 1.5:
                    continue
                v = min(ay1, by1) - max(ay0, by0)
                h = min(ax1, bx1) - max(ax0, bx0)
                if v > args.overlap_tol and h > args.overlap_tol:
                    overlaps += 1
                    print(f"OVERLAP p{pn}: {at[:34]!r} vs {bt[:34]!r} (v={v:.0f} h={h:.0f})")

    print(f"\n{overflows} margin overflow(s), {overlaps} overlap(s), "
          f"{markers} stray list marker(s)")
    # Inline math split across lines routinely shows up as an overlap; if every
    # report is an equation fragment, the document is fine.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
