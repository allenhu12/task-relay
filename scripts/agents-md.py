#!/usr/bin/env python3
"""Write or check a task-relay project's AGENTS.md (ITEM-003 / C).

Usage:
    python3 scripts/agents-md.py check <project_root>
    python3 scripts/agents-md.py write <project_root> [--name NAME] [--dry-run]

`check` compares the project's AGENTS.md with assets/AGENTS.template.md:
    exit 0  current   — same template version, no unresolved skill placeholders
    exit 1  outdated  — older or missing version marker, or unresolved placeholders
    exit 2  missing   — the project has no AGENTS.md

`write` renders the template with real paths ({PROJECT_NAME}, {SKILL_SCRIPTS_PATH},
{SKILL_REFERENCES_PATH}, {SKILL_ASSETS_PATH}). An existing AGENTS.md that differs is
first copied to 90-archive/AGENTS.md.bak-<UTC timestamp>. `--dry-run` prints a
unified diff and writes nothing.

Standard library only.
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_ROOT / "assets" / "AGENTS.template.md"
MARKER_RE = re.compile(r"<!--\s*task-relay-agents:\s*(\d+)\s*-->")
SKILL_PLACEHOLDERS = (
    "{PROJECT_NAME}",
    "{SKILL_SCRIPTS_PATH}",
    "{SKILL_REFERENCES_PATH}",
    "{SKILL_ASSETS_PATH}",
)


def marker_version(text: str) -> Optional[int]:
    match = MARKER_RE.search(text)
    return int(match.group(1)) if match else None


def render(project_root: Path, name: Optional[str] = None) -> str:
    text = TEMPLATE.read_text(encoding="utf-8")
    values = {
        "{PROJECT_NAME}": name or project_root.resolve().name,
        "{SKILL_SCRIPTS_PATH}": str(SKILL_ROOT / "scripts"),
        "{SKILL_REFERENCES_PATH}": str(SKILL_ROOT / "references"),
        "{SKILL_ASSETS_PATH}": str(SKILL_ROOT / "assets"),
    }
    for key, value in values.items():
        text = text.replace(key, value)
    return text


def check(project_root: Path) -> int:
    target = project_root / "AGENTS.md"
    if not target.is_file():
        print(f"missing: {target}")
        return 2
    text = target.read_text(encoding="utf-8")
    want = marker_version(TEMPLATE.read_text(encoding="utf-8"))
    have = marker_version(text)
    problems = []
    if have != want:
        problems.append(f"outdated: version {have if have is not None else 'none'} -> {want}")
    for placeholder in SKILL_PLACEHOLDERS:
        if placeholder in text:
            problems.append(f"unresolved placeholder: {placeholder}")
    if problems:
        for line in problems:
            print(line)
        return 1
    print(f"current: version {have}")
    return 0


def write(project_root: Path, name: Optional[str], dry_run: bool) -> int:
    target = project_root / "AGENTS.md"
    new = render(project_root, name)
    old = target.read_text(encoding="utf-8") if target.is_file() else None
    if old == new:
        print(f"unchanged: {target}")
        return 0
    if dry_run:
        sys.stdout.writelines(
            difflib.unified_diff(
                (old or "").splitlines(keepends=True),
                new.splitlines(keepends=True),
                "AGENTS.md (current)",
                "AGENTS.md (new)",
            )
        )
        return 0
    if old is not None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = project_root / "90-archive" / f"AGENTS.md.bak-{stamp}"
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_text(old, encoding="utf-8")
        print(f"backup: {backup}")
    target.write_text(new, encoding="utf-8")
    print(f"wrote: {target}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    check_p = sub.add_parser("check", help="report whether AGENTS.md is current")
    check_p.add_argument("project_root", type=Path)
    write_p = sub.add_parser("write", help="write AGENTS.md from the template")
    write_p.add_argument("project_root", type=Path)
    write_p.add_argument("--name", help="project name for the title (default: folder name)")
    write_p.add_argument("--dry-run", action="store_true", help="print a diff, write nothing")
    args = parser.parse_args(argv)
    if not args.project_root.is_dir():
        print(f"error: not a directory: {args.project_root}", file=sys.stderr)
        return 2
    if args.command == "check":
        return check(args.project_root)
    return write(args.project_root, args.name, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
