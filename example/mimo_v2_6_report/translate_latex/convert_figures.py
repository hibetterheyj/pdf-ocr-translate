#!/usr/bin/env python3
"""Turn MinerU's image stubs + plain-text captions into real LaTeX figures.

MinerU emits a figure as one bare
``\\pandocbounded{\\includegraphics[keepaspectratio,alt={image}]{images/<sha>.jpg}}``
line per *panel*, with the caption as unmarked body prose ("Figure 4 The overall
...").  This pass runs **before translation** so the translators see the final
structure, and it:

  * drops every OCR stub, replacing it with the 400 DPI render in ``images_hi/``
    (one file per figure, all panels together — see ``render_figures.py``)
  * wraps that in a ``figure`` environment carrying a real ``\\caption`` and
    ``\\label``, so the Chinese PDF numbers figures itself and cross-references
    resolve
  * anchors on the caption paragraph rather than the stub, because a stub can
    land on either side of its caption (Figure 1 has five panels above the
    caption and a sixth below it)

Run before splitting.  Re-running after translation would delete the Chinese
captions, so it is not part of the build script.

Usage:  convert_figures.py main.tex
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

STUB = re.compile(
    r"^\s*\\pandocbounded\{\\includegraphics\[[^\]]*\]\{images/[0-9a-f]+\.jpg\}\}\s*$"
)
CAPTION = re.compile(r"^Figure\s+(\d+)\s+(.*)$")


def paragraph(lines: list[str], start: int) -> tuple[str, int]:
    """Return (joined caption text, exclusive end index) of the paragraph."""
    i = start
    while i < len(lines) and lines[i].strip():
        i += 1
    return " ".join(l.strip() for l in lines[start:i]), i


def enumerate_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """Return (start, exclusive_end) line spans of every enumerate environment."""
    spans, start = [], None
    for i, line in enumerate(lines):
        if start is None and "\\begin{enumerate}" in line:
            start = i
        elif start is not None and "\\end{enumerate}" in line:
            spans.append((start, i + 1))
            start = None
    return spans


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tex")
    args = ap.parse_args()
    path = Path(args.tex)
    lines = path.read_text(encoding="utf-8").split("\n")

    stubs = [i for i, l in enumerate(lines) if STUB.match(l)]
    stub_set = set(stubs)
    ents = enumerate_blocks(lines)

    # Blank lines and the subfigure-label lists we are about to delete carry no
    # reading order, so the adjacency test looks past them.  Stubs are the
    # thing being looked *for*, so they stay visible.
    ignored = {i for i, l in enumerate(lines) if not l.strip()}
    for bs, be in ents:
        ignored.update(range(bs, be))

    def neighbour(idx: int, step: int) -> int | None:
        j = idx
        while 0 <= j < len(lines):
            if j not in ignored:
                return j
            j += step
        return None

    captions: dict[int, tuple[int, int]] = {}
    for i, line in enumerate(lines):
        m = CAPTION.match(line)
        if not m or int(m.group(1)) in captions:
            continue
        _, end = paragraph(lines, i)
        prev, nxt = neighbour(i - 1, -1), neighbour(end, +1)
        # A real caption touches its image; a cross-reference ("Figure 5
        # summarizes this pipeline") is boxed in by running prose.
        if prev in stub_set or nxt in stub_set:
            captions[int(m.group(1))] = (i, end)

    # Ownership: each stub belongs to the *nearest* caption, in either
    # direction.  MinerU's reading order puts the caption above the stub for
    # some figures (Fig 8, 9, 15) and below it for others, and Figure 1 has one
    # panel after its caption — "first caption below" mis-assigns both cases.
    owner: dict[int, int] = {}
    for i in stubs:
        if not captions:
            owner[i] = None
            continue
        owner[i] = min(captions, key=lambda n: min(abs(captions[n][0] - i),
                                                  abs(captions[n][1] - i)))

    counts: dict[int, int] = defaultdict(int)
    for fig in owner.values():
        counts[fig] += 1
    orphan = [i for i, f in owner.items() if f is None]

    drop: set[int] = set(stubs)
    for s, e in captions.values():
        drop.update(range(s, e))

    # Subfigure labels ("(a) Domain-Specific Teachers") arrive as `enumerate`
    # blocks sitting between the figure's stub and its caption.  They are panel
    # labels, and the re-rendered PNG already carries them, so keeping the list
    # would print them twice.
    for num, (cs, ce) in captions.items():
        lo = min([stub for stub, f in owner.items() if f == num] + [cs])
        hi = max([stub for stub, f in owner.items() if f == num] + [ce])
        for bs, be in ents:
            if bs > lo and be - 1 < hi:
                drop.update(range(bs, be))

    emit: dict[int, str] = {}
    for num in sorted(captions):
        if num not in counts:
            print(f"  warning: figure {num} has a caption but no image stub")
            continue
        emit[captions[num][0]] = (
            "\\begin{figure}[htbp]\n"
            "\\centering\n"
            f"\\includegraphics[width=\\linewidth]{{images_hi/fig{num:02d}.png}}\n"
            f"\\caption{{{paragraph(lines, captions[num][0])[0][len(f'Figure {num} '):]}}}\n"
            f"\\label{{fig:{num}}}\n"
            "\\end{figure}"
        )

    out: list[str] = []
    for i, line in enumerate(lines):
        if i in emit:
            out.append(emit[i])
            continue
        if i in drop:
            continue
        out.append(line)

    path.write_text("\n".join(out), encoding="utf-8")
    print(f"removed {len(stubs)} OCR stubs, emitted {len(emit)} figures "
          f"({len(captions)} captions seen)")
    for num in sorted(counts):
        print(f"  figure {num:>2}: {counts[num]} stub(s)")
    if orphan:
        print(f"  WARNING: {len(orphan)} stub(s) matched no caption: lines {orphan}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
