#!/usr/bin/env python3
"""Count structural LaTeX tokens across the chunks.

Translation must not change these.  Run before and after the translation pass and
compare: a dropping ``\\label`` or ``\\cite`` count means an agent rewrote
structure it should have preserved.

Usage:  check_structure.py --parts parts [--baseline baseline.json]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

TOKENS = {
    "begin": r"\\begin\{",
    "end": r"\\end\{",
    "label": r"\\label\{",
    "ref": r"\\ref\{",
    "cite": r"\\cite\{",
    "includegraphics": r"\\includegraphics",
    "caption": r"\\caption\{",
    "tag": r"\\tag\{",
    "longtable": r"\\begin\{longtable\}",
    "subsection": r"\\subsection\{",
}


def scan(parts: Path) -> dict[str, int]:
    counts = {name: 0 for name in TOKENS}
    for path in sorted(parts.glob("*.tex")):
        text = path.read_text()
        for name, pattern in TOKENS.items():
            counts[name] += len(re.findall(pattern, text))
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", required=True)
    ap.add_argument("--baseline", help="JSON file to write (omit --compare) or read")
    ap.add_argument("--compare", help="compare against this JSON file")
    args = ap.parse_args()

    counts = scan(Path(args.parts))
    if args.compare:
        base = json.loads(Path(args.compare).read_text())
        bad = False
        for key, before in base.items():
            after = counts.get(key, 0)
            flag = "" if after == before else "   <-- CHANGED"
            if after != before:
                bad = True
            print(f"{key:18s} {before:6d} -> {after:6d}{flag}")
        return 1 if bad else 0

    for key, value in counts.items():
        print(f"{key:18s} {value:6d}")
    if args.baseline:
        Path(args.baseline).write_text(json.dumps(counts, indent=2))
        print(f"baseline written to {args.baseline}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
