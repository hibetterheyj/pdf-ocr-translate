#!/usr/bin/env python3
"""Apply the CJK-safe preamble edits to `main.tex`.

Four edits to MinerU's stock preamble, each placement-sensitive (see the
skill's `assets/preamble_patches_cn.tex` for why):

  * put ``Songti SC`` / ``Heiti SC`` at the head of the CJK font chain so the
    document builds on a stock macOS box, and set them as the CJK main/sans
    fonts — these two are *preamble-only* commands;
  * load ``xurl`` before ``hyperref`` so a repaired reference URL can break;
  * add ``ragged2e`` and a wrappable ``L{}`` column type, used later to keep
    the wide benchmark tables inside the margin;
  * replace the OCR ``\\section{<paper title>}`` with the header logo plus a
    centred title block, and drop the stray "Xiaomi MIMO" line MinerU read out
    of that logo.

Applied to ``main.tex`` (not to ``parts/``) so re-splitting regenerates the
preamble chunk with these edits already in place.  Idempotent.

Usage:  patch_preamble.py main.tex
"""
from __future__ import annotations

import argparse
from pathlib import Path

FONT_CHAIN_MARKER = r"\IfFontExistsTF{Songti SC}"

OLD_FONTS = r"""\setotherlanguages{english}
\IfFontExistsTF{Source Han Serif CN}
{\newfontfamily\chinesefont{Source Han Serif CN}}
{\IfFontExistsTF{Noto Serif CJK SC}
  {\newfontfamily\chinesefont{Noto Serif CJK SC}}
  {\IfFontExistsTF{SimSun}
    {\newfontfamily\chinesefont{SimSun}}
    {\IfFontExistsTF{FangSong}
      {\newfontfamily\chinesefont{FangSong}}
      {\newfontfamily\chinesefont{Arial Unicode MS}}
}}}"""

NEW_FONTS = r"""\setotherlanguages{english}
\IfFontExistsTF{Songti SC}
{\newfontfamily\chinesefont{Songti SC}}
{\IfFontExistsTF{Source Han Serif CN}
{\newfontfamily\chinesefont{Source Han Serif CN}}
{\IfFontExistsTF{Noto Serif CJK SC}
  {\newfontfamily\chinesefont{Noto Serif CJK SC}}
  {\IfFontExistsTF{SimSun}
    {\newfontfamily\chinesefont{SimSun}}
    {\IfFontExistsTF{FangSong}
      {\newfontfamily\chinesefont{FangSong}}
      {\newfontfamily\chinesefont{Arial Unicode MS}}
}}}}"""

PREAMBLE_FONTS = r"""\setCJKmainfont{Songti SC}
\setCJKsansfont{Heiti SC}

\IfFontExistsTF{Times New Roman}"""

OLD_HYPERREF = r"""\usepackage{ucharclasses}
\usepackage{hyperref}"""

NEW_HYPERREF = r"""\usepackage{ucharclasses}
\usepackage{xurl}
\usepackage{hyperref}"""

TABLE_COLS = r"""\usepackage{ragged2e}
\newcolumntype{L}[1]{>{\RaggedRight\arraybackslash}p{#1}}
\newcolumntype{C}[1]{>{\Centering\arraybackslash}p{#1}}
% longtable typesets its \caption in a box \LTcapwidth wide, defaulting to 4in
% (~289pt) regardless of how wide the table is.  In a ~499pt table that renders
% as a narrow, centred caption that lines up with neither the table's left edge
% nor the body text.  The report's own captions span the full text block.
\setlength{\LTcapwidth}{\textwidth}
% Both longtable and the standard caption code centre a caption that fits on one
% line and justify longer ones, so a short caption lands in the middle of the
% page while a long one starts at the margin.  The report left-aligns every
% caption and sets the label in bold with a quad after it; match that, for
% tables and figures alike.
\usepackage{caption}
\captionsetup{labelfont=bf, labelsep=quad, justification=raggedright,
              singlelinecheck=false}

\author{}"""

OLD_TITLE = r"""Xiaomi MIMO

\section{MiMo-V2.6: Scaling Reinforcement Learning Towards
Self-Improvement}\label{mimo-v2.6-scaling-reinforcement-learning-towards-self-improvement}

LLM-Core Xiaomi"""

NEW_TITLE = r"""\begin{center}
\includegraphics[width=0.34\linewidth]{images_hi/title_logo.png}
\vspace{1.0em}

{\LARGE MiMo-V2.6: Scaling Reinforcement Learning\\[0.25em] Towards Self-Improvement\par}
\vspace{0.5em}
{\large MiMo-V2.6：面向自我改进的强化学习扩展\par}
\vspace{0.8em}
{\normalsize LLM-Core Xiaomi\par}
\end{center}"""

CAPTION_NAMES = r"""\renewcommand{\figurename}{图}
\renewcommand{\tablename}{表}"""


CAPTION_WIDTH_ANCHOR = r"\newcolumntype{C}[1]{>{\Centering\arraybackslash}p{#1}}"
CAPTION_WIDTH = CAPTION_WIDTH_ANCHOR + r"""
\setlength{\LTcapwidth}{\textwidth}"""

CAPTION_STYLE_ANCHOR = r"\setlength{\LTcapwidth}{\textwidth}"
CAPTION_STYLE = CAPTION_STYLE_ANCHOR + "\n" + r"""\usepackage{caption}
\captionsetup{labelfont=bf, labelsep=quad, justification=raggedright,
              singlelinecheck=false}"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tex", nargs="?", default="main.tex")
    args = ap.parse_args()
    path = Path(args.tex)
    text = path.read_text(encoding="utf-8")
    changed = 0

    def patch(marker: str, old: str, new: str, label: str) -> None:
        nonlocal text, changed
        if marker in text:
            print(f"{label}: already patched")
        elif old in text:
            text = text.replace(old, new, 1)
            changed += 1
            print(f"{label}: patched")
        else:
            raise SystemExit(f"{label}: anchor not found — inspect {path.name}")

    patch(FONT_CHAIN_MARKER, OLD_FONTS, NEW_FONTS, "font chain")
    patch(r"\setCJKmainfont{Songti SC}", r"\IfFontExistsTF{Times New Roman}",
          PREAMBLE_FONTS, "CJK main/sans font")
    patch(r"\usepackage{xurl}", OLD_HYPERREF, NEW_HYPERREF, "xurl")
    patch(r"\newcolumntype{L}", r"\author{}", TABLE_COLS, "table column type")
    patch(r"\setlength{\LTcapwidth}", CAPTION_WIDTH_ANCHOR, CAPTION_WIDTH,
          "table caption width")
    patch(r"\usepackage{caption}", CAPTION_STYLE_ANCHOR, CAPTION_STYLE,
          "caption style")
    patch("MiMo-V2.6：面向自我改进的强化学习扩展", OLD_TITLE, NEW_TITLE, "title block")

    if r"\renewcommand{\figurename}{图}" in text:
        print("caption names: already set")
    elif r"\begin{document}" in text:
        text = text.replace(r"\begin{document}",
                            "\\begin{document}\n\n" + CAPTION_NAMES, 1)
        changed += 1
        print("caption names: set")
    else:
        raise SystemExit("\\begin{document} not found")

    if changed:
        path.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
