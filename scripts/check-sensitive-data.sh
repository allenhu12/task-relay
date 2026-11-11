#!/usr/bin/env bash
# Check the current worktree for personal paths, internal identifiers and common secret formats.

set -u

case "${BASH_SOURCE[0]}" in
  */*) script_dir=${BASH_SOURCE[0]%/*} ;;
  *) script_dir=. ;;
esac
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
scan_root=${1:-$repo_root}

if ! command -v rg >/dev/null 2>&1; then
  echo "sensitive-data check: rg is required" >&2
  exit 2
fi

personal_or_internal='/Users/|/Volumes/|/home/hubo|hubo@|commscope\.com|ruckus\.atlassian\.net|unleashed_200|openwrt_miami|ubuntu20|BackupT7'
secret_material='BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY|github_pat_[A-Za-z0-9_]+|ghp_[A-Za-z0-9]+|AKIA[0-9A-Z]{16}|authorization:[[:space:]]*bearer[[:space:]]+[A-Za-z0-9._~+/-]+'
private_network='https?://(10\.|127\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)'

status=0
for pattern in "$personal_or_internal" "$secret_material" "$private_network"; do
  if rg -n --hidden --no-ignore -i \
    -g '!.git/**' \
    -g '!**/__pycache__/**' \
    -g '!scripts/check-sensitive-data.sh' \
    -e "$pattern" "$scan_root"; then
    status=1
  fi
done

if [ "$status" -ne 0 ]; then
  echo "sensitive-data check: found content that must be reviewed" >&2
  exit 1
fi

echo "sensitive-data check: clean"
