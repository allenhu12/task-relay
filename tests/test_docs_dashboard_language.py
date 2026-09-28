"""Doc tests for the dashboard-language field (TASK-001-06, gap from the user trial).

The trial failed because nothing in the initialization flow asked for or recorded
the dashboard language. These tests pin the documentation that closes the gap.

Run from the repository root:
    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SKILL = REPO_ROOT / "SKILL.md"
INITIALIZATION = REPO_ROOT / "references" / "initialization-phase.md"
EXECUTION = REPO_ROOT / "references" / "execution-phase.md"
SPEC_TEMPLATE = REPO_ROOT / "assets" / "spec.template.md"
AGENTS_TEMPLATE = REPO_ROOT / "assets" / "AGENTS.template.md"
USER_GUIDE = REPO_ROOT / "user-guide.md"


class SpecTemplateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = SPEC_TEMPLATE.read_text(encoding="utf-8")

    def test_dashboard_language_is_a_real_field(self):
        self.assertIn("Dashboard language:", self.text)
        lines = [
            line for line in self.text.splitlines() if "Dashboard language:" in line
        ]
        self.assertTrue(lines, "the spec template must carry the field")
        # Required, not a commented-out option.
        for line in lines:
            self.assertFalse(
                line.lstrip().startswith("#"),
                msg=f"the field must not be commented out: {line!r}",
            )

    def test_none_is_documented_as_the_off_value(self):
        self.assertIn("none", self.text)
        self.assertIn("REQUIRED", self.text)
        joined = " ".join(self.text.split())
        self.assertIn("`none` to show the stored text as written", joined)
        self.assertIn("Ask the user during initialization", joined)

    def test_the_placeholder_is_not_a_language_code(self):
        joined = " ".join(self.text.split())
        self.assertNotIn("Dashboard language: `zh-CN`", joined)


class SkillTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = SKILL.read_text(encoding="utf-8")
        self.joined = " ".join(self.text.split())

    def test_initialization_step0_asks_and_records(self):
        self.assertIn("Dashboard language:", self.text)
        self.assertIn("Ask the user which language the dashboard should show", self.joined)
        self.assertIn("Dashboard language: none", self.joined)
        self.assertIn("This is required, for custom specs too", self.joined)

    def test_first_dashboard_is_rendered_after_the_spec_line(self):
        self.assertIn(
            "render the first (empty) `00-current/dashboard.html`", self.joined
        )
        self.assertIn("after the spec carries its `Dashboard language:` line", self.joined)

    def test_state_recovery_handles_an_older_project(self):
        self.assertIn("if the spec has no `Dashboard language:` line", self.joined)
        self.assertIn("ask the user once", self.joined)
        self.assertIn("the one agent-allowed spec write outside initialization", self.joined)
        self.assertIn("`none` means omit `DASHBOARD_LANGUAGE`", self.joined)


class InitializationPhaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = INITIALIZATION.read_text(encoding="utf-8")
        self.joined = " ".join(self.text.split())

    def test_spec_creation_asks_the_question(self):
        self.assertIn("Dashboard language:", self.text)
        self.assertIn("ask the user which language the", self.joined)
        self.assertIn("Ask which language the dashboard page should show", self.joined)
        self.assertIn("Propose the language the user writes in", self.joined)

    def test_both_values_are_spelled_out(self):
        self.assertIn("Dashboard language: `zh-CN`", self.text)
        self.assertIn("Dashboard language: `none`", self.text)
        self.assertIn("`none` -> dashboard shows the stored text as written", self.joined)

    def test_custom_spec_still_needs_the_line(self):
        self.assertIn("even when you author a custom spec", self.joined)
        self.assertIn("Never omit this line", self.joined)

    def test_first_render_follows_the_spec_line(self):
        self.assertIn(
            "the spec must already carry `Dashboard language:`", self.joined
        )
        self.assertIn("refresh the translation cache first", self.joined)


class ExecutionPhaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = EXECUTION.read_text(encoding="utf-8")
        self.joined = " ".join(self.text.split())

    def test_state_recovery_reads_the_field(self):
        self.assertIn("Dashboard language:", self.text)
        self.assertIn("ask the user once", self.joined)
        self.assertIn("ONLY write an agent may", self.joined)
        self.assertIn(
            "one agent-allowed spec write outside initialization", self.joined
        )

    def test_values_map_to_the_update_request(self):
        self.assertIn("pass DASHBOARD_LANGUAGE: <code> in every update request", self.joined)
        self.assertIn("none -> omit DASHBOARD_LANGUAGE", self.joined)


class TemplateAndGuideTest(unittest.TestCase):
    def test_agents_template_reads_the_field(self):
        joined = " ".join(AGENTS_TEMPLATE.read_text(encoding="utf-8").split())
        self.assertIn("Dashboard language:", joined)
        self.assertIn("ask the user once", joined)
        self.assertIn("`none` means the dashboard shows the stored text as written", joined)

    def test_user_guide_explains_switching_later(self):
        joined = " ".join(USER_GUIDE.read_text(encoding="utf-8").split())
        self.assertIn("Dashboard language: zh-CN", joined)
        self.assertIn("Dashboard language: none", joined)
        self.assertIn("The next state write refreshes the cache", joined)


if __name__ == "__main__":
    unittest.main()
