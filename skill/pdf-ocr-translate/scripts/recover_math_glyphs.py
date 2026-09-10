#!/usr/bin/env python3
"""Recover the math symbols MinerU drops, using the PDF's span-level font data.

The problem this solves
-----------------------
When a paper sets math variables in a math font (``XCharterMathMI``, ``Cambria
Math``, or Unicode Mathematical Italic in general), MinerU cannot map the glyph
and writes U+FFFD instead.  The trap is that **pymupdf's plain text layer loses
them too**, so comparing MinerU's output against ``page.get_text("text")``
suggests the symbol is simply gone.  It is not: ``page.get_text("dict")``
carries a per-span ``font`` name, and a span whose font looks like a math font
holds the real codepoint — ``𝐿`` (U+1D43F) is just "MATHEMATICAL ITALIC CAPITAL
L", i.e. ``L``.

So the recovery is: read the span fonts, pull the math glyphs out, and put them
back where MinerU left a hole.

Why you cannot skip the verification
------------------------------------
A *wrong* symbol compiles cleanly.  A real run shipped ``λ`` where the PDF said
``τ`` (equation defined ``τ = λ·Δb``; the decay rate is ``τ``), and nothing in
the LaTeX or the PDF rendering complained.  Always read the proposed symbol
against its surrounding sentence before accepting it.

What this script does
---------------------
1. Extracts every math glyph from the given pages, in reading order.
2. Prints the surrounding prose with each symbol marked as ``‹X›``, so you can
   line the PDF up against a chunk by eye.
3. Prints the symbol vocabulary with counts (a small vocabulary — usually just
   italic letters — is the norm).
4. With ``--chunks``, aligns each chunk against the reference and proposes a
   replacement for every U+FFFD, flagging low-confidence matches.

The output is a *worklist*.  Turn it into exact substring replacements and apply
them with a small table-driven pass (see ``fix_lost_math.py`` in the worked
example for the shape of that table).

Usage
-----
    recover_math_glyphs.py --pdf paper.pdf --pages 4-51
    recover_math_glyphs.py --pdf paper.pdf --pages 9 --chunks parts/ --out worklist.txt
"""
from __future__ import annotations

import argparse
import difflib
import re
import unicodedata
from collections import Counter
from pathlib import Path

import fitz

# Unicode Mathematical Alphanumeric Symbols: 𝐀..𝐳, plus the bold/italic variants.
_MATH_LATIN: dict[str, str] = {}
for _base, _start in (
    ("A", 0x1D400), ("a", 0x1D41A),   # bold
    ("A", 0x1D434), ("a", 0x1D44E),   # italic
    ("A", 0x1D468), ("a", 0x1D482),   # bold italic
    ("A", 0x1D49C), ("a", 0x1D4B6),   # script
    ("A", 0x1D4D0), ("a", 0x1D4EA),   # bold script
    ("A", 0x1D504), ("a", 0x1D51E),   # fraktur
    ("A", 0x1D538), ("a", 0x1D552),   # double-struck
    ("A", 0x1D56C), ("a", 0x1D586),   # bold fraktur
    ("A", 0x1D5A0), ("a", 0x1D5BA),   # sans-serif
    ("A", 0x1D5D4), ("a", 0x1D5EE),   # sans-serif bold
    ("A", 0x1D608), ("a", 0x1D622),   # sans-serif italic
    ("A", 0x1D63C), ("a", 0x1D656),   # sans-serif bold italic
    ("A", 0x1D670), ("a", 0x1D68A),   # monospace
):
    for _i in range(26):
        _MATH_LATIN[chr(_start + _i)] = chr(ord(_base) + _i)
_MATH_LATIN.update({chr(0x1D7CE + i): chr(ord("0") + i) for i in range(10)})
_MATH_LATIN.update({chr(0x1D7D8 + i): chr(ord("0") + i) for i in range(10)})

MARK = "\x00"          # internal sentinel in the page-reference stream
MATH_HOLE = "Zq"        # stand-in for a damaged site while aligning chunk text
MATHPAGE_FONT = ("Math", "MI", "Symbol", "MTMI")


def is_math_font(name: str) -> bool:
    return any(tag in name for tag in MATHPAGE_FONT)


def math_symbol(ch: str) -> str | None:
    """Return a printable label for one math codepoint, or None if it is not math."""
    if ch in _MATH_LATIN:
        return _MATH_LATIN[ch]
    name = unicodedata.name(ch, "")
    if name.startswith("GREEK"):
        tail = name.rsplit(" ", 1)[-1]
        return tail.capitalize() if "CAPITAL" in name else tail.lower()
    if name.startswith("MATHEMATICAL"):
        tail = name.rsplit(" ", 1)[-1]
        return tail.capitalize() if "CAPITAL" in name else tail.lower()
    if name in ("SCRIPT SMALL L", "SCRIPT CAPITAL L"):
        return "l"
    return None


def page_reference(page: fitz.Page) -> tuple[str, list[str]]:
    """Render one page as prose with ``‹X›`` in place of each math symbol."""
    parts: list[str] = []
    symbols: list[str] = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                if not is_math_font(span["font"]):
                    parts.append(span["text"])
                    continue
                for ch in span["text"]:
                    label = math_symbol(ch)
                    if label is None:
                        parts.append(ch if ch.isascii() else " ")
                    else:
                        symbols.append(label)
                        parts.append(f"‹{label}›")
    return "".join(parts), symbols


def plain(s: str) -> str:
    """Collapse a reference or chunk string for fuzzy alignment."""
    s = re.sub(r"\\[a-zA-Z]+\*?", " ", s)
    s = s.replace("{", " ").replace("}", " ").replace("$", " ").replace(MARK, " ")
    s = re.sub(r"[^A-Za-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def chunk_stream(text: str) -> str:
    """Reduce a chunk to plain prose, keeping U+FFFD as a single MARK."""
    text = re.sub(r"\\begin\{figure\}.*?\\end\{figure\}", " ", text, flags=re.DOTALL)
    text = re.sub(r"\\begin\{longtable\}.*?\\end\{longtable\}", " ", text, flags=re.DOTALL)
    text = re.sub(r"\\[a-zA-Z]+\*?", " ", text)
    text = text.replace("{", " ").replace("}", " ").replace("$", " ")
    # Give the hole a single-letter stand-in before flattening, so it reads as a
    # word boundary.  Emitting the raw sentinel here would work too, but then the
    # aligner's context strings contain a control character and are unreadable.
    text = text.replace("\ufffd", f" {MATH_HOLE} ")
    return plain(text).replace(MATH_HOLE.lower(), MATH_HOLE)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", default=None,
                    help="printed page range, e.g. 4-51 (default: whole PDF). "
                         "Printed page N is the PDF page whose footer reads N; "
                         "there is usually an unnumbered title page first.")
    ap.add_argument("--chunks", help="directory of chunk .tex files to align")
    ap.add_argument("--out", help="write the report here instead of stdout")
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    if args.pages:
        lo, _, hi = args.pages.partition("-")
        lo, hi = int(lo), int(hi or lo)
    else:
        lo, hi = 0, doc.page_count - 1

    lines: list[str] = []
    vocab: Counter = Counter()
    # Printed page N sits at PDF index N when page 0 is an unnumbered title.
    for printed in range(lo, hi + 1):
        idx = printed
        if idx >= doc.page_count:
            break
        ref, symbols = page_reference(doc[idx])
        vocab.update(symbols)
        lines.append(f"\n===== printed page {printed} (pdf index {idx}) =====")
        lines.append(ref.strip())

    lines.append("\n===== symbol vocabulary =====")
    for sym, n in vocab.most_common():
        lines.append(f"  {sym:>10s}  {n}")

    if args.chunks:
        chunks = Path(args.chunks)
        reference = plain(" ".join(lines))
        for path in sorted(chunks.glob("*.tex")):
            text = path.read_text()
            if "\ufffd" not in text:
                continue
            stream = chunk_stream(text)
            lines.append(f"\n===== {path.name}: proposed recoveries =====")
            for m in re.finditer(re.escape(MATH_HOLE), stream):
                before = stream[max(0, m.start() - 70):m.start()]
                after = stream[m.end():m.end() + 70]
                hit = difflib.SequenceMatcher(None, before[-40:] + " " + after[:40],
                                              reference, autojunk=False) \
                    .find_longest_match(0, len(before[-40:]) + 1 + len(after[:40]),
                                        0, len(reference))
                window = reference[max(0, hit.b - 30):hit.b + hit.size + 30] if hit.size > 12 else "?"
                note = "" if hit.size > 20 else "   <- LOW CONFIDENCE, read the PDF"
                lines.append(f"  ...{before[-45:]} [??] {after[:45]}...")
                lines.append(f"      pdf~ {window[:90]}{note}")

    report = "\n".join(lines)
    if args.out:
        Path(args.out).write_text(report)
        print(f"wrote {args.out} ({len(report.splitlines())} lines)")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
