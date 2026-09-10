#!/usr/bin/env python3
"""Post-normalization fixes for main_cn.tex.

``normalize_heading_levels.py`` handles the numbered body headings but stops
short of this document's appendix conventions and of one heading that was
already translated to Chinese before it ran.  This pass:

  * retranslates headings whose Chinese form contains Latin the normalizer's
    patterns missed (``\\section{General Infrastructures}`` -> ``通用基础设施``);
  * turns ``\\section*{References}`` into ``\\section*{参考文献}``;
  * drops the bare ``\\subsection{附录}`` wrapper, which carried no content of
    its own — the appendix is entered directly through its lettered sections;
  * promotes the lettered appendix headings ``A.``/``B.``/``C.`` to ``\\section``
    and strips the letter from the title (the letter survives in the label);
  * demotes the sub-headings underneath them (``B.1.`` -> ``\\subsection``)
    and strips their letter.number prefix.

Run on the merged main_cn.tex after the stock normalizer.  Idempotent.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

# Latin headings the stock normalizer left untranslated.
RETRANSLATE = {
    r"\section{General Infrastructures}": r"\section{通用基础设施}",
    r"\section{Pre-Training}": r"\section{预训练}",
    r"\section{Post-Training}": r"\section{后训练}",
}

REFERENCES_OLD = r"\section*{References}\label{references}"
REFERENCES_NEW = r"\section*{参考文献}\label{references}"

APPENDIX_WRAPPER = "\\subsection{附录}\\label{appendix}\n\n"

LETTERED = re.compile(r"\\subsection\{([A-Z])\.\s+([^}]*)\}")
LETTERED_SUB = re.compile(r"\\subsection\{([A-Z])\.(\d+)\.\s+([^}]*)\}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tex", nargs="?", default="main_cn.tex")
    args = ap.parse_args()
    path = Path(args.tex)
    text = path.read_text()
    before = text

    for old, new in RETRANSLATE.items():
        text = text.replace(old, new)

    text = text.replace(REFERENCES_OLD, REFERENCES_NEW)

    text = text.replace(APPENDIX_WRAPPER, "")
    text = re.sub(r"\\subsection\{附录\}\\label\{appendix\}[ \t]*\n*", "", text)

    # B.1 -> \subsection, before the broader A./B./C. rule so it does not fire on them.
    text = LETTERED_SUB.sub(lambda m: f"\\subsection{{{m.group(3)}}}", text)
    text = LETTERED.sub(lambda m: f"\\section{{{m.group(2)}}}", text)

    if text != before:
        path.write_text(text)
    changed = sum(1 for a, b in zip(before.split("\n"), text.split("\n")) if a != b)
    print(f"post-normalize fixes applied ({changed} line(s) changed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
