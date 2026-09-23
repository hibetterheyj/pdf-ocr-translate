#!/bin/bash
# Rebuild the pre-translation source `main.tex` from the two OCR outputs.
#
# Run this ONLY before translating: the later steps rewrite the frontmatter and
# strip the OCR image stubs, so running it over translated chunks would discard
# the Chinese.  After translation, `assemble.sh` merges and compiles instead.
#
# The table-width / caption / footnote / leaked-label passes run here *and* in
# assemble.sh.  They are idempotent, so running both is safe, and it means a
# translation that predates a given fix still picks it up at merge time.
set -euo pipefail
cd "$(dirname "$0")"

PY="${PY:-/Users/he/Documents/cn_data_pipeline/env/data_env/bin/python}"

echo "== 1/9 hybrid base: v2 prose + v1 tables =="
"$PY" build_hybrid.py \
    --v2 ../ocr_latex/MiMo_V26_ocr_latex_v2.tex \
    --v1 ../ocr_latex/MiMo_V26_ocr_latex_v1.tex \
    --out main.tex

echo "== 2/9 OCR artifact sweep =="
"$PY" fix_ocr_artifacts.py main.tex -v

echo "== 3/9 dropped math + equation (1) =="
"$PY" fix_lost_math.py main.tex

echo "== 4/9 ligature restoration =="
"$PY" fix_ligatures.py main.tex

echo "== 5/12 table widths =="
"$PY" fix_table_width.py main.tex

echo "== 6/12 table captions + footnotes + leaked figure labels =="
"$PY" fix_table_captions.py main.tex
"$PY" fix_footnotes.py main.tex
"$PY" strip_leaked_figure_labels.py main.tex

echo "== 7/12 figure stubs -> figure environments =="
"$PY" convert_figures.py main.tex

echo "== 8/12 strip the hand-built OCR contents =="
"$PY" strip_ocr_contents.py main.tex

echo "== 9/12 preamble (fonts, logo, captions) =="
"$PY" patch_preamble.py main.tex

echo "== 10/12 split into translation chunks =="
rm -rf parts
"$PY" split_translation_chunks.py main.tex --output-dir parts --pdf-pages-dir ../pdf_pages

"$PY" check_structure.py --parts parts --baseline structure_baseline.json
echo "source rebuilt."
