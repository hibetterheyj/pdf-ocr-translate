---
name: pdf-ocr-translate
description: Translate OCR-produced LaTeX/Markdown papers into high-quality Chinese PDFs with source-PDF cross-checking, multi-agent chunked translation, heading normalization, high-resolution figure extraction, and reliable XeLaTeX/pandoc packaging. Use when the input comes from MinerU, Nougat, Mathpix, OCR-to-LaTeX pipelines, or other noisy PDF-to-LaTeX conversions and the user wants a polished translated PDF rather than raw OCR output.
---

# PDF OCR Translate

Use this skill as an orchestration layer on top of the local `pdf` skill when a user has:

- a source PDF,
- OCR-generated LaTeX or Markdown,
- noisy formulas, symbols, headings, or captions,
- blurry extracted figures,
- and a requirement to produce a polished translated PDF.

Follow this workflow:

1. Inspect the OCR project and the source PDF.
2. Initialize a separate working copy with `scripts/init_translation_workspace.sh`.
3. Extract a clean text layer and image candidates from the source PDF. Read [references/workflow.md](references/workflow.md).
4. Split translation into disjoint chunks and, when the user explicitly wants parallel work or the document is large, use multiple worker subagents for translation and consistency checking.
5. Apply the translation scope and heading rules from [references/translation-policy.md](references/translation-policy.md).
6. Normalize numbered headings with `scripts/normalize_heading_levels.py`.
7. Run `scripts/check_latex_translation.py` before compiling.
8. Compile natively with XeLaTeX or `latexmk`. If the user explicitly requires a pandoc-generated PDF artifact, compile native LaTeX first and then wrap the native PDF with pandoc using `scripts/build_pandoc_wrapper.py` or `scripts/compile_pdf.sh`.

Read these files only when needed:

- [references/workflow.md](references/workflow.md): full end-to-end workflow, including subagent chunking and delivery order.
- [references/translation-policy.md](references/translation-policy.md): what to translate, what to preserve, and heading mapping rules.
- [references/tooling-and-gotchas.md](references/tooling-and-gotchas.md): compilation strategy, font pitfalls, image heuristics, and lessons from a real session.
- [references/example-session.md](references/example-session.md): concrete local template paths from a successful OCR-to-Chinese-PDF run.

Use these scripts:

- `scripts/init_translation_workspace.sh`: create a safe working copy and scaffold `parts/` and `images_hi/`.
- `scripts/normalize_heading_levels.py`: convert OCR-numbered headings into proper LaTeX section commands and optionally demote selected unnumbered headings to bold inline headings.
- `scripts/check_latex_translation.py`: scan for untranslated prose, bad escapes, OCR placeholders, and unnormalized headings.
- `scripts/extract_hd_figures.py`: render candidate figure pages and/or extract embedded page images from the source PDF.
- `scripts/build_pandoc_wrapper.py`: create a minimal pandoc wrapper that inlines an already-compiled native PDF with `pdfpages`.
- `scripts/compile_pdf.sh`: compile native LaTeX robustly and optionally emit a pandoc PDF wrapper artifact.

Use these assets when helpful:

- [assets/pandoc_wrapper.template.md](assets/pandoc_wrapper.template.md): minimal pandoc wrapper template.
- [assets/font_preamble_snippet.tex](assets/font_preamble_snippet.tex): CJK-safe XeLaTeX font setup snippet for OCR translation projects.
- [assets/heading_examples.tex](assets/heading_examples.tex): examples of heading normalization and inline-bold demotion.
- [assets/deepseek_v4_paper_template/](assets/deepseek_v4_paper_template): a copyable modular starter project modeled on a DeepSeek_V4-scale OCR-LaTeX translation workflow, including `main.tex`, `parts/`, `images/`, `images_hi/`, and a pandoc wrapper.
