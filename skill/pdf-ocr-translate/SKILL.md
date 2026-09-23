---
name: pdf-ocr-translate
description: Translate OCR-produced LaTeX/Markdown papers into high-quality Chinese PDFs with source-PDF cross-checking, multi-agent chunked translation, heading normalization, high-resolution figure extraction, and reliable XeLaTeX/pandoc packaging. Recovers math symbols OCR dropped, refits over-wide tables, puts table captions back where they belong, reattaches flattened footnotes, and audits the compiled layout. Use when the input comes from MinerU, Nougat, Mathpix, OCR-to-LaTeX pipelines, or other noisy PDF-to-LaTeX conversions and the user wants a polished translated PDF rather than raw OCR output — especially when the OCR output is littered with U+FFFD placeholders, tables run off the page or their captions sit below/narrower than the table, footnotes have collapsed into stray digits and orphan paragraphs, or figures came out as low-resolution fragments. Also use when two OCR passes exist for the same PDF and someone has to decide which to trust.
---

# PDF OCR Translate

Orchestration layer on top of the local `pdf` skill for translating OCR-generated LaTeX/Markdown papers (from MinerU, Nougat, Mathpix) into polished Chinese PDFs.

## Before You Start: Environment Check

Before any translation work, verify the toolchain is available:

1. **XeLaTeX** — required for CJK compilation. If missing:
   ```bash
   brew install --cask basictex
   eval "$(/usr/libexec/path_helper)"
   ```
2. **LaTeX packages** — BasicTeX is minimal. Common missing packages:
   ```bash
   sudo /Library/TeX/texbin/tlmgr install ctex adjustbox multirow footmisc
   ```
   If compilation fails with "File `X.sty' not found", install the missing package with `sudo tlmgr install X`.

3. **Python with pymupdf** — for PDF text extraction and cross-validation. Use the project's Python env:
   ```bash
   env/data_env/bin/python -c "import fitz; print('pymupdf OK')"
   ```

## Translation Workflow

### 1. Inspect and Initialize

Inspect the OCR project and source PDF, then create a working copy. If the `init_translation_workspace.sh` script encounters recursion issues (target inside source), create the workspace manually:

```bash
mkdir -p <working_dir>/{parts,images}
cp <source_main.tex> <working_dir>/
ln -s <source_images_dir> <working_dir>/images
```

### 1.5. If You Have Two OCR Passes, Cross-Validate Them

When the user supplies more than one OCR result for the same PDF — commonly a
MinerU pipeline pass and a VLM pass — do not pick one wholesale. They fail in
different places, and which one wins is not predictable in advance:

| | DeepSeek-V4.1-Flash | MiMo-V2.6 |
|---|---|---|
| normalised line similarity | 98.9% | **87.8%** |
| better prose | tie | pipeline pass (28 split-word errors vs 34) |
| better tables | tie | **VLM, on all five differing tables** |
| better formulas | tie | **VLM** — the pipeline pass produced a double subscript (a hard compile error) and renamed a variable |

Two runs, opposite verdicts. So measure your own document instead of trusting
either precedent.

The comparison that pays for itself is **per-table**, because that is where the
passes diverge most and where the damage is quietest. Pull each `longtable`
block out of both files and diff them. The failures to look for, none of which
break the build:

  * `\multicolumn` spans dropped, so values that should straddle two columns get
    pushed into one;
  * `-` placeholders lost from a results matrix — the missing-measurement cells
    go blank and a reader can no longer tell "not evaluated" from "evaluated,
    empty";
  * the wrong column count declared (a five-column table read as six);
  * one row split across several.

Splice the better version of each table into the base, and keep the splice in a
script so it is reproducible and reviewable — `build_hybrid.py` in the MiMo-V2.6
example is 60 lines and does exactly this.

For prose, an objective tiebreak that needs no PDF reading: tokenise both and
count the words that do not occur anywhere in the PDF text layer, ignoring the
references and figure content.

### 2. Clean OCR Artifacts

OCR output contains predictable noise. Run the cleanup script before translation:

```bash
python3 scripts/fix_ocr_artifacts.py <working_dir>/main.tex
```

This fixes: escaped `\$ → $` (math mode), Unicode math chars (`ϕ→$\phi$`, `α→$\alpha$`), invisible control characters, and other common MinerU/Nougat artifacts. Read [references/tooling-and-gotchas.md](references/tooling-and-gotchas.md) for the full list of OCR failure patterns.

### 2.5. Recover the Math Symbols Mining Tools Drop

Do this before translating, because the translators will otherwise guess at holes
they cannot see. When a paper sets variables in a math font, MinerU writes U+FFFD
for each one — and **pymupdf's plain text layer loses them too**, so comparing
against `page.get_text("text")` makes them look unrecoverable. They are not:
`page.get_text("dict")` exposes a per-span `font` name, and a span whose font
looks like a math font holds the real codepoint (`𝐿` U+1D43F is just
"MATHEMATICAL ITALIC CAPITAL L"). Extract them and put them back:

```bash
scripts/recover_math_glyphs.py --pdf source.pdf --pages 4-51 \
    --chunks parts/ --out worklist.txt
```

The output marks every symbol as `‹X›` inside its sentence, so you can read a
proposed symbol against the surrounding words. **Do not skip that reading.** A
wrong symbol compiles cleanly and renders plausibly — a real run shipped `λ`
where the equation said `τ`, and nothing in LaTeX or the PDF complained. The
worklist is a proposal; turn it into an exact-substring replacement table and
apply it with a small script, so re-running the pipeline stays deterministic.

### 2.6. Structural Artifacts the Cleanup Script Does Not Cover

`fix_ocr_artifacts.py` handles character-level noise. Four structural classes
survive it, and all four compile cleanly — which is what makes them worth a
deliberate pass:

  * **Footnotes arrive in two pieces.** The marker digit is glued to whatever
    precedes it, and the footnote text is emitted as its own paragraph at the
    bottom of the page — marker and all. You get `... (Wang et al., 2025)1,`
    mid-sentence and a stray `2https://...` paragraph further down. Reattach
    them into `\footnote{}`; the `xurl` package lets a long URL in a footnote
    break.
  * **Table captions arrive as prose**, before or after the table depending on
    reading order, and with the number written into the text — see step 6.5.
  * **Figure interiors leak into the prose.** A figure containing a small table
    or a legend gets its cells read out as body paragraphs, often a section away
    from the figure, so they land as orphaned fragments. The re-rendered image
    already carries that text, so the leaked copies are pure duplication;
    `scripts/strip_leaked_figure_labels.py` is the shape of the fix (matching
    whole standalone lines, so a same-named table row label is not caught).
  * **The printed table of contents is copied verbatim**, carrying the *source*
    language's page numbers. Replace it with `\tableofcontents` (step 5) and
    delete the OCR copy — note it usually sits mid-chunk, so the splitter's
    `DROP_AT_MERGE` marker does not catch it.

And one character-level class the cleanup script misses because it is a *glyph
loss* rather than an escape: **ligatures**. MinerU drops the `f` from `ff`/`fi`
ligatures, so "effective" becomes "efective", "offline" becomes "ofline", and
reference author names get mangled the same way. `scripts/fix_ligatures.py`
documents the two-sided test that finds them — the broken spelling must be
absent from `pdf_pages/*.txt` and the repaired one present. A dictionary-only
scan fails in both directions: it invents repairs for surnames and acronyms that
were never broken, and it misses real losses whenever the repair is an inflected
form the system word list lacks.

### 2.7. Make Every Fix Pass Idempotent

These passes typically run **twice** — once on the source before splitting, and
again on the merged file, so that a translation predating the fix still picks it
up. A pass that is correct only on its first run will quietly corrupt the
second, and the failure looks like nothing at all.

A real one: the table-sizing pass located each table's wrapper by searching
globally for the marker text `{\def\LTcaptype{none}`. On a fresh file every
table's wrapper looked like that, so the first run was fine — but the pass
*rewrites* the wrapper to `{\footnotesize\def\LTcaptype{none}`, so a second run
searched past those, latched onto the previous un-sized table's wrapper, and
re-emitted the whole region between them. Seven tables became nine, and one
table silently acquired another's column widths. Nothing errored.

The rule that avoids the class: **anchor on the structure you are editing, not
on text you have already rewritten.** Walk up from the table's own
`\begin{longtable}` line rather than searching for a marker string. And when a
pass is meant to be re-runnable, test it by running it twice.

### 3. Split into Translation Chunks

For papers longer than ~300 lines, split the document at major section boundaries. Use the bundled splitter — it handles page-marker removal, chunk size budgeting, and page-range mapping:

```bash
python3 scripts/split_translation_chunks.py <working_dir>/main.tex \
    --output-dir <working_dir>/parts \
    --pdf-pages-dir <working_dir>/pdf_pages
```

This writes `parts/chunk_NN_*.tex` plus `parts/CHUNK_MAP.json` (chunk → source PDF page range). It:
- removes page-marker residue (standalone digits flanked by blank lines, one per PDF page)
- merges small adjacent sections into 150-700 line chunks, sub-splits oversized sections at the nearest sub-heading
- slices heading-free text (e.g. a plain References list) at blank-line boundaries (~500 lines each)
- keeps the multi-line title heading whole in the preamble chunk
- flags chunks whose heading matches `--drop-markers` (default `contents`) as `DROP_AT_MERGE`

Budget chunk size by `�` density, not just line count — a 500-line proof chunk with 300 `�` symbols takes longer than an 800-line prose chunk with none. Reference the Kimi K3 example (~4000 lines, 9 chunks, 6 agents) and the MAI-Thinking-1 example (7495 lines, 35 chunks, 27 agents in two waves of 14+13).

### 4. Translate Chunks in Parallel

Launch subagents for each chunk with these instructions:
- Translate English prose to Chinese (section titles, body text, figure/table captions)
- **Preserve exactly**: all LaTeX commands, math environments (`$...$`, `\[...\]`, `\begin{equation}`), `\cite{}`, `\ref{}`, `\label{}`, `\includegraphics{}`, table environments, `\multirow`, `\multicolumn`
- **Keep in English**: model names, benchmark names, technical identifiers, citation keys, library/framework names
- Translate figure captions: `Figure X: ...` → `图 X: ...`
- Translate table captions: `Table X: ...` → `表 X: ...`
- Write each translated chunk back to its original file

Read [references/translation-policy.md](references/translation-policy.md) for full rules, [references/ocr-failure-patterns.md](references/ocr-failure-patterns.md) for the systematic corruption catalog (fi/ff ligature loss, scrambled tables, math transcription garbage), and [references/orchestration.md](references/orchestration.md) for how to brief and sequence the agents. Two things from that last file matter enough to repeat here:

- **Give each agent its own page range, and state the mapping explicitly.** Printed page N is `pdf_pages/page_NNN.txt` — but PDF *file* page N+1, because the first page is usually an unnumbered title. Agents that are told the wrong mapping still tend to find the right text, but they burn turns discovering it.
- **Separate checking from translating.** The agents that stall are the ones that keep re-reading the PDF to verify. Do the verification in its own pass, hand the translator a pre-verified list of corrections, and tell it not to re-investigate. Measured on a real run: the same chunk that exhausted an agent's context across 23 turns finished in 5 once scoped that way.

### 5. Merge and Fix Fonts

Merge all chunks (preamble + translated body parts) into a single `main_cn.tex` with the bundled merger:

```bash
python3 scripts/merge_translation_chunks.py parts/ --output main_cn.tex --dedupe-headings
```

The merger drops `DROP_AT_MERGE` chunks (hand-built Contents), injects `\tableofcontents` before the Abstract heading, and removes duplicated heading blocks across adjacent chunks. Then ensure the font preamble uses macOS-compatible fallbacks:

- Add `Songti SC` and `Heiti SC` between `Noto Serif CJK SC` and `SimSun` in the CJK font chain
- macOS system fonts: Songti SC (serif), Heiti SC (sans), PingFang SC (modern) are available without additional installs
- Reference: [assets/font_preamble_snippet.tex](assets/font_preamble_snippet.tex)

Several preamble edits are placement-sensitive, and getting the placement wrong
produces errors that do not obviously point at the cause. [assets/preamble_patches_cn.tex](assets/preamble_patches_cn.tex)
collects them with the reasoning:

- `\setCJKmainfont` / `\setCJKsansfont` are **preamble-only** — after `\begin{document}` they raise "Can be used only in preamble".
- `\renewcommand{\contentsname}{目录}` must go **in the body**, right before `\tableofcontents`: polyglossia re-activates the language and resets it, so a preamble-level setting is silently lost.
- Insert the TOC **after the centred title block**, not right after `\begin{document}`. MinerU's preamble chunk contains `\begin{document}` and the title follows it, so inserting at `\begin{document}` puts the contents pages ahead of the title page.
- ctex does not relabel caption prefixes; add `\renewcommand{\figurename}{图}` and `\renewcommand{\tablename}{表}` or every caption reads `Figure N:`.
- Load `xurl` **before** `hyperref` so long URLs can break (see step 6.5).

### 5.5. Normalize Heading Levels

OCR output flattens all headings to `\subsection{}` with number prefixes merged into the title text. After merge, run the heading normalizer to restore proper hierarchy:

```bash
python3 scripts/normalize_heading_levels.py main_cn.tex --write -v
```

This applies five rules (in order). The number-prefix patterns accept both `1 引言` and `1. 引言` (trailing dot optional — MinerU commonly leaves the dot before the space).

**Rule 0 — Title → centered block.** The first `\section{...}` near the top of the document (no number prefix) is converted to a centered title block:
```latex
% Before:
\section{KIMI K3：开放前沿智能}

% After:
\begin{center}
{\LARGE KIMI K3：开放前沿智能\par}
\end{center}
```
**Caveat**: Rule 0 only fires within the first 30 lines of the file. With a long preamble (~100 lines) the title `\section` is out of range — convert it manually to the centered block (see the spatiotemporal example's frontmatter chunk).

**Rule 1 — Abstract / References → `\section*`.** Unnumbered special sections that should not appear in the table of contents:
- `\subsection{摘要}` / `\subsection{Abstract}` → `\section*{摘要}`
- `\subsection{参考文献}` / `\subsection{References}` → `\section*{参考文献}`

**Rule 2 — Numbered headings → correct level.** Strip the OCR-merged number prefix and promote/demote by depth:
| OCR Input | Correct Output |
|---|---|
| `\subsection{1 引言}` | `\section{引言}` |
| `\subsection{2.1 Hybrid Attention}` | `\subsection{Hybrid Attention}` |
| `\subsection{2.1.1 KDA}` | `\subsubsection{KDA}` |

The depth is determined by the count of dots in the prefix: single digit → section, digit.digit → subsection, digit.digit.digit → subsubsection.

**Rule 3 — Appendix letters → `\section`.** Strip the A-Z prefix but preserve the appendix letter in the `\label{}` for ordering (MinerU papers often carry appendices beyond F):
```latex
% Before:
\subsection{A 贡献者名单}\label{a-contributions}

% After:
\section{贡献者名单}\label{a-contributions}
```

**Rule 4 — Inline bold demotion.** Specific unnumbered headings can be demoted to bold inline text (pass with `--inline-bold "标题文本"`). This is used for section summaries that shouldn't be numbered.

Run the normalizer on both `main_cn.tex` and all `parts/*.tex` for consistency. If the document has a hand-built Contents (enumerate TOC from OCR), replace it with `\tableofcontents` — the OCR copy carries the English-version page numbers and will mislead. Put `\renewcommand{\contentsname}{目录}` **in the document body** right before `\tableofcontents`: `polyglossia` re-defines `\contentsname` at language activation, so a preamble-level renewcommand is silently lost. Reference the DeepSeek V4, Kimi K3, and spatiotemporal composability examples in `example/` for the expected output pattern.

### 6. Cross-Validate Against Source PDF

Use pymupdf to extract text from the source PDF and verify key facts survived translation:

```python
import fitz
doc = fitz.open("source.pdf")
for page in doc:
    text = page.get_text('text')
    # Compare key numbers, technical claims with translated output
```

Focus verification on: numerical values, model sizes, benchmark scores, citation keys. This catches OCR errors that would otherwise go unnoticed. See [references/workflow.md](references/workflow.md) for the full approach.

**Missing-glyph sweep**: after the first clean compile, grep the log for `Missing character`. MinerU frequently leaves raw Unicode math in prose (`⋄`, `≃`, `∎`, `⊥`, `⌀`, `▷`, `↦`, `∘`, `•`, `‣`, `φ`, `ϵ`, `≤`). Fix with a stateful text/math-mode tracker that wraps each occurrence in `$\diamond$`, `$\simeq$`, `$\bot$`, `$\emptyset$`, `$\triangleright$`, `$\mapsto$`, `$\circ$` etc. — a naive global regex replace corrupts surrounding CJK text.

**Math transcription junk**: MinerU writes pandoc-escaped tokens inside math (`\textgreater0`, `x\^{}2`, `\textasciitilde{}`, misplaced `\textsuperscript` braces, stray `}` after `)^*`). `fix_ocr_artifacts.py` now rewrites these automatically, but only inside `$...$`/`\[...\]` spans — run it again on the merged file before compiling. A per-line odd-`$` scan finds cross-line split math (each half has an odd `$` count): join those lines.

**The `\n` literal trap**: body text containing a literal `\n` breaks compilation, but never do a global `\n` → `\textbackslash{}n` replace — the preamble is full of macro names (`\newcommand`, ...) that start with backslash-n. Restrict the replace to body chunks, or restore afterwards with `\textbackslash{}n` + `[a-zA-Z]` → `\n` + letter.

### 6.5. Make the Tables Fit, Then Audit the Layout

Every MinerU table comes out with `l` columns, and `l` never wraps — so one long
benchmark name (`Terminal-Bench v2.1 (Pass@1)`) or a row of model names pushes
the table straight off the page. Fix this on the merged file, before compiling:

1. **Convert the leading label column to a wrappable `L{}` column.** Define
   `\newcolumntype{L}[1]{>{\RaggedRight\arraybackslash}p{#1}}` in the preamble,
   and give each table's label column — and any other column holding prose, such
   as a row of model names — an explicit width in `em` so it tracks the font size.
2. **Wrap the whole table in `{\footnotesize ... }`.** The size command has to go
   *outside* the `longtable`; putting it inside the alignment preamble (after
   `\endlastfoot`) triggers `Misplaced \noalign`.
3. **Check the header actually lines up with the data.** MinerU sometimes emits a
   header as one `\multicolumn` of flowing text, e.g.
   `\multicolumn{7}{c}{Opus-5 GPT-5.6 Sol K3 GLM-5.3 DS-V4-Pro DS-V4-Flash|...}`.
   That text is spaced by the typesetter and bears no relation to the columns
   below it — the table looks misaligned even though every number is right. Give
   each header its own cell (a `\shortstack{...}` where a name needs two lines) so
   each label sits over its own column, and keep the model order from the PDF.

4. **Give the caption the full width, and put it above the table.** MinerU
   emits the caption as a body paragraph whose position follows reading order,
   so it lands after the table about as often as before it — and consecutive
   tables' captions bunch up and read as both belonging to the later one. Move
   each into a real `\caption` directly under `\begin{longtable}` (that is where
   longtable prints a top caption) and drop the `\def\LTcaptype{none}` that
   suppressed numbering. Then two longtable defaults still bite:

   - `\caption` is typeset in a box `\LTcapwidth` wide, and **that length
     defaults to 4in — about 289pt — no matter how wide the table is.** In a
     500pt table the caption renders as a narrow box centred inside it, its left
     edge matching neither the table nor the body text. Set
     `\setlength{\LTcapwidth}{\textwidth}` in the preamble.
   - a caption that fits on one line is *centred* (`\LT@makecaption` measures
     `\wd\@tempboxa` and wraps it in `\hfil...\hfil`), so a short caption sits
     mid-page while a longer one on the next table starts at the margin. Load
     the `caption` package with `singlelinecheck=false` for consistency, and
     match the paper's own style while you are there (`labelfont=bf`,
     `labelsep=quad` are common).

   The paper's existing captions are the reference for both — measure where the
   original's caption starts and how wide it runs before choosing.

5. **A table that fills the text block also fixes its own alignment.** longtable
   centres a table narrower than `\textwidth`, so a table at, say, 75% of the
   width sits inset from both margins and lines up with neither its caption nor
   the body prose. Measure the *original* PDF's column positions and rescale
   them so the columns plus their gutter fill `\textwidth`; `em` widths track
   the font size, `\linewidth` fractions survive a caption-size change.

Then verify the result against the compiled PDF rather than the source:

```bash
scripts/audit_layout.py --pdf build/main_cn.pdf --margin 555
scripts/check_tables.py --parts parts          # add --fix to pad short rows in place
```

`audit_layout.py` reports margin overflows, text overlaps, and stray list
markers. `check_tables.py` catches a row with the wrong `&` count before LaTeX
does — pass `--fix` and it will also append the missing trailing `&` to rows
that are merely short (a header row under a `\multirow`, or a data row with an
empty last cell). It appends only; rows that are too *long* mean a merged cell
and need the PDF.

Set the margin from your own geometry and measure the worst case once before
believing a report: pymupdf line boxes include italic correction and side
bearings, so lines that visually end inside the margin can measure a few points
past it. A document whose worst overhang is ~8pt is fine; a real defect is tens
of points. Expect a few "overlaps" that are just inline math split across lines —
read the reported text before acting on it. Tall delimiters are another benign
case: `\left\{` is drawn as several stacked `CMEX10` glyphs whose bounding boxes
overlap by construction.

**Measure the text block, do not assume it.** Read `\textwidth` off the compiled
PDF (page rect minus the geometry margins) before sizing anything against it: US
Letter with 2cm margins is 498.6pt, A4 is 481.9pt, and a 17pt error is exactly
the size of the problem you are trying to fix. A table sized for the wrong width
looks like a mysterious new overflow.

Two spills worth knowing about, both seen in practice:

- **A joined URL becomes an unbreakable token.** OCR sometimes turns a wrapped
  URL into a URL containing a space (`https://doi. org/...`,
  `arXiv.2405.04 434`). Joining that space is right, but without `xurl` the
  repaired URL is a ~180pt atom that shoots past the margin. Fix both together.
- **Empty `enumerate` blocks print as `(a)` `(b)`.** MinerU emits subfigure
  labels as `enumerate` blocks with no content; once the images are wrapped in
  `figure` environments the empty lists remain and LaTeX still numbers them.
  Delete the whole environment, and note that this legitimately changes your
  `\begin`/`\end` counts in the structure check.

### 7. Compile

Compile natively with XeLaTeX (required for CJK + ctex):

```bash
xelatex -interaction=nonstopmode main_cn.tex
xelatex -interaction=nonstopmode main_cn.tex  # second pass for cross-refs
xelatex -interaction=nonstopmode main_cn.tex  # third pass for TOC
```

**Troubleshooting compilation errors:**
- `File 'X.sty' not found` → `sudo tlmgr install X`
- `I can't find file 'SimSun'` → Update font fallback chain (add macOS fonts)
- `Missing $ inserted` / `Missing number` → Run `fix_ocr_artifacts.py` again on the merged file; these come from OCR artifacts that survived translation
- `Undefined control sequence` (many, clustered) → usually the `\n` literal trap or stray text-mode math; check the compile log for `\textbackslash{}n` and `\leq`/`\nmid` in prose
- `Extra alignment tab has been changed to \cr` → a table row has one `&` too many (OCR merged two cells); compare with the PDF page
- `Text line contains an invalid character` → Control characters in OCR output; run cleanup script
- `Missing character: There is no X` → Raw Unicode math left in prose; wrap in math mode (see step 6)
- Non-zero errors with `-halt-on-error` are expected (OCR artifacts); use `-interaction=nonstopmode` to power through. Zero-error compiles are achievable — see the spatiotemporal and MAI-Thinking-1 examples

If the user explicitly requires a pandoc-generated artifact, wrap the already-compiled native PDF:
```bash
scripts/compile_pdf.sh path/to/main_cn.tex path/to/output_pandoc.pdf
```

### 8. Verify Output

- Open the compiled PDF and spot-check random sections
- Verify tables rendered correctly (longtables are fragile in OCR output)
- Check that figure captions are translated and images are visible
- Confirm citation keys are intact

Then run the mechanical checks, which catch what a spot-check misses:

```bash
scripts/audit_layout.py --pdf build/main_cn.pdf --margin <textblock-right-edge>
scripts/check_tables.py --parts parts
scripts/check_structure.py --parts parts --compare baseline.json   # if you took one
```

Read the compile log for `Missing character` too — raw Unicode math left in
prose shows up there and nowhere else. A clean finish looks like 0 errors,
0 missing glyphs, all figures and tables present, and a layout audit whose only
findings are inline-math fragments.

## Reference Files

Read only when needed:

- **[references/workflow.md](references/workflow.md)** — Full end-to-end flow with subagent chunking strategy and cross-validation
- **[references/orchestration.md](references/orchestration.md)** — How to brief and sequence translation subagents: page mapping, scoping, why the verifying agents stall and how to stop it, what to do when one does, and why every fix pass has to be idempotent
- **[references/translation-policy.md](references/translation-policy.md)** — What to translate, what to preserve, heading mapping rules
- **[references/ocr-failure-patterns.md](references/ocr-failure-patterns.md)** — Systematic MinerU corruption catalog, with a section on diffing two OCR passes and one on table/caption damage. Covers ligature loss, dropped math glyphs, flattened footnotes, scrambled tables, broken URLs, the `\n` trap — give the relevant sections to translation subagents
- **[references/tooling-and-gotchas.md](references/tooling-and-gotchas.md)** — Compilation troubleshooting, font pitfalls, OCR failure patterns, figure extraction, and the longtable caption/width defaults that make a correctly-sized table still look wrong
- **[references/example-session.md](references/example-session.md)** — Concrete paths and commands from a successful DeepSeek V4 run

## Scripts

Existing scripts:

- **`scripts/fix_ocr_artifacts.py`** — Clean common OCR artifacts: escaped `\$`, Unicode math chars, control characters, and MinerU math transcription junk (`\textgreater`, `\^{}`, `\textasciitilde`) inside math spans
- **`scripts/split_translation_chunks.py`** — Split at heading boundaries: removes page-marker lines, merges small sections, sub-splits oversized ones, slices References lists, writes `CHUNK_MAP.json` with page ranges
- **`scripts/merge_translation_chunks.py`** — Merge translated parts: drops `DROP_AT_MERGE` chunks, injects `\tableofcontents`, dedupes shared headings across adjacent chunks
- **`scripts/init_translation_workspace.sh`** — Create working copy with `parts/` and `images_hi/`
- **`scripts/normalize_heading_levels.py`** — Convert OCR-numbered headings to proper LaTeX section commands (A-Z appendices, letter.N sub-headings, no stray spaces before `\label`)
- **`scripts/check_latex_translation.py`** — Scan for untranslated prose, bad escapes, OCR placeholders, unnormalized headings
- **`scripts/extract_hd_figures.py`** — Render high-DPI figure pages from source PDF
- **`scripts/build_pandoc_wrapper.py`** — Create minimal pandoc wrapper using `pdfpages`
- **`scripts/compile_pdf.sh`** — Compile native LaTeX, optionally emit pandoc PDF wrapper

Added after a full DeepSeek-V4.1-Flash run; each one paid for itself on that job:

- **`scripts/recover_math_glyphs.py`** — Recover the math symbols MinerU replaced with U+FFFD, using the PDF's span-level font data. Emits a worklist with each symbol shown in its sentence, so you can check it against the prose before trusting it. **Run this before translating** (step 2.5)
- **`scripts/audit_layout.py`** — Post-compile layout audit: margin overflows, text overlaps, stray `(a)`/`(b)` list markers
- **`scripts/check_tables.py`** — Verify every `longtable` row has the column count its preamble declares (catches merged/shifted cells before LaTeX does). Understands custom column types such as `L{15em}`/`C{7em}`, and `--fix` pads rows that are short by trailing empty cells
- **`scripts/check_structure.py`** — Count `\label`/`\caption`/`\includegraphics`/`\tag`/… before and after translation to prove the pass was lossless
- **`scripts/verify_corrections.py`** — Check a subagent's claimed correction really exists in the source PDF, tolerating the whitespace pymupdf inserts between math glyphs

Added after a MiMo-V2.6 run; these cover the structural artifact classes in step 2.6 and the table geometry in step 6.5:

- **`scripts/fix_ligatures.py`** — Restore the `f` that `ff`/`fi` ligatures lost (`efective` → `effective`). Documents the two-sided PDF test that finds them, and why a dictionary-only scan both over- and under-reports. The word list is per-document, like a table-width plan
- **`scripts/render_figures.py`** — Re-render every figure from the source PDF at 400 DPI by finding each caption's ink bbox, instead of using MinerU's per-panel cutouts. Also crops a title-page header logo if the paper has one. Writes a manifest so a bad crop is visible
- **`scripts/fix_table_width.py`** — Size the longtables so they fill the text block; takes the per-document column plan as JSON (`--plan`) and carries one worked example. Idempotent by construction — see step 2.7 for why that matters
- **`scripts/fix_table_captions.py`** — Move each table's prose caption into a `\caption` above the table, restore numbering, and mark continuation pages `（续表）` instead of repeating the caption
- **`scripts/strip_ocr_contents.py`** — Delete the OCR copy of the printed table of contents (it carries the source language's page numbers, and sits mid-chunk so DROP_AT_MERGE misses it)
- **`scripts/strip_leaked_figure_labels.py`** — Drop body paragraphs MinerU read out of a figure's interior; matches whole standalone lines so real table labels are not caught

## Assets

- **[assets/pandoc_wrapper.template.md](assets/pandoc_wrapper.template.md)** — Minimal pandoc wrapper template
- **[assets/font_preamble_snippet.tex](assets/font_preamble_snippet.tex)** — CJK-safe XeLaTeX font setup with macOS fallbacks
- **[assets/preamble_patches_cn.tex](assets/preamble_patches_cn.tex)** — Placement-sensitive preamble edits for a MinerU project (CJK fonts, `xurl`, wrappable `L{}` column, centred title, caption names, `\contentsname`), with why each one goes where it goes
- **[assets/heading_examples.tex](assets/heading_examples.tex)** — Heading normalization and inline-bold demotion examples
- **[assets/deepseek_v4_paper_template/](assets/deepseek_v4_paper_template)** — Copyable modular starter project for OCR-LaTeX translation

## Example

See **[example/kimi_k3_report/](example/kimi_k3_report/)** for a complete worked example: the Kimi K3 technical report (~4000 lines OCR LaTeX) translated to Chinese, compiled to a 65-page PDF. Includes the split chunks, merged `main_cn.tex`, and compiled PDF.

See **[example/spatiotemporal_composability_report/](example/spatiotemporal_composability_report/)** for a formal-methods paper (6570 lines, heavy math): 17 chunks, ~900 OCR `�` symbols reconstructed from the source PDF, zero-error compilation. Demonstrates: repeated-letter OCR drops ("efects"→"effects"), per-page PDF text as cross-validation reference, hand-built TOC replacement, and the missing-glyph sweep.

See **[example/mai_thinking_1_report/](example/mai_thinking_1_report/)** for the largest run (7495 lines, 109-page PDF): 35 chunks translated by 27 parallel agents in two waves, ~170 fi/ff ligature fixes, scrambled-table reconstruction, the `\n`-literal trap (global replace → 173 errors → targeted restore), and a 120-page Chinese PDF with 0 errors and 0 missing glyphs.

See **[example/deepseek_v4_1_flash_report/](example/deepseek_v4_1_flash_report/)** for the run that produced the scripts in step 2.5 and 6.5 (3,313-line OCR, 51-page PDF, 15 chunks, 49-page output, 0 errors / 0 missing glyphs). It is the best example to read if you need to recover dropped math or fix table layout. It demonstrates: **80 U+FFFD symbols recovered from PDF span-font data** (including a wrong `λ`/`τ` that only the surrounding sentence exposed), 12 figures re-rendered at 400 DPI from vector PDF because the OCR cutouts were 41 fragments, a table header written as one `\multicolumn` of flowing text that had to be split into per-column cells, three URLs that OCR had split with a space, two empty `enumerate` blocks printing as stray `(a)` `(b)`, and a merge order bug that put the table of contents before the title page. `translate_latex/` keeps every pipeline script and `README.md` records the reasoning.

See **[example/mimo_v2_6_report/](example/mimo_v2_6_report/)** for the run that produced the cross-validation step (1.5) and the structural-artifact scripts (2.6). Unlike the earlier examples it had **two OCR passes that disagreed**, so the base is a splice: pipeline-pass prose, VLM-pass tables. It demonstrates per-table cross-validation and why one pass is not uniformly better (87.8% similarity; the pipeline pass broke equation (1) with a double subscript and dropped 11 of 12 `-` placeholders, while its prose was cleaner), 24 U+FFFD recovered, 97 ligature losses restored, 31 image stubs re-rendered into 17 figures, footnotes reattached, captions moved above their tables with `\LTcapwidth` set, and the two idempotency bugs described in step 2.7.
