#!/usr/bin/env python3
"""Apply the CJK-safe preamble edits to main.tex.

Two changes to MinerU's stock preamble:

  * prepend ``Songti SC`` / ``Heiti SC`` to the CJK font fallback chain and set
    them as the CJK main/sans fonts, so the document compiles on macOS without
    installing Source Han or Noto CJK;
  * replace the OCR ``\\section{<paper title>}`` with a centered title block and
    promote Abstract to an unnumbered ``\\section*{摘要}``.

Applied to main.tex (not to parts/) so that ``build_parts.sh`` regenerates the
preamble chunk with these edits already in place.  Idempotent.
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
}}}}
% \setCJKmainfont and \setCJKsansfont are preamble-only commands; the patcher
% inserts them just above the english-font block, after the CJK chain.
"""

# Preamble-only CJK font selection, inserted before the English font block.
PREAMBLE_FONTS = r"""\setCJKmainfont{Songti SC}
\setCJKsansfont{Heiti SC}

\IfFontExistsTF{Times New Roman}"""

OLD_TITLE = r"""\section{DeepSeek-V4.1-Flash: Pushing the Limits of KV Cache
Compression}\label{deepseek-v4.1-flash-pushing-the-limits-of-kv-cache-compression}

DeepSeek-AI research@deepseek.com

\subsection{Abstract}\label{abstract}"""

NEW_TITLE = r"""\begin{center}
{\LARGE DeepSeek-V4.1-Flash\par}
\vspace{0.5em}
{\large 突破 KV 缓存压缩的极限\par}
\vspace{0.8em}
{\normalsize DeepSeek-AI\quad research@deepseek.com\par}
\end{center}

\section*{摘要}\label{abstract}"""

CAPTION_NAMES = r"""\renewcommand{\figurename}{图}
\renewcommand{\tablename}{表}"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tex", nargs="?", default="main.tex")
    args = ap.parse_args()
    path = Path(args.tex)
    text = path.read_text()

    changed = 0
    if FONT_CHAIN_MARKER in text:
        print("font chain: already patched")
    elif OLD_FONTS in text:
        text = text.replace(OLD_FONTS, NEW_FONTS, 1)
        changed += 1
        print("font chain: patched")
    else:
        raise SystemExit("preamble font chain not found — inspect main.tex")

    if r"\setCJKmainfont{Songti SC}" in text:
        print("CJK main/sans font: already set")
    elif r"\IfFontExistsTF{Times New Roman}" in text:
        text = text.replace(r"\IfFontExistsTF{Times New Roman}", PREAMBLE_FONTS, 1)
        changed += 1
        print("CJK main/sans font: set")
    else:
        raise SystemExit("english-font block not found — inspect main.tex")

    if "突破 KV 缓存压缩的极限" in text:
        print("title block: already patched")
    elif OLD_TITLE in text:
        text = text.replace(OLD_TITLE, NEW_TITLE, 1)
        changed += 1
        print("title block: patched")
    else:
        raise SystemExit("title / abstract block not found — inspect main.tex")

    if r"\renewcommand{\figurename}{图}" in text:
        print("caption names: already set")
    elif r"\section*{摘要}" in text:
        text = text.replace(r"\section*{摘要}", r"\section*{摘要}" + "\n\n" + CAPTION_NAMES, 1)
        changed += 1
        print("caption names: set")
    else:
        raise SystemExit("abstract heading not found — inspect main.tex")

    if changed:
        path.write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
