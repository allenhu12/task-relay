# AI Agent Instructions

You are working in a project workspace with a structured folder system. This guide establishes the protocols for how you interact with project files, create documentation artifacts, and maintain project organization.

---

## Project Folder Structure

This project uses a 9-zone folder system:

```
{PROJECT_NAME}/
├── AGENTS.md                  # Instructions for the Agent (Read this first!)
├── 00-current/               # THE TRUTH (State files)
│   ├── progress.log          # Single global narrative — every session appends here
│   ├── item-list.json        # Active items (with tasks[]) + compact terminal summaries
│   ├── item-list-archive.json # Full records of terminal items (read on demand)
│   ├── memory.md             # Curated insights captured via "remember this" / "don't forget"
│   └── user-decision.md      # User comments and decisions (DO NOT modify)
├── 05-plans/                 # THE BLUEPRINT (Implementation plans, design docs, planning artifacts)
├── 10-reference/             # Reference materials (progressive disclosure via MANIFEST.md)
│   ├── MANIFEST.md           # Auto-generated index of all reference files (always read)
│   └── 000_YYYY-MM-DD_spec.md # Project spec with paths and URLs (always read)
├── 20-working/               # PER-ITEM WORKSPACES
│   └── ITEM-001/             # Created lazily when item first goes in_progress
│       ├── log.md            # Detailed log for this item (tasks, decisions, blockers)
│       └── ...               # Other files produced while working this item
├── 50-drafts/                # THE LONG-FORM (Drafts being prepared toward a final deliverable)
├── 60-handoffs/              # THE HANDOFFS (External handoff packages)
├── 80-issues/                # THE BACKLOG (Ideas, bugs, improvements - on user request only)
└── 90-archive/               # Obsolete files; 90-archive/progress-log/ for rotated progress logs
```

### Zone Descriptions

| Zone | Purpose | Access |
|------|---------|--------|
| `00-current/` | The current truth - state, tasks, decisions | Read for context; Update (except `user-decision.md`) |
| `05-plans/` | Implementation plans, design docs, planning artifacts | Read/Write |
| `10-reference/` | Reference documents, specs, external materials. Uses MANIFEST.md for progressive disclosure | Read-only (except MANIFEST.md which agent may regenerate) |
| `20-working/<ITEM-ID>/` | Per-item workspace; durable across completion; manual cleanup only | Read/Write |
| `50-drafts/` | Long-form drafts being prepared toward a final deliverable | Read/Write |
| `60-handoffs/` | External handoff packages | Read/Write |
| `80-issues/` | Backlog of ideas, bugs, improvements | Read/Write (on user request only) |
| `90-archive/` | Obsolete/superseded files | Move files here when obsolete |

### Critical Rules

1. **NEVER modify `00-current/user-decision.md`** - This file contains user comments and decisions and is maintained exclusively by the user.
2. **ALWAYS read `10-reference/000_YYYY-MM-DD_spec.md`** - Use it to find reference paths and URLs.
   - If it is missing in an existing project, ask the user and do not create it outside initialization.
   - If source path placeholders such as `{PROJECT_ROOT}`, `{TARGET_ROOT}`, or `{REPO_PROFILE_ROOT}` are still unresolved, ask the user or infer only when the value is obvious. Do not run source edits, git commands, or rsync commands with unresolved placeholders.
   - Read the `Dashboard language:` line too. If it is missing (an older project), ask the user once which language the dashboard should show, propose a default, and add that single line only after they answer. `none` means the dashboard shows the stored text as written. This one line is the only edit an agent may make to the spec outside initialization.
3. **ALWAYS read `10-reference/MANIFEST.md`** during State Recovery. Use it to discover available reference files. Only open files relevant to the current item. Check staleness by comparing `ls 10-reference/` against entries; update MANIFEST if files were added or removed.
4. **NEVER work on multiple items per session** - ONE item per session, no exceptions.
5. **NEVER mark completed without validation** - ALL item-level `validation_steps` must pass AND every task must be `completed` or `cancelled`.
6. **NEVER skip state updates** - Flush `item-list.json` after every task status change; always update `item-list-archive.json` when an item becomes terminal; always append to `progress.log`. Route every flush through the `task-relay-state-writer` subagent, which also re-renders `00-current/dashboard.html`. See "State Writer" below.
7. **NEVER auto-advance to the next task** - After each task completes (or is cancelled/blocked), STOP and ask the user which task to run next. Task order is user-chosen.
8. **NEVER execute without confirming item selection** - Present the candidate item and wait for user confirmation before marking it `in_progress`. A status check is read-only.
9. **Rotate `progress.log` when it gets large.** Before ending the session, if `wc -l 00-current/progress.log` exceeds ~1000 lines (or ~200 KB), run `bash {SKILL_SCRIPTS_PATH}/rotate-progress-log.sh`. This archives to `90-archive/progress-log/progress-archive-YYYY-MM-DD.log` and regenerates `90-archive/progress-log/PROGRESS-ARCHIVE-MANIFEST.md`. NEVER truncate `progress.log` by hand. NEVER auto-read `90-archive/` during state recovery.
10. **NEVER hand-edit the state files while the state writer is available** - `item-list.json`, `item-list-archive.json`, and `progress.log` belong to the `task-relay-state-writer` subagent. If it fails, stop and offer the three D11 choices instead of writing them yourself.

### State Writer

State writes go through a lightweight subagent so the main agent keeps its context:

| CLI | Call |
|---|---|
| Claude Code | Agent/Task tool, subagent `task-relay-state-writer` |
| Codex CLI | `spawn_agent` with `agent_type = "task-relay-state-writer"` (the role pins model and reasoning effort — do not override them) |

Install once per machine with `bash {SKILL_SCRIPTS_PATH}/install-state-writer.sh`. Full contract: `{SKILL_REFERENCES_PATH}/state-writer-contract.md`.

- Send **one update request** per flush: `PROJECT_ROOT`, `RENDER_SCRIPT`, the ordered ops (task status/notes/completed_at, set or clear `blocker`, item status, archive a terminal item), and the `progress.log` bullet lines.
- A `blocked` task must carry a classified `blocker`: `needs_user` (`question`, optional `default_action`) or `external` (`waiting_on`), plus `type`, `summary`, `since`. For `needs_user`, **stop and ask the user**; `default_action` is a suggestion only.
- Legacy `blocked` tasks without a `blocker` show as 未分类 on the dashboard; add the `blocker` in the next request once the user says which kind it is.
- The subagent owns `00-current/item-list.json`, `00-current/item-list-archive.json`, and `00-current/progress.log`, and re-renders `00-current/dashboard.html`. The main agent still writes `20-working/<ITEM-ID>/log.md` and `memory.md`. Nobody writes `00-current/user-decision.md`.
- If the subagent cannot run (not found, `unknown agent_type`, model unavailable, spawn error, or a `STATE-WRITER ERROR` reply): **stop**, report the failing step + error + fix (`scripts/install-state-writer.sh`), and offer exactly three choices — ① retry after the fix; ② the main agent writes the state itself this time and runs the render script; ③ write nothing and end the session. Wait for the user.

---

## File Naming Convention

All generated documents must follow this format:

```
<num>_<YYYY-MM-DD>_<author>_<description>.md
```

Where:
- `<num>` is a 3-digit sequence number (e.g., 000, 001, 002)
- `<YYYY-MM-DD>` is the creation date
- `<author>` is the creator (claude, cursor, gemini, user, etc.)
- `<description>` is a hyphenated description of the content

**Note**: State files keep their standard names.

**Exception**: `10-reference/000_YYYY-MM-DD_spec.md` is required and does not include an author segment.

---

## YAML Frontmatter

All AI-generated markdown documents must include YAML frontmatter:

```yaml
---
Type: working | spec | decision | note | session-log
Status: Active | Superseded | Obsolete
Author: claude | cursor | gemini | user
Created: YYYY-MM-DD
Superseded_by: (optional path to replacement document)
---
```

---

## Housekeeping Rules

| Status | Action |
|--------|--------|
| `Obsolete` | Move file to `90-archive/` |
| `Superseded` | Keep in place, but ensure `Superseded_by` links to replacement |
| `Active` | Keep in `20-working/<ITEM-ID>/` or promote to `00-current/` if finalized |

When creating new documents that replace existing ones:
1. Update the old document's frontmatter: set `Status: Superseded` and add `Superseded_by` path
2. Move the old document to `90-archive/` if it's now obsolete
3. Create the new document with `Status: Active`

---

## Session-End Protocol

At the end of every execution session, produce two outputs:

### 1. Item Log Update (goes to `20-working/<ITEM-ID>/log.md`)

Update the item's log with:
- Tasks worked this session and their outcomes
- Validation results (ALL steps documented)
- Blockers encountered
- Key decisions made
- Files created or modified

### 2. Update Pack (updates `00-current/`)

Update the following files in `00-current/` to reflect the session outcomes:
- `progress.log` - Append session summary (with handoff note if mid-item overflow)
- `item-list.json` - Flush task/item status changes and metadata; on terminal status, move full record to archive and add compact entry to `terminal_summary`
- `item-list-archive.json` - Append full record of terminal items
- `dashboard.html` - Re-rendered by the state writer after every update request (never hand-edited)

The three JSON/log updates go out as **one update request to the `task-relay-state-writer` subagent**, which also re-renders `dashboard.html`.

**Remember:** Never modify `user-decision.md` - this is user-maintained only.

Non-item sessions (init, batch ingest, status checks) update `progress.log` only — no item log needed.

---

## Item/Task Model

### Model summary

- **Project** = many items. **Item** = one session's work. **Tasks** = checkpoints within an item.
- Every item has `tasks[]` (≥1). A trivial item has a single task.
- Task IDs: `TASK-<item-number>-<task-number>` (e.g. `TASK-001-01`). Numbering is identity, not mandated run order.
- Status enum (items and tasks): `pending | in_progress | completed | blocked | cancelled`.
  - `blocked` — not terminal; user can pick another task.
  - `cancelled` — terminal; `notes` REQUIRED explaining why.

### Selection gate (confirm before execute)

1. Identify the candidate item (resume `in_progress` item, else `next_override`, else lowest-priority pending). If all pending are blocked → "nothing actionable".
2. **STOP. Present candidate to user. Wait for confirmation.**
3. On confirm: mark item `in_progress`; create `20-working/<ITEM-ID>/` lazily; clear `next_override`.
4. On reject: leave state unchanged; `next_override` stays.
5. **Status check is strictly read-only** — report state + suggested next; never mark anything `in_progress`.

### Task loop (user-driven)

After item is confirmed `in_progress`:
1. List remaining `pending` tasks.
2. Ask user which task to work on next. **Wait for selection.**
3. Mark task `in_progress`; flush `item-list.json`.
4. Do the work; validate; mark `completed` / `blocked` / `cancelled`; flush `item-list.json`.
5. **STOP. Go back to step 1.** Never auto-advance.

### Item completion rollup

- Every task must be `completed` or `cancelled`.
- Every `cancelled` task must have non-empty `notes`.
- All item-level `validation_steps` must pass.
- Then mark item terminal and archive.

### Overflow (context fills mid-item)

- Leave item and current task `in_progress`.
- Write handoff note to `progress.log` specifying which task to resume.
- Next session picks up the `in_progress` task or user picks next pending task.

---

## Memory Capture (00-current/memory.md)

When the user says "remember this", "remember that", "don't forget", "note for later", "add to memory", "记一下", "记住", or "别忘了":

1. Extract the candidate insight from surrounding conversation.
2. Propose a section (`Gotchas` / `Decisions` / `Preferences` / `Facts`) and a one-line phrasing.
3. Wait for user approval / edits.
4. On approval, check for similar entries; increment `[N=k]` if found, else append new bullet:
   `- [N=1] [YYYY-MM-DD] <phrasing>`
5. Echo the entry written. No `progress.log` update needed.

`memory.md` is auto-loaded during State Recovery so insights persist across sessions.

---

## Operating Principles

1. **Read First**: Always read `AGENTS.md`, the current state files (`item-list.json`, `user-decision.md`, `memory.md` if present, and only the last 100 lines of `progress.log`), `10-reference/000_YYYY-MM-DD_spec.md`, and `10-reference/MANIFEST.md` before starting work
2. **Maintain Structure**: Follow the folder structure and naming conventions strictly
3. **Track Status**: Keep frontmatter status updated as documents evolve
4. **Link Knowledge**: Create meaningful connections between related documents using `[[document-name]]` syntax
5. **Clean Up**: Actively archive obsolete files and maintain organization
6. **Respect Boundaries**: Never modify user-maintained files (`user-decision.md`)
7. **One Item Per Session**: Focus on a single item to ensure quality
8. **User-Driven Tasks**: Never auto-pick or auto-advance tasks; always ask the user
9. **Progressive Reference Disclosure**: Read MANIFEST.md to discover references. Match file descriptions/tags against the current item's category and description. Only load files that are clearly relevant.

Your goal is not just to complete tasks, but to build an interconnected, well-organized knowledge base that grows more valuable over time.
