# Translation Policy

Apply these rules unless the user overrides them.

## What To Translate

- Translate all normal prose.
- Translate section, subsection, and subsubsection titles.
- Translate necessary figure and table captions.
- Translate explanatory comments around code, pseudocode, and algorithms only when needed.

## What To Preserve

- Preserve formulas exactly.
- Preserve LaTeX environments and commands unless they are structurally broken.
- Preserve citation keys, bibliography entries, and author names unless the user explicitly asks otherwise.
- Preserve technical identifiers such as model names, library names, benchmark names, and file names.

## Common Exemptions

These are user-policy dependent. Clarify when needed.

- `References` often stays in the source language.
- `Appendix / Author List / Acknowledgment` may be partially exempt.
- Code blocks may need only comment translation rather than full localization.

## Heading Mapping Rules

OCR output (MinerU/Nougat) typically flattens all headings to `\subsection{}` with number prefixes merged into the title text. After translation, run `scripts/normalize_heading_levels.py --write -v` to restore proper hierarchy. The script applies five rules:

| Rule | OCR Input | Correct Output | When |
|------|-----------|---------------|------|
| **Title** | `\section{KIMI K3：开放前沿智能}` | `\begin{center}{\LARGE ...\par}\end{center}` | First `\section` near document top, no number prefix |
| **Abstract/Refs** | `\subsection{摘要}` / `\subsection{参考文献}` | `\section*{摘要}` / `\section*{参考文献}` | Unnumbered, should not appear in TOC |
| **Numbered** | `\subsection{1 引言}` | `\section{引言}` | Single digit → section |
| | `\subsection{2.1 Hybrid Attention}` | `\subsection{Hybrid Attention}` | N.M → subsection |
| | `\subsection{2.1.1 KDA}` | `\subsubsection{KDA}` | N.M.K → subsubsection |
| **Appendix** | `\subsection{A 贡献者名单}` | `\section{贡献者名单}` | Letter A-F stripped from title, kept in `\label{}` |
| **Inline bold** | `\subsection{核心评测结果摘要}` | `\noindent\textbf{核心评测结果摘要}` | Pass via `--inline-bold` flag |

The depth is determined by the count of dots in the number prefix: 0 dots → section, 1 dot → subsection, 2 dots → subsubsection.

Reference [assets/heading_examples.tex](../assets/heading_examples.tex) for before/after examples, and `example/kimi_k3_report/` for the full working result.

## Consistency Checklist

- No section titles keep literal numeric prefixes unless the user wants them.
- No long English prose remains in translated sections, except deliberate exemptions.
- No formulas were rewritten into prose.
- No literal `\n`, `\$`, `??`, or broken OCR placeholders remain.
- Figure captions are consistent with the upgraded image set.
- Appendix lettering and table/figure references still match the compiled output.
