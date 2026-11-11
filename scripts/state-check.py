#!/usr/bin/env python3
"""Deterministic checks for a task-relay project's state files (TASK-001-06).

Usage:
    python3 scripts/state-check.py <project_root> [--fix] [--language zh-CN]

Check-only by default: prints one line per problem and exits 1 when anything is
wrong, 0 when the state is clean. Warnings (for example a `rulebook` or
`context` file that does not exist yet) print as `state-check: warning: ...`
and do not change the exit code.

`--read-first TASK-ID` runs no checks. It prints one line, `READ FIRST: <paths>`
(or `READ FIRST: none`): the item's `rulebook` and `context`, then the task's,
in that order, without duplicates. The state writer copies this line into its
reply when a task goes `in_progress`.

`--fix` repairs **only** mechanical fields — the `metadata` counts and the item
blocked/in_progress rollup. It never invents a timestamp or any text, and never
touches a definition field.

Standard library only; the shared helpers live in `dashboard_strings.py`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dashboard_strings as ds  # noqa: E402  (path set up above)

TERMINAL_STATUSES = ("completed", "cancelled")
ACTIVE_STATUSES = ("pending", "in_progress", "blocked")
METADATA_KEYS = (
    "total_items",
    "completed",
    "in_progress",
    "blocked",
    "pending",
    "cancelled",
)

ISO_UTC = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$"
)


def parse_utc(value: Any) -> Optional[datetime]:
    """Return the datetime for an ISO-8601 UTC string, else None."""
    text = value if isinstance(value, str) else ""
    if not ISO_UTC.match(text):
        return None
    try:
        stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.utcoffset() != timedelta(0):
        return None
    return stamp


def as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def as_text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def item_tasks(item: dict) -> list[dict]:
    return [as_dict(task) for task in as_list(item.get("tasks"))]


def non_terminal_tasks(item: dict) -> list[dict]:
    return [task for task in item_tasks(item) if as_text(task.get("status")) in ACTIVE_STATUSES]


def expected_metadata(item_list: dict) -> dict[str, int]:
    """Counts the metadata block must match: active items + terminal summaries."""
    counts = {key: 0 for key in ACTIVE_STATUSES}
    counts["completed"] = 0
    counts["cancelled"] = 0
    items = [as_dict(entry) for entry in as_list(item_list.get("items"))]
    terminal = [as_dict(entry) for entry in as_list(item_list.get("terminal_summary"))]
    for item in items:
        status = as_text(item.get("status"))
        if status in counts:
            counts[status] += 1
    for entry in terminal:
        status = as_text(entry.get("status"))
        if status in TERMINAL_STATUSES:
            counts[status] += 1
    counts["total_items"] = len(items) + len(terminal)
    return counts


def expected_item_status(item: dict) -> Optional[str]:
    """The rollup status an item must have, or None when no rule applies.

    Rule (TASK-001-06): an item is `blocked` when every non-terminal task is
    blocked, and it goes back to `in_progress` once a non-terminal task is no
    longer blocked. Terminal items and items with no non-terminal task are left
    alone. `pending` is never forced: it only flips when the item is currently
    `blocked` and the blockage is gone.
    """
    status = as_text(item.get("status"))
    if status in TERMINAL_STATUSES:
        return None
    remaining = non_terminal_tasks(item)
    if not remaining:
        return None
    if all(as_text(task.get("status")) == "blocked" for task in remaining):
        return "blocked"
    return "in_progress" if status == "blocked" else None


def blocker_problems(task: dict, label: str) -> list[str]:
    """Required blocker fields. Legacy blocked tasks without a blocker are valid (D14)."""
    blocker = task.get("blocker")
    if blocker is None:
        return []
    if not isinstance(blocker, dict):
        return [f"{label}: blocker must be a JSON object"]
    problems = []
    kind = as_text(blocker.get("type"))
    if kind not in ("needs_user", "external"):
        problems.append(f"{label}: blocker.type must be needs_user or external")
    for field in ("summary", "since"):
        if not as_text(blocker.get(field)).strip():
            problems.append(f"{label}: blocker.{field} is required")
    if kind == "needs_user" and not as_text(blocker.get("question")).strip():
        problems.append(f"{label}: blocker.question is required for a needs_user blocker")
    if kind == "external" and not as_text(blocker.get("waiting_on")).strip():
        problems.append(f"{label}: blocker.waiting_on is required for an external blocker")
    return problems


def path_problem(value: Any) -> Optional[str]:
    """Why a rulebook/context path is not a safe project-relative path, else None."""
    if not isinstance(value, str) or not value.strip():
        return "must be a non-empty string"
    text = value.replace("\\", "/")
    if text.startswith(("/", "~")) or re.match(r"^[A-Za-z]:", text):
        return f"must be relative to the project root: {value!r}"
    if ".." in text.split("/"):
        return f"must not contain '..': {value!r}"
    return None


def guide_paths(record: dict, label: str) -> tuple[list[tuple[str, str]], list[str]]:
    """The (label, path) pairs of a record's rulebook/context, plus shape problems."""
    paths: list[tuple[str, str]] = []
    problems: list[str] = []
    if "rulebook" in record and record["rulebook"] is not None:
        paths.append((f"{label}.rulebook", record["rulebook"]))
    if "context" in record:
        context = record["context"]
        if not isinstance(context, list):
            problems.append(f"paths: {label}.context must be a list of paths")
        else:
            paths.extend(
                (f"{label}.context[{index}]", entry) for index, entry in enumerate(context)
            )
    return paths, problems


class Checker:
    def __init__(self, root: Path, language: Optional[str]) -> None:
        self.root = root
        self.language = language
        self.problems: list[str] = []
        self.warnings: list[str] = []
        self.fixes: list[str] = []

    # -- helpers ---------------------------------------------------------
    def problem(self, message: str) -> None:
        self.problems.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def fix(self, message: str) -> None:
        self.fixes.append(message)

    def timestamp(self, value: Any, label: str, created: Optional[datetime]) -> Optional[datetime]:
        stamp = parse_utc(value)
        if stamp is None:
            self.problem(f"timestamps: {label} is not an ISO-8601 UTC timestamp: {value!r}")
            return None
        if created is not None and stamp == created:
            self.problem(
                f"timestamps: {label} equals assignment.created ({value}); "
                "the state writer reused the creation time instead of reading the clock"
            )
        return stamp

    # -- checks ----------------------------------------------------------
    def check_blockers(self, items: Sequence[dict]) -> None:
        for item in items:
            for task in item_tasks(item):
                label = as_text(task.get("id")) or "task"
                status = as_text(task.get("status"))
                if status != "blocked" and task.get("blocker") is not None:
                    self.problem(
                        f"blocker: {label} is {status} but still carries a blocker "
                        "(remove it when the task leaves blocked)"
                    )
                if status == "blocked":
                    self.problems.extend(blocker_problems(task, label))

    def check_paths(self, items: Sequence[dict]) -> None:
        """rulebook/context on active items and tasks: bad path = problem, missing file = warning."""
        for item in items:
            records = [(item, as_text(item.get("id")) or "item")]
            records += [(task, as_text(task.get("id")) or "task") for task in item_tasks(item)]
            for record, label in records:
                paths, problems = guide_paths(record, label)
                self.problems.extend(problems)
                for path_label, value in paths:
                    reason = path_problem(value)
                    if reason:
                        self.problem(f"paths: {path_label} {reason}")
                    elif not (ds.current_dir(self.root).parent / value).exists():
                        self.warning(f"paths: {path_label} file not found: {value}")

    def check_rollup(self, items: Sequence[dict]) -> None:
        for item in items:
            label = as_text(item.get("id")) or "item"
            status = as_text(item.get("status"))
            expected = expected_item_status(item)
            if expected is None or expected == status:
                continue
            if expected == "blocked":
                self.problem(
                    f"rollup: {label} is {status} but every non-terminal task is blocked "
                    "(the item must be blocked)"
                )
            else:
                self.problem(
                    f"rollup: {label} is blocked but a non-terminal task is not blocked "
                    "(the item must go back to in_progress)"
                )

    def check_metadata(self, item_list: dict) -> None:
        expected = expected_metadata(item_list)
        metadata = as_dict(item_list.get("metadata"))
        for key in METADATA_KEYS:
            if key not in metadata:
                self.problem(f"metadata: {key} is missing")
                continue
            actual = metadata.get(key)
            if actual != expected[key]:
                self.problem(
                    f"metadata: {key} is {actual!r}, expected {expected[key]}"
                )

    def check_timestamps(self, item_list: dict, archive: dict) -> None:
        assignment = as_dict(item_list.get("assignment"))
        created_raw = assignment.get("created")
        created = parse_utc(created_raw)
        if created is None:
            self.problem(
                f"timestamps: assignment.created is not an ISO-8601 UTC timestamp: {created_raw!r}"
            )

        last_updated_raw = assignment.get("last_updated")
        last_updated = self.timestamp(last_updated_raw, "assignment.last_updated", None)

        stamps: list[tuple[str, datetime]] = []
        archived = [as_dict(entry) for entry in as_list(archive.get("items"))]
        for item in [as_dict(entry) for entry in as_list(item_list.get("items"))] + archived:
            for task in item_tasks(item):
                label = f"{as_text(task.get('id')) or 'task'}.completed_at"
                status = as_text(task.get("status"))
                completed_at = task.get("completed_at")
                if status in TERMINAL_STATUSES:
                    if not as_text(completed_at).strip():
                        self.problem(
                            f"timestamps: {label} is missing for a {status} task"
                        )
                        continue
                    stamp = self.timestamp(completed_at, label, created)
                    if stamp is not None:
                        stamps.append((label, stamp))
                elif as_text(completed_at).strip():
                    self.problem(
                        f"timestamps: {label} is set while the task is {status} "
                        "(it must be null until the task is terminal)"
                    )
                blocker = task.get("blocker")
                if isinstance(blocker, dict) and as_text(blocker.get("since")).strip():
                    since_label = f"{as_text(task.get('id')) or 'task'}.blocker.since"
                    stamp = self.timestamp(blocker.get("since"), since_label, created)
                    if stamp is not None:
                        stamps.append((since_label, stamp))

        if last_updated is None:
            return
        for label, stamp in stamps:
            if stamp > last_updated:
                self.problem(
                    f"timestamps: {label} ({stamp.isoformat()}) is newer than "
                    f"assignment.last_updated ({last_updated_raw})"
                )
        if stamps and created is not None and last_updated <= created:
            self.problem(
                "timestamps: assignment.last_updated was not refreshed "
                f"({last_updated_raw}); it must be newer than assignment.created "
                f"({created_raw}) once tasks carry timestamps"
            )

    def check_translation(self) -> None:
        cache_file = ds.cache_path(self.root)
        if not cache_file.exists() and not self.language:
            return
        entries, _language = ds.read_cache_strict(cache_file)
        strings = ds.collection(self.root)
        missing = {key: value for key, value in strings.items() if key not in entries}
        if missing:
            example = next(iter(missing.values()))
            self.problem(
                f"translation: {len(missing)} string(s) have no cached translation "
                f'(for example "{example}"); run dashboard-i18n.py list-missing, translate, then apply'
            )

    # -- fixing ----------------------------------------------------------
    def apply_fixes(self, item_list: dict) -> bool:
        """Repair metadata counts and the item rollup. Returns True when changed."""
        changed = False

        for item in [as_dict(entry) for entry in as_list(item_list.get("items"))]:
            status = as_text(item.get("status"))
            expected = expected_item_status(item)
            if expected is None or expected == status:
                continue
            item["status"] = expected
            label = as_text(item.get("id")) or "item"
            self.fix(f"rollup: {label} {status} -> {expected}")
            changed = True

        metadata = item_list.get("metadata")
        if not isinstance(metadata, dict):
            item_list["metadata"] = {}
            metadata = item_list["metadata"]
        expected = expected_metadata(item_list)
        for key in METADATA_KEYS:
            if metadata.get(key) != expected[key]:
                self.fix(f"metadata: {key} {metadata.get(key)!r} -> {expected[key]}")
                metadata[key] = expected[key]
                changed = True
        return changed


def read_first_paths(item: dict, task: dict) -> list[str]:
    """Item rulebook + context, then task rulebook + context; order kept, no duplicates."""
    paths: list[str] = []
    for record in (item, task):
        rulebook = record.get("rulebook")
        candidates = [rulebook] if isinstance(rulebook, str) else []
        candidates += [entry for entry in as_list(record.get("context")) if isinstance(entry, str)]
        for entry in candidates:
            if entry.strip() and entry not in paths:
                paths.append(entry)
    return paths


def run_read_first(root: Path, task_id: str) -> int:
    try:
        item_list, _archive = ds.load_project_documents(root)
    except ds.I18nError as exc:
        print(f"state-check: json: {exc}", file=sys.stderr)
        return 1
    for item in [as_dict(entry) for entry in as_list(item_list.get("items"))]:
        for task in item_tasks(item):
            if as_text(task.get("id")) == task_id:
                paths = read_first_paths(item, task)
                print("READ FIRST: " + (", ".join(paths) if paths else "none"))
                return 0
    print(f"state-check: read-first: unknown active task {task_id!r}", file=sys.stderr)
    return 1


def run(root: Path, fix: bool, language: Optional[str]) -> int:
    try:
        item_list, archive = ds.load_project_documents(root)
    except ds.I18nError as exc:
        print(f"state-check: json: {exc}", file=sys.stderr)
        return 1

    fixes: list[str] = []
    if fix:
        fixer = Checker(root, language)
        if fixer.apply_fixes(item_list):
            ds.atomic_write(
                ds.current_dir(root) / ds.ITEM_LIST_NAME,
                json.dumps(item_list, ensure_ascii=False, indent=2) + "\n",
            )
            # Re-read so the checks below judge exactly what is on disk.
            item_list, archive = ds.load_project_documents(root)
        fixes = fixer.fixes

    # Every check runs against the (possibly repaired) document.
    checker = Checker(root, language)
    items = [as_dict(entry) for entry in as_list(item_list.get("items"))]
    checker.check_metadata(item_list)
    checker.check_blockers(items)
    checker.check_paths(items)
    checker.check_rollup(items)
    checker.check_timestamps(item_list, archive)
    try:
        checker.check_translation()
    except ds.I18nError as exc:
        checker.problem(f"translation: {exc}")

    for message in fixes:
        print(f"state-check: fixed {message}")
    for message in checker.problems:
        print(f"state-check: {message}")
    for message in checker.warnings:
        print(f"state-check: warning: {message}")
    if checker.problems:
        return 1
    print("state-check: OK")
    return 0


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="state-check.py",
        description="Check (and optionally repair) a task-relay project's state files.",
    )
    parser.add_argument("root")
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("--language", default=None)
    parser.add_argument("--read-first", metavar="TASK_ID", default=None)
    args = parser.parse_args(list(argv[1:]))
    if args.read_first:
        return run_read_first(Path(args.root).expanduser(), args.read_first)
    return run(Path(args.root).expanduser(), args.fix, args.language)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
