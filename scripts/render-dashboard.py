#!/usr/bin/env python3
"""Render the task-relay HTML dashboard (D1, D3, D4, D5, D8, D9, D14, D15).

Usage:
    python3 scripts/render-dashboard.py <project_root>

Reads:
    <project_root>/00-current/item-list.json            (required)
    <project_root>/00-current/item-list-archive.json    (optional)
    assets/dashboard.template.html                      (skeleton, next to this script)

Writes:
    <project_root>/00-current/dashboard.html            (rewritten in full, atomically)

Standard library only. The output never changes unless the input changes: the
"updated" line comes from ``assignment.last_updated``, never from the clock.
"""

from __future__ import annotations

import html
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dashboard_strings as ds  # noqa: E402  (path set up above)

# --------------------------------------------------------------------------
# UI labels (D5/D9). Chinese, matching layout A of the approved mockup.
# Change labels here only; the script and the template read nothing else.
# --------------------------------------------------------------------------
LABELS = {
    "page_title_suffix": "项目状态",
    "updated": "更新于",
    "kpi_needs_you": "等你处理",
    "kpi_external": "等外部",
    "kpi_in_progress_items": "进行中事项",
    "kpi_completed_items": "已完成事项",
    "section_needs_you": "需要你处理",
    "section_external": "等外部",
    "section_active": "进行中和待办的事项",
    "section_activity": "最近动态",
    "section_deliverables": "最新交付物",
    "section_finished": "已结束的事项",
    "who_needs_you": "需要你",
    "who_external": "等外部",
    "unclassified": "未分类",
    "unclassified_hint": "请说明这是「等你决定」还是「等外部」",
    "no_note": "（没有说明）",
    "default_action": "不回答时默认",
    "waiting_on": "等",
    "since": "挂起自",
    "item_arrow": "→",
    "note_needs_you": "等你",
    "note_external": "等外部",
    "activity_completed": "完成",
    "activity_cancelled": "取消",
    "activity_blocked": "受阻",
    "finished_at": "结束于",
    "summary_only": "只有一行摘要（archive 里没有完整记录）",
    "activity_cap": "只显示最近 5 条",
    "deliverables_cap": "只显示最近 5 个文件",
    "finished_cap": "默认折叠，点开看 task。所有已结束事项都保留 task 明细。",
    "status": {
        "pending": "待办",
        "in_progress": "进行中",
        "completed": "完成",
        "blocked": "受阻",
        "cancelled": "取消",
    },
}

TRUNCATE_LIMIT = 120
TRUNCATION_SUFFIX = "…"
ACTIVITY_LIMIT = 5
DELIVERABLE_LIMIT = 5

CURRENT_DIR = "00-current"
ITEM_LIST_NAME = "item-list.json"
ARCHIVE_NAME = "item-list-archive.json"
DASHBOARD_NAME = "dashboard.html"
TEMPLATE_RELATIVE = ("assets", "dashboard.template.html")

PLACEHOLDERS = (
    "{{PAGE_TITLE}}",
    "{{HEADER}}",
    "{{KPIS}}",
    "{{NEEDS_YOU}}",
    "{{EXTERNAL}}",
    "{{ACTIVE_ITEMS}}",
    "{{ACTIVITY_ROW}}",
    "{{FINISHED}}",
)


class RenderError(Exception):
    """Raised when the dashboard cannot be rendered. Message goes to stderr."""


# --------------------------------------------------------------------------
# Small, total helpers. Every value that reaches the page goes through esc().
# --------------------------------------------------------------------------
def esc(value: Any) -> str:
    """HTML-escape a value for use in text or in a quoted attribute."""
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return html.escape(value, quote=True)


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def clip(text: Any) -> tuple[str, Optional[str]]:
    """Return (visible, full). ``full`` is set only when clipping happened."""
    value = as_text(text)
    if len(value) <= TRUNCATE_LIMIT:
        return value, None
    return value[:TRUNCATE_LIMIT] + TRUNCATION_SUFFIX, value


def translated(value: Any, translations: Optional[dict]) -> str:
    """Return the cached translation of a data string, else the original."""
    original = as_text(value)
    if not original or not translations:
        return original
    return translations.get(ds.translation_key(original), original)


def value_span(original: Any, shown: Any, css_class: str = "") -> str:
    """Render ``shown``, clipped, with the ORIGINAL full text in ``title`` (D16).

    The title is emitted whenever the shown text was clipped or translated, so
    hovering always reveals the stored original.
    """
    original_text = as_text(original)
    shown_text = as_text(shown)
    visible, _clipped = clip(shown_text)
    truncated = len(shown_text) > TRUNCATE_LIMIT or len(original_text) > TRUNCATE_LIMIT
    needs_title = bool(original_text) and (shown_text != original_text or truncated)
    title = f' title="{esc(original_text)}"' if needs_title else ""
    attribute = f' class="{css_class}"' if css_class else ""
    return f"<span{attribute}{title}>{esc(visible)}</span>"


def data_span(value: Any, translations: Optional[dict], css_class: str = "") -> str:
    """Clip the display text of a data string; keep the original for hover."""
    return value_span(as_text(value), translated(value, translations), css_class)


def timestamp_key(value: Any) -> str:
    """Sortable form of an ISO-8601-ish timestamp. Missing values sort first."""
    text = as_text(value).strip()
    if not text:
        return ""
    normalised = text.replace(" ", "T")
    while normalised.endswith("Z"):
        normalised = normalised[:-1]
    return normalised


def percent(part: int, total: int) -> str:
    if total <= 0:
        return "0%"
    value = round(part * 100.0 / total, 2)
    return f"{value:g}%"


def chip(status: Any) -> str:
    key = as_text(status)
    label = LABELS["status"].get(key, key)
    css = f"s-{key}" if key in LABELS["status"] else "s-pending"
    return f'<span class="chip {css}">{esc(label)}</span>'


def status_label(status: Any) -> str:
    key = as_text(status)
    return LABELS["status"].get(key, key)


# --------------------------------------------------------------------------
# Shaping the input documents
# --------------------------------------------------------------------------
def task_items(item: dict) -> list[dict]:
    return [as_dict(task) for task in as_list(item.get("tasks"))]


def blocker_of(task: dict) -> Optional[dict]:
    raw = task.get("blocker")
    return raw if isinstance(raw, dict) else None


def blocker_kind(task: dict) -> str:
    """Return 'needs_user', 'external', 'unclassified', or ''."""
    blocker = blocker_of(task)
    if blocker is None:
        return "unclassified" if as_text(task.get("status")) == "blocked" else ""
    kind = as_text(blocker.get("type"))
    if kind in ("needs_user", "external"):
        return kind
    return "unclassified"


def note_from(task: dict, render: Callable[[Any], str]) -> str:
    """Compose the one-line note, translating each field through ``render``."""
    blocker = blocker_of(task)
    if blocker is not None:
        kind = blocker_kind(task)
        if kind == "needs_user":
            detail = as_text(blocker.get("question")) or as_text(blocker.get("summary"))
            if detail:
                return f"{LABELS['note_needs_you']}：{render(detail)}"
        elif kind == "external":
            detail = as_text(blocker.get("waiting_on")) or as_text(blocker.get("summary"))
            if detail:
                return f"{LABELS['note_external']}：{render(detail)}"
        else:
            detail = as_text(blocker.get("summary"))
            if detail:
                return f"{LABELS['unclassified']}：{render(detail)}"
    return render(task.get("notes"))


def task_note(task: dict) -> str:
    """Original one-line note for a task: blocker question / waiting_on, else notes."""
    return note_from(task, as_text)


def shown_note(task: dict, translations: Optional[dict]) -> str:
    """Same note with each translatable field passed through the cache."""
    return note_from(task, lambda value: translated(value, translations))


def progress_bar(tasks: Sequence[dict]) -> str:
    total = len(tasks)
    counts = {key: 0 for key in LABELS["status"]}
    for task in tasks:
        key = as_text(task.get("status"))
        if key in counts:
            counts[key] += 1
    segments = (
        ("completed", "var(--ok)", "1"),
        ("cancelled", "var(--cxl)", ".5"),
        ("in_progress", "var(--run)", "1"),
        ("blocked", "var(--user)", "1"),
    )
    spans = []
    for key, colour, opacity in segments:
        if counts[key] <= 0:
            continue
        width = percent(counts[key], total)
        spans.append(
            f'<span style="width:{width};background:{colour};opacity:{opacity}"></span>'
        )
    done = counts["completed"] + counts["cancelled"]
    return (
        '<div class="prog"><div class="bar">'
        + "".join(spans)
        + f'</div><small>{done}/{total}</small></div>'
    )


def task_line(task: dict, translations: Optional[dict] = None) -> str:
    kind = blocker_kind(task)
    status = as_text(task.get("status"))
    marker = f"i-{status}" if status in LABELS["status"] else "i-pending"
    if status == "blocked" and kind == "external":
        marker = "i-blocked ext"
    elif status == "blocked":
        marker = "i-blocked"
    parts = [
        f'<span class="ic {marker}"></span>',
        "<span>",
        f'<span class="mono">{esc(task.get("id"))}</span> ',
        data_span(task.get("description"), translations),
    ]
    original_note = task_note(task)
    if original_note:
        shown = shown_note(task, translations)
        visible, _clipped = clip(shown)
        needs_title = shown != original_note or len(original_note) > TRUNCATE_LIMIT or len(shown) > TRUNCATE_LIMIT
        title = f' title="{esc(original_note)}"' if needs_title else ""
        parts.append(f'<span class="tnote"{title}>{esc(visible)}</span>')
    parts.append("</span>")
    parts.append(chip(status))
    return "<li>" + "".join(parts) + "</li>"


def task_lines(item: dict, translations: Optional[dict] = None) -> str:
    lines = "".join(task_line(task, translations) for task in task_items(item))
    return f'<ul class="tasks">{lines}</ul>' if lines else ""


def item_summary(item: dict, open_by_default: bool, translations: Optional[dict] = None,
                 suffix: str = "") -> str:
    tasks = task_items(item)
    status = as_text(item.get("status"))
    open_attr = " open" if open_by_default else ""
    return (
        f'<details class="item"{open_attr}><summary>'
        f'<span class="mono">{esc(item.get("id"))}</span>'
        f"{data_span(item.get('description'), translations)}"
        f"{chip(status)}"
        f"{progress_bar(tasks)}"
        f"</summary>{suffix}{task_lines(item, translations)}</details>"
    )


# --------------------------------------------------------------------------
# Page sections
# --------------------------------------------------------------------------
def render_header(assignment: dict, updated: str,
                  translations: Optional[dict] = None) -> str:
    name = as_text(assignment.get("name"))
    description = as_text(assignment.get("description"))
    meta = (
        f'<div class="meta">{data_span(description, translations)}</div>'
        if description
        else ""
    )
    updated_line = f'{LABELS["updated"]} {esc(updated)}'.strip()
    return (
        '<div class="head"><div>'
        f"<h1>{esc(name)}</h1>{meta}"
        "</div>"
        f'<div class="meta">{esc(updated_line)}</div>'
        "</div>"
    )


def render_kpis(needs_you: int, external: int, in_progress_items: int,
                completed_items: int, total_items: int) -> str:
    return (
        '<div class="kpis">'
        f'<div class="kpi user"><div class="n">{needs_you}</div>'
        f'<div class="l">{esc(LABELS["kpi_needs_you"])}</div></div>'
        f'<div class="kpi ext"><div class="n">{external}</div>'
        f'<div class="l">{esc(LABELS["kpi_external"])}</div></div>'
        f'<div class="kpi"><div class="n">{in_progress_items}</div>'
        f'<div class="l">{esc(LABELS["kpi_in_progress_items"])}</div></div>'
        f'<div class="kpi"><div class="n">{completed_items}/{total_items}</div>'
        f'<div class="l">{esc(LABELS["kpi_completed_items"])}</div></div>'
        "</div>"
    )


def render_needs_you(entries: Sequence[tuple[dict, dict]],
                     translations: Optional[dict] = None) -> str:
    heading = (
        f'<h2>{esc(LABELS["section_needs_you"])}（{len(entries)}）</h2>'
    )
    if not entries:
        return heading + '<div class="card">—</div>'
    cards = []
    for item, task in entries:
        blocker = blocker_of(task)
        task_id = esc(task.get("id"))
        route = (
            f'{esc(item.get("id"))} {LABELS["item_arrow"]} {esc(task.get("id"))}'
        )
        if blocker is None:
            who = f'{LABELS["who_needs_you"]} · {task_id} · {LABELS["unclassified"]}'
            notes = as_text(task.get("notes"))
            question = (
                data_span(notes, translations) if notes else esc(LABELS["no_note"])
            )
            cards.append(
                '<div class="card bl">'
                f'<div class="who">{esc(who)}</div>'
                f'<div class="q">{question}</div>'
                f'<div class="d">{esc(route)}</div>'
                f'<div class="d">{esc(LABELS["unclassified_hint"])}</div>'
                "</div>"
            )
            continue
        kind = blocker_kind(task)
        label = LABELS["who_needs_you"] if kind == "needs_user" else LABELS["unclassified"]
        who = f'{label} · {task_id}'
        summary = as_text(blocker.get("summary"))
        question = as_text(blocker.get("question")) or summary
        details = [f'<div class="q">{data_span(question, translations)}</div>']
        if summary and summary != question:
            details.append(f'<div class="d">{data_span(summary, translations)}</div>')
        details.append(f'<div class="d">{esc(route)}</div>')
        default_action = as_text(blocker.get("default_action"))
        if default_action:
            details.append(
                f'<div class="d">{esc(LABELS["default_action"])}：'
                f"<b>{data_span(default_action, translations)}</b></div>"
            )
        since = as_text(blocker.get("since"))
        if since:
            details.append(f'<div class="d">{esc(LABELS["since"])} {esc(since)}</div>')
        cards.append(
            f'<div class="card bl"><div class="who">{esc(who)}</div>'
            + "".join(details)
            + "</div>"
        )
    return heading + f'<div class="grid2">{"".join(cards)}</div>'


def render_external(entries: Sequence[tuple[dict, dict]],
                    translations: Optional[dict] = None) -> str:
    heading = f'<h2>{esc(LABELS["section_external"])}（{len(entries)}）</h2>'
    if not entries:
        return heading + '<div class="card">—</div>'
    cards = []
    for item, task in entries:
        blocker = blocker_of(task) or {}
        summary = as_text(blocker.get("summary")) or as_text(task_note(task))
        waiting_on = as_text(blocker.get("waiting_on"))
        since = as_text(blocker.get("since"))
        route = f'{esc(item.get("id"))} {LABELS["item_arrow"]} {esc(task.get("id"))}'
        detail = f'<div class="d">{route}'
        if since:
            detail += f' · {esc(LABELS["since"])} {esc(since)}'
        detail += "</div>"
        cards.append(
            '<div class="card bl ext">'
            f'<div class="who">{esc(LABELS["who_external"])} · {esc(task.get("id"))}</div>'
            f'<div class="q">{data_span(summary, translations)}</div>'
            f'<div class="d">{esc(LABELS["waiting_on"])}：'
            f"<b>{data_span(waiting_on, translations)}</b></div>"
            f"{detail}</div>"
        )
    return heading + f'<div class="grid2">{"".join(cards)}</div>'


def render_active_items(items: Sequence[dict],
                        translations: Optional[dict] = None) -> str:
    heading = f'<h2>{esc(LABELS["section_active"])}（{len(items)}）</h2>'
    if not items:
        return heading + '<div class="card">—</div>'
    return heading + "".join(
        item_summary(item, open_by_default=True, translations=translations)
        for item in items
    )


def render_activity(events: Sequence[tuple[str, str, str]]) -> str:
    heading = f'<h2>{esc(LABELS["section_activity"])}</h2>'
    if not events:
        return (
            heading
            + '<div class="card"><ul class="feed"></ul>'
            + f'<div class="cap">{esc(LABELS["activity_cap"])}</div></div>'
        )
    rows = []
    for stamp, original, shown in events:
        rows.append(
            f'<li><time>{esc(stamp)}</time>{value_span(original, shown)}</li>'
        )
    return (
        heading
        + f'<div class="card"><ul class="feed">{"".join(rows)}</ul>'
        + f'<div class="cap">{esc(LABELS["activity_cap"])}</div></div>'
    )


def render_deliverables(entries: Sequence[tuple[str, str]]) -> str:
    if not entries:
        return ""
    rows = "".join(
        f'<li><span class="mono">{esc(item_id)}</span> {esc(path)}</li>'
        for item_id, path in entries
    )
    return (
        f'<h2>{esc(LABELS["section_deliverables"])}</h2>'
        f'<div class="card"><ul class="feed">{rows}</ul>'
        f'<div class="cap">{esc(LABELS["deliverables_cap"])}</div></div>'
    )


def render_activity_row(activity: Sequence[tuple[str, str]],
                        deliverables: Sequence[tuple[str, str]]) -> str:
    """Layout A puts 最近动态 and 最新交付物 side by side (D3)."""
    activity_block = f"<div>{render_activity(activity)}</div>"
    deliverables_block = render_deliverables(deliverables)
    if not deliverables_block:
        return activity_block
    return (
        '<div class="grid2" style="margin-top:8px">'
        f"{activity_block}<div>{deliverables_block}</div></div>"
    )


def render_finished(entries: Sequence[tuple[dict, bool]],
                    translations: Optional[dict] = None) -> str:
    heading = f'<h2>{esc(LABELS["section_finished"])}（{len(entries)}）</h2>'
    if not entries:
        return (
            heading
            + '<div class="card"><ul class="feed"></ul>'
            + f'<div class="cap">{esc(LABELS["finished_cap"])}</div></div>'
        )
    blocks = []
    for record, has_archive in entries:
        if not has_archive:
            completed_at = as_text(record.get("completed_at"))
            blocks.append(
                '<div class="card">'
                f'<span class="mono">{esc(record.get("id"))}</span> '
                f"{data_span(record.get('description'), translations)} "
                f"{chip(record.get('status'))} "
                f'<span class="summaryline">{esc(LABELS["summary_only"])}'
                + (f' · {esc(completed_at)}' if completed_at else "")
                + "</span></div>"
            )
            continue
        completed_at = as_text(record.get("completed_at"))
        suffix = (
            f'<div class="cap">{esc(LABELS["finished_at"])} {esc(completed_at)}</div>'
            if completed_at
            else ""
        )
        blocks.append(
            item_summary(
                record,
                open_by_default=False,
                translations=translations,
                suffix=suffix,
            )
        )
    return (
        heading
        + "".join(blocks)
        + f'<div class="cap">{esc(LABELS["finished_cap"])}</div>'
    )


# --------------------------------------------------------------------------
# Collecting the data that drives the sections
# --------------------------------------------------------------------------
def collect_needs_you(items: Sequence[dict]) -> list[tuple[dict, dict]]:
    entries = []
    for item in items:
        for task in task_items(item):
            if as_text(task.get("status")) != "blocked":
                continue
            if blocker_kind(task) in ("needs_user", "unclassified"):
                entries.append((item, task))
    return entries


def collect_external(items: Sequence[dict]) -> list[tuple[dict, dict]]:
    entries = []
    for item in items:
        for task in task_items(item):
            if as_text(task.get("status")) != "blocked":
                continue
            if blocker_kind(task) == "external":
                entries.append((item, task))
    return entries


def collect_activity(items: Sequence[dict], archived: Sequence[dict],
                     translations: Optional[dict] = None) -> list[tuple[str, str, str]]:
    """Return ``(timestamp, original message, shown message)``, newest first."""
    events: list[tuple[str, str, str, str]] = []
    for item in list(items) + list(archived):
        for task in task_items(item):
            status = as_text(task.get("status"))
            task_id = as_text(task.get("id"))
            description = as_text(task.get("description"))
            if status in ("completed", "cancelled"):
                stamp = as_text(task.get("completed_at"))
                if not stamp:
                    continue
                verb = LABELS["activity_completed"] if status == "completed" else LABELS["activity_cancelled"]
                original = f"{task_id} {verb}：{description}"
                shown = f"{task_id} {verb}：{translated(description, translations)}"
                events.append((stamp, verb, original, shown))
            elif status == "blocked":
                blocker = blocker_of(task)
                stamp = as_text(blocker.get("since")) if blocker else ""
                if not stamp:
                    continue
                verb = LABELS["activity_blocked"]
                detail = task_note(task) or description
                shown_detail = shown_note(task, translations) or translated(description, translations)
                events.append((stamp, verb, f"{task_id} {verb}：{detail}", f"{task_id} {verb}：{shown_detail}"))
    events.sort(key=lambda row: timestamp_key(row[0]), reverse=True)
    return [(stamp, original, shown) for stamp, _kind, original, shown in events[:ACTIVITY_LIMIT]]


def collect_finished(item_list: dict, archive: dict) -> tuple[list[tuple[dict, bool]], list[tuple[str, str]]]:
    archive_index: dict[str, dict] = {}
    archive_order: list[str] = []
    for record in as_list(archive.get("items")):
        record = as_dict(record)
        record_id = as_text(record.get("id"))
        if not record_id or record_id in archive_index:
            continue
        archive_index[record_id] = record
        archive_order.append(record_id)

    entries: list[tuple[dict, bool]] = []
    seen: set[str] = set()
    for summary in as_list(item_list.get("terminal_summary")):
        summary = as_dict(summary)
        summary_id = as_text(summary.get("id"))
        if not summary_id or summary_id in seen:
            continue
        seen.add(summary_id)
        record = archive_index.get(summary_id)
        if record is None:
            entries.append((summary, False))
            continue
        merged = dict(record)
        if not as_text(merged.get("status")):
            merged["status"] = summary.get("status")
        if not as_text(merged.get("description")):
            merged["description"] = summary.get("description")
        if not as_text(merged.get("completed_at")):
            merged["completed_at"] = summary.get("completed_at")
        entries.append((merged, True))
    for record_id in archive_order:
        if record_id in seen:
            continue
        seen.add(record_id)
        entries.append((archive_index[record_id], True))

    entries.sort(key=lambda pair: timestamp_key(pair[0].get("completed_at")), reverse=True)

    deliverables: list[tuple[str, str]] = []
    for record, _has_archive in entries:
        if as_text(record.get("status")) != "completed":
            continue
        for path in as_list(record.get("files")):
            path_text = as_text(path)
            if not path_text:
                continue
            deliverables.append((as_text(record.get("id")), path_text))
            if len(deliverables) >= DELIVERABLE_LIMIT:
                return entries, deliverables
    return entries, deliverables


# --------------------------------------------------------------------------
# Rendering and file plumbing
# --------------------------------------------------------------------------
def template_path() -> Path:
    return Path(__file__).resolve().parent.parent.joinpath(*TEMPLATE_RELATIVE)


def read_json(path: Path, required: bool) -> dict:
    if not path.exists():
        if required:
            raise RenderError(f"missing required file: {path}")
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RenderError(f"cannot read {path}: {exc}") from exc
    if not raw.strip():
        if required:
            raise RenderError(f"empty JSON file: {path}")
        return {}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RenderError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise RenderError(f"expected a JSON object at the top level of {path}")
    return loaded


def build_page(project_root: Path) -> tuple[str, Path]:
    current = project_root / CURRENT_DIR
    item_list = read_json(current / ITEM_LIST_NAME, required=True)
    archive = read_json(current / ARCHIVE_NAME, required=False)

    # D16: the translation cache is optional. A malformed cache is a warning,
    # never a failure — the page is rendered with the original strings.
    translations, warning = ds.load_translations(current / ds.CACHE_NAME)
    if warning:
        print(f"render-dashboard: warning: ignoring translation cache: {warning}",
              file=sys.stderr)

    raw_items = item_list.get("items")
    if raw_items is not None and not isinstance(raw_items, list):
        raise RenderError(f'"items" must be a list in {current / ITEM_LIST_NAME}')
    items = [as_dict(entry) for entry in as_list(raw_items)]

    assignment = as_dict(item_list.get("assignment"))
    updated = as_text(assignment.get("last_updated"))

    needs_you = collect_needs_you(items)
    external = collect_external(items)
    finished, deliverables = collect_finished(item_list, archive)
    activity = collect_activity(items, [record for record, _ in finished], translations)

    in_progress_items = sum(1 for item in items if as_text(item.get("status")) == "in_progress")
    completed_items = sum(
        1 for record, _ in finished if as_text(record.get("status")) == "completed"
    )
    total_items = len(items) + len(finished)

    name = as_text(assignment.get("name")) or project_root.name
    page_title = f"{name} · {LABELS['page_title_suffix']}"

    sections = {
        "{{PAGE_TITLE}}": esc(page_title),
        "{{HEADER}}": render_header(assignment, updated, translations),
        "{{KPIS}}": render_kpis(
            len(needs_you), len(external), in_progress_items, completed_items, total_items
        ),
        "{{NEEDS_YOU}}": render_needs_you(needs_you, translations),
        "{{EXTERNAL}}": render_external(external, translations),
        "{{ACTIVE_ITEMS}}": render_active_items(items, translations),
        "{{ACTIVITY_ROW}}": render_activity_row(activity, deliverables),
        "{{FINISHED}}": render_finished(finished, translations),
    }

    path = template_path()
    try:
        template = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RenderError(f"cannot read dashboard template {path}: {exc}") from exc

    page = template
    for placeholder in PLACEHOLDERS:
        page = page.replace(placeholder, sections[placeholder])
    leftover = [token for token in PLACEHOLDERS if token in page]
    if leftover:
        raise RenderError(f"unreplaced placeholder(s) in template: {', '.join(leftover)}")
    if "{{" in page:
        raise RenderError("template still contains an unknown '{{' placeholder")

    return page, current / DASHBOARD_NAME


def atomic_write(path: Path, text: str) -> None:
    """Atomic write, shared with the translation helper (D16)."""
    ds.atomic_write(path, text)


def render_project(project_root: Path, write: bool = True) -> Path:
    page, destination = build_page(project_root)
    if write:
        atomic_write(destination, page)
    return destination


def main(argv: Sequence[str]) -> int:
    if len(argv) != 2:
        print("usage: render-dashboard.py <project_root>", file=sys.stderr)
        return 2
    project_root = Path(argv[1]).expanduser()
    try:
        destination = render_project(project_root)
    except RenderError as exc:
        print(f"render-dashboard: {exc}", file=sys.stderr)
        return 1
    print(f"render-dashboard: wrote {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
