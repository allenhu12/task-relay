"""Shared rules and helpers for the dashboard translation cache (D16).

Both `scripts/render-dashboard.py` (which displays translations) and
`scripts/dashboard-i18n.py` (which maintains the cache) import this module, so
the list of translatable fields lives in exactly one place.

The cache stores one entry per distinct original string:

    {"language": "zh-CN", "entries": {"<key>": "<translated text>"}}

where `<key>` is the first 16 hex characters of the SHA-256 of the exact
original UTF-8 string.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

CACHE_NAME = "dashboard-translations.json"
CURRENT_DIR = "00-current"
ITEM_LIST_NAME = "item-list.json"
ARCHIVE_NAME = "item-list-archive.json"

DEFAULT_LANGUAGE = "zh-CN"
KEY_LENGTH = 16

# D16: which fields are translatable. Items and tasks are both covered,
# including archived items. Ids, names, timestamps, statuses, validation steps
# and file paths are deliberately not in this list.
ASSIGNMENT_FIELDS = ("description",)
TASK_FIELDS = ("description", "notes")
BLOCKER_FIELDS = ("summary", "question", "default_action", "waiting_on")


class I18nError(Exception):
    """Raised when the translation cache or the input data cannot be used."""


def translation_key(text: str) -> str:
    """First KEY_LENGTH hex characters of the SHA-256 of the UTF-8 text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:KEY_LENGTH]


def cache_path(root: Any) -> Path:
    return Path(root) / CURRENT_DIR / CACHE_NAME


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def iter_translatable(item_list: dict, archive: dict) -> dict[str, str]:
    """Return ``{key: original}`` for every translatable string, first-seen order."""
    found: dict[str, str] = {}

    def take(value: Any) -> None:
        if isinstance(value, str) and value.strip():
            found.setdefault(translation_key(value), value)

    assignment = _as_dict(_as_dict(item_list).get("assignment"))
    for field in ASSIGNMENT_FIELDS:
        take(assignment.get(field))

    items = _as_list(_as_dict(item_list).get("items")) + _as_list(
        _as_dict(archive).get("items")
    )
    for raw_item in items:
        item = _as_dict(raw_item)
        take(item.get("description"))
        for raw_task in _as_list(item.get("tasks")):
            task = _as_dict(raw_task)
            for field in TASK_FIELDS:
                take(task.get(field))
            blocker = task.get("blocker")
            if isinstance(blocker, dict):
                for field in BLOCKER_FIELDS:
                    take(blocker.get(field))
    return found


def read_json_object(path: Path) -> dict:
    if not path.exists():
        raise I18nError(f"missing required file: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise I18nError(f"cannot read {path}: {exc}") from exc
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise I18nError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise I18nError(f"expected a JSON object at the top level of {path}")
    return loaded


def load_project_documents(root: Any) -> tuple[dict, dict]:
    """Return ``(item_list, archive)``; the archive may be missing or empty."""
    current = Path(root) / CURRENT_DIR
    item_list = read_json_object(current / ITEM_LIST_NAME)
    archive_file = current / ARCHIVE_NAME
    archive = read_json_object(archive_file) if archive_file.exists() else {}
    return item_list, archive


def collection(root: Any) -> dict[str, str]:
    """Every translatable string currently present in the project data."""
    item_list, archive = load_project_documents(root)
    return iter_translatable(item_list, archive)


def read_cache_strict(path: Path) -> tuple[dict[str, str], str]:
    """Return ``(entries, language)``. Raises I18nError when the cache is bad."""
    if not path.exists():
        return {}, DEFAULT_LANGUAGE
    data = read_json_object(path)
    language = data.get("language")
    if not isinstance(language, str) or not language:
        language = DEFAULT_LANGUAGE
    entries = data.get("entries", {})
    if entries is None:
        entries = {}
    if not isinstance(entries, dict):
        raise I18nError(f'"entries" must be a JSON object in {path}')
    clean: dict[str, str] = {}
    for key, value in entries.items():
        if isinstance(key, str) and isinstance(value, str):
            clean[key] = value
    return clean, language


def load_translations(path: Path) -> tuple[dict[str, str], str | None]:
    """Renderer-friendly loader: never raises. Returns ``(entries, warning)``."""
    if not path.exists():
        return {}, None
    try:
        entries, _language = read_cache_strict(path)
    except I18nError as exc:
        return {}, str(exc)
    return entries, None


def dump_cache(entries: dict[str, str], language: str) -> str:
    """Serialise the cache with sorted keys and a trailing newline."""
    payload = {
        "language": language or DEFAULT_LANGUAGE,
        "entries": {key: entries[key] for key in sorted(entries)},
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def atomic_write(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` atomically (temp file in the same directory)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.chmod(temp_name, 0o644)
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def write_cache(path: Path, entries: dict[str, str], language: str) -> None:
    atomic_write(path, dump_cache(entries, language))
