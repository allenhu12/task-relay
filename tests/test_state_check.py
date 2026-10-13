"""Tests for scripts/state-check.py (TASK-001-06).

The two `live-*` fixtures are byte-exact copies of the state folders produced by
the live Claude/haiku and Codex/gpt-6-luna runs, so the checker is tested against
data a cheap model actually wrote.

Run from the repository root:
    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
CHECKER = SCRIPTS_DIR / "state-check.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

sys.path.insert(0, str(SCRIPTS_DIR))
sys.dont_write_bytecode = True


class Base(unittest.TestCase):
    def project(self, fixture: str) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / "project"
        shutil.copytree(FIXTURES / fixture, root)
        return root

    def check(self, root: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(CHECKER), str(root), *args],
            capture_output=True,
            text=True,
        )

    def problems(self, result: subprocess.CompletedProcess) -> list[str]:
        return [
            line
            for line in result.stdout.splitlines()
            if line.startswith("state-check: ")
            and not line.startswith("state-check: fixed")
            and not line.startswith("state-check: warning:")
            and line.strip() != "state-check: OK"
        ]

    def warnings(self, result: subprocess.CompletedProcess) -> list[str]:
        return [
            line for line in result.stdout.splitlines() if line.startswith("state-check: warning:")
        ]

    def fixes(self, result: subprocess.CompletedProcess) -> list[str]:
        return [
            line for line in result.stdout.splitlines() if line.startswith("state-check: fixed")
        ]

    def load(self, root: Path) -> dict:
        return json.loads((root / "00-current" / "item-list.json").read_text("utf-8"))

    def write(self, root: Path, payload: dict) -> None:
        (root / "00-current" / "item-list.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def minimal_project(self, **overrides) -> Path:
        """A tiny valid project that individual tests then break on purpose."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / "project"
        (root / "00-current").mkdir(parents=True)
        payload = {
            "assignment": {
                "name": "demo",
                "description": "demo project",
                "created": "2026-09-01T00:00:00Z",
                "last_updated": "2026-09-28T10:00:00Z",
            },
            "items": [
                {
                    "id": "ITEM-001",
                    "category": "feature",
                    "description": "Do the thing",
                    "priority": 1,
                    "validation_steps": ["it works"],
                    "status": "in_progress",
                    "completed_at": None,
                    "notes": "",
                    "working_dir": "20-working/ITEM-001",
                    "files": [],
                    "tasks": [
                        {
                            "id": "TASK-001-01",
                            "description": "First step",
                            "status": "in_progress",
                            "validation_steps": ["ok"],
                            "completed_at": None,
                            "notes": "",
                        }
                    ],
                }
            ],
            "terminal_summary": [],
            "metadata": {
                "total_items": 1,
                "completed": 0,
                "in_progress": 1,
                "blocked": 0,
                "pending": 0,
                "cancelled": 0,
            },
        }
        payload.update(overrides)
        self.write(root, payload)
        return root


class LiveEvidenceTest(Base):
    """The three mistakes the live runs made must be reported, and nothing else."""

    def test_claude_run_reports_rollup_and_invented_timestamps(self):
        result = self.check(self.project("live-claude"))
        self.assertEqual(result.returncode, 1)
        lines = self.problems(result)
        self.assertEqual(len(lines), 4, msg=result.stdout)
        self.assertEqual(sum("rollup: ITEM-001" in line for line in lines), 1)
        self.assertEqual(sum("equals assignment.created" in line for line in lines), 2)
        self.assertEqual(sum("last_updated was not refreshed" in line for line in lines), 1)
        # No metadata or blocker complaints: those fields matched the (wrong) rollup.
        self.assertFalse([line for line in lines if "metadata:" in line or "blocker:" in line])

    def test_codex_run_reports_rollup_and_missing_translations(self):
        result = self.check(self.project("live-codex"))
        self.assertEqual(result.returncode, 1)
        lines = self.problems(result)
        self.assertEqual(len(lines), 2, msg=result.stdout)
        self.assertEqual(sum("rollup: ITEM-001" in line for line in lines), 1)
        self.assertEqual(sum("translation: 3 string(s)" in line for line in lines), 1)

    def test_fix_repairs_rollup_and_metadata_only(self):
        root = self.project("live-claude")
        before = self.load(root)
        result = self.check(root, "--fix")
        self.assertEqual(result.returncode, 1, msg=result.stdout)  # timestamps remain
        after = self.load(root)
        self.assertEqual(after["items"][0]["status"], "blocked")
        self.assertEqual(after["metadata"]["blocked"], 1)
        self.assertEqual(after["metadata"]["in_progress"], 0)
        self.assertEqual(after["metadata"]["total_items"], 1)
        # Everything else is untouched: same values, same order.
        self.assertEqual(self.normalized(before), self.normalized(after))
        self.assertEqual(
            after["items"][0]["tasks"][0]["completed_at"],
            "2026-09-28T00:00:00Z",
        )
        self.assertEqual(
            after["items"][0]["tasks"][1]["blocker"]["since"],
            "2026-09-28T00:00:00Z",
        )
        self.assertFalse((root / "00-current" / "00-current").exists())

    def test_fix_leaves_the_translation_problem_alone(self):
        root = self.project("live-codex")
        result = self.check(root, "--fix")
        self.assertEqual(result.returncode, 1, msg=result.stdout)
        self.assertEqual(len(self.problems(result)), 1)
        self.assertIn("translation:", self.problems(result)[0])
        self.assertEqual(self.load(root)["items"][0]["status"], "blocked")

    def normalized(self, doc: dict) -> dict:
        clone = copy.deepcopy(doc)
        clone.pop("metadata", None)
        for item in clone.get("items", []):
            item.pop("status", None)
        return clone


class FixtureTest(Base):
    def test_clean_fixtures_pass(self):
        for fixture in ("empty", "mockup", "long", "special", "english"):
            with self.subTest(fixture=fixture):
                result = self.check(self.project(fixture))
                self.assertEqual(result.returncode, 0, msg=result.stdout)
                self.assertEqual(self.problems(result), [])
                self.assertEqual(result.stdout.strip(), "state-check: OK")

    def test_legacy_fixture_item_rollup_is_reported(self):
        # Older data can park an item in `blocked` while a task is still pending;
        # the rollup rule (TASK-001-06) says that item must be in_progress.
        result = self.check(self.project("legacy"))
        self.assertEqual(result.returncode, 1)
        lines = self.problems(result)
        self.assertEqual(len(lines), 1, msg=result.stdout)
        self.assertIn("rollup: ITEM-010", lines[0])
        self.assertIn("must go back to in_progress", lines[0])

    def test_legacy_blocked_task_without_blocker_is_not_a_problem(self):
        # D14: a blocked task with no blocker is valid legacy data.
        result = self.check(self.project("legacy"))
        self.assertFalse(
            [line for line in self.problems(result) if "blocker" in line], msg=result.stdout
        )

    def test_fix_on_a_clean_fixture_changes_nothing(self):
        root = self.project("mockup")
        before = (root / "00-current" / "item-list.json").read_bytes()
        result = self.check(root, "--fix")
        self.assertEqual(result.returncode, 0, msg=result.stdout)
        self.assertEqual(self.fixes(result), [])
        self.assertEqual((root / "00-current" / "item-list.json").read_bytes(), before)


class RollupTest(Base):
    def test_item_becomes_blocked_when_every_remaining_task_is_blocked(self):
        root = self.minimal_project()
        doc = self.load(root)
        doc["items"][0]["tasks"][0]["status"] = "blocked"
        doc["items"][0]["tasks"][0]["blocker"] = {
            "type": "needs_user",
            "summary": "need a decision",
            "question": "Which one?",
            "since": "2026-09-28T09:00:00Z",
        }
        self.write(root, doc)
        result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be blocked", self.problems(result)[0])
        self.check(root, "--fix")
        self.assertEqual(self.load(root)["items"][0]["status"], "blocked")

    def test_item_returns_to_in_progress_when_a_task_is_not_blocked(self):
        root = self.minimal_project()
        doc = self.load(root)
        doc["items"][0]["status"] = "blocked"
        doc["items"][0]["tasks"].append(
            {
                "id": "TASK-001-02",
                "description": "Second step",
                "status": "pending",
                "validation_steps": ["ok"],
                "completed_at": None,
                "notes": "",
            }
        )
        self.write(root, doc)
        result = self.check(root)
        self.assertEqual(result.returncode, 1)
        joined = " ".join(self.problems(result))
        self.assertIn("must go back to in_progress", joined)
        self.assertIn("metadata: in_progress", joined)
        self.check(root, "--fix")
        self.assertEqual(self.load(root)["items"][0]["status"], "in_progress")
        self.assertEqual(self.load(root)["metadata"]["in_progress"], 1)

    def test_pending_item_is_not_forced_to_in_progress(self):
        root = self.minimal_project()
        doc = self.load(root)
        doc["items"][0]["status"] = "pending"
        doc["items"][0]["tasks"][0]["status"] = "pending"
        doc["metadata"]["in_progress"] = 0
        doc["metadata"]["pending"] = 1
        self.write(root, doc)
        result = self.check(root)
        self.assertEqual(result.returncode, 0, msg=result.stdout)

    def test_terminal_items_are_left_alone(self):
        root = self.minimal_project()
        doc = self.load(root)
        doc["items"][0]["tasks"][0]["status"] = "completed"
        doc["items"][0]["tasks"][0]["completed_at"] = "2026-09-28T09:00:00Z"
        doc["items"][0]["status"] = "completed"
        doc["items"][0]["completed_at"] = "2026-09-28T09:30:00Z"
        doc["metadata"].update({"completed": 1, "in_progress": 0})
        self.write(root, doc)
        self.assertEqual(self.check(root).returncode, 0)


class MetadataTest(Base):
    def test_wrong_counts_are_reported_per_key(self):
        root = self.minimal_project()
        doc = self.load(root)
        doc["metadata"].update({"total_items": 9, "in_progress": 0, "blocked": 3})
        self.write(root, doc)
        result = self.check(root)
        self.assertEqual(result.returncode, 1)
        lines = self.problems(result)
        self.assertEqual(len(lines), 3, msg=result.stdout)
        for expected in ("metadata: total_items", "metadata: in_progress", "metadata: blocked"):
            self.assertIn(expected, " ".join(lines))

    def test_fix_repairs_metadata(self):
        root = self.minimal_project()
        doc = self.load(root)
        doc["metadata"] = {"total_items": 9, "completed": 0, "in_progress": 0,
                           "blocked": 3, "pending": 0, "cancelled": 0}
        self.write(root, doc)
        result = self.check(root, "--fix")
        self.assertEqual(result.returncode, 0, msg=result.stdout)
        self.assertEqual(
            self.load(root)["metadata"],
            {"total_items": 1, "completed": 0, "in_progress": 1,
             "blocked": 0, "pending": 0, "cancelled": 0},
        )

    def test_missing_metadata_key_is_reported(self):
        root = self.minimal_project()
        doc = self.load(root)
        del doc["metadata"]["cancelled"]
        self.write(root, doc)
        result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("metadata: cancelled is missing", " ".join(self.problems(result)))


class TimestampTest(Base):
    def test_terminal_task_without_completed_at(self):
        root = self.minimal_project()
        doc = self.load(root)
        doc["items"][0]["tasks"][0]["status"] = "completed"
        doc["items"][0]["completed_at"] = "2026-09-28T09:00:00Z"
        doc["items"][0]["status"] = "completed"
        doc["metadata"].update({"completed": 1, "in_progress": 0})
        self.write(root, doc)
        result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("is missing for a completed task", " ".join(self.problems(result)))

    def test_non_iso_timestamp_is_reported(self):
        root = self.minimal_project()
        doc = self.load(root)
        doc["items"][0]["tasks"][0]["completed_at"] = "2026-09-28"
        doc["items"][0]["tasks"][0]["status"] = "completed"
        self.write(root, doc)
        result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("is not an ISO-8601 UTC timestamp", " ".join(self.problems(result)))

    def test_timestamp_newer_than_last_updated_is_reported(self):
        root = self.minimal_project()
        doc = self.load(root)
        doc["items"][0]["tasks"][0]["status"] = "completed"
        doc["items"][0]["tasks"][0]["completed_at"] = "2026-09-29T10:00:00Z"
        self.write(root, doc)
        result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("is newer than assignment.last_updated", " ".join(self.problems(result)))

    def test_completed_at_on_a_non_terminal_task_is_reported(self):
        root = self.minimal_project()
        doc = self.load(root)
        doc["items"][0]["tasks"][0]["completed_at"] = "2026-09-28T09:00:00Z"
        self.write(root, doc)
        result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must be null until the task is terminal", " ".join(self.problems(result)))

    def test_invented_timestamp_equal_to_created_is_reported(self):
        root = self.minimal_project()
        doc = self.load(root)
        doc["assignment"]["created"] = "2026-09-28T10:00:00Z"
        doc["assignment"]["last_updated"] = "2026-09-28T10:00:00Z"
        doc["items"][0]["tasks"][0]["status"] = "completed"
        doc["items"][0]["tasks"][0]["completed_at"] = "2026-09-28T10:00:00Z"
        self.write(root, doc)
        result = self.check(root)
        self.assertEqual(result.returncode, 1)
        joined = " ".join(self.problems(result))
        self.assertIn("equals assignment.created", joined)
        self.assertIn("was not refreshed", joined)


class BlockerTest(Base):
    def test_blocker_on_a_non_blocked_task_is_reported(self):
        root = self.minimal_project()
        doc = self.load(root)
        doc["items"][0]["tasks"][0]["blocker"] = {
            "type": "external",
            "summary": "waiting",
            "waiting_on": "someone",
            "since": "2026-09-28T09:00:00Z",
        }
        self.write(root, doc)
        result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("still carries a blocker", " ".join(self.problems(result)))

    def test_missing_required_blocker_fields_are_reported(self):
        root = self.minimal_project()
        doc = self.load(root)
        doc["items"][0]["tasks"][0]["status"] = "blocked"
        doc["items"][0]["tasks"][0]["blocker"] = {
            "type": "needs_user",
            "summary": "",
            "since": "",
        }
        self.write(root, doc)
        result = self.check(root)
        joined = " ".join(self.problems(result))
        self.assertIn("blocker.summary is required", joined)
        self.assertIn("blocker.since is required", joined)
        self.assertIn("blocker.question is required", joined)

    def test_external_blocker_needs_waiting_on(self):
        root = self.minimal_project()
        doc = self.load(root)
        doc["items"][0]["tasks"][0]["status"] = "blocked"
        doc["items"][0]["tasks"][0]["blocker"] = {
            "type": "external",
            "summary": "waiting",
            "since": "2026-09-28T09:00:00Z",
        }
        self.write(root, doc)
        result = self.check(root)
        self.assertIn("blocker.waiting_on is required", " ".join(self.problems(result)))


class RulebookContextPathTest(Base):
    """`rulebook` / `context` on items and tasks: bad path = problem, missing file = warning."""

    def with_paths(self, item: dict, task: dict, files: tuple[str, ...] = ()) -> Path:
        root = self.minimal_project()
        doc = self.load(root)
        doc["items"][0].update(item)
        doc["items"][0]["tasks"][0].update(task)
        self.write(root, doc)
        for name in files:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("x", encoding="utf-8")
        return root

    def test_existing_files_pass_without_warnings(self):
        root = self.with_paths(
            {"rulebook": "20-working/ITEM-001/ITEM-001-rulebook.md", "context": ["10-reference/a.md"]},
            {"rulebook": "20-working/ITEM-001/TASK-001-01-rulebook.md", "context": ["05-plans/b.md"]},
            files=(
                "20-working/ITEM-001/ITEM-001-rulebook.md",
                "10-reference/a.md",
                "20-working/ITEM-001/TASK-001-01-rulebook.md",
                "05-plans/b.md",
            ),
        )
        result = self.check(root)
        self.assertEqual(result.returncode, 0, msg=result.stdout)
        self.assertEqual(self.warnings(result), [])

    def test_absent_and_null_fields_pass(self):
        root = self.with_paths({"rulebook": None, "context": []}, {"rulebook": None})
        result = self.check(root)
        self.assertEqual(result.returncode, 0, msg=result.stdout)
        self.assertEqual(self.warnings(result), [])

    def test_missing_file_is_a_warning_only(self):
        root = self.with_paths({}, {"rulebook": "20-working/ITEM-001/TASK-001-01-rulebook.md"})
        result = self.check(root)
        self.assertEqual(result.returncode, 0, msg=result.stdout)
        self.assertEqual(self.problems(result), [])
        self.assertIn("TASK-001-01.rulebook file not found", " ".join(self.warnings(result)))
        self.assertIn("state-check: OK", result.stdout)

    def test_absolute_path_is_a_problem(self):
        root = self.with_paths({"context": ["/etc/passwd"]}, {"rulebook": "~/rules.md"})
        result = self.check(root)
        self.assertEqual(result.returncode, 1)
        joined = " ".join(self.problems(result))
        self.assertIn("ITEM-001.context[0] must be relative", joined)
        self.assertIn("TASK-001-01.rulebook must be relative", joined)

    def test_parent_segment_is_a_problem(self):
        root = self.with_paths({}, {"context": ["05-plans/../../secret.md"]})
        result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must not contain '..'", " ".join(self.problems(result)))

    def test_wrong_shapes_are_problems(self):
        root = self.with_paths({"context": "10-reference/a.md"}, {"rulebook": "", "context": [3]})
        result = self.check(root)
        self.assertEqual(result.returncode, 1)
        joined = " ".join(self.problems(result))
        self.assertIn("ITEM-001.context must be a list", joined)
        self.assertIn("TASK-001-01.rulebook must be a non-empty string", joined)
        self.assertIn("TASK-001-01.context[0] must be a non-empty string", joined)

    def test_paths_resolve_from_project_root_when_given_00_current(self):
        root = self.with_paths(
            {}, {"rulebook": "20-working/ITEM-001/TASK-001-01-rulebook.md"},
            files=("20-working/ITEM-001/TASK-001-01-rulebook.md",),
        )
        result = self.check(root / "00-current")
        self.assertEqual(result.returncode, 0, msg=result.stdout)
        self.assertEqual(self.warnings(result), [])


class TranslationTest(Base):
    def test_language_flag_reports_missing_translations(self):
        root = self.project("english")
        result = self.check(root, "--language", "zh-CN")
        self.assertEqual(result.returncode, 1)
        self.assertIn("translation:", " ".join(self.problems(result)))

    def test_cache_without_language_flag_is_still_checked(self):
        root = self.project("live-codex")
        result = self.check(root)
        self.assertIn("translation:", " ".join(self.problems(result)))

    def test_no_cache_and_no_language_flag_skips_the_check(self):
        root = self.project("mockup")
        result = self.check(root)
        self.assertEqual(result.returncode, 0, msg=result.stdout)
        self.assertFalse([line for line in self.problems(result) if "translation:" in line])

    def test_complete_cache_passes(self):
        root = self.project("live-claude")
        result = self.check(root)
        self.assertFalse([line for line in self.problems(result) if "translation:" in line])


class CliTest(Base):
    def test_missing_item_list_is_an_error(self):
        root = self.project("empty")
        (root / "00-current" / "item-list.json").unlink()
        result = self.check(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("state-check: json:", result.stderr)

    def test_accepts_a_00_current_directory(self):
        root = self.project("mockup")
        result = self.check(root / "00-current")
        self.assertEqual(result.returncode, 0, msg=result.stdout)

    def test_help_exits_zero(self):
        result = subprocess.run(
            [sys.executable, str(CHECKER), "--help"], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage", result.stdout.lower())

    def test_script_imports_only_stdlib_and_siblings(self):
        import ast

        tree = ast.parse(CHECKER.read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
        allowed = set(sys.stdlib_module_names) | {path.stem for path in SCRIPTS_DIR.glob("*.py")}
        self.assertTrue(names.issubset(allowed), msg=f"non-stdlib imports: {names - allowed}")


if __name__ == "__main__":
    unittest.main()
