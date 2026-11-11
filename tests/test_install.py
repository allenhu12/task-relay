"""Tests for the unified task-relay installer."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "install.sh"


class UnifiedInstallerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.cursor_home = root / "cursor"
        self.claude_home = root / "claude"
        self.codex_home = root / "codex"

    def run_installer(self, *args: str) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["CURSOR_CONFIG_DIR"] = str(self.cursor_home)
        env["CLAUDE_CONFIG_DIR"] = str(self.claude_home)
        env["CODEX_HOME"] = str(self.codex_home)
        return subprocess.run(
            ["/bin/bash", str(INSTALLER), *args],
            capture_output=True,
            text=True,
            env=env,
        )

    def test_script_is_valid_bash(self):
        result = subprocess.run(
            ["/bin/bash", "-n", str(INSTALLER)], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_cursor_installs_skill_and_state_writer(self):
        result = self.run_installer("--cursor")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        skill = self.cursor_home / "skills" / "task-relay"
        self.assertEqual((skill / "SKILL.md").read_bytes(), (REPO_ROOT / "SKILL.md").read_bytes())
        self.assertTrue((skill / "scripts" / "render-dashboard.sh").exists())
        self.assertTrue((skill / "references" / "state-writer-contract.md").exists())
        self.assertTrue((skill / "assets" / "item-list.template.json").exists())
        writer = self.cursor_home / "agents" / "task-relay-state-writer.md"
        self.assertTrue(writer.exists())
        self.assertFalse(self.claude_home.exists())
        self.assertFalse(self.codex_home.exists())

    def test_claude_and_codex_use_their_own_skill_roots(self):
        claude = self.run_installer("--claude")
        self.assertEqual(claude.returncode, 0, msg=claude.stderr)
        self.assertTrue((self.claude_home / "skills" / "task-relay" / "SKILL.md").exists())
        self.assertTrue((self.claude_home / "agents" / "task-relay-state-writer.md").exists())

        codex = self.run_installer("--codex")
        self.assertEqual(codex.returncode, 0, msg=codex.stderr)
        self.assertTrue((self.codex_home / "skills" / "task-relay" / "SKILL.md").exists())
        self.assertTrue((self.codex_home / "agents" / "task-relay-state-writer.toml").exists())

    def test_dry_run_writes_nothing(self):
        result = self.run_installer("--cursor", "--dry-run")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("[dry-run]", result.stdout)
        self.assertFalse(self.cursor_home.exists())

    def test_second_install_is_idempotent(self):
        first = self.run_installer("--cursor")
        self.assertEqual(first.returncode, 0, msg=first.stderr)
        second = self.run_installer("--cursor")
        self.assertEqual(second.returncode, 0, msg=second.stderr)
        self.assertIn("already installed:", second.stdout)

    def test_conflict_stops_before_any_new_write(self):
        skill = self.cursor_home / "skills" / "task-relay"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("local edits\n", encoding="utf-8")

        result = self.run_installer("--cursor")
        self.assertEqual(result.returncode, 1)
        self.assertIn("refusing to overwrite", result.stderr)
        self.assertFalse((skill / "scripts").exists())
        self.assertFalse((self.cursor_home / "agents").exists())

    def test_state_writer_conflict_stops_before_skill_write(self):
        writer = self.cursor_home / "agents" / "task-relay-state-writer.md"
        writer.parent.mkdir(parents=True)
        writer.write_text("local agent\n", encoding="utf-8")

        result = self.run_installer("--cursor")
        self.assertEqual(result.returncode, 1)
        self.assertIn("refusing to overwrite", result.stderr)
        self.assertFalse((self.cursor_home / "skills").exists())
        self.assertEqual(writer.read_text(encoding="utf-8"), "local agent\n")

    def test_force_replaces_conflicting_files(self):
        skill = self.cursor_home / "skills" / "task-relay"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("stale\n", encoding="utf-8")

        result = self.run_installer("--cursor", "--force")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual((skill / "SKILL.md").read_bytes(), (REPO_ROOT / "SKILL.md").read_bytes())
        self.assertTrue((self.cursor_home / "agents" / "task-relay-state-writer.md").exists())

    def test_requires_exactly_one_client(self):
        missing = self.run_installer()
        self.assertEqual(missing.returncode, 2)
        self.assertIn("choose one client", missing.stderr)

        multiple = self.run_installer("--cursor", "--codex")
        self.assertEqual(multiple.returncode, 2)
        self.assertIn("choose exactly one client", multiple.stderr)

    def test_help_exits_zero(self):
        result = self.run_installer("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stdout)


if __name__ == "__main__":
    unittest.main()
