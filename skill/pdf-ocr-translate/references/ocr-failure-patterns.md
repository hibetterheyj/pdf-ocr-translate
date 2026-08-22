# MinerU OCR Failure Patterns & Cross-Validation Checklist

Catalog of failure patterns observed across real MinerU runs (Kimi K3, DeepSeek V4, Spatiotemporal, MAI-Thinking-1). New patterns should be appended here after each translation project.

## Text-level corruption

| Pattern | Example | Fix |
|---|---|---|
| **fi/ff ligature loss** (systematic) | `eficiency→efficiency`, `diferent→different`, `ofer→offer`, `efort→effort`, `afected→affected`, `bufers→buffers`, `oficial→official`, `Jefrey→Jeffrey`, `Hofmann→Hoffmann`, `Muennighof→Muennighoff`, `coeficient→coefficient` | Translators fix per-occurrence against the source PDF page text. **Reference author names are not exempt** — MAI-Thinking-1 had ~30 corrupted author names. |
| Word-join/space loss | `ofLiveCodeBench→of LiveCodeBench`, `domainspecific→domain-specific`, `ofthe→of the`, `vocab ulary→vocabulary` | Per-occurrence, check PDF. |
| Hyphen loss | `crossreferences→cross-references`, `localitysensitive→locality-sensitive`, `singleturn→single-turn`, `failtopass→fail-to-pass` | Check PDF. |
| Wrong word | `evalulation` (sometimes a genuine source typo — keep it if the PDF has it), `Ofice→Office`, `of-the-shelf→off-the-shelf` | PDF is the tiebreaker. |
| Page-marker residue | Standalone digits (e.g. `108`) on their own line, flanked by blank lines, one per PDF page | `split_translation_chunks.py` removes these automatically. |
| Footnote misplacement | `1Correspondence should be sent to ...` appears as body prose instead of a footnote | Convert to `\footnote{...}` anchored at its paragraph. |

## Structure-level corruption

| Pattern | Example | Fix |
|---|---|---|
| Missing section heading | Section 6's `\subsection{6 Cluster Environment}` was emitted as plain text, not a heading command | Cross-check the PDF table of contents against the heading inventory; restore the command. |
| Hand-built Contents | OCR emits a text `Contents` with stale English page numbers | Drop at merge; inject `\tableofcontents` + `\renewcommand{\contentsname}{目录}` **in the document body** (polyglossia resets `\contentsname` at language activation). |
| Scrambled table rows | Table 12's data rows had doubled/merged cells | Rewrite the table cell-by-cell from the PDF page text; verify column counts per row with a script. |
| Em dash → CJK 一 | `—` recognized as the Chinese character 一 inside tables | Replace with `---` (LaTeX em dash) when inside table cells. |
| Split table header cells | `Down\nProj` merged across lines | Collapse to one line; keep `&` count consistent. |
| Duplicate section tails | A heading + intro paragraph appears at the end of chunk N and the start of chunk N+1 | `merge_translation_chunks.py --dedupe-headings` drops the later copy. |
| Lost content blocks | A whole excerpt paragraph missing between two headings | Compare chunk line counts against the PDF page range; reconstruct from `pdf_pages/`. |

## Math transcription garbage

MinerU emits pandoc-escaped tokens inside math that compile but render wrong:

| Pattern | Example | Fix |
|---|---|---|
| Escaped comparisons | `x \textgreater 0` inside `$...$` | `fix_ocr_artifacts.py` rewrites `\textgreater→>`, `\textless→<`, `\textgreater=→\geq`, `\textless=→\leq`, `=\textgreater→\Rightarrow` — **only inside math spans** (text-mode occurrences are legal). |
| Empty-brace carets | `x\^{}2` | → `x^2`. |
| `\textasciitilde{}` as tilde | `EG \textasciitilde{} = 1.3` | → `\sim`. |
| Misplaced `\textsuperscript` | `(\mathbb{Z}/3\textsuperscript{7\mathbb{Z})}*` | Rewrite as `(\mathbb{Z}/3^7\mathbb{Z})^*`. |
| Stray braces | `(\mathbb{Z}/3^e\mathbb{Z})}*` | Remove the stray `}`. |
| Cross-line math | One inline `$...$` split across two lines (each line has odd `$` count) | Join onto one line; a per-line odd-`$` scan finds these. |
| Unicode math in text mode | `φ`, `ϵ`, `≤`, `−`, `≪`, `⋆` outside `$...$` | Wrap in math mode (`$\varphi$` etc.). The compile log's "Missing character" warnings enumerate them. |

## The `\n` literal trap

Body text containing a literal backslash-n (`\n`) breaks compilation, but **never do a global `\n` → `\textbackslash{}n` replace**: the preamble is full of legitimate commands (`\newcommand`, `\textcolor`, ...) whose backslash-n starts a macro name. A global replace turned a 0-error file into 173 errors in the MAI run.

Safe procedure:
1. Replace `\n` only in *body* chunks (after `\begin{document}`), or
2. If a global replace slipped through, restore with `\textbackslash{}n` + `[a-zA-Z]` → `\n` + letter (macro names always continue with a letter).

## Compile-iteration protocol

Expected trajectory per project: ~20-50 non-fatal errors → 0 errors.

1. First compile: collect `grep "^!"` error counts by type.
2. Fix in order: undefined control sequences (usually the `\n` trap or stray text-mode math), `Missing $ inserted` (cross-line math, prose `\leq`), alignment-tab errors (extra `&` in table rows).
3. After 0 errors: `grep 'Missing character'` the log — enumerate remaining Unicode math in prose and wrap each in math mode.
4. Recompile twice more for cross-references and TOC; re-check for 0 errors + 0 missing glyphs.
