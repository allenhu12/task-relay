#!/bin/bash
# rotate-progress-log.sh — Rotate 00-current/progress.log when it grows large,
# archive it to 90-archive/progress-log/, and update
# 90-archive/progress-log/PROGRESS-ARCHIVE-MANIFEST.md.
#
# Usage:
#   bash rotate-progress-log.sh [--threshold-lines N] [--threshold-bytes N] [--force] [--manifest-only]
#
# Defaults:
#   --threshold-lines 1000
#   --threshold-bytes 204800   (200 KB)
#
# Behavior:
#   1. If progress.log is under both thresholds and --force not set, exits cleanly.
#   2. Otherwise, archives 00-current/progress.log to
#      90-archive/progress-log/progress-archive-YYYY-MM-DD.log (suffix added if collision).
#   3. Creates a fresh 00-current/progress.log with a continuity header that
#      links to the archive and shows cumulative stats.
#   4. Regenerates 90-archive/progress-log/PROGRESS-ARCHIVE-MANIFEST.md from all archive files.
#
# Use --manifest-only to skip rotation and just rebuild the manifest (e.g. for
# staleness recovery if files were added/removed by hand).
#
# State-recovery rule: ONLY read 00-current/progress.log during state recovery.
# NEVER auto-load archives from 90-archive/ — they exist for audit purposes only.
#
# Run from the project root directory.

set -euo pipefail

THRESHOLD_LINES=1000
THRESHOLD_BYTES=204800
FORCE=0
MANIFEST_ONLY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --threshold-lines) THRESHOLD_LINES="$2"; shift 2 ;;
    --threshold-bytes) THRESHOLD_BYTES="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    --manifest-only) MANIFEST_ONLY=1; shift ;;
    -h|--help) sed -n '2,32p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

LOG="00-current/progress.log"
ARCHIVEDIR="90-archive/progress-log"
MANIFEST="$ARCHIVEDIR/PROGRESS-ARCHIVE-MANIFEST.md"

if [ ! -d "00-current" ]; then
  echo "Error: run from the project root (need 00-current/)." >&2
  exit 1
fi

# Create archive directory if it doesn't exist
mkdir -p "$ARCHIVEDIR"

# ---------- helpers ----------

# Extract first/last "### Session" date stamps from a log file.
extract_date_range() {
  local file="$1"
  local first last
  first=$(grep -E '^### Session ' "$file" 2>/dev/null | head -1 \
          | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1 || true)
  last=$(grep -E '^### Session ' "$file" 2>/dev/null | tail -1 \
         | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1 || true)
  [ -z "$first" ] && first="?"
  [ -z "$last" ] && last="?"
  echo "$first → $last"
}

# Extract item IDs touched in the file.
extract_items() {
  local file="$1"
  grep -oiE '\bitem-[0-9]+\b' "$file" 2>/dev/null \
    | tr '[:lower:]' '[:upper:]' | sort -u | paste -sd, - || true
}

# Extract milestones
extract_milestones() {
  local file="$1"
  local out
  out=$(grep -E '^\*\*Milestone\*\*:|^## Milestone' "$file" 2>/dev/null \
        | sed -E 's/^\*\*Milestone\*\*:[[:space:]]*//; s/^## Milestone[[:space:]]*-?[[:space:]]*//' \
        | head -5 | paste -sd'; ' - || true)
  [ -z "$out" ] && out="(none flagged)"
  echo "$out"
}

# Count completed-item events in a log file.
count_completed() {
  local file="$1"
  grep -ciE 'complet(ed|ion)[^A-Za-z]+item-[0-9]+|status:[[:space:]]*completed' "$file" 2>/dev/null || echo 0
}

write_manifest() {
  {
    cat <<'HEADER'
# Progress Log Archive Manifest

> Read this file to discover archived progress logs. NEVER load archives during
> normal state recovery — only on demand when the current item references context
> outside the fresh `00-current/progress.log`.
> Match by date, item IDs, or milestone keywords.

| File | Date range | Items touched | Completed events | Key milestones |
|------|-----------|---------------|------------------|----------------|
HEADER

    local count=0
    for f in "$ARCHIVEDIR"/progress-archive-*.log; do
      [ -e "$f" ] || continue
      local name range items milestones completed
      name=$(basename "$f")
      range=$(extract_date_range "$f")
      items=$(extract_items "$f")
      [ -z "$items" ] && items="(none parsed)"
      milestones=$(extract_milestones "$f")
      completed=$(count_completed "$f")
      echo "| \`$name\` | $range | $items | $completed | $milestones |"
      count=$((count + 1))
    done

    if [ "$count" -eq 0 ]; then
      echo "| *(no archives yet)* | — | — | — | — |"
    fi

    cat <<'FOOTER'

<!-- Regenerate with: bash {SKILL_SCRIPTS_PATH}/rotate-progress-log.sh --manifest-only -->
<!-- Staleness check: compare `ls 90-archive/progress-log/progress-archive-*.log` against the table above. -->
FOOTER
  } > "$MANIFEST"

  echo "Wrote: $MANIFEST"
}

# ---------- manifest-only path ----------

if [ "$MANIFEST_ONLY" -eq 1 ]; then
  write_manifest
  exit 0
fi

# ---------- rotation path ----------

if [ ! -f "$LOG" ]; then
  echo "No $LOG to rotate. (Did the project initialize?)" >&2
  exit 0
fi

lines=$(wc -l < "$LOG" | tr -d ' ')
bytes=$(wc -c < "$LOG" | tr -d ' ')

if [ "$FORCE" -ne 1 ] && [ "$lines" -lt "$THRESHOLD_LINES" ] && [ "$bytes" -lt "$THRESHOLD_BYTES" ]; then
  echo "No rotation needed: $lines lines / $bytes bytes (thresholds: $THRESHOLD_LINES lines / $THRESHOLD_BYTES bytes)."
  exit 0
fi

# Pick archive filename
today=$(date +%Y-%m-%d)
target="$ARCHIVEDIR/progress-archive-$today.log"
suffix=1
while [ -e "$target" ]; do
  target="$ARCHIVEDIR/progress-archive-$today-$suffix.log"
  suffix=$((suffix + 1))
done

# Snapshot stats from the file we are about to archive (for the new header)
range=$(extract_date_range "$LOG")
items=$(extract_items "$LOG")
[ -z "$items" ] && items="(none parsed)"
completed=$(count_completed "$LOG")
milestones=$(extract_milestones "$LOG")

mv "$LOG" "$target"
echo "Archived: $target ($lines lines, $bytes bytes)"

# Build fresh progress.log with a continuity header
cat > "$LOG" <<EOF
# Assignment Progress Log

**Status**: rotated on $today — prior history archived.

> Continuity header (auto-generated by rotate-progress-log.sh).
> Read \`90-archive/progress-log/PROGRESS-ARCHIVE-MANIFEST.md\` to discover all archives.
> Pull a specific archive ONLY when the current item needs detail beyond what's in
> this fresh log and the canonical state files
> (\`00-current/item-list.json\`, \`00-current/item-list-archive.json\`).
> NEVER load archives speculatively during state recovery.

## Carry-Over Summary (from $(basename "$target"))

- **Date range archived**: $range
- **Items referenced**: $items
- **Completed events in archive**: $completed
- **Flagged milestones**: $milestones
- **Archive file**: [[$(basename "$target" .log)]]

---

### Session - $today
**Phase**: Post-rotation continuation
**Notes**: Fresh progress.log started after rotation. See archive above for prior sessions.

EOF

echo "Created fresh: $LOG"

write_manifest
