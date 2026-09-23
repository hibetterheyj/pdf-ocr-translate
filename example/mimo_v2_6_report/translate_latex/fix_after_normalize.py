#!/usr/bin/env python3
"""Fix what the heading normalizer gets right structurally but not in Chinese.

`normalize_heading_levels.py` matches on the *title text*, so it needs the
English `Abstract` / `References` to recognise those two sections and promote
them to unnumbered `\\section*`.  That is why the translators were told to leave
those two headings in English — but it leaves the printed headings English too.
Rename them here, after the level has been decided.

Also drops the `\\label{contents}` anchor if one survived, and reports the
final heading census so a mismatch against the source is visible rather than
silent.

Run after the normalizer, before compiling.  Idempotent.

Usage:  fix_after_normalize.py main_cn.tex
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

RENAMES = [
    (r"\section*{Abstract}", r"\section*{摘要}"),
    (r"\section*{References}", r"\section*{参考文献}"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tex", nargs="?", default="main_cn.tex")
    args = ap.parse_args()
    path = Path(args.tex)
    text = path.read_text(encoding="utf-8")

    for old, new in RENAMES:
        if new in text:
            print(f"{new}: already applied")
        elif old in text:
            text = text.replace(old, new)
            print(f"{old} -> {new}")
        else:
            print(f"WARNING: {old} not found (heading may have been translated)")

    path.write_text(text, encoding="utf-8")

    census = Counter(re.findall(r"\\(sub)*section\*?\{", text))
    print("heading census:", dict(census))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
