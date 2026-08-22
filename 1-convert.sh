#!/usr/bin/env bash
# Stage 1: PST -> mbox files (one per Outlook folder) via readpst. Read-only on the PST.
# Usage: ./1-convert.sh maildata/foo.pst   -> workdata/foo/<folder tree>/*.mbox
set -euo pipefail
pst="${1:?usage: 1-convert.sh <file.pst>}"
name="$(basename "${pst%.pst}")"
out="workdata/$name"
command -v readpst >/dev/null || { echo "readpst missing: sudo apt install pst-utils" >&2; exit 1; }
mkdir -p "$out"
# -r: folder tree as directories (each folder -> an mbox named after it)
# -8: UTF-8 output   -w: overwrite   -j 0: single process (deterministic order)
readpst -r -8 -w -j 0 -o "$out" "$pst"
echo "--- mbox files under $out:"
find "$out" -type f | while read -r f; do
  n=$(grep -c '^From ' "$f" || true); printf '%6d  %s\n' "$n" "$f"
done
