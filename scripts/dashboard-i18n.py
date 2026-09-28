#!/usr/bin/env python3
"""Maintain the dashboard translation cache (D16).

Usage:
    python3 scripts/dashboard-i18n.py list-missing <project_root> [--language zh-CN]
    python3 scripts/dashboard-i18n.py apply <project_root> <translations.json|->
    python3 scripts/dashboard-i18n.py prune <project_root>

The state-writer subagent uses `list-missing` to see which strings still need a
translation, translates them itself, then feeds the result back with `apply`.
The renderer only reads the cache. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dashboard_strings as ds  # noqa: E402  (path set up above)


def _read_payload(source: str) -> dict:
    if source == "-":
        raw = sys.stdin.read()
    else:
        path = Path(source).expanduser()
        if not path.exists():
            raise ds.I18nError(f"missing translations file: {path}")
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ds.I18nError(f"cannot read {path}: {exc}") from exc
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ds.I18nError(f"invalid JSON in the translations input: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ds.I18nError("the translations input must be a JSON object of key -> text")
    clean: dict[str, str] = {}
    for key, value in loaded.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ds.I18nError("every translation must be a string keyed by a string")
        if value.strip():
            clean[key] = value
    return clean


def cmd_list_missing(root: Path, language: str | None) -> int:
    strings = ds.collection(root)
    cache_file = ds.cache_path(root)
    entries, cache_language = ds.read_cache_strict(cache_file)
    chosen = language or cache_language
    missing = {key: value for key, value in strings.items() if key not in entries}
    payload = {
        "language": chosen,
        "missing": {key: missing[key] for key in sorted(missing)},
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_apply(root: Path, source: str) -> int:
    payload = _read_payload(source)
    strings = ds.collection(root)
    unknown = sorted(key for key in payload if key not in strings)
    if unknown:
        raise ds.I18nError(
            "unknown key(s) not present in the current data: "
            + ", ".join(unknown[:5])
            + (f" (+{len(unknown) - 5} more)" if len(unknown) > 5 else "")
        )
    cache_file = ds.cache_path(root)
    entries, language = ds.read_cache_strict(cache_file)
    kept = {key: value for key, value in entries.items() if key in strings}
    kept.update(payload)
    ds.write_cache(cache_file, kept, language)
    print(
        f"dashboard-i18n: applied {len(payload)} translation(s); "
        f"cache holds {len(kept)} entr(y/ies) in {cache_file}"
    )
    return 0


def cmd_prune(root: Path) -> int:
    cache_file = ds.cache_path(root)
    if not cache_file.exists():
        print(f"dashboard-i18n: no cache at {cache_file}; nothing to prune")
        return 0
    strings = ds.collection(root)
    entries, language = ds.read_cache_strict(cache_file)
    kept = {key: value for key, value in entries.items() if key in strings}
    removed = len(entries) - len(kept)
    ds.write_cache(cache_file, kept, language)
    print(
        f"dashboard-i18n: pruned {removed} stale entr(y/ies); "
        f"cache holds {len(kept)} entr(y/ies)"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dashboard-i18n.py",
        description="Maintain the task-relay dashboard translation cache.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_missing = sub.add_parser(
        "list-missing", help="print the strings that have no cached translation"
    )
    list_missing.add_argument("root")
    list_missing.add_argument("--language", default=None)

    apply_cmd = sub.add_parser(
        "apply", help="merge a {key: translation} JSON file into the cache"
    )
    apply_cmd.add_argument("root")
    apply_cmd.add_argument("source", help="path to the JSON file, or - for stdin")

    prune = sub.add_parser("prune", help="drop cache entries whose text is gone")
    prune.add_argument("root")
    return parser


def main(argv: Sequence[str]) -> int:
    args = build_parser().parse_args(list(argv[1:]))
    root = Path(args.root).expanduser()
    try:
        if args.command == "list-missing":
            return cmd_list_missing(root, args.language)
        if args.command == "apply":
            return cmd_apply(root, args.source)
        return cmd_prune(root)
    except ds.I18nError as exc:
        print(f"dashboard-i18n: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
