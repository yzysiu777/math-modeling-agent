#!/bin/sh

# Read-only preflight for a competition-paper PDF.
# It is a warning-oriented check, not proof of mathematical correctness or official compliance.

set -eu

if [ "$#" -lt 1 ]; then
  echo "Usage: check_pdf.sh PAPER.pdf [identity-token ...]" >&2
  exit 2
fi

pdf=$1
shift

if [ ! -f "$pdf" ]; then
  echo "FAIL missing file: $pdf" >&2
  exit 1
fi

for tool in file pdfinfo pdftotext shasum rg; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "FAIL required tool not found: $tool" >&2
    exit 1
  fi
done

file_type=$(file -b "$pdf")
case "$file_type" in
  *PDF*) ;;
  *)
    echo "FAIL not recognized as PDF: $file_type" >&2
    exit 1
    ;;
esac

tmp_dir=$(mktemp -d /tmp/huawei-paper-check.XXXXXX)
trap 'rm -rf "$tmp_dir"' EXIT HUP INT TERM

info="$tmp_dir/pdfinfo.txt"
text="$tmp_dir/paper.txt"
pdfinfo "$pdf" > "$info"
pdftotext -layout "$pdf" "$text"

pages=$(awk '/^Pages:/ {print $2; exit}' "$info")
size=$(awk '/^Page size:/ {$1=""; $2=""; sub(/^ +/, ""); print; exit}' "$info")
bytes=$(wc -c < "$pdf" | tr -d ' ')
hash=$(shasum -a 256 "$pdf" | awk '{print $1}')

echo "PDF: $pdf"
echo "Pages: $pages"
echo "Page size: $size"
echo "Bytes: $bytes"
echo "SHA-256: $hash"

status=0

for marker in 摘要 关键词 参考文献; do
  if rg -q "$marker" "$text"; then
    echo "PASS marker: $marker"
  else
    echo "WARN marker not found: $marker"
    status=1
  fi
done

if rg -q '页眉|Header' "$text"; then
  echo "WARN header-like text detected; inspect visually and compare with the current official template."
  status=1
else
  echo "PASS no header-like text detected by text extraction"
fi

if [ "$#" -gt 0 ]; then
  for token in "$@"; do
    if awk -v RS='\f' -v needle="$token" 'NR > 1 && index($0, needle) {found=1} END {exit(found ? 0 : 1)}' "$text"; then
      echo "WARN identity token appears after cover: $token"
      status=1
    else
      echo "PASS identity token absent after cover: $token"
    fi
  done
fi

echo "NOTE visual rendering, official-template comparison, equation/figure/table continuity, source correctness, and human sign-off remain mandatory."
exit "$status"
