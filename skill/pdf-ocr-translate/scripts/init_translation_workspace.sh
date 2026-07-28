#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  init_translation_workspace.sh <ocr_project_dir> <output_dir>

Create a safe working copy for OCR-LaTeX translation.

Behavior:
  - copy the OCR project into <output_dir>
  - create parts/ and images_hi/ inside the working copy
  - refuse to overwrite a non-empty target directory
  - refuse if output_dir is under ocr_project_dir (would cause recursion)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -ne 2 ]]; then
  usage >&2
  exit 2
fi

src="$(realpath "$1")"
dst="$(realpath "$2" 2>/dev/null || echo "$2")"

if [[ ! -d "$src" ]]; then
  echo "Source directory not found: $src" >&2
  exit 1
fi

# Safety: prevent infinite recursion when dst is under src
if [[ "$dst" == "$src"* ]]; then
  echo "ERROR: Output directory must NOT be under the source directory." >&2
  echo "  source: $src" >&2
  echo "  output: $dst" >&2
  echo "  This would cause an infinite copy loop." >&2
  exit 1
fi

if [[ -e "$dst" ]]; then
  if [[ ! -d "$dst" ]]; then
    echo "Target exists and is not a directory: $dst" >&2
    exit 1
  fi
  if [[ -n "$(find "$dst" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
    echo "Target directory is not empty: $dst" >&2
    exit 1
  fi
else
  mkdir -p "$dst"
fi

cp -R "$src"/. "$dst"/
mkdir -p "$dst/parts" "$dst/images_hi"

printf 'Workspace initialized:\n'
printf '  source : %s\n' "$src"
printf '  target : %s\n' "$dst"
printf '  parts  : %s\n' "$dst/parts"
printf '  images : %s\n' "$dst/images_hi"
