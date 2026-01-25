#!/usr/bin/env bash
set -euo pipefail

start_pattern="^\\*\\*\\* START OF THE PROJECT GUTENBERG EBOOK .* \\*\\*\\*$"
end_pattern="^\\*\\*\\* END OF THE PROJECT GUTENBERG EBOOK .* \\*\\*\\*$"

usage() {
  cat <<'USAGE'
Usage: prepare_gutenberg_corpus.sh <input_file> [input_file...]

Extracts text between Project Gutenberg START/END markers for any ebook.
Concatenates extracted content from all input files to stdout.
USAGE
}

if [[ ${#} -lt 1 ]]; then
  usage >&2
  exit 2
fi

overall_status=0

for input_file_path in "$@"; do
  if [[ ! -f "${input_file_path}" ]]; then
    echo "Input file not found: ${input_file_path}" >&2
    overall_status=1
    continue
  fi

  awk -v start_pattern="${start_pattern}" -v end_pattern="${end_pattern}" '
    $0 ~ start_pattern { in_block = 1; found_start = 1; next }
    $0 ~ end_pattern { found_end = 1; exit }
    in_block { print }
    END {
      if (!found_start || !found_end) {
        exit 3
      }
    }
  ' "${input_file_path}" || {
    status=$?
    if [[ ${status} -eq 3 ]]; then
      echo "Warning: markers not found in ${input_file_path}" >&2
      overall_status=3
    else
      overall_status=${status}
    fi
  }
done

exit "${overall_status}"
