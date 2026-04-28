#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def parse_pages(raw: str | None) -> list[int]:
    if not raw:
        return []
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def extract_embedded(pdf: Path, output_dir: Path, page: int) -> None:
    prefix = output_dir / f"p{page}"
    run(["pdfimages", "-f", str(page), "-l", str(page), "-j", str(pdf), str(prefix)])


def render_page(pdf: Path, output_dir: Path, page: int, dpi: int) -> Path:
    prefix = output_dir / f"p{page}"
    run(["pdftocairo", "-png", "-r", str(dpi), "-f", str(page), "-l", str(page), str(pdf), str(prefix)])
    return output_dir / f"p{page}-{page:02d}.png"


def crop_with_sips(image: Path, output: Path, x: int, y: int, w: int, h: int) -> None:
    if not shutil.which("sips"):
        raise RuntimeError("sips is required for crop mode when Pillow is unavailable.")
    run(["sips", "-c", str(h), str(w), "--cropOffset", str(y), str(x), str(image), "--out", str(output)])


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract high-resolution figure candidates from a source PDF.")
    parser.add_argument("--pdf", required=True, help="Source PDF path")
    parser.add_argument("--output-dir", required=True, help="Directory for extracted files")
    parser.add_argument("--list-embedded", action="store_true", help="Print embedded image inventory via pdfimages -list")
    parser.add_argument("--pdfimages-pages", help="Comma-separated pages to extract embedded images from")
    parser.add_argument("--render-pages", help="Comma-separated pages to render with pdftocairo")
    parser.add_argument("--dpi", type=int, default=600, help="Render DPI for pdftocairo")
    parser.add_argument(
        "--crop",
        action="append",
        default=[],
        help="Crop spec: page=<n>,x=<left>,y=<top>,w=<width>,h=<height>,name=<file>",
    )
    args = parser.parse_args()

    pdf = Path(args.pdf).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.list_embedded:
        run(["pdfimages", "-list", str(pdf)])

    for page in parse_pages(args.pdfimages_pages):
        extract_embedded(pdf, output_dir, page)

    rendered: dict[int, Path] = {}
    for page in parse_pages(args.render_pages):
        rendered[page] = render_page(pdf, output_dir, page, args.dpi)

    for raw in args.crop:
        spec = {}
        for item in raw.split(","):
            key, value = item.split("=", 1)
            spec[key.strip()] = value.strip()
        page = int(spec["page"])
        image = rendered.get(page) or output_dir / f"p{page}-{page:02d}.png"
        if not image.exists():
            raise FileNotFoundError(f"Rendered page image not found: {image}")
        crop_with_sips(
            image=image,
            output=output_dir / spec["name"],
            x=int(spec["x"]),
            y=int(spec["y"]),
            w=int(spec["w"]),
            h=int(spec["h"]),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
