#!/usr/bin/env python3
"""Reposition two figures in chunk 11 to match the source-PDF reading order.

The bundle keeps Figure 9's caption paragraph first, but MinerU emitted Figure 9's
image on a later page and Figure 10's caption on an earlier one, so both figure
blocks came out at the end of the chunk.  LaTeX would still float them near their
``\\ref``, but the input order should read like the paper: Figure 9 right after its
introductory paragraph in Section 5.3.3, Figure 10 inside Section 5.3.5.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

FIG_BLOCK = re.compile(r"\\begin\{figure\}\[htbp\].*?\\end\{figure\}", re.DOTALL)


def extract(text: str, label: str) -> tuple[str, str]:
    """Remove every figure block carrying ``label`` and return (remaining, block)."""
    blocks = [b for b in FIG_BLOCK.findall(text) if f"\\label{{{label}}}" in b]
    if not blocks:
        raise SystemExit(f"no figure block labelled {label}")
    for b in blocks:
        text = re.sub(re.escape(b) + r"[ \t]*\n*", "", text, count=1)
    return text, blocks[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    args = ap.parse_args()
    p = Path(args.path)
    text = p.read_text()

    text, fig9 = extract(text, "fig:9")
    text, fig10 = extract(text, "fig:10")
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Figure 9 goes just before the Section 5.3.4 heading.
    anchor9 = "\\subsection{5.3.4. Performance across agent scaffolds}"
    if anchor9 not in text:
        raise SystemExit("chunk 11: Section 5.3.4 heading not found")
    text = text.replace(anchor9, fig9 + "\n\n" + anchor9, 1)

    # Figure 10 goes at the end of Section 5.3.5, i.e. at the end of the chunk.
    text = text.rstrip("\n") + "\n\n" + fig10 + "\n"
    p.write_text(text)
    print(f"{p.name}: fig:9 moved before 5.3.4, fig:10 moved to end of 5.3.5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
