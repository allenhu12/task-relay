#!/bin/bash
# generate-manifest.sh — Generate 10-reference/MANIFEST.md from file frontmatters
#
# Usage:
#   bash generate-manifest.sh [REFDIR]
#
# REFDIR defaults to "10-reference" if not specified.
# Run from the project root directory.
#
# This script reads YAML frontmatter from markdown files in the reference
# directory and generates a MANIFEST.md index file. The agent reads this
# single file during State Recovery instead of scanning all reference files.

set -euo pipefail

REFDIR="${1:-10-reference}"
MANIFEST="$REFDIR/MANIFEST.md"
SPEC_PATTERN="000_*_spec.md"

if [ ! -d "$REFDIR" ]; then
  echo "Error: Directory '$REFDIR' not found. Run from the project root." >&2
  exit 1
fi

# Write header
cat > "$MANIFEST" << 'HEADER'
# Reference Manifest

> Read this file to discover available references. Do NOT load reference
> files unless they are relevant to the current item. Use descriptions
> below to decide.

| File | Description | Tags |
|------|-------------|------|
HEADER

# Track if we found any files
found_files=0

for f in "$REFDIR"/*; do
  [ -e "$f" ] || continue  # handle empty directory

  filename=$(basename "$f")

  # Skip MANIFEST itself and the spec file
  [[ "$filename" == "MANIFEST.md" ]] && continue
  [[ "$filename" == $SPEC_PATTERN ]] && continue

  # Only process markdown files (non-markdown files need manual entries)
  if [[ "$f" != *.md ]]; then
    echo "Skipped (non-markdown): $filename — add manually to MANIFEST.md" >&2
    continue
  fi

  # Extract description from YAML frontmatter
  desc=""
  tags=""
  in_frontmatter=0
  line_num=0

  while IFS= read -r line; do
    line_num=$((line_num + 1))

    # Detect frontmatter boundaries
    if [ "$line_num" -eq 1 ] && [ "$line" = "---" ]; then
      in_frontmatter=1
      continue
    fi
    if [ "$in_frontmatter" -eq 1 ] && [ "$line" = "---" ]; then
      break
    fi
    if [ "$in_frontmatter" -eq 0 ]; then
      break  # No frontmatter found
    fi

    # Extract description field
    if [[ "$line" =~ ^description:\ *\"?(.*)\"?$ ]]; then
      desc="${BASH_REMATCH[1]}"
      # Strip trailing quote if present
      desc="${desc%\"}"
    fi

    # Extract tags field
    if [[ "$line" =~ ^tags:\ *\[(.*)\ *\]$ ]]; then
      tags="${BASH_REMATCH[1]}"
    fi

    # Safety: don't read beyond line 30
    [ "$line_num" -gt 30 ] && break
  done < "$f"

  # Default if no description found
  [ -z "$desc" ] && desc="(no description — add frontmatter)"

  echo "| \`$filename\` | $desc | $tags |" >> "$MANIFEST"
  found_files=$((found_files + 1))
done

if [ "$found_files" -eq 0 ]; then
  echo "| *(no reference files yet)* | — | — |" >> "$MANIFEST"
fi

# Append manual section marker
cat >> "$MANIFEST" << 'FOOTER'

<!-- Manual entries for non-markdown files (PDF, JSON, images, etc.) -->
<!-- Add entries below in the same table format: -->
<!-- | `filename.pdf` | Description of the file | tags | -->
FOOTER

echo "Generated: $MANIFEST ($found_files files indexed)"
