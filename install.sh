#!/usr/bin/env bash
#
# Install the task-relay skill and its state-writer subagent for one client.

set -u

usage() {
  cat <<'USAGE'
Usage: install.sh CLIENT [OPTIONS]

Install the task-relay skill and state-writer subagent in one operation.

Clients (choose exactly one):
  --cursor       Install for Cursor Agent.
  --claude       Install for Claude Code.
  --codex        Install for Codex CLI.

Options:
  --dry-run      Print the actions and change nothing.
  --force        Replace installed task-relay files that differ.
  -h, --help     Show this help.
USAGE
}

client=""
dry_run=0
force=0

for arg in "$@"; do
  case "$arg" in
    --cursor|--claude|--codex)
      selected=${arg#--}
      if [ -n "$client" ] && [ "$client" != "$selected" ]; then
        echo "task-relay install: choose exactly one client" >&2
        usage >&2
        exit 2
      fi
      client=$selected
      ;;
    --dry-run) dry_run=1 ;;
    --force) force=1 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "task-relay install: unknown option: $arg" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$client" ]; then
  echo "task-relay install: choose one client: --cursor, --claude, or --codex" >&2
  usage >&2
  exit 2
fi

case "${BASH_SOURCE[0]}" in
  */*) script_dir=${BASH_SOURCE[0]%/*} ;;
  *) script_dir=. ;;
esac
source_root=$(CDPATH= cd -- "$script_dir" && pwd)

case "$client" in
  cursor)
    client_home=${CURSOR_CONFIG_DIR:-$HOME/.cursor}
    writer_flag=--cursor-only
    writer_src=$source_root/assets/agents/cursor/task-relay-state-writer.md
    writer_dest=$client_home/agents/task-relay-state-writer.md
    ;;
  claude)
    client_home=${CLAUDE_CONFIG_DIR:-$HOME/.claude}
    writer_flag=--claude-only
    writer_src=$source_root/assets/agents/claude/task-relay-state-writer.md
    writer_dest=$client_home/agents/task-relay-state-writer.md
    ;;
  codex)
    client_home=${CODEX_HOME:-$HOME/.codex}
    writer_flag=--codex-only
    writer_src=$source_root/assets/agents/codex/task-relay-state-writer.toml
    writer_dest=$client_home/agents/task-relay-state-writer.toml
    ;;
esac

skill_dest=$client_home/skills/task-relay
package_files=(
  "$source_root/SKILL.md"
  "$source_root/install.sh"
  "$source_root/user-guide.md"
  "$source_root/CONTEXT.md"
)

for package_dir in assets references scripts; do
  while IFS= read -r -d '' path; do
    package_files+=("$path")
  done < <(find "$source_root/$package_dir" -type f \
    ! -path '*/__pycache__/*' ! -name '*.pyc' ! -name '.DS_Store' -print0)
done

# Preflight the complete skill before writing any file. The state writer is
# installed only after this check and the skill copy both succeed.
if [ -e "$writer_dest" ] && [ ! -f "$writer_dest" ]; then
  echo "task-relay install: refusing to replace non-file path $writer_dest" >&2
  exit 1
fi
if [ "$force" -ne 1 ] && [ -f "$writer_dest" ] && ! cmp -s "$writer_src" "$writer_dest"; then
  echo "task-relay install: refusing to overwrite $writer_dest (it differs from $writer_src); re-run with --force" >&2
  if [ "$dry_run" -eq 1 ]; then
    echo "[dry-run] would refuse: $writer_dest"
  fi
  exit 1
fi
for src in "${package_files[@]}"; do
  rel=${src#"$source_root/"}
  dest=$skill_dest/$rel
  if [ -e "$dest" ] && [ ! -f "$dest" ]; then
    echo "task-relay install: refusing to replace non-file path $dest" >&2
    exit 1
  fi
  if [ "$force" -ne 1 ] && [ -f "$dest" ] && ! cmp -s "$src" "$dest"; then
    echo "task-relay install: refusing to overwrite $dest (it differs from $src); re-run with --force" >&2
    if [ "$dry_run" -eq 1 ]; then
      echo "[dry-run] would refuse: $dest"
    fi
    exit 1
  fi
done

for src in "${package_files[@]}"; do
  rel=${src#"$source_root/"}
  dest=$skill_dest/$rel

  if [ -f "$dest" ] && cmp -s "$src" "$dest"; then
    echo "already installed: $dest"
    continue
  fi

  if [ -f "$dest" ]; then
    action=overwrite
  else
    action=install
  fi

  if [ "$dry_run" -eq 1 ]; then
    echo "[dry-run] $action: $src -> $dest"
    continue
  fi

  dest_dir=${dest%/*}
  if ! mkdir -p -- "$dest_dir"; then
    echo "task-relay install: cannot create $dest_dir" >&2
    exit 1
  fi
  if ! cp -- "$src" "$dest"; then
    echo "task-relay install: cannot write $dest" >&2
    exit 1
  fi
  echo "$action: $dest"
done

writer_args=("$writer_flag")
if [ "$dry_run" -eq 1 ]; then
  writer_args+=(--dry-run)
fi
if [ "$force" -eq 1 ]; then
  writer_args+=(--force)
fi

if ! bash "$source_root/scripts/install-state-writer.sh" "${writer_args[@]}"; then
  echo "task-relay install: state-writer installation failed" >&2
  exit 1
fi

if [ "$dry_run" -eq 0 ]; then
  echo "task-relay installed for $client: $skill_dest"
fi
