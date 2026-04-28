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

Treat numbering as structure metadata, not display text.

- `1. 引言` -> `\section{引言}`
- `2.1. 继承自...` -> `\subsection{继承自...}`
- `2.3.4. 效率讨论` -> `\subsubsection{效率讨论}`
- Unnumbered structural summaries such as `核心评测结果摘要` are often better as inline bold headings, not numbered section commands.

Use `scripts/normalize_heading_levels.py` for deterministic cleanup, then manually review special unnumbered headings.

## Consistency Checklist

- No section titles keep literal numeric prefixes unless the user wants them.
- No long English prose remains in translated sections, except deliberate exemptions.
- No formulas were rewritten into prose.
- No literal `\n`, `\$`, `??`, or broken OCR placeholders remain.
- Figure captions are consistent with the upgraded image set.
- Appendix lettering and table/figure references still match the compiled output.
