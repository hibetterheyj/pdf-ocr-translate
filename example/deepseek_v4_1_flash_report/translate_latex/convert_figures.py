#!/usr/bin/env python3
"""Convert MinerU image stubs + plain-text captions into real LaTeX figures.

MinerU emits figures as a bare ``\\pandocbounded{\\includegraphics{images/<sha>.jpg}}``
line with the caption as unmarked body prose (``Figure 3 \\textbar{} ...``).  The
image often lands on a different page from its caption, and multi-panel figures
arrive as several stubs.  This pass runs **before** translation and:

  * replaces the stubs with the high-resolution renders in ``images_hi/``
  * wraps them in one ``figure`` environment carrying a real ``\\caption``
  * drops OCR image fragments that duplicate a figure already emitted
  * restores Figure 10's caption, which MinerU split across a page boundary

Everything is anchored on the caption paragraph: each stub is assigned to the
first planned caption that follows it, so images that floated to an earlier
section still land with the right figure.

Run before translation so the translators see the final structure.
"""
from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

STUB = re.compile(
    r"\\pandocbounded\{\\includegraphics\[keepaspectratio,alt=\{image\}\]"
    r"\{images/[0-9a-f]+\.jpg\}\}"
)
CAPTION = re.compile(r"^\s*(?:Figure|Table)\s+(\d+)\s*\\textbar\{\}\s*(.*)$")

# chunk file -> ordered figure plan: (figure number, images_hi basenames)
# Tables are not listed; they keep their longtable plus prose caption.
FIG_PLAN: dict[str, list[tuple[str, list[str]]]] = {
    "01_body.tex": [("1", ["fig01a", "fig01b"]), ("2", ["fig02"]), ("3", ["fig03"])],
    "02_2__architecture.tex": [("4", ["fig04"])],
    "03_body.tex": [("5", ["fig05"])],
    "07_4_2__pre-training_setups.tex": [("6", ["fig06"])],
    "08_5__post-training.tex": [("7", ["fig07"]), ("8", ["fig08"])],
    "11_body.tex": [("9", ["fig09"]), ("10", ["fig10"])],
    "14_body.tex": [("11", ["fig11"]), ("12", ["fig12"])],
}

# Lines MinerU tore out of a caption or an equation; drop them outright.
STRAY = {
    "11_body.tex": {"Agent Teams Test-Time Compute Scaling"},
    "14_body.tex": {"length"},
}

# Figure 10's caption lost its "Figure 10 |" prefix at the page break.
FIG10_PREFIX = "Test-time compute scaling for single-agent and"


def paragraph_at(lines: list[str], start: int) -> tuple[str, int]:
    """Return (joined text, exclusive end index) of the paragraph at ``start``."""
    i = start
    while i < len(lines) and lines[i].strip():
        i += 1
    return " ".join(l.strip() for l in lines[start:i]), i


def clean_caption(raw: str) -> str:
    raw = re.sub(r"^(?:Figure|Table)\s+\d+\s*\\textbar\{\}\s*", "", raw)
    return raw.replace("\\textbar{}", "|").strip()


def render_figure(fig: str, images: list[str], caption: str) -> list[str]:
    out = ["\\begin{figure}[htbp]", "\\centering"]
    if len(images) == 1:
        out.append(f"\\includegraphics[width=\\linewidth]{{images_hi/{images[0]}}}")
    else:
        for img in images:
            out.append(f"\\includegraphics[width=0.48\\linewidth]{{images_hi/{img}}}")
        out.append("\\hfill")
    out += [f"\\caption{{{caption}}}", f"\\label{{fig:{fig}}}", "\\end{figure}"]
    return out


def process(path: Path) -> str:
    lines = path.read_text().split("\n")
    plan = FIG_PLAN.get(path.name)
    if not plan:
        return f"{path.name}: no figures planned"
    fig_ids = [f for f, _ in plan]
    images_for = dict(plan)
    strays = STRAY.get(path.name, set())

    if path.name == "11_body.tex":
        for i, line in enumerate(lines):
            if line.strip().startswith(FIG10_PREFIX):
                lines[i] = f"Figure 10 \\textbar{{}} {line.strip()}"
                break

    caption_at: dict[str, int] = {}
    caption_end: dict[str, int] = {}
    for i, line in enumerate(lines):
        m = CAPTION.match(line)
        if m and m.group(1) in images_for and m.group(1) not in caption_at:
            caption_at[m.group(1)] = i
            caption_end[m.group(1)] = paragraph_at(lines, i)[1]
    missing = [f for f in fig_ids if f not in caption_at]
    if missing:
        raise SystemExit(f"{path.name}: no caption paragraph for figure(s) {missing}")

    # Assign every stub to the first planned caption below it.
    stub_owner: dict[int, str] = {}
    for i, line in enumerate(lines):
        if not STUB.search(line):
            continue
        for j in range(i + 1, len(lines)):
            m = CAPTION.match(lines[j])
            if m and m.group(1) in images_for:
                stub_owner[i] = m.group(1)
                break
            if lines[j].startswith("\\subsection"):
                break
    images_found: dict[str, list[int]] = defaultdict(list)
    for i, fig in stub_owner.items():
        images_found[fig].append(i)

    drop = set()
    for fig in fig_ids:
        drop.update(range(caption_at[fig], caption_end[fig]))
    drop.update(i for i, l in enumerate(lines) if l.strip() in strays)
    drop.update(i for i, l in enumerate(lines) if STUB.search(l))
    drop.update(i for i, fig in stub_owner.items() if fig not in images_for)

    body: list[str] = []
    emitted: set[str] = set()
    for i, line in enumerate(lines):
        if i in drop:
            continue
        m = CAPTION.match(line)
        fig = m.group(1) if m and m.group(1) in images_for else None
        if fig and fig not in emitted:
            caption, _ = paragraph_at(lines, i)
            body.extend(render_figure(fig, images_for[fig], clean_caption(caption)))
            emitted.add(fig)
            continue
        body.append(line)

    for fig in fig_ids:
        if fig not in emitted:
            caption, _ = paragraph_at(lines, caption_at[fig])
            body.extend(render_figure(fig, images_for[fig], clean_caption(caption)))
            emitted.add(fig)
    path.write_text("\n".join(body))
    return f"{path.name}: emitted figures {sorted(emitted, key=int)}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", required=True)
    args = ap.parse_args()
    for name in FIG_PLAN:
        p = Path(args.parts) / name
        if not p.exists():
            print(f"skip (missing): {name}")
            continue
        print(process(p))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
