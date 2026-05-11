# Deep-Task Adapter (`/task-relay deep ITEM-XXX`)

Full procedure for the file-shaped contract bridge to the `deep-task`
skill. Routed from `SKILL.md` § Deep-Task Adapter. This is the **only**
coupling code between task-relay and deep-task.

## When to use

- The item to execute has `complexity: complex` (per the decomposition
  rules).
- User explicitly requests deeper treatment via `/task-relay deep ITEM-XXX`
  even on a `simple` item.

If `complexity: simple`, do **not** invoke deep-task — execute inline as
usual. Forcing deep-task on every item bloats every session.

## Inputs

- `ITEM-XXX` from `00-current/item-list.json` (must be `status: pending`
  or `in_progress`).
- The `deep-task` skill installed and reachable via `/deep-task`.
- The seven file interfaces from `INTERFACES.md` at `schema_version: 1`.

## Step 1 — Materialize `task-input.yaml` (Interface 4)

Create the workdir and the input file:

```bash
WORKDIR="20-working/${ITEM_ID}/"
mkdir -p "$WORKDIR"
```

Build `${WORKDIR}/task-input.yaml` from the item (template:
`assets/task-input.template.yaml`):

```yaml
schema_version: 1
title: <item.description (truncate to ≤80 chars if needed)>
description: |
  <item.description (full)>
  <if item.notes non-empty, append:>
  Additional notes: <item.notes>
validation_criteria:
  <copy each entry from item.validation_criteria (or .validation_steps) verbatim>
references:
  <add each spec/design path from 10-reference/ matching the item's category>
  <add 10-reference/MANIFEST.md so deep-task can discover more if needed>
context_hints:
  preferences_file: ./00-current/memory.md
  related_items:
    <add ITEM-IDs from item.depends_on>
workdir: ./20-working/<ITEM_ID>/
```

> **Path note.** `workdir` is relative to the task-relay project root.
> Deep-task interprets it as the folder it operates inside.

## Step 2 — Mark item in progress

In `00-current/item-list.json`:
- Set the item's `status: in_progress`.
- Update `metadata.in_progress += 1`, `metadata.pending -= 1`.

Log a session start in `progress.log`:

```markdown
## Session N - YYYY-MM-DD HH:MM
**Phase**: Execution (deep-task)
**Item**: ITEM-XXX - <description>
**Workdir**: 20-working/ITEM-XXX/
**Status**: Started — invoking deep-task...
```

## Step 3 — Invoke deep-task

Hand off pointing at the workdir:

```
/deep-task <WORKDIR>
```

Deep-task will:
1. Read `task-input.yaml`.
2. Run its pipeline: `00_design.md` → `01_plan.md` review gate →
   `02_execution.md` → `03_verify.md`.
3. Halt at `01_plan.md` `Status: review-pending` for human review.
4. On user approval, continue.
5. Write `task-result.yaml` on exit.

**Task-relay stays out of the way during this period.** It does not parse
phase artifacts; it does not write into the workdir. Deep-task owns the
folder until it exits.

## Step 4 — Ingest `task-result.yaml` (Interface 5)

Once deep-task exits, read `${WORKDIR}/task-result.yaml`:

1. **Validate `schema_version: 1`.** Refuse if mismatched.

2. **Branch on `status`:**

   - **`completed`:**
     - Sanity-check all `validation_results[].passed == true`.
     - Set item `status: completed`, `completed_at: <result.completed_at>`.
     - Move full record to `item-list-archive.json`; add compact entry to
       `completed_summary` in `item-list.json`.
     - Update metadata counts.
     - Move `${WORKDIR}` to `90-archive/${ITEM_ID}/` (audit trail).

   - **`blocked`:**
     - Set item `status: blocked`.
     - Copy `result.blockers[]` into `item.notes` with prefix `"BLOCKED:"`.
     - Update metadata.
     - **Do NOT archive the workdir** — it stays in `20-working/` so the
       user can inspect and resume.

   - **`abandoned`:**
     - Confirm with user before applying (abandoning is unusual).
     - On confirmation: set `status: cancelled`, append `result.summary`
       to `item.notes`, move workdir to `90-archive/${ITEM_ID}_abandoned/`.

3. **Ingest `lessons[]`** (if present and `status == completed`):
   - For each lesson, propose to `00-current/memory.md` via the
     confirmed-capture workflow (`[N=k]` counter). User confirms
     per-lesson.

4. **Record `skills_invoked[]`** (if present) in the session log for
   transparency.

## Step 5 — Create the session log

In `30-logs/`, create a session-log file:

```
30-logs/<seq>_<YYYY-MM-DD>_claude_session-log-<item-id>-<short-desc>.md
```

YAML frontmatter:

```yaml
---
Type: session-log
Status: Active
Author: claude
Created: <YYYY-MM-DDTHH:MM:SSZ>
description: "Deep-task execution of <ITEM_ID>: <short outcome>"
related_item: <ITEM_ID>
---
```

Body:
- Wiki-link the four phase artifacts:
  `[[20-working/ITEM-XXX/00_design]]` etc. (or the archive path if archived).
- Copy `result.summary` verbatim.
- List validation results.
- Note any lessons captured (with their `memory.md` targets).
- Note any skills invoked (with phase and reason).

## Step 6 — Suggest retrospective

If `status == completed` and the user has not run `/task-relay learn`
recently, suggest:

> "Item ITEM-XXX completed. Consider running `/task-relay learn` to extract
> lessons from any user hand-edits made during execution."

Advisory only — never auto-run `learn` (which requires user confirmation
per-lesson anyway).

## Failure modes

| Failure | Adapter response |
|---|---|
| Deep-task crashes mid-pipeline (no `task-result.yaml`) | Leave item `in_progress`. Tell user: "Deep-task did not complete; resume by re-invoking `/deep-task ${WORKDIR}`." |
| `task-result.yaml` has unknown `schema_version` | Refuse to ingest; alert user with the offending value. |
| `task-result.yaml.validation_results` shows failure but `status: completed` | Treat as contract violation; alert user; do NOT mark item completed. |
| User cancels mid-flight | Keep workdir intact; item remains `in_progress`. They can resume. |

## Anti-patterns

- ❌ **Reading `02_execution.md` to deduce progress.** Read
  `task-result.yaml` only. Reading phase artifacts re-couples the skills.
- ❌ **Auto-applying lessons.** Always confirm per-lesson via the capture
  workflow.
- ❌ **Archiving on `blocked` status.** The workdir is the user's evidence
  for unblocking.
- ❌ **Forcing deep-task on `complexity: simple` items.** Honor the flag.

## Acceptance criteria

- A `complexity: complex` item runs end-to-end through deep-task and lands
  in `completed` state with all validations green.
- A `complexity: simple` item is NOT routed through deep-task.
- `task-result.yaml` is the only file the adapter parses from the workdir.
- A blocked outcome leaves the workdir in `20-working/` for inspection.
- Lessons are proposed (not silently applied) to `memory.md`.
- The adapter is the only task-relay code aware of deep-task. Removing
  deep-task and patching this section out leaves the rest of task-relay
  functional.
