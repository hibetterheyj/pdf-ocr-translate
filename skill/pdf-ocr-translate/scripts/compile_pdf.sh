#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  compile_pdf.sh <main.tex> [pandoc_output.pdf]

Compile native LaTeX first. If a second argument is provided, also emit a pandoc-generated
wrapper PDF that inlines the native PDF using pdfpages.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage >&2
  exit 2
fi

main_tex="$1"
main_dir="$(cd "$(dirname "$main_tex")" && pwd)"
main_file="$(basename "$main_tex")"
base_name="${main_file%.tex}"
native_pdf="$main_dir/$base_name.pdf"

cd "$main_dir"

if command -v latexmk >/dev/null 2>&1; then
  latexmk -xelatex -interaction=nonstopmode -halt-on-error "$main_file"
else
  xelatex -interaction=nonstopmode -halt-on-error "$main_file"
  xelatex -interaction=nonstopmode -halt-on-error "$main_file"
  xelatex -interaction=nonstopmode -halt-on-error "$main_file"
fi

echo "Native PDF: $native_pdf"

if [[ $# -eq 2 ]]; then
  pandoc_output="$2"
  wrapper="$main_dir/.pandoc_wrapper.auto.md"
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  python3 "$script_dir/build_pandoc_wrapper.py" --pdf "$native_pdf" --output "$wrapper" >/dev/null
  pandoc "$wrapper" -o "$pandoc_output" --pdf-engine=xelatex
  echo "Pandoc PDF: $pandoc_output"
fi
