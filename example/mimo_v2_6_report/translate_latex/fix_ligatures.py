#!/usr/bin/env python3
"""Restore the ligature glyphs MinerU swallowed.

Both OCR passes drop the `f` that belongs to an `ff`/`fi`/`fl` ligature, so
"effective" becomes "efective", "offline" becomes "ofline", "buffer" becomes
"bufer".  The damage is invisible in isolation — the result is still a
word-shaped string and nothing in LaTeX complains.

Confirmed against the PDF text layer in both directions: the broken spelling
does **not** occur in `pdf_pages/*.txt`, the repaired one does.  That two-sided
test is what keeps this list honest.  A dictionary-only scan is not enough in
either direction:

  * it proposes repairs for surnames and acronyms that were never broken
    ("Guo" -> "gulo", "SFT" -> "sift");
  * it *misses* real losses whenever the repair is an inflected form the system
    word list lacks — `/usr/share/dict/words` has no "efforts", so the scan
    above silently dropped `eforts -> efforts` until the PDF was used as the
    dictionary instead.

Run before splitting; the chunks inherit the fix.

The word list below is the set found in one report (MiMo-V2.6, 97 occurrences
across 33 forms).  It is document-specific in the same way a table-width plan
is: re-derive it per document with the two-sided PDF test described above
rather than assuming these words appear.  The scan is cheap — a dictionary pass
over the prose, then confirm each candidate against `pdf_pages/*.txt`.

Usage:  fix_ligatures.py main.tex          # in place
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

# Broken -> repaired, lower case.  Applied with the first letter's case
# preserved (Efective -> Effective).
LIGATURES: dict[str, str] = {
    # ff
    "efective": "effective",
    "efectively": "effectively",
    "efectiveness": "effectiveness",
    "efects": "effects",
    "efect": "effect",
    "eficient": "efficient",
    "eficiency": "efficiency",
    "efort": "effort",
    "eforts": "efforts",
    "ofer": "offer",
    "sufers": "suffers",
    "ofline": "offline",
    "ofloads": "offloads",
    "ofloading": "offloading",
    "coeficient": "coefficient",
    "sufix": "suffix",
    "ofset": "offset",
    "trafic": "traffic",
    # ff inside inflections the system word list does not carry
    "diferent": "different",
    "diferences": "differences",
    "diferential": "differential",
    "difer": "differ",
    "dificult": "difficult",
    "dificulty": "difficulty",
    "difusion": "diffusion",
    "bufer": "buffer",
    "suficiently": "sufficiently",
    "insuficient": "insufficient",
    # fi in the reference author list
    "laufer": "lauffer",
    "sutclife": "sutcliffe",
    "muennighof": "muennighoff",
}

# Forms whose internal capitalisation the generic case-preserving rule would
# mangle ("OficeQA" must not become "Officeqa"), applied verbatim first.
EXACT: dict[str, str] = {
    "OficeQA": "OfficeQA",
    "Oficeqa": "Officeqa",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tex")
    args = ap.parse_args()

    path = pathlib.Path(args.tex)
    text = path.read_text(encoding="utf-8")
    total, detail = 0, []

    def counted(broken: str, fixed: str, n: int) -> None:
        nonlocal total
        if n:
            detail.append((broken, fixed, n))
            total += n

    for broken, fixed in EXACT.items():
        pattern = re.compile(r"(?<![\\A-Za-z])" + re.escape(broken) + r"(?![A-Za-z])")
        text, n = pattern.subn(fixed, text)
        counted(broken, fixed, n)

    for broken, fixed in LIGATURES.items():
        # Never inside a control sequence (\efective) or glued to a word.
        pattern = re.compile(r"(?<![\\A-Za-z])" + broken + r"(?![A-Za-z])", re.I)

        def repl(m: re.Match, fixed: str = fixed) -> str:
            got = m.group(0)
            if got.isupper():
                return fixed.upper()
            if got[0].isupper():
                return fixed[0].upper() + fixed[1:]
            return fixed

        text, n = pattern.subn(repl, text)
        counted(broken, fixed, n)

    path.write_text(text, encoding="utf-8")
    for broken, fixed, n in sorted(detail, key=lambda x: -x[2]):
        print(f"  {n:>3}x  {broken} -> {fixed}")
    print(f"restored {total} ligature losses across {len(detail)} forms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
