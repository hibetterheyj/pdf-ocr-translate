#!/usr/bin/env python3
"""Turn MinerU's flattened footnotes back into real `\\footnote`s.

MinerU reads a footnote as two unrelated pieces: the marker digit gets glued to
whatever precedes it in the body, and the footnote text is emitted as its own
paragraph at the bottom of the page — the marker digit and all:

    ... using CyberGym (Wang et al., 2025)1,
    ...
    1We corrected the flawed evaluation environments based on ...

Rendered, that reads as a stray "1" mid-sentence and a stray paragraph further
down.  This pass reattaches the two, in either language, and drops the orphan
paragraph.  The pairs are listed explicitly because there are only two and the
marker digit alone is ambiguous (there is a "1" and a "2" in the prose too).

Needs `xurl` (already in the preamble) so the URL in footnote 2 can break.

Usage:  fix_footnotes.py main.tex          # idempotent
"""
from __future__ import annotations

import argparse
from pathlib import Path

URL = "https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B"

# (marker glued in the body, replacement, orphan footnote paragraph)
CASES: list[tuple[str, str, str]] = [
    (
        "CyberGym（Wang et al., 2025）1、",
        "CyberGym（Wang et al., 2025）\\footnote{我们根据 4.2.4 节所述方法修正了有缺陷的评测环境。}、",
        "1我们根据 4.2.4 节所述方法修正了有缺陷的评测环境。",
    ),
    (
        "CyberGym (Wang et al., 2025)1,",
        "CyberGym (Wang et al., 2025)\\footnote{We corrected the flawed evaluation "
        "environments based on the method described in Section 4.2.4.},",
        "1We corrected the flawed evaluation environments based on the method "
        "described in Section 4.2.4.",
    ),
    (
        "MiMo-V2.6-Distill-Qwen-9B,2，",
        f"MiMo-V2.6-Distill-Qwen-9B\\footnote{{\\url{{{URL}}}}}，",
        "2" + URL,
    ),
    (
        "MiMo-V2.6-Distill-Qwen-9B,2 ",
        f"MiMo-V2.6-Distill-Qwen-9B\\footnote{{\\url{{{URL}}}}} ",
        "2" + URL,
    ),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tex", nargs="?", default="main.tex")
    args = ap.parse_args()
    path = Path(args.tex)
    text = path.read_text(encoding="utf-8")

    attached = []
    for old, new, _orphan in CASES:
        if old in text:
            text = text.replace(old, new)
            attached.append(old[:28])

    orphans = {c[2] for c in CASES}
    lines = [l for l in text.split("\n") if l.strip() not in orphans]
    removed = len(text.split("\n")) - len(lines)
    path.write_text("\n".join(lines), encoding="utf-8")

    for a in attached:
        print(f"  attached: ...{a}...")
    print(f"footnotes attached: {len(attached)}; orphan footnote paragraphs removed: {removed}")
    print(f"\\footnote{{}} occurrences now: {text.count(chr(92) + 'footnote{')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
