"""Tests for the current-worktree sensitive-data check."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "check-sensitive-data.sh"


class SensitiveDataCheckTest(unittest.TestCase):
    def run_checker(self, root: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["/bin/bash", str(CHECKER), str(root)],
            capture_output=True,
            text=True,
        )

    def test_script_is_valid_bash(self):
        result = subprocess.run(
            ["/bin/bash", "-n", str(CHECKER)], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_current_worktree_is_clean(self):
        result = self.run_checker(REPO_ROOT)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("sensitive-data check: clean", result.stdout)

    def test_personal_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sensitive_path = "/" + "Users/example/private-project"
            (root / "note.md").write_text(sensitive_path + "\n", encoding="utf-8")
            result = self.run_checker(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("note.md", result.stdout)

    def test_private_key_header_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            header = "-----BEGIN " + "OPENSSH PRIVATE KEY-----"
            (root / "key.txt").write_text(header + "\n", encoding="utf-8")
            result = self.run_checker(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("key.txt", result.stdout)


if __name__ == "__main__":
    unittest.main()
