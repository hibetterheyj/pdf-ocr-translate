#!/usr/bin/env python3
"""Apply the PDF-verified corrections to the merged source `main.tex`.

Everything here was read against `pdf_pages/` before being written down; the PDF
page each correction came from is in the comment beside it.  Two families:

  1. MinerU dropped 24 math symbols (U+FFFD) set in `XCharterMathMI`.  The PDF's
     span-font data recovers them (`recover_math_glyphs.py` -> `math_worklist.txt`),
     but a wrong symbol still compiles, so each was checked in its sentence.
  2. Math that survived as *raw Unicode* (`×`, `≈`) or as VLM pandoc escapes
     (`\\textbackslash times`) needs converting to real math mode.

Run after `build_hybrid.py` and `fix_ocr_artifacts.py`, before splitting.

Usage:  fix_lost_math.py main.tex          # in place
"""
from __future__ import annotations

import argparse
import pathlib
import sys

# (old, new, source PDF page) — old strings must match verbatim.
REPLACEMENTS: list[tuple[str, str, str]] = [
    # -- §2 Architecture, p.4 -------------------------------------------------
    ("It stacks \ufffd hybrid blocks, each structured with \ufffd",
     "It stacks $M$ hybrid blocks, each structured with $N$", "p.4"),
    ("The sliding window size \ufffd used in MiMo-V2.6 is 128",
     "The sliding window size $W$ used in MiMo-V2.6 is 128", "p.4"),
    # -- §4.1, p.8 ------------------------------------------------------------
    ("group size \ufffd=16", "group size $G=16$", "p.8"),
    ("where \ufffd denotes the importance sampling ratio, \ufffd is the token-level",
     "where $r$ denotes the importance sampling ratio, $M$ is the token-level", "p.8"),
    ("mask, and \ufffd is the advantage.", "mask, and $A$ is the advantage.", "p.8"),
    ("every prompt \ufffd drawn from the", "every prompt $q$ drawn from the", "p.8"),
    ("group of \ufffd candidate solutions \\{\ufffd\ufffd\\}.",
     "group of $G$ candidate solutions $\\{o_i\\}$.", "p.8"),
    ("the collected tokens update \ufffd through the gradient",
     "the collected tokens update $\\theta$ through the gradient", "p.8"),
    # -- §4.3.3, p.18 ---------------------------------------------------------
    ("For trajectory \ufffd, let", "For trajectory $i$, let", "p.18"),
    ("binary reward after hack correction, \ufffd\u00af its group mean,",
     "binary reward after hack correction, $\\bar{R}$ its group mean,", "p.18"),
    # MinerU read the bar accent as a hat; the same symbol is \\bar{p} elsewhere.
    ("\\(A _ { i } = R _ { i } - \\hat { R }\\) its sequence-level advantage",
     "\\(A _ { i } = R _ { i } - \\bar { R }\\) its sequence-level advantage", "p.18"),
    # -- §4.3.3, p.20 ---------------------------------------------------------
    ("For each prompt \ufffd with \ufffd sampled rollouts",
     "For each prompt $q$ with $G$ sampled rollouts", "p.20"),
    # "ethethreshold" is the stray tilde glyph from the preceding \\widetilde{R}
    # bleeding into the next word; the PDF reads "threshold $A$ is a separate".
    ("the ethreshold \ufffd is a separate", "the threshold $A$ is a separate", "p.20"),
    # -- §7.1 Prefix-Conditioned OPD, p.25 ------------------------------------
    ("A source trajectory with \ufffd assistant-turn decision\npoints yields \ufffd complete history prefixes",
     "A source trajectory with $k$ assistant-turn decision\npoints yields $k$ complete history prefixes", "p.25"),
    ("A trajectory with \ufffd assistant turns provides \ufffd\ncomplete history prefixes",
     "A trajectory with $k$ assistant turns provides $k$\ncomplete history prefixes", "p.25"),
    # -- §6.3 Sample Mixer, p.30-31 -------------------------------------------
    ("For source \ufffd, let", "For source $i$, let", "p.30"),
    ("The shared factor \ufffd keeps the demand-weighted mean",
     "The shared factor $c$ keeps the demand-weighted mean", "p.30"),
    ("accepted from source \ufffd", "accepted from source $i$", "p.31"),
    # -- Table 1, p.6: the VLM pass wrote pandoc escapes for the times sign ----
    ("Patch Size (T \\textbackslash times H \\textbackslash times W)",
     "Patch Size ($T \\times H \\times W$)", "p.6"),
    ("2 \\textbackslash times 16 \\textbackslash times 16}",
     "$2 \\times 16 \\times 16$}", "p.6"),
    ("2 \\textbackslash times 2}", "$2 \\times 2$}", "p.6"),
    # -- Abstract, p.1: a raw U+223C survives as text and does not exist in the
    #    Latin Modern text font, so it prints as nothing (log: "Missing
    #    character: There is no ∼").  It is the range dash in "2.7∼3.7B".
    ("2.7∼3.7B", "$2.7\\sim$3.7B", "p.1"),
    # -- Reference list, p.41: pymupdf reports this one URL with a space between
    #    every glyph, and MinerU copied the spacing through.  The PDF's own link
    #    annotation gives the real target, so it is written back verbatim.
    ("h t t p s : / / g i t h u b . c o m / v l l m- p\n"
     "r oj e c t / h u m m i n g / r e l e a s e s / t a g / v 0 . 1 . 1 5,",
     "https://github.com/vllm-project/humming/releases/tag/v0.1.15,", "p.41"),
    # -- Equation (1), p.8: the two-stage pass mangled the expectation's
    #    subscript into `\bigcup_{d}_{\mathcal{D}_d}` (a double subscript, which
    #    is a hard LaTeX error) and renamed the rollout samples from `o_i` to
    #    `\mathcal{D}_i`. The PDF reads `∪_d D_d, {o_i}^G_{i=1} ~ μ_θold (·|q)`;
    #    the VLM pass has it right, so its transcription is used verbatim.
    (
        "\\mathcal { L } ( \\theta ) = - \\mathbb { E } _ { q \\sim \\bigcup _ { d } "
        "_ { \\mathbf { \\mathcal { D } } _ { d } } , \\{ \\mathbf { \\mathcal { D } } "
        "_ { i } \\} _ { i = 1 } ^ { G } \\sim \\mu _ { \\theta _ { \\mathrm { o l d } } } "
        "( \\cdot | q ) } \\left[ \\frac { 1 } { \\sum _ { i = 1 } ^ { G } | o _ { i } | } "
        "\\sum _ { i = 1 } ^ { G } \\sum _ { t = 1 } ^ { | o _ { i } | } r _ { i , t } "
        "M _ { i , t } A _ { i } \\log \\pi _ { \\theta } ( o _ { i , t } \\mid q , "
        "o _ { i , < t } ) \\right] ,\\tag{1}",
        "\\mathcal {L} (\\theta) = - \\mathbb {E} _ {q \\sim \\bigcup_ {d} "
        "\\mathcal {D} _ {d}, \\{o _ {i} \\} _ {i = 1} ^ {G} \\sim "
        "\\mu_ {\\theta_ {\\mathrm{old}}} (\\cdot | q)} \\left[ \\frac {1}"
        "{\\sum_ {i = 1} ^ {G} | o _ {i} |} \\sum_ {i = 1} ^ {G} \\sum_ {t = 1} ^ "
        "{| o _ {i} |} r _ {i, t} M _ {i, t} A _ {i} \\log \\pi_ {\\theta} "
        "(o _ {i, t} \\mid q, o _ {i, < t}) \\right],\\tag{1}",
        "p.8",
    ),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tex")
    args = ap.parse_args()

    path = pathlib.Path(args.tex)
    text = path.read_text(encoding="utf-8")
    before = text.count("\ufffd")
    applied, missed = 0, []

    for old, new, page in REPLACEMENTS:
        if old not in text:
            missed.append((page, old))
            continue
        text = text.replace(old, new)
        applied += 1

    path.write_text(text, encoding="utf-8")
    after = text.count("\ufffd")
    print(f"applied {applied}/{len(REPLACEMENTS)} replacements; "
          f"U+FFFD {before} -> {after}")
    for page, old in missed:
        print(f"  MISS [{page}] {old[:70]!r}", file=sys.stderr)
    return 1 if missed or after else 0


if __name__ == "__main__":
    raise SystemExit(main())
