"""Tests for scripts/render-dashboard.py and scripts/render-dashboard.sh.

Covers acceptance A1-A6 from the issue "task-relay HTML status dashboard",
plus the D14 legacy rule and the non-destructive failure rule.

Run from the repository root:
    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import ast
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
SCRIPT = SCRIPTS_DIR / "render-dashboard.py"
WRAPPER = SCRIPTS_DIR / "render-dashboard.sh"
TEMPLATE = REPO_ROOT / "assets" / "dashboard.template.html"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

FIXTURE_NAMES = ("empty", "mockup", "legacy", "long", "special")
MAX_DASHBOARD_BYTES = 200 * 1024

sys.path.insert(0, str(SCRIPTS_DIR))
render_mod = importlib.import_module("render-dashboard")


class StructureParser(HTMLParser):
    """Count <details> elements and collect the visible text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.details = 0
        self.open_details: list[bool] = []
        self.text_parts: list[str] = []
        self.tags: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag == "details":
            self.details += 1
            self.open_details.append("open" in dict(attrs))

    def handle_data(self, data):
        self.text_parts.append(data)

    @property
    def text(self) -> str:
        return "".join(self.text_parts)


def parse_structure(html_text: str) -> StructureParser:
    parser = StructureParser()
    parser.feed(html_text)
    parser.close()
    return parser


class DashboardTest(unittest.TestCase):
    def project(self, fixture: str) -> Path:
        """Copy a fixture into a temporary project root."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / "project"
        shutil.copytree(FIXTURES / fixture, root)
        return root

    def render(self, root: Path, expect: int = 0) -> subprocess.CompletedProcess:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(root)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            expect,
            msg=f"stdout={result.stdout!r} stderr={result.stderr!r}",
        )
        return result

    def dashboard_text(self, fixture: str) -> str:
        root = self.project(fixture)
        self.render(root)
        return (root / "00-current" / "dashboard.html").read_text(encoding="utf-8")

    def load(self, root: Path, name: str) -> dict:
        return json.loads((root / "00-current" / name).read_text(encoding="utf-8"))

    # ---- A1: every fixture renders -------------------------------------
    def test_a1_all_fixtures_render(self):
        for fixture in FIXTURE_NAMES:
            with self.subTest(fixture=fixture):
                text = self.dashboard_text(fixture)
                self.assertTrue(text.startswith("<!doctype html>"))
                self.assertIn('lang="zh-Hans"', text)
                self.assertNotIn("{{", text)

    def test_a1_empty_project_has_no_deliverables_section(self):
        text = self.dashboard_text("empty")
        self.assertNotIn(render_mod.LABELS["section_deliverables"], text)
        self.assertIn(render_mod.LABELS["section_needs_you"], text)

    # ---- A2: no script, no external URL --------------------------------
    def test_a2_no_script_and_no_external_urls(self):
        for fixture in FIXTURE_NAMES:
            with self.subTest(fixture=fixture):
                text = self.dashboard_text(fixture)
                lowered = text.lower()
                self.assertNotIn("<script", lowered)
                self.assertNotIn("http://", lowered)
                self.assertNotIn("https://", lowered)
                self.assertNotIn("//", text)
                self.assertNotIn("<link", lowered)
                self.assertNotIn("<img", lowered)

    def test_a2_template_has_no_external_resource_or_script(self):
        template = TEMPLATE.read_text(encoding="utf-8")
        lowered = template.lower()
        self.assertNotIn("<script", lowered)
        self.assertNotIn("<link", lowered)
        self.assertNotIn("http://", lowered)
        self.assertNotIn("https://", lowered)
        self.assertNotIn("//", template)
        self.assertIn("prefers-color-scheme", template)
        self.assertIn("details.item", template)
        for placeholder in render_mod.PLACEHOLDERS:
            with self.subTest(placeholder=placeholder):
                self.assertIn(placeholder, template)

    # ---- A3: escaping and structure ------------------------------------
    def test_a3_special_characters_are_escaped(self):
        text = self.dashboard_text("special")
        self.assertNotIn("<script", text.lower())
        self.assertIn("&lt;script&gt;", text)
        self.assertIn("&amp;", text)
        self.assertIn("&quot;", text)
        self.assertIn("&#x27;", text)
        parsed = parse_structure(text)
        # One active item, and the finished item has no archive record.
        self.assertEqual(parsed.details, 1)
        # The escaped markup must survive as visible text, not as elements.
        self.assertIn("<script>alert('x')</script>", parsed.text)
        self.assertNotIn("script", [tag for tag in parsed.tags])

    def test_a3_structure_counts_match_the_data(self):
        root = self.project("mockup")
        self.render(root)
        text = (root / "00-current" / "dashboard.html").read_text(encoding="utf-8")
        parsed = parse_structure(text)
        data = self.load(root, "item-list.json")
        archive = self.load(root, "item-list-archive.json")
        expected = len(data["items"]) + len(archive["items"])
        self.assertEqual(parsed.details, expected)

    # ---- A4: byte-identical output -------------------------------------
    def test_a4_two_runs_are_byte_identical(self):
        first_root = self.project("mockup")
        second_root = self.project("mockup")
        self.render(first_root)
        self.render(second_root)
        first = (first_root / "00-current" / "dashboard.html").read_bytes()
        second = (second_root / "00-current" / "dashboard.html").read_bytes()
        self.assertEqual(first, second)

    def test_a4_updated_line_comes_from_the_file_not_the_clock(self):
        root = self.project("mockup")
        self.render(root)
        text = (root / "00-current" / "dashboard.html").read_text(encoding="utf-8")
        data = self.load(root, "item-list.json")
        self.assertIn(data["assignment"]["last_updated"], text)
        self.assertIn(render_mod.LABELS["updated"], text)

    # ---- A5: bounded size ----------------------------------------------
    def test_a5_large_project_stays_under_200kb(self):
        root = self.large_project()
        self.render(root)
        dashboard = root / "00-current" / "dashboard.html"
        size = dashboard.stat().st_size
        self.assertLess(size, MAX_DASHBOARD_BYTES, msg=f"{size} bytes is over the cap")

    def large_project(self, items: int = 50, tasks_per_item: int = 5) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / "project"
        current = root / "00-current"
        current.mkdir(parents=True)
        long_text = ("lorem ipsum dolor sit amet consectetur adipiscing elit " * 12)[:300]
        payload = {
            "assignment": {
                "name": "large project",
                "description": "size test",
                "created": "2026-09-01T00:00:00Z",
                "last_updated": "2026-09-20T00:00:00Z",
            },
            "items": [],
            "terminal_summary": [],
            "metadata": {
                "total_items": items,
                "completed": 0,
                "in_progress": 1,
                "blocked": 0,
                "pending": items - 1,
                "cancelled": 0,
            },
        }
        for index in range(1, items + 1):
            tasks = []
            for step in range(1, tasks_per_item + 1):
                tasks.append(
                    {
                        "id": f"TASK-{index:03d}-{step:02d}",
                        "description": long_text,
                        "status": "completed" if step == 1 else "pending",
                        "validation_steps": [],
                        "completed_at": "2026-09-19T10:00:00Z" if step == 1 else None,
                        "notes": "",
                    }
                )
            payload["items"].append(
                {
                    "id": f"ITEM-{index:03d}",
                    "category": "bulk",
                    "description": long_text,
                    "priority": index,
                    "validation_steps": ["done"],
                    "status": "in_progress" if index == 1 else "pending",
                    "completed_at": None,
                    "notes": "",
                    "working_dir": None,
                    "files": [],
                    "tasks": tasks,
                }
            )
        (current / "item-list.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        return root

    # ---- A6: missing python3 -------------------------------------------
    def test_a6_wrapper_without_python3_exits_127(self):
        root = self.project("mockup")
        env = os.environ.copy()
        env["PATH"] = ""
        result = subprocess.run(
            ["/bin/sh", str(WRAPPER), str(root)],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 127)
        self.assertEqual(
            result.stderr.strip(),
            "render-dashboard: python3 not found; install Python 3 or ask the main agent to stop (D11)",
        )
        self.assertFalse((root / "00-current" / "dashboard.html").exists())

    def test_a6_wrapper_renders_when_python3_exists(self):
        root = self.project("mockup")
        result = subprocess.run(
            ["/bin/sh", str(WRAPPER), str(root)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue((root / "00-current" / "dashboard.html").exists())

    # ---- failure modes --------------------------------------------------
    def test_bad_json_exits_nonzero_and_keeps_existing_dashboard(self):
        root = self.project("mockup")
        dashboard = root / "00-current" / "dashboard.html"
        dashboard.write_text("SENTINEL", encoding="utf-8")
        (root / "00-current" / "item-list.json").write_text("{not json", encoding="utf-8")
        result = self.render(root, expect=1)
        self.assertIn("invalid JSON", result.stderr)
        self.assertEqual(dashboard.read_text(encoding="utf-8"), "SENTINEL")

    def test_missing_item_list_exits_nonzero(self):
        root = self.project("mockup")
        (root / "00-current" / "item-list.json").unlink()
        result = self.render(root, expect=1)
        self.assertIn("missing required file", result.stderr)
        self.assertFalse((root / "00-current" / "dashboard.html").exists())

    def test_missing_archive_is_allowed(self):
        root = self.project("empty")
        self.assertFalse((root / "00-current" / "item-list-archive.json").exists())
        self.render(root)

    def test_bad_archive_is_reported(self):
        root = self.project("mockup")
        (root / "00-current" / "item-list-archive.json").write_text("{oops", encoding="utf-8")
        result = self.render(root, expect=1)
        self.assertIn("invalid JSON", result.stderr)

    def test_missing_template_exits_nonzero(self):
        root = self.project("mockup")
        original = TEMPLATE.read_text(encoding="utf-8")
        TEMPLATE.unlink()
        try:
            result = self.render(root, expect=1)
            self.assertIn("template", result.stderr)
        finally:
            TEMPLATE.write_text(original, encoding="utf-8")

    # ---- page content ---------------------------------------------------
    def test_kpis_and_sections(self):
        root = self.project("mockup")
        self.render(root)
        text = (root / "00-current" / "dashboard.html").read_text(encoding="utf-8")
        labels = render_mod.LABELS
        self.assertIn(labels["kpi_needs_you"], text)
        self.assertIn(labels["kpi_external"], text)
        self.assertIn(labels["kpi_in_progress_items"], text)
        self.assertIn(labels["kpi_completed_items"], text)
        # 2 needs_user blockers, 1 external, 1 in-progress item, 2 completed of 7.
        self.assertIn('<div class="n">2</div><div class="l">等你处理</div>', text)
        self.assertIn('<div class="n">1</div><div class="l">等外部</div>', text)
        self.assertIn('<div class="n">2/7</div><div class="l">已完成 item</div>', text)

    def test_needs_you_card_shows_question_and_default_action(self):
        text = self.dashboard_text("mockup")
        self.assertIn("CSV 里要放完整手机号吗？", text)
        self.assertIn("脱敏为 138****1234", text)
        self.assertIn(render_mod.LABELS["default_action"], text)
        self.assertIn("2026-09-28T14:10:00Z", text)

    def test_external_card_shows_waiting_on(self):
        text = self.dashboard_text("mockup")
        self.assertIn("没有支付网关沙箱账号", text)
        self.assertIn("财务部开通沙箱商户号", text)

    def test_legacy_blocked_without_blocker_is_unclassified(self):
        text = self.dashboard_text("legacy")
        labels = render_mod.LABELS
        self.assertIn(labels["unclassified"], text)
        self.assertIn(labels["unclassified_hint"], text)
        self.assertIn("不确定要用自增还是 UUID，需要用户决定", text)

    def test_task_notes_render_blocker_detail(self):
        text = self.dashboard_text("mockup")
        self.assertIn("等你：CSV 里要放完整手机号吗？", text)
        self.assertIn("等外部：财务部开通沙箱商户号", text)

    def test_finished_items_are_collapsed_and_keep_tasks(self):
        root = self.project("mockup")
        self.render(root)
        text = (root / "00-current" / "dashboard.html").read_text(encoding="utf-8")
        self.assertIn("TASK-001-01", text)
        self.assertIn("TASK-002-03", text)
        self.assertIn("TASK-007-02", text)
        parsed = parse_structure(text)
        # Four active items open, three finished items collapsed.
        self.assertEqual(parsed.open_details.count(True), 4)
        self.assertEqual(parsed.open_details.count(False), 3)

    def test_terminal_summary_without_archive_record_is_one_line(self):
        text = self.dashboard_text("special")
        self.assertIn("ITEM-031", text)
        self.assertIn(render_mod.LABELS["summary_only"], text)

    def test_deliverables_come_from_most_recent_completed_item(self):
        text = self.dashboard_text("mockup")
        labels = render_mod.LABELS
        self.assertIn(labels["section_deliverables"], text)
        self.assertIn("src/auth/login.tsx", text)
        self.assertIn(labels["deliverables_cap"], text)
        section = text.split(labels["section_deliverables"], 1)[1]
        section = section.split("<h2>", 1)[0]
        self.assertEqual(section.count("<li>"), 5)
        # ITEM-002 finished after ITEM-001, so its files come first.
        self.assertLess(section.index("src/auth/login.tsx"), section.index("migrations/001_init.sql"))

    def test_history_fields_are_not_shown(self):
        text = self.dashboard_text("mockup")
        self.assertNotIn("validation_steps", text)
        self.assertNotIn("completed_at", text)
        self.assertNotIn("sanitise", text)
        self.assertNotIn("20-working/ITEM-003", text)

    def test_activity_is_derived_and_capped(self):
        text = self.dashboard_text("mockup")
        labels = render_mod.LABELS
        self.assertIn(labels["section_activity"], text)
        self.assertIn(labels["activity_cap"], text)
        section = text.split(labels["section_activity"], 1)[1]
        feed = section.split("</ul>", 1)[0]
        self.assertEqual(feed.count("<li>"), 5)
        # The newest blocked event (14:12) must come before the 11:20 completion.
        self.assertLess(section.index("2026-09-28T14:12:00Z"), section.index("2026-09-28T11:20:00Z"))
        self.assertNotIn("progress.log", text)

    def test_long_text_is_truncated_with_full_title(self):
        root = self.project("long")
        self.render(root)
        text = (root / "00-current" / "dashboard.html").read_text(encoding="utf-8")
        data = self.load(root, "item-list.json")
        item_description = data["items"][0]["description"]
        self.assertGreater(len(item_description), render_mod.TRUNCATE_LIMIT)
        visible = item_description[: render_mod.TRUNCATE_LIMIT] + render_mod.TRUNCATION_SUFFIX
        self.assertIn(visible, text)
        self.assertIn(f'title="{item_description}"', text)
        self.assertNotIn(f">{item_description}<", text)

    def test_progress_bar_counts_completed_and_cancelled(self):
        text = self.dashboard_text("mockup")
        # ITEM-003: 1 completed + 4 tasks.
        self.assertIn("<small>1/4</small>", text)
        # ITEM-002 (archived): 2 completed + 1 cancelled of 3 tasks.
        self.assertIn("<small>3/3</small>", text)

    def test_status_labels_are_chinese(self):
        text = self.dashboard_text("mockup")
        for value in ("待办", "进行中", "完成", "受阻", "取消"):
            with self.subTest(label=value):
                self.assertIn(value, text)

    # ---- source-level guarantees ---------------------------------------
    def test_script_imports_only_stdlib(self):
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    names.add(node.module.split(".")[0])
        allowed = set(sys.stdlib_module_names)
        self.assertTrue(names.issubset(allowed), msg=f"non-stdlib imports: {names - allowed}")

    def test_labels_dict_covers_every_section(self):
        labels = render_mod.LABELS
        for key in (
            "section_needs_you",
            "section_external",
            "section_active",
            "section_activity",
            "section_deliverables",
            "section_finished",
            "unclassified",
            "updated",
        ):
            with self.subTest(key=key):
                self.assertTrue(labels[key])
        self.assertEqual(
            set(labels["status"]),
            {"pending", "in_progress", "completed", "blocked", "cancelled"},
        )

    def test_usage_error_without_arguments(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage", result.stderr)


if __name__ == "__main__":
    unittest.main()
