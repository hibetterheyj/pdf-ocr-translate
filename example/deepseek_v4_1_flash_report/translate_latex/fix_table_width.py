#!/usr/bin/env python3
"""Size the longtables in the merged ``main_cn.tex`` so they fit the text block.

MinerU emits every table with ``l`` columns, and ``l`` never wraps, so a long
benchmark name or a run of model names pushes the table past the right margin.

Per table this pass:

  * turns the leading label column into a fixed-width ``p{}`` so long names wrap,
    leaving the numeric columns alone so scores stay aligned;
  * wraps the whole ``{\\def\\LTcaptype{none} ... }`` block in
    ``{\\footnotesize ... }``, shrinking every column.

The wrapper goes outside the ``longtable``.  An isolated test showed that
placing the size command inside the alignment preamble (after ``\\endlastfoot``)
breaks ``\\noalign``, while wrapping the enclosing group compiles cleanly.

Run after merge, before the heading normalizer.  Idempotent.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

MARKER = r"{\def\LTcaptype{none}"
BEGIN = re.compile(r"\\begin\{longtable\}(?:\[[^\]]*\])?\{@\{\}([lcr|]+)@\{\}\}")
END = r"\end{longtable}"
CAPTION = re.compile(r"(?:表|Table)\s*(\d+)\s*\\textbar")

# caption -> leading columns to rebind as p{width em}.
# The text block is 452pt; at \footnotesize one em is ~12.6pt.
#   T1 6 cols, label in col 1: p{5em} group + p{12em} label + 3 model + 1 shot
#   T3 8 cols, label in col 0: p{19em} label + 7 numeric
#   T4 9 cols, label in col 0: p{19em} label + 8 numeric
#   T5 6 cols, label in col 0: p{19em} label + 5 numeric
WRAP: dict[str, list[tuple[int, float]]] = {
    # T1 col0 = Chinese group name (5em is the minimum that fits 世界知识);
    #    col1 = benchmark name; cols 3-5 = the three model names, which are
    #    longer than their columns and must wrap too.
    "1": [(0, 5.0), (1, 9.0), (3, 5.5), (4, 5.5), (5, 5.5), (2, 4.5)],
    # T3/T4/T5 col0 = benchmark name.
    "3": [(0, 15.0)],
    "4": [(0, 13.0)],
    "5": [(0, 15.0)],
}


def rewrite_spec(spec: str, wrap: list[tuple[int, float]]) -> str:
    chars = list(spec)
    for idx, width in wrap:
        slot = -1
        for i, ch in enumerate(chars):
            if ch in "lcr":
                slot += 1
                if slot == idx:
                    chars[i] = f"L{{{width}em}}"
                    break
    return "".join(chars)


def caption_before(text: str, at: int) -> str | None:
    found = None
    for m in CAPTION.finditer(text, 0, at):
        found = m.group(1)
    return found


def process(text: str) -> tuple[str, list[str]]:
    out: list[str] = []
    pos = 0
    done: list[str] = []
    for m in BEGIN.finditer(text):
        cap = caption_before(text, m.start())
        end = text.find(END, m.end())
        if end < 0:
            continue
        if cap not in WRAP:
            continue
        # Emit everything up to the block opener unmodified, then the block.
        block_start = text.rfind(MARKER, 0, m.start())
        if block_start < 0:
            continue
        block_end = text.find("\n}", end) + 2
        out.append(text[pos:block_start])
        block = text[block_start:block_end]
        # rebind the column spec inside this block
        block = BEGIN.sub(lambda mm: mm.group(0).replace(mm.group(1),
                          rewrite_spec(mm.group(1), WRAP[cap])), block, count=1)
        out.append("{\\footnotesize" + block[1:])
        pos = block_end
        done.append(cap)
    out.append(text[pos:])
    return "".join(out), done


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tex", nargs="?", default="main_cn.tex")
    args = ap.parse_args()
    p = Path(args.tex)
    text, done = process(p.read_text())
    p.write_text(text)
    print(f"sized tables: {', '.join(done) if done else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
