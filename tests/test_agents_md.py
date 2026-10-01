"""Tests for scripts/agents-md.py (ITEM-003 / C).

Run from the repository root:
    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "agents-md.py"
TEMPLATE = REPO_ROOT / "assets" / "AGENTS.template.md"

sys.dont_write_bytecode = True

OLD_COPY = """# AI Agent Instructions

Rotate with `bash {SKILL_SCRIPTS_PATH}/rotate-progress-log.sh`.
"""


class AgentsMdTest(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "My Project"
        self.root.mkdir()

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
        )

    def test_template_has_version_marker(self):
        self.assertRegex(
            TEMPLATE.read_text(encoding="utf-8").splitlines()[0],
            r"^<!-- task-relay-agents: \d+ -->$",
        )

    def test_check_missing(self):
        result = self.run_script("check", str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing", result.stdout)

    def test_write_resolves_every_skill_placeholder(self):
        result = self.run_script("write", str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        text = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\{(PROJECT_NAME|SKILL_[A-Z_]+)\}", text))
        self.assertIn("# AI Agent Instructions — My Project", text)
        self.assertIn(str(REPO_ROOT / "scripts") + "/rotate-progress-log.sh", text)
        # Spec placeholders are documentation, not skill placeholders: keep them.
        self.assertIn("{PROJECT_ROOT}", text)

    def test_write_name_option(self):
        self.run_script("write", str(self.root), "--name", "Relay")
        text = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("# AI Agent Instructions — Relay", text)

    def test_check_current_after_write(self):
        self.run_script("write", str(self.root))
        result = self.run_script("check", str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("current", result.stdout)

    def test_check_old_copy_is_outdated(self):
        (self.root / "AGENTS.md").write_text(OLD_COPY, encoding="utf-8")
        result = self.run_script("check", str(self.root))
        self.assertEqual(result.returncode, 1)
        self.assertIn("outdated: version none", result.stdout)
        self.assertIn("unresolved placeholder: {SKILL_SCRIPTS_PATH}", result.stdout)

    def test_write_backs_up_old_copy(self):
        (self.root / "AGENTS.md").write_text(OLD_COPY, encoding="utf-8")
        result = self.run_script("write", str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        backups = list((self.root / "90-archive").glob("AGENTS.md.bak-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), OLD_COPY)

    def test_write_twice_is_unchanged_and_makes_no_backup(self):
        self.run_script("write", str(self.root))
        result = self.run_script("write", str(self.root))
        self.assertIn("unchanged", result.stdout)
        self.assertFalse((self.root / "90-archive").exists())

    def test_dry_run_writes_nothing(self):
        (self.root / "AGENTS.md").write_text(OLD_COPY, encoding="utf-8")
        result = self.run_script("write", str(self.root), "--dry-run")
        self.assertEqual(result.returncode, 0)
        self.assertIn("+++ AGENTS.md (new)", result.stdout)
        self.assertEqual((self.root / "AGENTS.md").read_text(encoding="utf-8"), OLD_COPY)
        self.assertFalse((self.root / "90-archive").exists())


if __name__ == "__main__":
    unittest.main()
