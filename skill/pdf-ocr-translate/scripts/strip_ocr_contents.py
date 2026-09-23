#!/usr/bin/env python3
"""Drop MinerU's hand-built table of contents from the source.

The OCR reads the printed Contents page as a plain list ("1 Introduction 3\\",
"2 Architecture 4\\", ...).  Those page numbers are the *English* edition's, so
keeping the list would both mislead and duplicate the real `\\tableofcontents`
that the merge step injects.

The bundled splitter flags a chunk as DROP_AT_MERGE when the marker heading
opens the chunk, but here the Contents sits mid-chunk (right behind the
abstract), so it needs removing at the source instead.  Only the heading and
the numbered list are removed; whatever follows the next heading is untouched.

Usage:  strip_ocr_contents.py main.tex
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

HEADING = re.compile(r"^\\subsection\{Contents\}\\label\{[^}]*\}\s*$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tex", nargs="?", default="main.tex")
    args = ap.parse_args()
    path = Path(args.tex)
    lines = path.read_text(encoding="utf-8").split("\n")

    start = next((i for i, l in enumerate(lines) if HEADING.match(l)), None)
    if start is None:
        print("contents block: not found (already stripped?)")
        return 0
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].lstrip().startswith("\\subsection")), len(lines))
    dropped = end - start

    path.write_text("\n".join(lines[:start] + lines[end:]), encoding="utf-8")
    print(f"contents block: dropped {dropped} lines "
          f"(hand-built list with English page numbers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
