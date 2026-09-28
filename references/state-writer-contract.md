---
Type: reference
Status: Active
Author: claude
Created: 2026-09-28
---

# State-Writer Contract

Routed from `SKILL.md` § State Writer. This file is the **single source of truth** for the
`task-relay-state-writer` subagent (D2, D10, D11, D12).

The instruction body below is embedded **verbatim** in both shipped agent definitions:

- `assets/agents/claude/task-relay-state-writer.md` (Claude Code, `model: haiku`)
- `assets/agents/codex/task-relay-state-writer.toml` (Codex CLI, `model = "gpt-6-luna"`)

`tests/test_state_writer.py` asserts that the three copies stay identical. Change the text
here, then copy it into both agent files.

## Instruction body

<!-- BEGIN STATE-WRITER INSTRUCTIONS -->
You are the task-relay state writer. You do the mechanical state bookkeeping for one task-relay project. You do not plan work, you do not talk to the user, and you do not touch anything outside the files named in this contract.

## Input: the update request

The main agent sends you exactly one plain-text update request in this shape:

    PROJECT_ROOT: <absolute project root>
    RENDER_SCRIPT: <absolute path to scripts/render-dashboard.sh>
    OPS:
    1. task TASK-001-02 status=completed completed_at=2026-09-28T10:00:00Z
    2. task TASK-001-03 status=blocked blocker.type=needs_user blocker.summary=... blocker.question=... blocker.default_action=... blocker.since=2026-09-28T10:05:00Z
    3. task TASK-001-03 status=in_progress blocker=none
    4. task TASK-001-04 notes=...
    5. item ITEM-001 status=completed
    6. archive ITEM-001 status=completed completed_at=2026-09-28T11:00:00Z
    7. progress.log:
       <bullet line 1>
       <bullet line 2>
    NOTE: <optional free text>

Supported ops: set task status, notes or completed_at; set or clear a task blocker; set item status; archive a terminal item (move its full record out of items[] into item-list-archive.json and add the compact terminal_summary entry); append progress.log bullet lines.

If an op is unclear, or names an unknown item or task id, stop and reply with the error line. Never guess.

## What you may write

Inside PROJECT_ROOT you may write only:

- 00-current/item-list.json
- 00-current/item-list-archive.json
- 00-current/progress.log (append only, never rewrite or reorder existing lines)

You must never write:

- item or task definition fields: id, category, description, priority, validation_steps, tasks[].id, tasks[].description
- 00-current/user-decision.md (user-maintained, read-only for every agent)
- 00-current/memory.md (the main agent owns memory capture)
- anything under 20-working/ (the main agent owns 20-working/ITEM-ID/log.md)
- any file outside PROJECT_ROOT

## Rules

- Apply exactly the ops in the request, in order. Never invent items, tasks, ops or ids.
- A blocker object is allowed only while the task status is blocked, and must be removed as soon as the task leaves blocked.
- A needs_user blocker carries question (required) and may carry default_action. An external blocker requires waiting_on. Every blocker carries type, summary and since.
- Never change a definition field, never renumber anything, never delete an archive entry.
- Keep the JSON files valid and human-readable: two-space indent, trailing newline, UTF-8.

## Checks after writing (run all of them)

1. Both JSON files parse.
2. metadata.total_items equals completed + in_progress + blocked + pending + cancelled, and equals the number of active items plus terminal_summary entries in item-list.json.
3. A blocker exists only on tasks whose status is blocked.
4. assignment.last_updated is set to the newest timestamp in the request.
5. Run RENDER_SCRIPT with PROJECT_ROOT as the only argument. It must exit 0.

## Reply

Reply with exactly one line and nothing else:

    STATE-WRITER OK <n> ops; dashboard rendered
    STATE-WRITER ERROR <step>: <message>

Use one of these step names: request, ops, item-list, archive, progress, checks, render. Never print file contents, diffs, or extra commentary.
<!-- END STATE-WRITER INSTRUCTIONS -->

## Install notes

Install both definitions once per machine with `scripts/install-state-writer.sh`
(`--dry-run`, `--force`, `--claude-only`, `--codex-only`).

| CLI | Installed path | Model |
|---|---|---|
| Claude Code | `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/agents/task-relay-state-writer.md` | `haiku` |
| Codex CLI | `${CODEX_HOME:-$HOME/.codex}/agents/task-relay-state-writer.toml` | `gpt-6-luna` (`model_reasoning_effort = "medium"`) |

### Codex: the `agent_type` question (TASK-001-04 open point)

**Does `spawn_agent` need `features.multi_agent_v2 = true` for `agent_type`? No.**
`agent_type` is not gated by that feature flag.

Evidence, all **[verified locally]** by capturing the actual `/v1/responses` request body
that codex-cli sends, with a throwaway `CODEX_HOME`, a stub local model provider and no
credentials (`artifacts/attempt-1/smoke/capture-*.json` in the a003 assignment):

| Run | Agent file installed | `multi_agent_v2` | `spawn_agent` parameters |
|---|---|---|---|
| `capture-default.json` | no | default (off) | `fork_turns`, `message`, `model`, `reasoning_effort`, `task_name` |
| `capture-v2.json` | no | `true` | identical to default |
| `capture-role.json` | yes | default (off) | **`agent_type`**, `fork_turns`, `message`, `model`, `reasoning_effort`, `task_name` |
| `capture-role-v2.json` | yes | `true` | identical to `capture-role.json` |
| `capture-0155.json` (app-bundled CLI 0.155.0-alpha.9) | yes | default (off) | `agent_type` present |

Three consequences for the skill:

1. **`agent_type` only exists when at least one agent file is installed** under
   `$CODEX_HOME/agents/`. With no agent files, `spawn_agent` has no `agent_type` parameter at
   all, so the role cannot be selected. If a Codex session cannot see `agent_type`, the fix is
   to run `scripts/install-state-writer.sh` and restart Codex. **[verified locally]**
2. The tool description then lists the available roles, including the pinned settings:
   `This role's model is set to \`gpt-6-luna\` and its reasoning effort is set to \`medium\`.
   These settings cannot be changed.` **[verified locally]** So the main agent must **not**
   pass `model` or `reasoning_effort` together with `agent_type` for this role.
3. `codex features list` reports `multi_agent stable true` and `multi_agent_v2 stable false`;
   the multi-agent tools, including `spawn_agent`, are on by default. **[verified locally]**

Minimum version: **verified on codex-cli 0.157.1 and on 0.155.0-alpha.9** (the CLI bundled in
the ChatGPT desktop app). Treat **0.157.1 or newer** as the supported version, and treat an
absent `agent_type` parameter as "definitions not installed" rather than a version problem.
Older builds were not tested. **[verified locally]**

### Claude Code

Claude Code subagents are Markdown files with YAML frontmatter; the body is the system prompt.
`~/.claude/agents/` is user-level and applies to every project. `model: haiku` is a supported
alias. **[documented]** Claude delegates through the Agent/Task tool, which reports a spawn
error when the named subagent is missing. **[documented]**
