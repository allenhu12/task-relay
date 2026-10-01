---
name: task-relay
description: Manage complex, multi-session assignments using persistent state files, like a relay race where each session picks up where the last left off. This skill should be used when users need to work on assignments that span multiple sessions, require tracking progress, or involve many discrete items. Triggers include keywords like "task relay", "multi-session", "track progress", "continue work", "manage items", "incremental progress", "/task-relay learn", "task-relay retrospective", "task-input-batch.yaml", "batch ingest items".
license: MIT
version: 1.3
---

# Task Relay

Manage complex assignments across multiple sessions by maintaining persistent state through structured files, enabling seamless handoffs between sessions like runners in a relay race.

## Purpose

This skill implements Anthropic's "Effective Harnesses for Long-Running Agents" principles to solve the core challenge of long-running work: **each new context window starts with zero memory of previous work**.

Without this skill, agents commonly fail by:
- Attempting to complete everything in one session → context exhaustion
- Declaring completion prematurely → incomplete work
- Skipping validation → broken deliverables
- Leaving unclear state → next session can't continue

This skill prevents these failures through a dual-phase workflow with persistent state files.

## When to Use This Skill

Activate this skill when the user's request involves:

**Size/Complexity Indicators**:
- Assignment will take multiple sessions to complete
- Task involves 5+ discrete items or steps
- Project spans hours, days, or weeks of work
- Complex deliverable with many components

**Continuity Indicators**:
- User says "continue", "resume", "pick up where we left off"
- User mentions "track progress" or "manage items"
- User asks "what's left to do?" or "what's the status?"

**Keywords**:
- "task relay", "multi-session", "complex assignment"
- "track progress", "manage items", "todo list"
- "incremental", "step by step", "phase by phase"
- "continue from last time", "resume work"

**Example Triggers**:
- "Help me build a web app over the next few days"
- "I need to refactor this codebase incrementally"
- "Track my progress on this research project"
- "Continue working on the assignment from yesterday"

## Project Folder Structure

Task Relay uses a 9-zone folder system for organizing project artifacts:

```
{PROJECT_NAME}/
├── AGENTS.md                  # Instructions for the Agent (copied from template)
├── 00-current/               # THE TRUTH (State files)
│   ├── progress.log          # Single global narrative spine — every session appends here
│   ├── item-list.json        # Active items (with tasks[]) + compact terminal summaries
│   ├── item-list-archive.json # Full records of terminal items (read on demand)
│   ├── memory.md             # Curated insights captured via "remember this" / "don't forget"
│   └── user-decision.md      # User comments and decisions (READ-ONLY)
├── 05-plans/                 # THE BLUEPRINT (Implementation plans, design docs, planning artifacts)
├── 10-reference/             # Reference materials (progressive disclosure via MANIFEST.md)
│   ├── MANIFEST.md           # Auto-generated index of all reference files (always read)
│   └── 000_YYYY-MM-DD_spec.md # Project spec with paths and URLs (always read)
├── 20-working/               # PER-ITEM WORKSPACES
│   └── ITEM-001/             # Created lazily when item first goes in_progress
│       ├── log.md            # Detailed log for this item (tasks, decisions, blockers)
│       └── ...               # Any other files produced while working this item
├── 50-drafts/                # THE LONG-FORM (Drafts being prepared toward a final deliverable)
├── 60-handoffs/              # THE HANDOFFS (Session-to-session or external handoff packages)
├── 80-issues/                # THE BACKLOG (Ideas, bugs, improvements)
└── 90-archive/               # Obsolete files; rotated progress.log archives at 90-archive/progress-log/
```

**Note**: `30-logs/` no longer exists as a zone. Detailed logs live in `20-working/<ITEM-ID>/log.md`; non-item session notes (init, batch ingest, status checks) go to `progress.log` only.

### Zone Access Rules

| Zone | Purpose | Access |
|------|---------|--------|
| `00-current/` | Current truth - state, tasks, decisions | Read for context; Update (except `user-decision.md`) |
| `05-plans/` | Implementation plans, design docs, planning artifacts | Read/Write |
| `10-reference/` | Reference documents, specs, external materials. Uses MANIFEST.md for progressive disclosure | Read-only (except MANIFEST.md which agent may regenerate) |
| `20-working/<ITEM-ID>/` | Per-item workspace; durable across completion/cancellation; manual cleanup only | Read/Write |
| `50-drafts/` | Long-form drafts being prepared toward a final deliverable | Read/Write |
| `60-handoffs/` | External handoff packages (different purpose from session handoffs) | Read/Write |
| `80-issues/` | Backlog of ideas, bugs, and improvements | Read/Write (on user request only) |
| `90-archive/` | Obsolete/superseded files; `90-archive/progress-log/` holds rotated progress logs | Move files here when obsolete |

### File Naming Convention

Generated documents must follow this format:
```
<num>_<YYYY-MM-DD>_<author>_<description>.md
```

Examples:
- `000_2025-12-17_claude_session-log-initialization.md`
- `001_2025-12-18_cursor_api-investigation.md`

**Exception**:
- `10-reference/000_YYYY-MM-DD_spec.md` is required for new projects and does not include an author segment.

### YAML Frontmatter

All generated markdown documents must include YAML frontmatter:

```yaml
---
Type: working | spec | decision | note | session-log
Status: Active | Superseded | Obsolete
Author: claude | cursor | gemini | user
Created: YYYY-MM-DD
Superseded_by: (optional path to replacement document)
---
```

### Reference File Frontmatter

Files in `10-reference/` (except the spec file and MANIFEST.md) should include a `description` field in their frontmatter. This is used to auto-generate `MANIFEST.md` for progressive disclosure.

```yaml
---
Type: spec | note | reference
Status: Active
Author: user | claude
Created: YYYY-MM-DD
description: "One-line summary specific enough for the agent to decide relevance without reading the full file"
tags: [keyword1, keyword2, keyword3]
---
```

**Guidelines for `description`**:
- Be specific: "REST API endpoint contracts, auth headers, rate limits, error codes" > "API documentation"
- Include key facts that may eliminate the need to open the file: "3 discount tiers, tax post-discount, $75 free shipping"
- Mention what item categories this file is relevant to

**`tags`** (optional): Keywords matching item categories or domains. Helps the agent match files to the current item.

### Critical Rule

**NEVER modify `00-current/user-decision.md`** - This file is maintained exclusively by the user. Read it for context but never write to it.

## Phase Detection

Determine whether to run Initialization or Execution phase:

### Check for State Files

```bash
# Look for the 9-zone folder structure
ls 00-current/item-list.json 00-current/item-list-archive.json 00-current/progress.log AGENTS.md 2>/dev/null

# Or check for legacy flat structure (for backwards compatibility)
ls item-list.json progress.log 2>/dev/null
```

**Decision Logic**:

```
IF 00-current/item-list.json EXISTS:
    ├─► Run EXECUTION PHASE workflow (9-zone structure)
    └─► Skip to Section 4
ELSE IF item-list.json EXISTS (legacy):
    ├─► Consider migrating to 9-zone structure (see Migration section)
    └─► Run EXECUTION PHASE workflow
ELSE:
    ├─► Run INITIALIZATION PHASE workflow
    └─► Continue to Section 3
```

### Manual Override

User can explicitly specify phase:
- "Initialize a new assignment for..."  → Force initialization
- "Continue working on..." → Force execution (warn if state files missing)

## Initialization Phase Workflow

Run this workflow when starting a NEW assignment (no state files exist).

**Steps (summary).**
- **Step 0** — Create the 9-zone folder structure (`00-current/`, `05-plans/`, `10-reference/`, `20-working/`, `50-drafts/`, `60-handoffs/`, `80-issues/`, `90-archive/`); write `AGENTS.md` with `python3 {SKILL_SCRIPTS_PATH}/agents-md.py write .` (fills real paths); copy `user-decision.md`, `memory.md`, spec template; run `scripts/generate-manifest.sh ./10-reference`. Per-item `20-working/<ITEM-ID>/` folders are created **lazily** at execution, not here. **Ask the user which language the dashboard should show** (propose the language they write in, e.g. `zh-CN`) and write `Dashboard language: <code>` — or `Dashboard language: none` — into `10-reference/000_*_spec.md`. This is required, for custom specs too.
- **Step 1** — Analyze the user's requirements; clarify scope; for code projects resolve `PROJECT_ROOT`/`TARGET_ROOT`/`REPO_PROFILE_ROOT`; record reference paths in `10-reference/000_*_spec.md`.
- **Step 1.5** — *Knowledge Front-Loading* (highly recommended): structured Q&A, one question at a time, update reference docs after each answer. Highest-ROI activity at project start.
- **Step 2** — Decompose into items **only if the user explicitly asks** ("generate items", "decompose the project", "fill in the item list"). When you do decompose, apply the decomposition rules (see `references/decomposition-rules.md`). Each item must have ≥1 task in `tasks[]`; a trivial item gets one task mirroring its description.
- **Step 3** — Create state files from `assets/` templates: `item-list.json` (starts empty unless Step 2 produced items), `item-list-archive.json`, `progress.log`, `init.sh`/`init.md`, initialization entry in `progress.log`. Then install the state writer and render the first (empty) `00-current/dashboard.html` — after the spec carries its `Dashboard language:` line.
- **Step 4** — Verify baseline (folders, state files, spec, run `init.sh`).
- **Step 5** — Handoff: summarize Session 1; if items exist, recommend the first; otherwise note that the item list is empty pending user direction.

Full procedure with all commands, templates, and acceptance criteria: see `references/initialization-phase.md`.

**Initialization Complete**: ready for execution-phase sessions.

## Ingesting a Batch (`task-input-batch.yaml`)

**When to use.** A decomposer (task-relay Step 2, `/project decompose`, or any external tool) produced a `task-input-batch.yaml` (Interface 3) and you need to load it into `00-current/item-list.json`.

**Procedure (summary).**
1. Validate `schema_version: 1`; assign ITEM-XXX ids; verify required fields per item.
2. If a batch item has `tasks[]`, ingest them as-is with TASK-NNN-MM ids. If absent, auto-derive a single `TASK-<NNN>-01` from the item description.
3. Append items, update metadata counts, log to `progress.log`, archive the batch file to `90-archive/`.
4. For delta batches (`delta: true`), apply add/modify/remove ops (see `references/batch-ingest.md` for task-level delta ops); never touch completed items.

Full procedure, delta semantics, validation failures, and acceptance criteria: see `references/batch-ingest.md`. Template: `assets/task-input-batch.template.yaml`.

## Execution Phase Workflow

Run this workflow when CONTINUING an existing assignment (state files exist).

**Steps (summary).**
- **Step 1 — State Recovery** (CRITICAL): `tail -100 00-current/progress.log`; read `item-list.json`, `user-decision.md`, `memory.md`, spec file, and `10-reference/MANIFEST.md`. Do **NOT** load `item-list-archive.json` or progress-archive files speculatively. Run `python3 {SKILL_SCRIPTS_PATH}/agents-md.py check .`; if `AGENTS.md` is not current, show the `write . --dry-run` diff and refresh it only after the user agrees. Run `./init.sh`. **Dashboard language**: if the spec has no `Dashboard language:` line (older projects), ask the user once, propose a default, and add the line only after the answer — the one agent-allowed spec write outside initialization (`none` means omit `DASHBOARD_LANGUAGE`). Full checklist: `references/execution-phase.md` § State Recovery.
- **Step 2 — Selection Gate** (read-only, then confirm before action):
  - If an item is already `in_progress` (overflow from prior session): do NOT run item selection. If a task is `in_progress`, propose resuming that task; else list remaining `pending` tasks for the **user to choose**.
  - Otherwise: identify the candidate item — honor `next_override` if set; else lowest-`priority` `pending` item; if all pending are `blocked` → report "nothing actionable" and stop.
  - **STOP and confirm** before marking any item `in_progress`. Clear `next_override` only after the user confirms.
  - **Status check is read-only** — report state + suggested next, never mark anything `in_progress`.
- **Step 3 — Task Loop** (user-driven, Option B):
  - Create `20-working/<ITEM-ID>/` folder lazily on first transition to `in_progress` (if not yet present).
  - Present remaining `pending` tasks; **user selects** which task to run next. Agent does **not** auto-pick.
  - Mark selected task `in_progress`; do the work; validate; mark `completed` / `blocked` / `cancelled`; **flush `item-list.json` immediately** by sending one update request to the state writer (see § State Writer). The subagent also re-renders `00-current/dashboard.html`.
  - **STOP and ask again** — never auto-advance to the next task.
  - If context fills before the item is done (overflow): record completed tasks in `item-list.json`; leave item `in_progress`; write handoff note to `progress.log`; end session. Next session resumes the `in_progress` task or user picks next.
- **Step 4 — Validation** (CRITICAL): run every entry in `validation_steps`. ONLY mark `completed` if ALL pass; otherwise fix or mark `blocked`.
- **Step 5 — Item Completion / Termination**:
  - An item may be `completed` only when **every task is either `completed` or `cancelled`** AND item-level `validation_steps` all pass. Every `cancelled` task must carry a `notes` explanation.
  - For **cancelled items**: require user confirmation; cascade — set every non-`completed` task to `cancelled` with `notes` referencing the item cancellation.
  - For **terminal items** (completed or cancelled): move full record to `item-list-archive.json`; append compact entry to `terminal_summary` (with `status: completed|cancelled`); remove from `items[]`; update metadata. Append session/handoff note to `progress.log`.
  - Send the archive op and the `progress.log` lines in the **same** update request, so the JSON and the dashboard change together.
- **Step 6 — Session Summary**: report progress, files updated, next item or "nothing actionable".

Full procedure with all commands, examples, algorithms, and acceptance criteria: see `references/execution-phase.md`.

## State Writer (Subagent)

Every task-relay state write goes through the **`task-relay-state-writer`** subagent (D1, D12). It runs on a cheap model on both CLIs, applies one update request, and re-renders the dashboard. It never decides what the work should be.

**Install once per machine** (first use, or when the definition is missing):

```bash
bash {SKILL_SCRIPTS_PATH}/install-state-writer.sh            # install for both CLIs
bash {SKILL_SCRIPTS_PATH}/install-state-writer.sh --dry-run  # preview without writing
```

This installs `~/.claude/agents/task-relay-state-writer.md` (Claude Code, `model: haiku`) and `~/.codex/agents/task-relay-state-writer.toml` (Codex CLI, `model = "gpt-6-luna"`). The exact instruction text, the update-request grammar, and the Codex install evidence live in `references/state-writer-contract.md`.

**How to call it**

| CLI | Call |
|---|---|
| Claude Code | Agent/Task tool with subagent `task-relay-state-writer`, passing the update request as the prompt |
| Codex CLI | `spawn_agent` with `agent_type = "task-relay-state-writer"` and the update request as `message`. Do **not** pass `model` or `reasoning_effort`; the role pins both. |

**The update request** — one plain-text message:

```
PROJECT_ROOT: /abs/path/to/project
RENDER_SCRIPT: /abs/path/to/skill/scripts/render-dashboard.sh
I18N_SCRIPT: /abs/path/to/skill/scripts/dashboard-i18n.py
CHECK_SCRIPT: /abs/path/to/skill/scripts/state-check.py
DASHBOARD_LANGUAGE: zh-CN          # optional; omit to keep the stored text
OPS:
1. task TASK-001-02 status=completed completed_at=2026-09-28T10:00:00Z
2. task TASK-001-03 status=blocked blocker.type=needs_user blocker.summary=... blocker.question=... blocker.since=...
3. task TASK-001-03 status=in_progress blocker=none
4. item ITEM-001 status=completed
5. archive ITEM-001 status=completed completed_at=2026-09-28T11:00:00Z
6. progress.log:
   <one bullet line per entry to append>
NOTE: <optional free text>
```

**Order of work.** Apply the ops → `state-check.py --fix` (repairs metadata counts and the item
rollup) → translation refresh when `DASHBOARD_LANGUAGE` is set → `state-check.py` must exit 0 →
render. The writer answers `STATE-WRITER OK` only when that final check passed; otherwise it
answers `STATE-WRITER ERROR state-check: <first problem line>`.

**Item rollup (enforced).** An item becomes `blocked` when every non-terminal task is blocked,
and returns to `in_progress` once a non-terminal task is no longer blocked. `state-check.py`
computes this, so the writer does not have to remember it. The writer also never invents a
timestamp: it reads `date -u +%Y-%m-%dT%H:%M:%SZ` for anything the request does not supply, and
refreshes `assignment.last_updated` on every write.

**Dashboard language (D16/D17).** Read `Dashboard language:` from the project spec file
(`10-reference/000_YYYY-MM-DD_spec.md`). When it is set, pass that value as `DASHBOARD_LANGUAGE`
in every update request; when it is absent, omit the line and the dashboard keeps showing the
stored text. With the line present the state writer refreshes
`00-current/dashboard-translations.json` (list missing → translate → apply) before rendering, so
the page shows Chinese while `item-list.json` keeps its original text. The renderer itself never
translates — it only reads the cache (ADR 0001).

**Who writes what (D12)**

- The **subagent** writes `00-current/item-list.json`, `00-current/item-list-archive.json`, and appends to `00-current/progress.log`, then runs the render script so `00-current/dashboard.html` is regenerated. Every state write includes the render.
- The **main agent** writes `20-working/<ITEM-ID>/log.md` and `memory.md` itself.
- Nobody writes `00-current/user-decision.md`.

**Blocked tasks must carry a `blocker` (D6, D7)**

- `needs_user` — `question` is required, `default_action` is optional. Use it when only the user can decide.
- `external` — `waiting_on` is required. Use it when an outside system, person, or event must act.
- Every blocker carries `type`, `summary`, and `since`. Clear it with `blocker=none` when the task leaves `blocked`.
- For `needs_user` the agent **stops and asks the user**. `default_action` is a suggestion only; never continue on it by default.
- Legacy (D14): a `blocked` task with no `blocker` shows on the dashboard as 未分类 with its `notes`. Add the `blocker` in the next update request once the user says which kind it is. There is no bulk migration.

**If the state writer fails (D11)**

Detection signals:

- Claude Code: the Agent/Task call reports the subagent is not found, or the spawn fails.
- Codex CLI: `spawn_agent` fails with `unknown agent_type 'task-relay-state-writer'`, the model is not available, or the spawn errors. If `spawn_agent` has **no** `agent_type` parameter at all, no agent definition is installed.
- Either CLI: the subagent returns `STATE-WRITER ERROR <step>: <message>`, or the render script exits non-zero.

Then the main agent:

1. **Stops.** It does not start the next task, and it does not write state itself yet.
2. Reports which step failed, the exact error, and the fix (usually `bash {SKILL_SCRIPTS_PATH}/install-state-writer.sh`, then restart the CLI).
3. Offers exactly three choices and waits for the user: ① retry the subagent after the fix; ② the main agent writes the state itself this time and runs the render script; ③ write nothing and end the session.

## Tasks under Items

**Model summary.**

- Every item has `tasks[]` (≥1). A trivial item has a single task.
- Tasks are the checkpoint/resumability mechanism. Normal case: work through an item's tasks until the item is done. Overflow case: completed tasks stay recorded; next session resumes.
- Task IDs: `TASK-<item-number>-<task-number>` (e.g. `TASK-001-01`, `TASK-001-02`). Numbering is identity, not mandated run order.
- **Status enum** (items and tasks share one set): `pending | in_progress | completed | blocked | cancelled`.
  - `blocked` — not terminal; user can pick another task.
  - `cancelled` — terminal; `notes` is required explaining why.
  - Deep's old `abandoned` outcome maps to `cancelled`. Do **NOT** introduce `abandoned`.
- **At most one** `in_progress` task within the `in_progress` item. Task execution order is user-chosen.
- **Item completion rollup**: every task must be `completed` or `cancelled`; every `cancelled` task must have `notes`; all item-level `validation_steps` must pass.
- **Item `blocked` rule**: an item is `blocked` when every non-terminal task is `blocked` (or the user explicitly blocks it), and it returns to `in_progress` once a non-terminal task is no longer blocked. A single blocked task does not block the item. The state writer applies this rollup, and `scripts/state-check.py` verifies it.
- **Whole-item `cancelled` lifecycle**: user-initiated or agent-proposed → **user-confirmed**; task cascade; archive to `terminal_summary` with `status: cancelled`; update `metadata.cancelled`.
- **`metadata.cancelled`** is required. All status counts must sum to `total_items`.

## Issues Backlog (`80-issues/`)

Lightweight backlog for ideas, bugs, and improvements discovered during work. Issues are separate from items — unstructured markdown, NOT tracked in `item-list.json`, accessed only on explicit user request.

**Do NOT read `80-issues/` during State Recovery.**

**Trigger phrases → workflow**:
- "log this issue" / "record this idea" / "add to backlog" → **Capture**: create `80-issues/<seq>_issue_<name>.md` from `assets/issue.template.md`; fill frontmatter; resume current work.
- "review backlog" / "show issues" → **Review**: list open issues in a table; user decides promote / dismiss / defer per issue.
- "promote issue NNN to an item" → **Promote**: create new item in `item-list.json` (with ≥1 task); update issue frontmatter `Status: promoted`, `Promoted_to: ITEM-XXX`; log to `progress.log`.
- Dismiss / Defer: update issue `Status` only; file stays in `80-issues/`.

Full procedures, templates, and examples: see `references/issues-backlog.md`.


## Memory Capture (00-current/memory.md)

`00-current/memory.md` is a curated, project-scoped store of insights captured during work sessions. It is auto-loaded into context on every session resume so prior insights stay available without the user re-explaining them.

**Do NOT confuse with `user-decision.md`**: that file is user-only-writable. `memory.md` is agent-writable upon user-confirmed capture.

### Trigger Phrases

When the user says any of the following (case-insensitive), enter the capture workflow:

- "remember this", "remember that"
- "don't forget", "note for later"
- "add to memory", "save to memory"
- "记一下", "记住", "别忘了"

### Capture Workflow

1. Extract the candidate insight from surrounding conversation context.
2. Propose to the user:
   - **Section** — one of `Gotchas` / `Decisions` / `Preferences` / `Facts`
   - **Phrasing** — a single concise line
3. Wait for the user to approve, edit, or reject.
4. On approval:
   a. Read the chosen `##` section in `00-current/memory.md`.
   b. **Check for similarity** to existing entries. Two entries are "similar enough" to merge if they describe the same gotcha/decision/preference/fact, even with different wording. Use semantic judgement, not string match.
   c. **If a similar entry exists:** increment its `[N=k]` counter; update its date to today; optionally tighten the phrasing (combine the best parts).
   d. **If no similar entry exists:** append a new bullet:
      ```
      - [N=1] [YYYY-MM-DD] <phrasing>
      ```
   e. **Re-sort the section descending by counter.** Ties broken by most recent date.
   f. **Legacy entries** without `[N=k]` are treated as `[N=1]` on first read; rewrite to the new format opportunistically.
5. Echo back a one-line confirmation indicating incremented vs. created (e.g. "Incremented Gotchas entry to N=3" or "Added new Decisions entry"). Do not log to `progress.log`.

**Section guidance**:
- **Gotchas** — non-obvious bugs, surprising behaviors, things that bit us
- **Decisions** — choices made with rationale ("we picked X over Y because…")
- **Preferences** — user's stylistic / workflow preferences for this project
- **Facts** — stable reference facts: URLs, IDs, paths, conventions

### Rotation

None. Memory is curated, not noise. The user prunes manually when entries become obsolete. Do not auto-archive.

## Learn Workflow (`/task-relay learn`)

**When to use.** User runs `/task-relay learn` (optionally `/task-relay learn ITEM-XXX`) after an item is marked `completed`, to extract lessons from any user hand-edits and propagate them into `memory.md` and not-yet-started items. Skip for `blocked` or `cancelled` items.

**Procedure (summary).**
1. Diff the execution plan in `20-working/<ITEM-ID>/log.md` vs. current source code; filter out fixing-attempts and documented updates; what remains is user hand-edits.
2. Categorize each hand-edit (Gotcha / Decision / Preference / Fact); build a candidate lessons list with evidence.
3. Per user confirmation, write each lesson to `memory.md` (via capture workflow with `[N=k]` counter) and append `[LEARNED ...]` notes to semantically-relevant pending items.

Full procedure, categorization rules, anti-patterns, and acceptance criteria: see `references/learn-workflow.md`.

## Core Rules (NEVER Violate)

🚫 **NEVER modify item definitions**
- Do NOT change: id, category, description, priority, validation_steps, tasks[].id, tasks[].description
- ONLY change: status, completed_at, notes, working_dir, files, metadata, tasks[].status, tasks[].completed_at, tasks[].notes

🚫 **NEVER modify user-decision.md**
- This file is maintained exclusively by the user
- Read it for context, but NEVER write to it
- Located at `00-current/user-decision.md`

✅ **ALWAYS read the reference spec file and MANIFEST**
- Read `10-reference/000_YYYY-MM-DD_spec.md` at the start of every session
- Read `10-reference/MANIFEST.md` at the start of every session
- Use MANIFEST.md to discover reference files; only open files relevant to the current item
- Check MANIFEST staleness: compare `ls 10-reference/` against entries; update if files added/removed

🚫 **NEVER work on multiple items per session**
- ONE item per session, no exceptions
- Prevents context exhaustion
- Ensures quality validation

🚫 **NEVER auto-advance to the next task**
- After each task completes (or is cancelled/blocked), STOP and ask the user which task to run next
- Task execution order is user-chosen; the agent only proposes, never auto-picks
- Exception: if a task is `in_progress` at session start (overflow), propose resuming that specific task

🚫 **NEVER execute without confirming item selection**
- Identify the candidate item and STOP; present it to the user for confirmation
- Mark `in_progress` ONLY after user confirms
- A status check is strictly read-only — never mark anything `in_progress` during a status check

🚫 **NEVER mark completed without validation**
- ALL item-level `validation_steps` must pass
- ALL tasks must be `completed` or `cancelled`; every `cancelled` task must have `notes`
- If any check fails, fix or mark blocked

🚫 **NEVER skip state updates**
- Flush `item-list.json` after every task status change (not just at item completion)
- Always update `00-current/item-list-archive.json` when an item becomes terminal
- Always append to `00-current/progress.log`
- Route every flush through the `task-relay-state-writer` subagent, which also re-renders `00-current/dashboard.html` (see § State Writer). The only exception is fallback ② under D11, after the user chooses it.
- Do this BEFORE session ends

🚫 **NEVER hand-edit the state files while the state writer is available**
- `00-current/item-list.json`, `00-current/item-list-archive.json`, and `00-current/progress.log` belong to the subagent
- If the subagent cannot run, follow the D11 fallback: stop, report, and offer the three choices

🚫 **NEVER delete items from item-list.json**
- Cancelled items are archived to `terminal_summary`, not deleted
- Maintains audit trail

✅ **Create per-item folder lazily**
- `20-working/<ITEM-ID>/` is created when the item first transitions to `in_progress`
- Never create it eagerly at batch ingest or decomposition time
- The folder is **stable** (never auto-moved on completion); `working_dir` in the archive records the stable path

## State File Specifications

| File | Purpose | Template |
|---|---|---|
| `00-current/item-list.json` | Active items (with tasks[]) + compact terminal summaries | `assets/item-list.template.json` |
| `00-current/item-list-archive.json` | Full records of terminal items (read on demand) | `assets/item-list-archive.template.json` |
| `00-current/progress.log` | Single global session narrative | `assets/progress.template.log` |
| `00-current/dashboard.html` | **Derived** static HTML dashboard (generated, never hand-edited) | `assets/dashboard.template.html` |
| `00-current/dashboard-translations.json` | **Derived** translation cache for the dashboard (generated by the state writer, never hand-edited) | `scripts/dashboard-i18n.py` |
| `00-current/user-decision.md` | User decisions (**read-only** for agents) | `assets/user-decision.template.md` |
| `00-current/memory.md` | Captured insights with `[N=k]` counters | `assets/memory.template.md` |
| `10-reference/MANIFEST.md` | Index of reference files (auto-generated) | `scripts/generate-manifest.sh` |
| `10-reference/000_YYYY-MM-DD_spec.md` | Project spec / reference paths | `assets/spec.template.md` |
| `20-working/<ITEM-ID>/log.md` | Per-item detailed log (tasks, decisions, blockers) | `assets/session-log.template.md` (repurposed) |
| `init.sh` / `init.md` | Environment bootstrap | `assets/init.template.{sh,md}` |

JSON schema for `item-list.json`: `references/item-list-schema.json`.
Full per-file invariants, key rules, and access policies: see `references/state-file-specs.md`.


## Housekeeping Rules

Actively maintain project organization:

### Document Lifecycle

| Status | Action |
|--------|--------|
| `Obsolete` | Move file to `90-archive/` |
| `Superseded` | Keep in place, update `Superseded_by` in frontmatter |
| `Active` | Keep in `20-working/<ITEM-ID>/` or promote to `00-current/` if finalized |

### When Replacing Documents

1. Update old document's frontmatter: set `Status: Superseded` and add `Superseded_by` path
2. Move old document to `90-archive/` if obsolete
3. Create new document with `Status: Active`

### Wiki Linking

Use `[[document-name]]` syntax to link related documents:
- Link item logs from progress.log entries
- Reference related working documents
- Create interconnected knowledge base

## Resources

This skill includes bundled resources to make implementation easier:

### assets/
Template files for creating new task relay assignments:
- `AGENTS.template.md` - Agent instructions written to the project root by `scripts/agents-md.py`. Line 1 is the version marker `<!-- task-relay-agents: N -->`; **bump N whenever you change the template** so old project copies show as outdated
- `item-list.template.json` - Template for 00-current/item-list.json (active items with tasks[] + terminal summaries)
- `item-list-archive.template.json` - Template for 00-current/item-list-archive.json (terminal item full records)
- `progress.template.log` - Template for 00-current/progress.log
- `user-decision.template.md` - Template for 00-current/user-decision.md
- `memory.template.md` - Template for 00-current/memory.md (curated insights captured via "remember this")
- `session-log.template.md` - Template for per-item `20-working/<ITEM-ID>/log.md`
- `spec.template.md` - Template for 10-reference/000_YYYY-MM-DD_spec.md
- `issue.template.md` - Template for backlog issues in 80-issues/
- `init.template.sh` - Template for code projects
- `init.template.md` - Template for non-code assignments
- `task-input-batch.template.yaml` - Interface 3 shape (consumed by batch ingestion)
- `dashboard.template.html` - Static skeleton for the generated `00-current/dashboard.html` (inline CSS, no JS)
- `agents/claude/task-relay-state-writer.md` - Claude Code state-writer subagent (installed to `~/.claude/agents/`)
- `agents/codex/task-relay-state-writer.toml` - Codex CLI state-writer agent (installed to `~/.codex/agents/`)

### scripts/
Executable utilities:
- `generate-manifest.sh` - Generates / regenerates `10-reference/MANIFEST.md` from file frontmatters
- `rotate-progress-log.sh` - Rotates `00-current/progress.log` to `90-archive/progress-log/progress-archive-YYYY-MM-DD.log` when it grows past thresholds (default 1000 lines / 200 KB), seeds a fresh log with a continuity header, and regenerates `90-archive/progress-log/PROGRESS-ARCHIVE-MANIFEST.md`. Run with `--manifest-only` to rebuild the manifest only. **State-recovery rule: only ever read `00-current/progress.log`; NEVER auto-read `90-archive/`.**
- `render-dashboard.sh` / `render-dashboard.py` - Render `00-current/dashboard.html` from `item-list.json` + `item-list-archive.json` (Python 3 standard library only; the shell wrapper reports a clear error and exits 127 when `python3` is missing).
- `dashboard-i18n.py` / `dashboard_strings.py` - Maintain the dashboard translation cache (`list-missing`, `apply`, `prune`) and hold the shared list of translatable fields (D16).
- `agents-md.py` - Write (`write <root> [--name] [--dry-run]`) or check (`check <root>`: exit 0 current, 1 outdated, 2 missing) a project's `AGENTS.md`. Fills `{PROJECT_NAME}` and the `{SKILL_*}` paths; backs up a replaced copy to `90-archive/AGENTS.md.bak-<timestamp>`.
- `state-check.py` - Deterministic state checker (`<root> [--fix] [--language]`): metadata counts, blocker placement, item rollup, timestamps, and untranslated strings. Exits 1 on any problem; `--fix` repairs only metadata and the rollup. Run it by hand any time.
- `install-state-writer.sh` - Install the state-writer subagent for Claude Code and Codex CLI (`--dry-run`, `--force`, `--claude-only`, `--codex-only`).

### references/
Additional documentation:
- `item-list-schema.json` - JSON schema for validation
- `workflow-checklists.md` - Detailed checklists for both phases
- `examples.md` - Real-world examples of item+tasks decomposition
- `decomposition-rules.md` - Decomposition rules (item sizing, task sizing) + examples
- `initialization-phase.md` - Full Initialization Phase procedure
- `execution-phase.md` - Full Execution Phase procedure (selection gate, task loop, archival)
- `state-file-specs.md` - Full per-file rules and invariants
- `state-writer-contract.md` - State-writer instruction text (single source), update-request grammar, install notes, and the Codex `agent_type` evidence
- `issues-backlog.md` - Full Issues Backlog workflows
- `batch-ingest.md` - Full batch-ingestion procedure (Interface 3, including tasks[] contract)
- `learn-workflow.md` - Full `/task-relay learn` retrospective

## Common Anti-Patterns

❌ **Scope Creep**
```
BAD:  "While implementing login, I also added logout and
       password reset since I was already in the auth code"

GOOD: "Implemented login only (ITEM-003). Logout (ITEM-007)
       and password reset (ITEM-004) remain pending"
```

❌ **Premature Completion**
```
BAD:  "Login page is done, looks good to me"
      (skipped validation steps, tasks still pending)

GOOD: "All tasks completed, ran all 3 item-level validation steps,
       all passed. Marking ITEM-003 as completed"
```

❌ **Auto-Advancing Tasks**
```
BAD:  Agent completes TASK-001-01 and immediately starts TASK-001-02
      without asking the user

GOOD: Agent marks TASK-001-01 completed, flushes JSON, then asks:
      "Task 1 done. Remaining tasks: TASK-001-02 (implement X),
       TASK-001-03 (write tests). Which task should we do next?"
```

❌ **Vague Progress Notes**
```
BAD:  "Worked on some items, made progress"

GOOD: "Completed TASK-003-02 (add login form validation).
       Item ITEM-003 has 1 task remaining."
```

❌ **Ignoring Blockers**
```
BAD:  "Can't get API credentials, but I'll mark this done
       and move on"

GOOD: "Marking TASK-005-01 as blocked: need production API
       credentials from user to test auth integration"
```

## Troubleshooting

### Problem: "Multiple items are marked in_progress"

**Solution**: This violates the single-item rule.
```bash
# Find all in-progress items
cat 00-current/item-list.json | grep -B 5 '"status": "in_progress"'

# Decide which ONE to continue
# Mark others back to "pending"
# Update metadata counts
```

### Problem: "Validation steps are failing but I think it's done"

**Solution**: Don't mark as completed. Either:
1. Fix the issues until validation passes, OR
2. Mark as blocked and note why validation is failing

**Never** skip validation or mark completed with failing checks.

### Problem: "Item is blocked and I can't proceed"

**Solution**:
```bash
# Mark item as blocked in 00-current/item-list.json
{
  "status": "blocked",
  "notes": "Detailed explanation of blocker and what's needed to unblock"
}

# Document in 00-current/progress.log
# Select next item that isn't blocked
```

### Problem: "State files got corrupted or deleted"

**Solution**:
```bash
# If using Git, restore from last commit
git checkout -- 00-current/item-list.json 00-current/item-list-archive.json 00-current/progress.log

# If no Git, reconstruct manually:
# 1. Check 20-working/<ITEM-ID>/log.md files for item history
# 2. Recreate 00-current/item-list.json as best as possible
# 3. Document the incident in 00-current/progress.log
# 4. Mark uncertain items as "pending" to be safe
```

### Problem: "Using legacy flat structure (no 9-zone folders)"

**Solution**: Migrate to the 9-zone structure:
```bash
# 1. Create the folder structure (no 30-logs/)
mkdir -p 00-current 05-plans 10-reference 20-working 50-drafts 60-handoffs 80-issues 90-archive

# 2. Move state files to 00-current/
mv item-list.json 00-current/
mv progress.log 00-current/

# 3. Create user-decision.md
cp {SKILL_ASSETS_PATH}/user-decision.template.md ./00-current/user-decision.md

# 4. Write AGENTS.md to project root (real paths, version marker)
python3 {SKILL_SCRIPTS_PATH}/agents-md.py write .

# 5. Document migration in progress.log
```

### Problem: "Migrating from v1.2 to v1.3"

**Old-project validation checklist** (run once after upgrade):
1. `items[]` all have `tasks[]` with ≥1 task — if absent, add a single `TASK-<NNN>-01` derived from the item description.
2. No `30-logs/` dependency — move any session logs you want to keep into `20-working/<ITEM-ID>/log.md` or `90-archive/`.
3. Item and task statuses within new enum (`pending | in_progress | completed | blocked | cancelled`). Map old `abandoned` → `cancelled` (add `notes`).
4. Per-item `20-working/<ITEM-ID>/` folders exist for any currently `in_progress` items.
5. `item-list.json` uses `terminal_summary` (renamed from `completed_summary`); each entry has `status: completed | cancelled`.
6. `metadata` has `cancelled` field.
7. Residual `progress-archive-*.log` files in `30-logs/` may be moved to `90-archive/progress-log/` manually.

## References

- [Anthropic Blog: Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Task Relay Framework Document](../task-relay-framework.md) - Comprehensive technical documentation
