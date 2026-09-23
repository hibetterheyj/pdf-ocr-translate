# MinerU OCR Failure Patterns & Cross-Validation Checklist

Catalog of failure patterns observed across real MinerU runs (Kimi K3, DeepSeek V4, Spatiotemporal, MAI-Thinking-1, MiMo-V2.6). New patterns should be appended here after each translation project.

## When you have two OCR passes

If the PDF was OCR'd twice (typically a pipeline pass and a VLM pass), diff them
before choosing a base — the winner is not predictable. DeepSeek-V4.1-Flash's two
passes agreed 98.9% and were interchangeable; MiMo-V2.6's agreed only 87.8%, and
each was better at something the other got wrong.

| Divergence | What it looks like |
|---|---|
| `\multicolumn` spans dropped | `\multicolumn{2}{l@{}}{28/24/4}` collapses to a plain cell, so values that should straddle two columns get pushed into one. MiMo-V2.6's pipeline pass had 22 spans become 0 in Table 1 |
| `-` placeholders lost | A results matrix's missing-measurement cells go blank. **The quietest one**: the table still compiles and reads as plausible, but a reader can no longer tell "not evaluated" from "evaluated, empty". MiMo-V2.6's pipeline pass kept 1 of 12 |
| Column count wrong | A five-column table declared as six, with a value pushed into the phantom column |
| Row split across lines | One data row emitted as several rows of a cell or two each |
| Formula mangled | A double subscript (`\bigcup_{d}_{\mathcal{D}_d}`) is a **hard compile error**; a renamed variable (`o_i` → `\mathcal{D}_i`) compiles silently |
| Word splitting | One pass inserts spaces inside words (`fur ther`, `sig nals`) — count tokens against the PDF text layer's vocabulary to compare objectively |

Splice the better version of each table into the base, and keep the splice in a
script so it is reviewable. Compare per-table rather than whole-file: on
MiMo-V2.6 the pipeline pass had the cleaner prose and the VLM pass had every
table intact.

## Text-level corruption

| Pattern | Example | Fix |
|---|---|---|
| **fi/ff ligature loss** (systematic) | `eficiency→efficiency`, `diferent→different`, `ofer→offer`, `efort→effort`, `afected→affected`, `bufers→buffers`, `oficial→official`, `Jefrey→Jeffrey`, `Hofmann→Hoffmann`, `Muennighof→Muennighoff`, `coeficient→coefficient`, `ofline→offline` | Translators fix per-occurrence against the source PDF page text; or run `scripts/fix_ligatures.py`. **Reference author names are not exempt** — MAI-Thinking-1 had ~30 corrupted author names, MiMo-V2.6 had `Laufer→Lauffer`, `Sutclife→Sutcliffe`. **Detect with a two-sided PDF test, not a dictionary**: a candidate is real only if the broken spelling is absent from `pdf_pages/*.txt` *and* the repaired one is present. A `/usr/share/dict/words` pass fails both ways — it proposes repairs for surnames and acronyms that were never broken (`Guo→gulo`, `SFT→sift`), and it misses real losses whose repair is an inflected form the list lacks (`eforts→efforts`; the macOS list has no plurals). |
| Word-join/space loss | `ofLiveCodeBench→of LiveCodeBench`, `domainspecific→domain-specific`, `ofthe→of the`, `vocab ulary→vocabulary` | Per-occurrence, check PDF. |
| Hyphen loss | `crossreferences→cross-references`, `localitysensitive→locality-sensitive`, `singleturn→single-turn`, `failtopass→fail-to-pass` | Check PDF. |
| Wrong word | `evalulation` (sometimes a genuine source typo — keep it if the PDF has it), `Ofice→Office`, `of-the-shelf→off-the-shelf` | PDF is the tiebreaker. |
| Page-marker residue | Standalone digits (e.g. `108`) on their own line, flanked by blank lines, one per PDF page | `split_translation_chunks.py` removes these automatically. |
| Footnote misplacement | `1Correspondence should be sent to ...` appears as body prose instead of a footnote | Convert to `\footnote{...}` anchored at its paragraph. |
| **Footnote flattened into two pieces** | The marker digit is glued to the preceding word (`... using CyberGym (Wang et al., 2025)1,`) *and* the footnote text is emitted as its own paragraph at the page bottom, marker and all (`2https://huggingface.co/...`). Rendered, that is a stray `1` mid-sentence and a stray `2https://...` further down | Reattach the two into `\footnote{}`: replace `<word>N` with `<word>\footnote{<text>}` and delete the orphan paragraph. Find the insertion point by searching for the digit immediately after a `)` / `）` / `,`. MiMo-V2.6 had two such footnotes, on pages 21 and 33. Load `xurl` so a long URL in a footnote can break. |

## Structure-level corruption

| Pattern | Example | Fix |
|---|---|---|
| Missing section heading | Section 6's `\subsection{6 Cluster Environment}` was emitted as plain text, not a heading command | Cross-check the PDF table of contents against the heading inventory; restore the command. |
| Hand-built Contents | OCR emits a text `Contents` with stale English page numbers | Drop at merge; inject `\tableofcontents` + `\renewcommand{\contentsname}{中文目录名}` **in the document body** (polyglossia resets `\contentsname` at language activation). Note the list usually sits *mid-chunk* (right behind the abstract), so the splitter's `DROP_AT_MERGE` never flags it — delete it at the source (`scripts/strip_ocr_contents.py`). |
| **Table caption emitted as prose** | `Table 4 Weighted SFT data composition. ...` as a normal body paragraph, **below** Table 4, with Table 5's caption immediately after it — so the two read as both annotating Table 5 | Move into a real `\caption` directly under `\begin{longtable}` and drop the `\def\LTcaptype{none}` that suppressed numbering (`scripts/fix_table_captions.py`). Longtable's caption box is `\LTcapwidth` wide — 4in by default — so also set that to `\textwidth` or the caption renders narrower than its own table. |
| **Figure interiors leak into the prose** | Figure 17 is a grid of web-page screenshots; its column header (`Qwen3.5-9B | MiMo-V2.6-Distill-Qwen-9B SFT RL`) was emitted as two body paragraphs a *section later*, reading as orphaned model names | The re-rendered figure already carries that text, so the copies are duplication. Delete whole standalone lines matching the leaked labels (`scripts/strip_leaked_figure_labels.py`) — matching the whole line avoids catching a same-named table row label. |
| Scrambled table rows | Table 12's data rows had doubled/merged cells | Rewrite the table cell-by-cell from the PDF page text; verify column counts per row with a script. |
| Em dash → CJK 一 | `—` recognized as the Chinese character 一 inside tables | Replace with `---` (LaTeX em dash) when inside table cells. |
| Split table header cells | `Down\nProj` merged across lines | Collapse to one line; keep `&` count consistent. |
| Duplicate section tails | A heading + intro paragraph appears at the end of chunk N and the start of chunk N+1 | `merge_translation_chunks.py --dedupe-headings` drops the later copy. |
| Lost content blocks | A whole excerpt paragraph missing between two headings | Compare chunk line counts against the PDF page range; reconstruct from `pdf_pages/`. |
| **Broken URL** | A wrapped URL has a space inside it: `https://doi. org/10.48550/arXiv.2412.19437`, `arXiv.2405.04 434`, `deepseek-a i/deepseek-harness` | Join the space — a space inside a URL is always an artifact. **But fix the breaking too**: the joined URL becomes a ~180pt unbreakable atom and shoots past the right margin. Load `xurl` *before* `hyperref` (see `assets/preamble_patches_cn.tex`). Joining without `xurl` makes the layout worse, not better. |
| **Empty `enumerate` blocks** | Subfigure labels `(a)`/`(b)` rendered as stray lines in the prose | MinerU emits them as `enumerate` blocks containing only `\item` and no content. Once the images are wrapped in `figure` environments the empty lists remain and LaTeX still prints their numbers. Delete the whole environment — expect `\begin`/`\end` counts in the structure check to drop accordingly. |
| **Orphaned footnote text** | `1mini-swe-agent, commit 04d809ceab9d.` sitting as a paragraph | The marker's host sentence is on a neighbouring page. Find the sentence the footnote annotates in the PDF and convert the text to `\footnote{...}` anchored there — do not leave it as a standalone block. |
| **Duplicated footnote** | The same footnote text appearing in both a body chunk and an appendix chunk | One translator saw the footnote on a shared page and added it locally. Check the PDF: if the footnote appears once, keep it once. |
| **`\tag{N}` lost in a retyped equation** | An equation carries `\tag{7}` in the OCR but the replacement line omits it | Count `\tag{` occurrences before and after — a dropped tag is silent and shifts every later equation number. |

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
| **Math-italic glyphs dropped entirely** | A variable MinerU cannot map becomes U+FFFD: `where � and � represent the KV entries` | `get_text("text")` cannot recover these — the glyphs are Unicode Mathematical Italic (`XCharterMathMI`, U+1D434+) and **both MinerU and pymupdf's plain-text layer lose them**. Use `page.get_text("dict")` and read the **span-level `font` name**: spans whose font contains `Math`/`MI` carry the real codepoint. Map U+1D434..U+1D44D → A..Z, U+1D44E..U+1D467 → a..z, and the Greek range likewise. DeepSeek-V4.1-Flash had 80 such sites; every one was recoverable this way. Do **not** guess from context — a wrong symbol passes compilation silently (a `λ`/`τ` swap in that run compiled and rendered fine). |
| Overline lost in prose | `\overline{\Delta b}` in an equation but plain `\Delta b` in the sentence referring to it | Re-check every symbol *mentioned in prose* against its definition in the equation. |
| Calligraphic set symbols flattened | `\mathcal{B}` in the equation, plain `B` in the prose | Same class of error; restore the calligraphic form. |

**Verifying a claimed correction.** The PDF text layer inserts a space between every math glyph (`f u s e d - R o P E`), so a naive `substring in page_text` gives false negatives. Collapse whitespace *and* hyphens on both sides before searching, and prefer searching the whole document over trusting a page number — chunk boundaries and printed page numbers do not align one-to-one.

## Table corruption (the highest-yield place to look)

Every run so far has had table damage; grep the longtables before trusting them:

| Pattern | Example | Fix |
|---|---|---|
| Em dash / hyphen read as CJK 一 | A `-` placeholder cell came through as `一` (U+4E00) | Replace with `-`; verify against the PDF cell. |
| Merged header cells | Three scaffold names collapsed into one `\multirow{2}{*}{Claude Code Codex OpenCode}` | Split back into one `\multirow` per column. |
| Merged sub-header row | `& & & & & & Minimal Standard PTC & &` | One cell per column: `Minimal & Standard & PTC`. |
| Group rows dropped | Standalone `Reasoning` / `Agentic` separator lines in the PDF are absent from the OCR | Re-add as `\multicolumn{N}{l}{...}` rows. |
| Bold/underline lost | The text layer carries no formatting, so "best is bold, second-best underlined" never survives | Rebuild from the caption's stated rule plus the values; flag the reconstruction as inferred, not verified. |
| Row label contaminated | `Agntic ExploitGym`, `Reasong GPQA Diamond` — a group name glued onto the next row's label | Split into the group row plus the clean label. |
| Shot/`-` columns shifted | A whole row one cell to the left because its `-` placeholders vanished | Check every row's `&` count with `check_tables.py`. |
| **Header written as flowing text** | `\multicolumn{7}{c}{Opus-5 GPT-5.6 Sol K3 GLM-5.3 DS-V4-Pro DS-V4-Flash\|DS-V4.1-Flash}` | The names are spaced by the typesetter and bear no relation to the columns below, so the table looks misaligned even though every number is right (the `Max` row underneath *does* align — that is the tell). Give each header its own cell, using `\shortstack{...}` where a name needs two lines, and keep the model order from the PDF. |
| **Multicolumn span count wrong** | A `\multicolumn{7}` in an 8-column table, or a row with one cell too few | Count the cells in every header and data row and reconcile against the declared column count. A span that is one short silently shifts the rest of the row. |
| **Label column too narrow, or `l` where it must wrap** | First column set to `3em` for a 4-character Chinese group label — the multirow text collides with the next column; or a model-name column left as `l`, so `DeepSeek-V4.1-Flash Base` pushes the row 20pt past the margin | Give prose columns an explicit `p{}`/`L{}` width in `em`. Measure the widest unbreakable token in each column — that, not the average, sets the minimum. |
| **Table wider than the text block** | 9 columns at `\normalsize` in a 452pt text block | Convert label columns to wrappable `L{}` and wrap the table in `{\footnotesize ... }`, keeping the size command *outside* the `longtable`. If it still overflows, the unbreakable header minimum is the floor — a residual overhang of a few points is usually acceptable; shrinking to `\scriptsize` rarely is. |

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
