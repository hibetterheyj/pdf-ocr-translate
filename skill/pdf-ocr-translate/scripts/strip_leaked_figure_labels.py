#!/usr/bin/env python3
"""Drop body text MinerU read out of a figure and left stranded in the prose.

Figure 17 in this report is a grid of generated web pages whose column header
("Qwen3.5-9B | MiMo-V2.6-Distill-Qwen-9B  SFT RL") MinerU emitted as ordinary
body paragraphs — and not next to the figure: the two lines land a section
later, just before the References heading, where they read as two stray model
names floating in the text.

The re-rendered `images_hi/fig17.png` already contains that header, so the
leaked copies are pure duplication.  Only whole standalone lines are matched,
so a table row label of the same name would not be caught.

Usage:  strip_leaked_figure_labels.py main.tex      # idempotent
"""
from __future__ import annotations

import argparse
from pathlib import Path

# Exact standalone lines, as they appear in both the English source and the
# translated file (the labels were never translated — they are figure content).
LEAKED: set[str] = {
    "Qwen3.5-9B",
    "MiMo-V2.6-Distill-Qwen-9B SFT RL",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tex", nargs="?", default="main.tex")
    args = ap.parse_args()
    path = Path(args.tex)
    lines = path.read_text(encoding="utf-8").split("\n")

    kept = [l for l in lines if l.strip() not in LEAKED]
    removed = len(lines) - len(kept)
    path.write_text("\n".join(kept), encoding="utf-8")
    print(f"leaked figure labels removed: {removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
