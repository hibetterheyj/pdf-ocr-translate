#!/bin/bash
# Merge the translated chunks and compile the Chinese PDF.
#
# Run this ONLY after `build_source.sh` and the translation pass: the merge
# consumes `parts/`, and re-running build_source.sh would overwrite it.
#
#   build_source.sh   -> main.tex (+ parts/, pre-translation)
#   [translation]     -> parts/ in Chinese
#   assemble.sh       -> build/final/main_cn.pdf
set -euo pipefail
cd "$(dirname "$0")"

PY="${PY:-/Users/he/Documents/cn_data_pipeline/env/data_env/bin/python}"

echo "== 1/6 repair short table rows =="
"$PY" check_tables.py --parts parts --fix

echo "== 2/6 merge chunks, inject the table of contents =="
"$PY" merge_chunks.py --parts parts --output main_cn.tex

echo "== 3/6 normalize heading levels =="
"$PY" normalize_heading_levels.py main_cn.tex --write

echo "== 4/6 post-normalization fixes (摘要 / 参考文献) =="
"$PY" fix_after_normalize.py main_cn.tex

echo "== 5/6 idempotent source passes (no-op on a fresh split) =="
"$PY" patch_preamble.py main_cn.tex
"$PY" fix_table_width.py main_cn.tex
"$PY" fix_table_captions.py main_cn.tex
"$PY" fix_footnotes.py main_cn.tex
"$PY" strip_leaked_figure_labels.py main_cn.tex

echo "== 6/6 compile =="
mkdir -p build/final
cp main_cn.tex build/final/
cd build/final
[ -d images_hi ] || cp -R ../../images_hi .
for _ in 1 2 3; do
    xelatex -interaction=nonstopmode main_cn.tex > /dev/null 2>&1 || true
done

echo
echo "errors:        $(grep -c '^!' main_cn.log || true)"
echo "missing glyph: $(grep -c 'Missing character' main_cn.log || true)"
echo "overfull:      $(grep -c 'Overfull \\hbox' main_cn.log || true)"
grep -o 'Output written.*' main_cn.log || true
echo
echo "layout audit:"
cd .. && "$PY" ../audit_layout.py --pdf final/main_cn.pdf --margin 555 | tail -3
