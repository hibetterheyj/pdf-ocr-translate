#!/usr/bin/env python3
"""Replace the U+FFFD symbols MinerU dropped, using the source PDF as the key.

MinerU cannot map the PDF's math-italic glyphs (XCharterMathMI, Unicode
Mathematical Italic) and writes U+FFFD instead.  pymupdf recovers those glyphs
with their font names, so every damaged site has an authoritative reading; the
table below was read off the PDF text layer with span-level font information.
Extract the glyphs with the skill's ``scripts/recover_math_glyphs.py``, which prints
each symbol in its sentence so it can be checked against the prose; the ``--pdf`` page
for each group is noted alongside it.

Each entry is an exact substring replacement against the chunk file.  Run after
``build_parts.sh`` (which regenerates parts/) and before translation.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

F = "�"

# chunk -> [(exact damaged substring, exact replacement), ...]
FIXES: dict[str, list[tuple[str, str]]] = {
    # pdfpage 6: "where 𝐿 is the number of layers"
    "01_body.tex": [
        (f"where {F} is the number", "where $L$ is the number"),
    ],
    # pdfpage 9-10: eq (1) uses 𝐶/𝑍; CSA2 compression ratio is 𝑚
    "02_2__architecture.tex": [
        (f"where {F} and {F} represent", "where $C$ and $Z$ represent"),
        (f"for any layer {F}, the local", "for any layer $l$, the local"),
        (f"where every {F} tokens", "where every $m$ tokens"),
        (f"compression ratio of {F} produces", "compression ratio of $m$ produces"),
        (f"each main KV entry from 2{F} original", "each main KV entry from $2m$ original"),
        (f"positions of these 2{F} entries", "positions of these $2m$ entries"),
    ],
    # pdfpage 11-13: mHC notation (n residual streams, d hidden dim, X_l coefficients)
    "03_body.tex": [
        (f"state of the ({F}/2)-th layer", "state of the $(L/2)$-th layer"),
        (f"which maintains {F}\nresidual streams", "which maintains $n$\nresidual streams"),
        (f"where {F} is the block index and {F} is the hidden dimension",
         "where $l$ is the block index and $d$ is the hidden dimension"),
        (f"coefficients predicted from {F}{F}. The coefficient predictor",
         "coefficients predicted from $X_l$. The coefficient predictor"),
        (f"Such a map requires ({F} + 1){F} reads", "Such a map requires $(n + 1)d$ reads"),
        (f"read \\(( n + 1 ) d ,\\) , {F}{F} and {F}{F} values", "read $((n + 1)d$, $nd$ and $nd$ values"),
        (f"would require (3{F} + 2){F} activation", "would require $(3n + 2)d$ activation"),
        (f"Each tile of {F}{F} can therefore", "Each tile of $X_l$ can therefore"),
        (f"mHC with (3{F} + 2){F} activation", "mHC with $(3n + 2)d$ activation"),
        (f"attaining the ({F} + 1){F}\nreads and ({F} + 1){F} writes",
         "attaining the $(n + 1)d$\nreads and $(n + 1)d$ writes"),
    ],
    # pdfpage 13-16: Engram (N-gram orders, hidden dim n, Muon constants gamma/epsilon)
    "04_2_4_2__engram.tex": [
        (f"Each module uses {F}-gram orders", "Each module uses $N$-gram orders"),
        (f"hidden dimension by {F}.", "hidden dimension by $n$."),
        (f"learning-rate correction {F}, numerical constants {F} and",
         r"learning-rate correction $\gamma$, numerical constants $\epsilon$ and"),
        (f"7: if {F} is odd then", "7: if $k$ is odd then"),
    ],
    # pdfpage 16-17: overlap schedule (V/T features, A/C overlap) and IO criterion (N, rho, C)
    "05_3__general_infrastructures.tex": [
        (f"where {F} and {F} denote the visual", "where $V$ and $T$ denote the visual"),
        (f"overlap of computation {F}\nwith communication", "overlap of computation $A$\nwith communication"),
        (f"where {F} is the token count, \\(\\rho\\) the raw bytes per token, {F} the per-token",
         r"where $N$ is the token count, $\rho$ the raw bytes per token, $C$ the per-token"),
        (f"Since {F} cancels, the criterion involves only pertoken quantities ({F} and {F})",
         r"Since $N$ cancels, the criterion involves only per-token quantities ($\rho$ and $C$)"),
    ],
    # pdfpage 19: SWA bounded replay positions s, i with window W
    "06_body.tex": [
        (f"the SWA KV of {F} layers", "the SWA KV of $L$ layers"),
        (f"for a replay starting at position {F}, a query at position {F} attends to SWA keys in -max({F}, {F} − {F} + 1), {F} .",
         r"for a replay starting at position $s$, a query at position $i$ attends to SWA keys" "\n" r"in $[\max(s, i - W + 1),\ i]$."),
    ],
    # pdfpage 21: "hidden dimension 𝑑 to 5120"
    "07_4_2__pre-training_setups.tex": [
        (f"hidden dimension {F}\nto 5120", "hidden dimension $d$\nto 5120"),
    ],
    # pdfpage 29-30: controllable reasoning effort — b, x, j and the k/tau/lambda schedule
    "09_body.tex": [
        (f"a scalar effort level {F} as an explicit", "a scalar effort level $b$ as an explicit"),
        (f"each training prompt {F}, we sample", "each training prompt $x$, we sample"),
        (f"Here, {F} indexes the responses", "Here, $j$ indexes the responses"),
        (f"at effort level {F}. Responses sharing", "at effort level $b$. Responses sharing"),
        (f"reward depend on {F}. Specifically", "reward depend on $b$. Specifically"),
        (f"minimum value of B, $\\Delta${F} is the average", "minimum value of B, $\\Delta b$ is the average"),
        (f"training effort levels, and {F} controls", r"training effort levels, and $\lambda$ controls"),
        (f"Increasing {F} by {F} multiplies", r"Increasing $b$ by $\tau$ multiplies"),
        (f"a smaller {F} causes", r"a smaller $\tau$ causes"),
        (f"parameterization of {F}({F}).", r"parameterization of $k(b)$."),
        (f"the scalar {F} provides", "the scalar $b$ provides"),
        (f"By varying {F}, a single model", "By varying $b$, a single model"),
        (f"effort values of {F} = 100, {F} = 75, and {F} = 50", "effort values of $b = 100$, $b = 75$, and $b = 50$"),
        (f"underlying scalar effort values {F}.", "underlying scalar effort values $b$."),
    ],
    # pdfpage 32: "temperature and top-𝑝 of 1.0"
    "10_body.tex": [
        (f"temperature and top-{F} of 1.0", "temperature and top-$p$ of 1.0"),
    ],
    # pdfpage 35: scaffold table note, N samples per task
    "11_body.tex": [
        (f"All scaffolds use {F} = 8 samples", "All scaffolds use $N = 8$ samples"),
        (f"and {F} = 3 on Terminal-Bench", "and $N = 3$ on Terminal-Bench"),
    ],
    # pdfpage 39: Polyak reference convergence rate O(1/k^2)
    "12_body.tex": [
        (f"convergence rate {F}(1/{F}2)", r"convergence rate $O(1/k^2)$"),
    ],
    # pdfpage 50: appendix C derivation — x, b, tau, lambda, and ℓ*_x(b).
    # Both "controls the rate of penalty decay" sites use tau, not lambda:
    # eq (10) defines tau = lambda * delta_b and tau is the decay rate.
    "14_body.tex": [
        (r"level \(b _ { \mathrm { m i n } }\) and " + F + " controls",
         r"level \(b _ { \mathrm { min } }\) and $\tau$ controls"),
        (f"a fixed problem {F}. Let", "a fixed problem $x$. Let"),
        (f"preferred reasoning $\\ell$∗{F} ({F}) by", r"preferred reasoning $\ell_x^*(b)$ by"),
        (f"is independent of {F}. Thus", "is independent of $b$. Thus"),
        (f"shorter reasoning, while {F} controls", r"shorter reasoning, while $\tau$ controls"),
        ("eight reasoningintensive", "eight reasoning-intensive"),
    ],
}

# URLs where OCR replaced a line break with a space.  A space inside a URL is
# always an artifact; xurl (preamble) lets the repaired long URL wrap.
URL_REPAIRS: dict[str, list[tuple[str, str]]] = {
    "12_body.tex": [
        ("https://doi. org/10.48550/arXiv.2412.19437",
         "https://doi.org/10.48550/arXiv.2412.19437"),
        ("https://doi.org/10.48550/arXiv.2405.04 434",
         "https://doi.org/10.48550/arXiv.2405.04434"),
        ("https://github.com/deepseek-a i/deepseek-harness",
         "https://github.com/deepseek-ai/deepseek-harness"),
    ],
}

# Non-ASCII math symbols MinerU left in text mode; XeLaTeX has no glyph for them.
UNICODE_MATH: dict[str, list[tuple[str, str]]] = {
    "04_2_4_2__engram.tex": [("⊲", r"$\triangleleft$")],          # algorithm comment marker
    "05_3__general_infrastructures.tex": [("∇", r"$\nabla$")],     # gradient operator
}


def flexible(pattern: str) -> re.Pattern[str]:
    """Match ``pattern`` allowing any whitespace run where it has whitespace.

    The chunk files are hard-wrapped, so the same sentence carries different
    newlines in different chunks; every literal space therefore matches ``\\s+``.
    """
    # Split on whitespace *before* escaping: Python 3.12's re.escape escapes the
    # space itself, which would survive as a literal backslash-space in the regex.
    parts = [re.escape(tok) for tok in pattern.split()]
    return re.compile(r"\s+".join(parts))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", required=True)
    args = ap.parse_args()
    parts = Path(args.parts)

    applied = missed = 0
    for chunk, pairs in FIXES.items():
        path = parts / chunk
        if not path.exists():
            print(f"MISSING FILE {chunk}")
            continue
        text = path.read_text()
        for old, new in pairs:
            rx = flexible(old)
            match = rx.search(text)
            if match:
                text = text[:match.start()] + new + text[match.end():]
                applied += 1
            else:
                missed += 1
                print(f"  NOT FOUND in {chunk}: {old!r}")
        path.write_text(text)

    for chunk, pairs in URL_REPAIRS.items():
        path = parts / chunk
        text = path.read_text()
        for old, new in pairs:
            if old in text:
                text = text.replace(old, new)
                applied += 1
                print(f"  {chunk}: joined broken URL")
        path.write_text(text)

    for chunk, pairs in UNICODE_MATH.items():
        path = parts / chunk
        if not path.exists():
            continue
        text = path.read_text()
        for old, new in pairs:
            if old in text:
                count = text.count(old)
                text = text.replace(old, new)
                applied += 1
                print(f"  {chunk}: {old!r} -> {new} ({count}x)")
        path.write_text(text)

    remaining = {
        p.name: p.read_text().count(F)
        for p in sorted(parts.glob("*.tex"))
        if F in p.read_text()
    }
    print(f"applied {applied} replacements, {missed} not found")
    print(f"remaining U+FFFD: {remaining if remaining else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
