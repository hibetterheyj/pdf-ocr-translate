#!/usr/bin/env python3
"""Render each figure from the source PDF at high resolution.

Why re-render instead of using MinerU's cutouts
-----------------------------------------------
MinerU slices a multi-panel figure into one bitmap per panel, at screen
resolution, so a six-panel figure arrives as six ~400x300 fragments whose axis
labels turn to mush once scaled to text width.  On the MiMo-V2.6 run that was
31 stubs for 17 figures.

The source PDF usually draws these figures as vectors, so rendering the ink
region at 400 DPI recovers crisp labels at no extra size cost.  Panels that are
genuine bitmaps (screenshots, photos) still re-render fine from the embedded
image.

How the crop box is found
-------------------------
The technique assumes figures sit at the top of a page with the caption
directly beneath — the common LaTeX float layout, and what MinerU's reading
order reflects.  For each caption it takes everything above, down to the last
line of running prose (a text block that is both near-column-width *and* long),
then trims the white border of the rendered bitmap.

Deriving the box rather than hand-listing crops means a caption that moves does
not silently produce a wrong crop; the manifest records what was used.  Two
guards keep it honest:

  * a caption must touch figure ink — a paragraph that merely opens with
    "Figure 11 compares ..." has running prose above it and is skipped;
  * the horizontal extent is *measured*, not assumed.  Figures are often wider
    than the text column, and a fixed clip shaves their outer panels.

Check the manifest after a run, and spot-check the contact sheet; a figure whose
crop box swallowed a paragraph is obvious there and nowhere else.

Usage:  render_figures.py --pdf <source.pdf> --out-dir images_hi [--dpi 400]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import fitz

PROSE_MIN_WIDTH = 380.0   # column text width is ~455pt; figure labels are much narrower
PROSE_MIN_WORDS = 12
SLACK_TOP = 6.0           # pt of padding above the ink
SLACK_BOTTOM = 4.0        # pt of gap between ink and caption


def caption_lines(page: fitz.Page) -> list[tuple[float, int, str]]:
    """Return (y_top, figure_number, text) for each real caption on the page.

    Body prose refers to figures too ("Figure 11 compares two ... RL runs"), so
    the discriminator is position within the block: a caption opens its own
    text block, whereas a cross-reference appears partway through a paragraph.
    """
    found = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        lines = block["lines"]
        if not lines:
            continue
        first = "".join(s["text"] for s in lines[0]["spans"]).strip()
        m = re.match(r"^Figure\s+(\d+)\b", first)
        if not m:
            continue
        rest = " ".join("".join(s["text"] for s in l["spans"]).strip() for l in lines[1:])
        found.append((lines[0]["bbox"][1], int(m.group(1)),
                      (first + " " + rest).strip()))
    return found


def prose_bottom(page: fitz.Page, limit_y: float) -> float:
    """y of the last running-prose line above `limit_y` (page top if none)."""
    bottom = None
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        x0, y0, x1, y1 = block["bbox"]
        text = " ".join("".join(s["text"] for s in l["spans"]) for l in block["lines"])
        if y1 <= limit_y and (x1 - x0) > PROSE_MIN_WIDTH and len(text.split()) > PROSE_MIN_WORDS:
            bottom = max(bottom or 0.0, y1)
    return bottom



def trim_white(path: Path, pad: int = 12) -> tuple[int, int]:
    from PIL import Image, ImageChops

    im = Image.open(path).convert("RGB")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bbox = ImageChops.difference(im, bg).getbbox()
    if bbox:
        x0, y0, x1, y1 = bbox
        im = im.crop((max(0, x0 - pad), max(0, y0 - pad),
                      min(im.width, x1 + pad), min(im.height, y1 + pad)))
    im.save(path)
    return im.size


def has_ink(page: fitz.Page, lo: float, hi: float) -> bool:
    """True if the band holds figure ink (a vector drawing or a bitmap)."""
    for im in page.get_image_info():
        if im["bbox"][3] > lo and im["bbox"][1] < hi:
            return True
    for dr in page.get_drawings():
        r = dr["rect"]
        # Ignore hairlines (the header rule, table rules): a figure has area.
        if r.y1 > lo and r.y0 < hi and (r.width > 4 or r.height > 4):
            return True
    return False


def content_bbox(page: fitz.Page, lo: float, hi: float) -> fitz.Rect | None:
    """Union bbox of all ink in the band, ignoring page-scale background rects.

    The band's horizontal extent is measured rather than assumed: Figure 4 is
    drawn as a box wider than the text column (34..549pt against a 64..531
    column), so a fixed clip silently shaves its outer panels.
    """
    page_area = abs(page.rect)
    boxes: list[fitz.Rect] = []

    def keep(r: fitz.Rect) -> bool:
        if r.y1 <= lo or r.y0 >= hi:
            return False
        # A drawing covering most of the sheet is a background, not the figure.
        return not (abs(r) > 0.9 * page_area)

    for block in page.get_text("dict")["blocks"]:
        if block.get("type") == 0:
            r = fitz.Rect(block["bbox"])
            if keep(r):
                boxes.append(r)
    for im in page.get_image_info():
        r = fitz.Rect(im["bbox"])
        if keep(r):
            boxes.append(r)
    for dr in page.get_drawings():
        r = dr["rect"]
        if keep(r):
            boxes.append(r)

    if not boxes:
        return None
    out = boxes[0]
    for r in boxes[1:]:
        out |= r
    return out


def render_logo(doc: fitz.Document, out: Path, zoom: float, manifest: dict) -> None:
    """Crop the title page's header band (publisher wordmark + icon).

    Papers from a company often put a logo above the title.  MinerU cannot
    reproduce it, so it transcribes the wordmark as body text — on the MiMo-V2.6
    run that surfaced as a stray "Xiaomi MIMO" line above the title.  Keeping
    the bitmap is both closer to the original and one less stray line in the
    frontmatter.  Skips silently if the first page has no header ink.
    """
    page = doc[0]
    xs, ys = [], []
    for im in page.get_image_info():
        b = im["bbox"]
        if b[1] < 80:                       # the wordmark bitmap
            xs += [b[0], b[2]]
            ys += [b[1], b[3]]
    for dr in page.get_drawings():          # the "mi" icon and the rule
        r = dr["rect"]
        if r.y0 < 80:
            xs += [r.x0, r.x1]
            ys += [r.y0, r.y1]
    if not xs:
        print("logo: no header ink found, skipping")
        return
    clip = fitz.Rect(min(xs) - 2, min(ys) - 2, max(xs) + 2, max(ys) + 2)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
    path = out / "title_logo.png"
    pix.save(path)
    manifest["title_logo"] = {"pdf_page": 1, "png": path.name,
                              "size": [pix.width, pix.height]}
    print(f"logo    page  1  y {clip.y0:6.1f}->{clip.y1:6.1f}  "
          f"{pix.width}x{pix.height}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--dpi", type=int, default=400)
    ap.add_argument("--only", type=int, nargs="*", help="render just these figure numbers")
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    zoom = args.dpi / 72
    manifest: dict[str, dict] = {}

    for pno in range(doc.page_count):
        page = doc[pno]
        for cap_y, num, text in caption_lines(page):
            if args.only and num not in args.only:
                continue
            prev = prose_bottom(page, cap_y - SLACK_BOTTOM)
            lo = prev + SLACK_TOP if prev else 0.0
            # A caption sits under its figure; a paragraph that merely opens
            # with "Figure 11 compares ..." has running prose above it instead.
            if not has_ink(page, lo, cap_y - SLACK_BOTTOM):
                continue
            ink = content_bbox(page, lo, cap_y - SLACK_BOTTOM)
            if ink is None:
                continue
            clip = fitz.Rect(ink.x0 - SLACK_TOP, ink.y0 - SLACK_TOP,
                             ink.x1 + SLACK_TOP, cap_y - SLACK_BOTTOM)
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
            name = f"fig{num:02d}"
            path = out / f"{name}.png"
            pix.save(path)
            size = trim_white(path)
            manifest[name] = {
                "pdf_page": pno + 1,
                "clip_pt": [round(v, 1) for v in (clip.x0, clip.y0, clip.x1, clip.y1)],
                "png": path.name,
                "size": list(size),
                "caption_head": text[:60],
            }
            print(f"{name:7s} page {pno + 1:>2}  y {clip.y0:6.1f}->{clip.y1:6.1f}  "
                  f"{size[0]}x{size[1]}  {text[:48]!r}")

    render_logo(doc, out, zoom, manifest)

    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"rendered {len(manifest)} assets (incl. logo) -> {out}/")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
