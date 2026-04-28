# Tooling and Gotchas

## Use the Neighboring PDF Skill

This skill should not duplicate generic PDF extraction advice. Reuse the local `pdf` skill for:

- text extraction,
- table extraction,
- OCR fallbacks,
- basic PDF manipulation.

This skill adds the OCR-LaTeX translation workflow on top.

## Prefer Native LaTeX Compilation

Complex OCR-derived LaTeX often contains:

- custom pandoc macros,
- fragile longtables,
- OCR noise in math,
- custom font logic,
- mixed English/CJK content.

Direct `pandoc input.tex -o out.pdf` often breaks or rewrites the source in unstable ways.

Recommended order:

1. Compile native TeX with `latexmk -xelatex` if available.
2. Fall back to repeated `xelatex` runs.
3. If the user explicitly needs a pandoc-generated artifact, wrap the already compiled native PDF using `pdfpages`.

## Font Snippet

If CJK font loading fails, start from [assets/font_preamble_snippet.tex](../assets/font_preamble_snippet.tex).

Key lessons from a real run:

- `\usepackage[fontset=none]{ctex}` is safer than relying on ctex defaults.
- Explicitly set `\setCJKmainfont` and `\setmainfont`.
- Use multiple fallbacks, for example:
  - `Source Han Serif CN`
  - `Noto Serif CJK SC`
  - `PingFang SC`
  - `SimSun`
  - `FangSong`
  - `Arial Unicode MS`

## Figure Extraction Heuristics

Use `pdfimages -list` first.

- If the source PDF has large embedded JPEG/PNG assets on the relevant page, extract them directly with `pdfimages`.
- If the figure is mostly vector charts or OCR split it into many tiny fragments, render the full page at high DPI with `pdftocairo` and crop the panel you need.

Example commands:

```bash
pdfimages -list source.pdf
python3 scripts/extract_hd_figures.py --pdf source.pdf --output-dir images_hi --pdfimages-pages 43,56
python3 scripts/extract_hd_figures.py --pdf source.pdf --output-dir images_hi --render-pages 1 --crop page=1,x=520,y=3900,w=3900,h=2050,name=Figure1_hi.png
```

## Common OCR Failures To Catch

- section titles encoded as `\section{2.3.4. ...}`
- literal `??` placeholders
- malformed math delimiters such as `\$ ... \$`
- literal escaped newlines inside prose prompts
- special symbols replaced by missing glyphs or invisible control characters
- source PDF screenshots exported as tiny low-resolution OCR images

## Packaging Strategy

When the user says "use pandoc", clarify whether they mean:

- "compile the final PDF somehow", or
- "the final artifact must be produced by pandoc".

If the second requirement is strict, use the wrapper approach. That preserves the native XeLaTeX result while still producing a pandoc-authored PDF container.
