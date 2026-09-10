#!/usr/bin/env python3
"""Collapse multi-line OCR headings onto one line and drop false headings.

MinerU wraps long headings across two or three source lines::

    \\subsection{2.1.1. Multimodal
    Architecture}\\label{multimodal-architecture}

The heading normalizer matches per line and cannot see a title split across
lines, so join each one before translation.  Also removes headings MinerU
invented from mid-sentence text (a line starting "V4.1 ..." was promoted to a
heading when it is really body prose).
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

OPEN_HEADING = re.compile(r"^\\(section|subsection|subsubsection)\*?\{")
# A line that begins mid-sentence and was wrongly promoted to a heading.
# Each is rewritten back into the body prose it was torn from.
FALSE_HEADINGS = {
    "V4.1 therefore revises persistent KV cache management as":
        "V4.1 therefore revises persistent KV cache management as follows:",
}


def collapse(text: str) -> tuple[str, int, int]:
    lines = text.split("\n")
    out: list[str] = []
    joined = 0
    removed = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if OPEN_HEADING.match(line) and "}" not in line:
            buf = [line]
            j = i + 1
            while j < len(lines):
                buf.append(lines[j].strip())
                if "}" in lines[j]:
                    break
                j += 1
            merged = " ".join(buf).replace("  ", " ")
            merged = re.sub(r"\{\s+", "{", merged)
            merged = re.sub(r"\s+\}", "}", merged)
            out.append(merged)
            joined += 1
            i = j + 1
            continue
        m = re.match(r"^\\(?:section|subsection|subsubsection)\*?\{([^}]*)\}", line)
        if m:
            title = m.group(1).strip()
            for frag, restored in FALSE_HEADINGS.items():
                if title.startswith(frag):
                    out.append(restored)
                    removed += 1
                    break
            else:
                out.append(line)
            i += 1
            continue
        out.append(line)
        i += 1
    stitched = "\n".join(out)
    # Restore heading commands MinerU invented out of mid-sentence prose.
    for frag, restored in FALSE_HEADINGS.items():
        pattern = re.compile(
            r"^\\(?:section|subsection|subsubsection)\*?\{"
            + re.escape(frag)
            + r"[^}]*\}(?:\\label\{[^}]*\})?[ \t]*$",
            re.MULTILINE,
        )
        stitched, n = pattern.subn(restored, stitched)
        removed += n
    return stitched, joined, removed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", required=True)
    args = ap.parse_args()
    total_j = total_r = 0
    for p in sorted(Path(args.parts).glob("*.tex")):
        text, j, r = collapse(p.read_text())
        if j or r:
            p.write_text(text)
            print(f"{p.name}: joined {j} heading(s), removed {r} false heading(s)")
        total_j += j
        total_r += r
    print(f"total: {total_j} headings joined, {total_r} false headings removed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
