#!/bin/sh
# Thin wrapper for scripts/render-dashboard.py (D13).
#
# Checks for python3 first so a missing interpreter produces one clear message
# and exit code 127 (acceptance A6). Uses only shell builtins, so it still runs
# when PATH is empty or unusual.
#
# Usage: sh scripts/render-dashboard.sh <project_root>

if ! command -v python3 >/dev/null 2>&1; then
  echo "render-dashboard: python3 not found; install Python 3 or ask the main agent to stop (D11)" >&2
  exit 127
fi

case "$0" in
  */*) script_dir=${0%/*} ;;
  *)   script_dir=. ;;
esac

exec python3 "$script_dir/render-dashboard.py" "$@"
