<!-- task-relay-agents: 2 -->
# AI Agent Instructions — {PROJECT_NAME}

This is a task-relay project. These rules apply in every session. The task-relay skill holds the full procedures.

## Folders

| Path | What it holds | Access |
|---|---|---|
| `00-current/` | The truth: `item-list.json` (active items with `tasks[]` + compact `terminal_summary`), `item-list-archive.json` (full terminal records, read on demand), `progress.log` (one global narrative), `memory.md`, `user-decision.md`, generated `dashboard.html` | Update through the state writer; `user-decision.md` is user-only |
| `05-plans/` | Implementation plans, design docs | Read/Write |
| `10-reference/` | References. `MANIFEST.md` (generated index) and `000_YYYY-MM-DD_spec.md` (paths, URLs) are always read | Read-only, except regenerating `MANIFEST.md` |
| `20-working/<ITEM-ID>/` | Per-item workspace with `log.md`. Created lazily when the item first goes `in_progress`. Kept after completion; manual cleanup only | Read/Write |
| `50-drafts/` | Long-form drafts toward a final deliverable | Read/Write |
| `60-handoffs/` | External handoff packages | Read/Write |
| `80-issues/` | Backlog of ideas, bugs, improvements | Only on user request |
| `90-archive/` | Obsolete files; `90-archive/progress-log/` holds rotated logs | Move files here; never auto-read |

## Session start (State Recovery)

Read `AGENTS.md`, `00-current/item-list.json`, `user-decision.md`, `memory.md` (if present), the last 100 lines of `progress.log`, `10-reference/000_YYYY-MM-DD_spec.md`, and `10-reference/MANIFEST.md`.

- **Spec missing** in an existing project: ask the user; do not create it outside initialization.
- **Unresolved placeholders** in the spec (`{PROJECT_ROOT}`, `{TARGET_ROOT}`, `{REPO_PROFILE_ROOT}`): ask the user, or infer only when the value is obvious. Do not run source edits, git commands, or rsync commands with unresolved placeholders.
- **Dashboard language:** read the `Dashboard language:` line in the spec. If it is missing (an older project), ask the user once which language the dashboard should show, propose a default, and add that single line only after they answer. `none` means the dashboard shows the stored text as written. This one line is the only edit an agent may make to the spec outside initialization.
- **MANIFEST:** use it to find references; open only files relevant to the current item (match descriptions/tags to the item). Compare `ls 10-reference/` with its entries and regenerate it if files were added or removed.

## Rules

1. **Never modify `00-current/user-decision.md`.** Only the user writes it.
2. **One item per session**, no exceptions.
3. **Confirm before you execute.** Find the candidate item (an `in_progress` item, else `next_override`, else the lowest-`priority` `pending` item; if every pending item is blocked, report "nothing actionable"). **Stop and wait for confirmation.** On confirm: mark it `in_progress`, create `20-working/<ITEM-ID>/` if missing, clear `next_override`. On reject: change nothing. **A status check is read-only.**
4. **Never auto-advance.** List the remaining `pending` tasks and let the user choose. Mark the task `in_progress` and flush; do the work; validate; mark it `completed` / `blocked` / `cancelled` and flush. Then **stop and ask again**.
5. **Never mark an item completed without validation.** All item-level `validation_steps` pass, every task is `completed` or `cancelled`, and every `cancelled` task has `notes`. Then mark the item terminal and archive it.
6. **Never skip state updates.** Flush `item-list.json` after every task status change, update `item-list-archive.json` when an item becomes terminal, and append to `progress.log` — all through the state writer (below), which also re-renders `00-current/dashboard.html`.
7. **Never hand-edit the state files while the state writer is available.** `item-list.json`, `item-list-archive.json` and `progress.log` belong to it.
8. **Rotate `progress.log`** before the session ends if it exceeds ~1000 lines or ~200 KB: `bash {SKILL_SCRIPTS_PATH}/rotate-progress-log.sh`. Never truncate it by hand.

## Items and tasks

- Project = many items. Item = one session's work. Tasks = checkpoints inside an item; every item has ≥1 task.
- Task IDs: `TASK-<item>-<task>` (e.g. `TASK-001-01`). The number is identity, not run order.
- Status (items and tasks): `pending | in_progress | completed | blocked | cancelled`. `blocked` is not terminal — the user can pick another task. `cancelled` is terminal and needs `notes`.
- **Overflow** (context fills mid-item): leave the item and the current task `in_progress`, write a handoff note in `progress.log` naming the task to resume. The next session resumes it, or the user picks another pending task.

## State writer

Every state write goes to the `task-relay-state-writer` subagent, so the main agent keeps its context.

| CLI | Call |
|---|---|
| Claude Code | Agent/Task tool, subagent `task-relay-state-writer` |
| Codex CLI | `spawn_agent` with `agent_type = "task-relay-state-writer"` — the role pins model and reasoning effort; do not override them |

- Install once per machine: `bash {SKILL_SCRIPTS_PATH}/install-state-writer.sh`. Contract: `{SKILL_REFERENCES_PATH}/state-writer-contract.md`.
- Send **one update request** per flush: `PROJECT_ROOT`, `RENDER_SCRIPT`, the ordered ops (task status/notes/completed_at, set or clear `blocker`, item status, archive a terminal item), and the `progress.log` bullet lines.
- A `blocked` task carries a `blocker` with `type`, `summary`, `since`: `needs_user` (needs `question`, optional `default_action`) or `external` (needs `waiting_on`). For `needs_user`, **stop and ask the user**; `default_action` is a suggestion only. A legacy blocked task with no `blocker` shows as 未分类; add the `blocker` in the next request once the user says which kind it is.
- Who writes what: the subagent writes the three state files and re-renders `dashboard.html`; the main agent writes `20-working/<ITEM-ID>/log.md` and `memory.md`; nobody writes `user-decision.md`.
- **If it fails** (not found, `unknown agent_type`, model unavailable, spawn error, or a `STATE-WRITER ERROR` reply): **stop**, report the failing step, the error and the fix (`{SKILL_SCRIPTS_PATH}/install-state-writer.sh`), and offer exactly three choices — ① retry after the fix; ② the main agent writes the state itself this time and runs the render script; ③ write nothing and end the session. Wait for the user.

## Session end

1. Update `20-working/<ITEM-ID>/log.md`: tasks worked and outcomes, all validation results, blockers, key decisions, files created or modified.
2. Send the `progress.log` summary (with a handoff note on overflow) and any status changes or archive ops in **one** state-writer request.

Non-item sessions (init, batch ingest, status checks) append to `progress.log` only; no item log.

## Documents

- Name generated documents `<num>_<YYYY-MM-DD>_<author>_<description>.md` (3-digit number; author = claude, cursor, gemini, user, …; hyphenated description). State files keep their standard names. Exception: `10-reference/000_YYYY-MM-DD_spec.md` has no author segment.
- Every AI-generated markdown document starts with:

  ```yaml
  ---
  Type: working | spec | decision | note | session-log
  Status: Active | Superseded | Obsolete
  Author: claude | cursor | gemini | user
  Created: YYYY-MM-DD
  Superseded_by: (optional path to replacement document)
  ---
  ```

- Keep `Status` current. `Obsolete` → move to `90-archive/`. `Superseded` → keep in place with `Superseded_by`. `Active` → keep in `20-working/<ITEM-ID>/`, or promote to `00-current/` when final. When a new document replaces an old one: mark the old one `Superseded` with `Superseded_by`, move it to `90-archive/` if obsolete, create the new one as `Active`.
- Link related documents with `[[document-name]]`.

## Memory capture

When the user says "remember this", "remember that", "don't forget", "note for later", "add to memory", "记一下", "记住", or "别忘了":

1. Extract the insight; propose a section (`Gotchas` / `Decisions` / `Preferences` / `Facts`) and a one-line phrasing.
2. Wait for approval or edits.
3. If a similar entry exists, increment its `[N=k]`; else append `- [N=1] [YYYY-MM-DD] <phrasing>`.
4. Echo the entry written. No `progress.log` update.
