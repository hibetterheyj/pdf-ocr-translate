#!/usr/bin/env bash
# Rebuild parts/ from main.tex with figures, heading fixes, and figure ordering.
#
# WARNING: this DELETES parts/ and regenerates it from main.tex. Once translation
# has begun, parts/ holds the translated text and re-running this script destroys
# it. It is only safe to run before the translation pass, or after re-applying the
# translation. Set FORCE=1 to acknowledge and proceed anyway.
#
# Run from translate_latex/. Idempotent with respect to main.tex: parts/ is
# regenerated from scratch, so re-running after editing the pipeline scripts is
# safe as long as no translation has been written into parts/.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL="$HERE/../../../skill/pdf-ocr-translate"
PY="${PY:-python3}"

cd "$HERE"

if [ -d parts ] && [ "${FORCE:-0}" != "1" ] && \
   "$PY" -c "
import sys, pathlib
for p in pathlib.Path('parts').glob('*.tex'):
    if any('一' <= c <= '鿿' for c in p.read_text(errors='ignore')):
        sys.exit(0)
sys.exit(1)
" ; then
    echo "refusing to overwrite parts/: it contains translated (CJK) text." >&2
    echo "set FORCE=1 if you really mean to regenerate everything from main.tex." >&2
    exit 1
fi

rm -rf parts
mkdir -p parts

"$PY" "$SKILL/scripts/split_translation_chunks.py" main.tex \
    --output-dir parts --pdf-pages-dir ../pdf_pages
"$PY" patch_preamble.py parts/chunk_00_preamble.tex
"$PY" convert_figures.py --parts parts
"$PY" fix_headings.py --parts parts
"$PY" fix_lost_math.py --parts parts
"$PY" fix_figure_order.py parts/11_body.tex

echo "parts/ rebuilt: $(ls parts/*.tex | wc -l | tr -d ' ') chunks"
