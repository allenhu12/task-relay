"""Tests for the state-writer subagent definitions, the contract and the installer.

Covers TASK-001-04 of the issue "task-relay HTML status dashboard" (D2, D10,
D11, D12) plus the Codex `multi_agent_v2` open point.

Run from the repository root:
    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = REPO_ROOT / "references" / "state-writer-contract.md"
CLAUDE_AGENT = REPO_ROOT / "assets" / "agents" / "claude" / "task-relay-state-writer.md"
CODEX_AGENT = REPO_ROOT / "assets" / "agents" / "codex" / "task-relay-state-writer.toml"
INSTALLER = REPO_ROOT / "scripts" / "install-state-writer.sh"

BEGIN = "<!-- BEGIN STATE-WRITER INSTRUCTIONS -->"
END = "<!-- END STATE-WRITER INSTRUCTIONS -->"

ALLOWED_CODEX_KEYS = {
    "name",
    "description",
    "developer_instructions",
    "model",
    "model_reasoning_effort",
}


def contract_body() -> str:
    text = CONTRACT.read_text(encoding="utf-8")
    match = re.search(re.escape(BEGIN) + r"\n(.*?)\n" + re.escape(END), text, re.S)
    if match is None:
        raise AssertionError("instruction-body markers are missing from the contract")
    return match.group(1).strip("\n")


def claude_frontmatter_and_body() -> tuple[dict, str]:
    text = CLAUDE_AGENT.read_text(encoding="utf-8")
    parts = text.split("---\n")
    if len(parts) < 3 or parts[0].strip():
        raise AssertionError("claude agent file does not start with YAML frontmatter")
    frontmatter = {}
    for line in parts[1].strip().splitlines():
        key, _, value = line.partition(":")
        frontmatter[key.strip()] = value.strip()
    return frontmatter, parts[2].strip("\n")


class AgentDefinitionTest(unittest.TestCase):
    def test_instruction_bodies_are_identical(self):
        body = contract_body()
        _frontmatter, claude_body = claude_frontmatter_and_body()
        codex = tomllib.loads(CODEX_AGENT.read_text(encoding="utf-8"))
        codex_body = str(codex["developer_instructions"]).strip("\n")
        self.assertEqual(claude_body, body)
        self.assertEqual(codex_body, body)
        self.assertGreater(len(body), 1000)

    def test_body_defines_the_reply_protocol_and_write_limits(self):
        body = contract_body()
        self.assertIn("STATE-WRITER OK <n> ops; dashboard rendered", body)
        self.assertIn("STATE-WRITER ERROR <step>: <message>", body)
        self.assertIn("user-decision.md", body)
        self.assertIn("memory.md", body)
        self.assertIn("20-working/", body)
        self.assertIn("00-current/item-list.json", body)
        self.assertIn("00-current/item-list-archive.json", body)
        self.assertIn("00-current/progress.log", body)

    def test_body_defines_the_update_request_shape(self):
        body = contract_body()
        for token in ("PROJECT_ROOT:", "RENDER_SCRIPT:", "OPS:", "progress.log:"):
            with self.subTest(token=token):
                self.assertIn(token, body)
        self.assertIn("blocker=none", body)
        self.assertIn("archive ITEM-001", body)

    def test_codex_definition_keys_and_pinned_model(self):
        data = tomllib.loads(CODEX_AGENT.read_text(encoding="utf-8"))
        self.assertEqual(set(data.keys()), ALLOWED_CODEX_KEYS)
        self.assertEqual(data["name"], "task-relay-state-writer")
        self.assertEqual(data["model"], "gpt-6-luna")
        self.assertEqual(data["model_reasoning_effort"], "medium")
        self.assertTrue(data["description"])

    def test_claude_definition_frontmatter(self):
        frontmatter, _body = claude_frontmatter_and_body()
        self.assertEqual(frontmatter["name"], "task-relay-state-writer")
        self.assertEqual(frontmatter["model"], "haiku")
        self.assertEqual(frontmatter["tools"], "Read, Write, Edit, Bash")
        self.assertTrue(frontmatter["description"])

    def test_contract_documents_the_agent_type_answer(self):
        text = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("multi_agent_v2", text)
        self.assertIn("agent_type", text)
        self.assertIn("gpt-6-luna", text)
        self.assertIn("haiku", text)
        for tag in ("[verified locally]", "[documented]"):
            with self.subTest(tag=tag):
                self.assertIn(tag, text)


class InstallerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        home = Path(self._tmp.name)
        self.claude_home = home / "claude"
        self.codex_home = home / "codex"
        self.claude_dest = self.claude_home / "agents" / "task-relay-state-writer.md"
        self.codex_dest = self.codex_home / "agents" / "task-relay-state-writer.toml"

    def run_installer(self, *args: str, claude_home: Path | None = None,
                      codex_home: Path | None = None) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["CLAUDE_HOME"] = str(claude_home or self.claude_home)
        env["CODEX_HOME"] = str(codex_home or self.codex_home)
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

    def test_fresh_install_copies_both_files(self):
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(self.claude_dest.exists())
        self.assertTrue(self.codex_dest.exists())
        self.assertEqual(
            self.claude_dest.read_bytes(), CLAUDE_AGENT.read_bytes()
        )
        self.assertEqual(self.codex_dest.read_bytes(), CODEX_AGENT.read_bytes())
        self.assertIn(f"install: {self.claude_dest}", result.stdout)
        self.assertIn(f"install: {self.codex_dest}", result.stdout)

    def test_second_run_is_idempotent(self):
        self.run_installer()
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(f"already installed: {self.claude_dest}", result.stdout)
        self.assertIn(f"already installed: {self.codex_dest}", result.stdout)

    def test_refuses_to_overwrite_a_different_file(self):
        self.claude_dest.parent.mkdir(parents=True)
        self.claude_dest.write_text("hand written local edits\n", encoding="utf-8")
        result = self.run_installer()
        self.assertEqual(result.returncode, 1)
        self.assertIn("refusing to overwrite", result.stderr)
        self.assertEqual(
            self.claude_dest.read_text(encoding="utf-8"), "hand written local edits\n"
        )
        # The other target still installs.
        self.assertTrue(self.codex_dest.exists())

    def test_force_overwrites_a_different_file(self):
        self.claude_dest.parent.mkdir(parents=True)
        self.claude_dest.write_text("stale\n", encoding="utf-8")
        result = self.run_installer("--force")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(f"overwrite: {self.claude_dest}", result.stdout)
        self.assertEqual(self.claude_dest.read_bytes(), CLAUDE_AGENT.read_bytes())

    def test_dry_run_writes_nothing(self):
        result = self.run_installer("--dry-run")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("[dry-run]", result.stdout)
        self.assertIn(str(self.claude_dest), result.stdout)
        self.assertIn(str(self.codex_dest), result.stdout)
        self.assertFalse(self.claude_home.exists())
        self.assertFalse(self.codex_home.exists())

    def test_dry_run_reports_a_refusal_and_still_writes_nothing(self):
        self.claude_dest.parent.mkdir(parents=True)
        self.claude_dest.write_text("stale\n", encoding="utf-8")
        result = self.run_installer("--dry-run")
        # A dry run predicts the same refusal as a real run, and writes nothing.
        self.assertEqual(result.returncode, 1)
        self.assertIn("[dry-run] would refuse", result.stdout)
        self.assertIn("refusing to overwrite", result.stderr)
        self.assertEqual(self.claude_dest.read_text(encoding="utf-8"), "stale\n")

    def test_dry_run_with_force_reports_the_overwrite(self):
        self.claude_dest.parent.mkdir(parents=True)
        self.claude_dest.write_text("stale\n", encoding="utf-8")
        result = self.run_installer("--dry-run", "--force")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("[dry-run] overwrite", result.stdout)
        self.assertEqual(self.claude_dest.read_text(encoding="utf-8"), "stale\n")

    def test_claude_only_leaves_codex_untouched(self):
        result = self.run_installer("--claude-only")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(self.claude_dest.exists())
        self.assertFalse(self.codex_home.exists())

    def test_codex_only_leaves_claude_untouched(self):
        result = self.run_installer("--codex-only")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(self.codex_dest.exists())
        self.assertFalse(self.claude_home.exists())

    def test_unknown_option_is_a_usage_error(self):
        result = self.run_installer("--nope")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown option", result.stderr)

    def test_help_exits_zero(self):
        result = self.run_installer("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stdout)

    def test_installed_codex_file_still_parses(self):
        self.run_installer("--codex-only")
        data = tomllib.loads(self.codex_dest.read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "task-relay-state-writer")
        self.assertEqual(set(data.keys()), ALLOWED_CODEX_KEYS)


if __name__ == "__main__":
    unittest.main()
