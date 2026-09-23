#!/usr/bin/env python3
"""Count structural LaTeX tokens so a translation pass can be proved lossless.

Translators are told to leave ``\\label``, ``\\cite``, ``\\includegraphics``,
``\\caption`` and friends untouched, but a chunk that silently drops one still
compiles — the damage only shows up later as an undefined reference or a missing
figure.  Counting the tokens before and after catches it directly.

    check_structure.py --parts parts --baseline baseline.json   # before
    check_structure.py --parts parts --compare baseline.json    # after

Expect a handful of deliberate deltas; the tool prints them so you can confirm
each is intentional rather than accidental.  In a worked run the only changes
were the two empty ``enumerate`` blocks removed as OCR litter and one heading
promoted from ``\\subsection`` to a preamble ``\\section*``.
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
    ap.add_argument("--baseline", help="write counts here")
    ap.add_argument("--compare", help="compare against this file and exit non-zero on any change")
    args = ap.parse_args()

    counts = scan(Path(args.parts))
    if args.compare:
        base = json.loads(Path(args.compare).read_text())
        bad = False
        for key, before in base.items():
            after = counts.get(key, 0)
            if after != before:
                bad = True
                print(f"{key:18s} {before:6d} -> {after:6d}   <-- CHANGED")
            else:
                print(f"{key:18s} {before:6d} -> {after:6d}")
        return 1 if bad else 0

    for key, value in counts.items():
        print(f"{key:18s} {value:6d}")
    if args.baseline:
        Path(args.baseline).write_text(json.dumps(counts, indent=2))
        print(f"baseline written to {args.baseline}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
