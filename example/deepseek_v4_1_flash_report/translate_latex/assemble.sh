#!/usr/bin/env bash
# Assemble the translated chunks into main_cn.tex and compile it with XeLaTeX.
#
# Run from translate_latex/ after the translation pass has written parts/.
# Safe to re-run: main_cn.tex is regenerated from parts/ each time, and parts/
# is never modified here.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL="$HERE/../../../skill/pdf-ocr-translate"
PY="${PY:-python3}"

cd "$HERE"

"$PY" refine_terminology.py --parts parts
"$PY" merge_chunks.py parts --output main_cn.tex
"$PY" fix_table_width.py main_cn.tex
"$PY" "$SKILL/scripts/normalize_heading_levels.py" main_cn.tex --write
"$PY" fix_after_normalize.py main_cn.tex

rm -rf build/final
mkdir -p build/final
cp main_cn.tex build/final/
ln -sfn "$HERE/images" build/final/images
ln -sfn "$HERE/images_hi" build/final/images_hi

cd build/final
for _ in 1 2 3; do
    xelatex -interaction=nonstopmode main_cn.tex >/dev/null 2>&1 || true
done

errors=$(grep -c '^!' main_cn.log || true)
missing=$(grep -c 'Missing character' main_cn.log || true)
pages=$("$PY" -c "import fitz;print(fitz.open('main_cn.pdf').page_count)" 2>/dev/null || echo '?')
echo "compile: ${errors} error(s), ${missing} missing glyph(s), ${pages} pages"
