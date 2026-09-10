#!/usr/bin/env python3
"""Render high-resolution figure PNGs from the source PDF.

Crop boxes are given in PDF points (top-left origin) and were derived from the
figure ink bounding box above each caption. Text-bearing figures keep their
original vector labels; the Chinese caption is supplied by the LaTeX \\caption.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz

CROPS: dict[str, tuple[int, float, float, float, float]] = {
    # name: (pdf_page_1indexed, x0, y0, x1, y1)
    # Figure 1 is two side-by-side panels; each is cropped to its own bitmap.
    "fig01a": (1, 66, 500, 297, 678),
    "fig01b": (1, 298, 500, 529, 678),
    "fig02": (5, 156, 80, 440, 234),
    "fig03": (7, 68, 80, 527, 323),
    "fig04": (10, 68, 80, 527, 233),
    "fig05": (11, 68, 80, 527, 293),
    "fig06": (25, 147, 80, 449, 243),
    "fig07": (27, 86, 80, 506, 357),
    "fig08": (28, 86, 80, 506, 242),
    "fig09": (35, 68, 80, 527, 202),
    "fig10": (36, 88, 80, 508, 242),
    "fig11": (49, 88, 80, 508, 317),
    "fig12": (50, 68, 80, 527, 273),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--dpi", type=int, default=400)
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    zoom = args.dpi / 72
    manifest = {}
    for name, (page, x0, y0, x1, y1) in CROPS.items():
        src = doc[page - 1]
        clip = fitz.Rect(x0, y0, x1, y1)
        # Guard: the crop must not swallow the caption or body prose.
        for block in src.get_text("blocks"):
            r = fitz.Rect(block[:4])
            overlap = r & clip
            if overlap.get_area() > 0.6 * r.get_area() and len(block[4].strip()) > 120:
                raise SystemExit(f"{name}: crop overlaps prose block at {r}")
        pix = src.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
        path = out / f"{name}.png"
        pix.save(path)
        manifest[name] = {
            "pdf_page": page,
            "clip_pt": [x0, y0, x1, y1],
            "png": path.name,
            "size": [pix.width, pix.height],
        }
        print(f"{name:8s} page {page:3d}  {pix.width}x{pix.height}  -> {path.name}")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
