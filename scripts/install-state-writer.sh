#!/usr/bin/env bash
#
# Install the task-relay state-writer subagent for Claude Code, Codex CLI and Cursor (D10).
#
# Usage: install-state-writer.sh [--dry-run] [--force] [--claude-only|--codex-only|--cursor-only]
#
#   Claude Code -> ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/agents/task-relay-state-writer.md
#   Codex CLI   -> ${CODEX_HOME:-$HOME/.codex}/agents/task-relay-state-writer.toml
#   Cursor      -> ${CURSOR_CONFIG_DIR:-$HOME/.cursor}/agents/task-relay-state-writer.md
#
# An existing file that is identical to the shipped definition counts as
# "already installed". An existing file that differs is left alone unless
# --force is passed.

set -u

usage() {
  cat <<'USAGE'
Usage: install-state-writer.sh [OPTIONS]

Install the task-relay state-writer subagent for all supported clients:
  Claude Code -> ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/agents/task-relay-state-writer.md
  Codex CLI   -> ${CODEX_HOME:-$HOME/.codex}/agents/task-relay-state-writer.toml
  Cursor      -> ${CURSOR_CONFIG_DIR:-$HOME/.cursor}/agents/task-relay-state-writer.md

Options:
  --dry-run       Print the actions and change nothing.
  --force         Replace an existing file that differs from the shipped one.
  --claude-only   Install only the Claude Code subagent.
  --codex-only    Install only the Codex subagent.
  --cursor-only   Install only the Cursor subagent.
  -h, --help      Show this help.
USAGE
}

dry_run=0
force=0
do_claude=1
do_codex=1
do_cursor=1

for arg in "$@"; do
  case "$arg" in
    --dry-run) dry_run=1 ;;
    --force) force=1 ;;
    --claude-only) do_codex=0; do_cursor=0 ;;
    --codex-only) do_claude=0; do_cursor=0 ;;
    --cursor-only) do_claude=0; do_codex=0 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "install-state-writer: unknown option: $arg" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "${BASH_SOURCE[0]}" in
  */*) script_dir=${BASH_SOURCE[0]%/*} ;;
  *) script_dir=. ;;
esac
source_root=$(CDPATH= cd -- "$script_dir/.." && pwd)

python_missing_note() {
  # The state writer needs the renderer, which needs python3 (D13).
  if ! command -v python3 >/dev/null 2>&1; then
    echo "install-state-writer: warning: python3 not found; the state writer needs it to render the dashboard (D11)" >&2
  fi
}

install_one() {
  src=$1
  dest=$2

  if [ ! -f "$src" ]; then
    echo "install-state-writer: missing source file: $src" >&2
    return 1
  fi

  if [ -f "$dest" ] && cmp -s "$src" "$dest"; then
    echo "already installed: $dest"
    return 0
  fi

  if [ -f "$dest" ]; then
    if [ "$force" -ne 1 ]; then
      echo "install-state-writer: refusing to overwrite $dest (it differs from $src); re-run with --force" >&2
      if [ "$dry_run" -eq 1 ]; then
        echo "[dry-run] would refuse: $dest"
      fi
      return 1
    fi
    action="overwrite"
  else
    action="install"
  fi

  if [ "$dry_run" -eq 1 ]; then
    echo "[dry-run] $action: $src -> $dest"
    return 0
  fi

  case "$dest" in
    */*) dest_dir=${dest%/*} ;;
    *) dest_dir=. ;;
  esac

  if ! mkdir -p -- "$dest_dir"; then
    echo "install-state-writer: cannot create $dest_dir" >&2
    return 1
  fi
  if ! cp -- "$src" "$dest"; then
    echo "install-state-writer: cannot write $dest" >&2
    return 1
  fi

  echo "$action: $dest"
  return 0
}

status=0

if [ "$do_claude" -eq 1 ]; then
  claude_dir=${CLAUDE_CONFIG_DIR:-$HOME/.claude}
  install_one "$source_root/assets/agents/claude/task-relay-state-writer.md" \
    "$claude_dir/agents/task-relay-state-writer.md" || status=1
fi

if [ "$do_codex" -eq 1 ]; then
  codex_home=${CODEX_HOME:-$HOME/.codex}
  install_one "$source_root/assets/agents/codex/task-relay-state-writer.toml" \
    "$codex_home/agents/task-relay-state-writer.toml" || status=1
fi

if [ "$do_cursor" -eq 1 ]; then
  cursor_dir=${CURSOR_CONFIG_DIR:-$HOME/.cursor}
  install_one "$source_root/assets/agents/cursor/task-relay-state-writer.md" \
    "$cursor_dir/agents/task-relay-state-writer.md" || status=1
fi

if [ "$status" -eq 0 ] && [ "$dry_run" -eq 0 ]; then
  python_missing_note
fi

exit "$status"
