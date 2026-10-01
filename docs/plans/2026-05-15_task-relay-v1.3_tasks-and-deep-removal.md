# Plan: Task Relay v1.3 — Tasks-under-Items, Per-Item Folders, Remove `deep`

Status: Draft for review
Author: claude
Created: 2026-05-15
Scope: `task-relay` skill (this repo). The separate external `deep-task` skill is OUT OF SCOPE.

---

## 1. Goal

Collapse the "simple item" vs. "complex/deep item" distinction into **one uniform model**:

- A project decomposes into **items** (sized to fit roughly one session).
- Each item contains **one or more tasks** (`TASK-NN-MM`), tracked with per-task status in `item-list.json`.
- Each item gets a **dedicated working subfolder** under `20-working/`, holding all of that item's files (including its detailed log).
- The `/task-relay deep` adapter is **removed entirely**.
- `30-logs/` as a project-wide session-log zone is **removed**; `00-current/progress.log` remains the single global narrative spine; detailed per-item logs live in the item folder.

Everything else (initialization phase, batch ingest, memory capture, `/task-relay learn`, issues backlog, decomposition into items, core state files) stays.

This is a **schema version bump**: skill `version: 1.2 → 1.3`, item-list schema gains a `tasks[]` array and an item `working_dir`.

---

## 2. Agreed design decisions (from discussion)

1. **Session unit = one item.** Project = many sessions = many items. This is unchanged from today's model and is correct *provided items are decomposed to be session-sized*.
2. **Tasks are the checkpoint/resumability mechanism**, not an alternative session unit. Normal case: a session works the item's tasks (one at a time, user-selected — see §3 Selection gate) until the item is done. Overflow case (context fills before the item is done): completed tasks are recorded in `item-list.json`, the item stays `in_progress`, and the next session resumes the `in_progress` task (or the user picks the next `pending` task).
   - "Overflow" = the context window fills up before the item's work is finished. The task list makes this degrade gracefully instead of failing — this is what replaces `deep`.
3. **No `current_task` field.** Task execution order is **user-driven (Option B)**; the resume pointer is the single `in_progress` task (if any), otherwise the user explicitly chooses the next `pending` task. `item-list.json` = structured truth (per-task status); `progress.log` = ordered narrative + handoff note. The two files together are sufficient for handoff.
4. **No escape hatch for under-decomposition.** With `deep` gone, decomposition quality is the only defense against oversized items. `decomposition-rules.md` must gain explicit item-sizing + task-sizing guidance, and "is this item session-sized?" becomes a check at item creation / batch ingest.
5. **Per-item folder = stable ID, created lazily.** Folder name is the item ID (`20-working/ITEM-001/`), NOT the description. Created when the item first transitions to `in_progress` (not at creation time — batch ingest can create many items at once; eager creation would mint dozens of empty folders and churn git).

---

## 3. New `item-list.json` item shape

Each item gains `working_dir`, `files[]`, and a `tasks[]` array. Existing item fields are unchanged.

```jsonc
{
  "id": "ITEM-001",
  "category": "implementation",
  "description": "Clear, actionable description of the item",
  "priority": 1,
  "status": "in_progress",                 // pending | in_progress | completed | blocked | cancelled
  "completed_at": null,
  "notes": "",
  "working_dir": "20-working/ITEM-001",     // present once the folder exists; null/absent before
  "files": [                                 // files inside working_dir, agent-maintained
    "20-working/ITEM-001/log.md",
    "20-working/ITEM-001/notes.md"
  ],
  "validation_steps": [                       // ITEM-level rollup validation (kept)
    "All tasks completed",
    "End-to-end check X passes"
  ],
  "tasks": [
    {
      "id": "TASK-001-01",
      "description": "First concrete sub-step",
      "status": "completed",                 // pending | in_progress | completed | blocked | cancelled
      "validation_steps": ["Task-level check passes"],
      "completed_at": "2026-05-15T10:00:00Z",
      "notes": ""                            // REQUIRED to explain why, when status == cancelled
    },
    {
      "id": "TASK-001-02",
      "description": "Second concrete sub-step",
      "status": "pending",
      "validation_steps": ["..."],
      "completed_at": null,
      "notes": ""
    }
  ]
}
```

### ID conventions
- Items: `ITEM-NNN` (zero-padded, min 3 digits) — unchanged.
- Tasks: `TASK-<item-number>-<task-number>`, e.g. `TASK-001-01`, `TASK-001-02`. Task number zero-padded to 2 digits. The embedded item number makes the ITEM↔TASK relationship explicit and machine-obvious.

### Status model (canonical, items AND tasks)

Single enum for both items and tasks: `pending | in_progress | completed | blocked | cancelled`.

- `blocked` — cannot proceed now, potentially resumable. **Not terminal.**
- `cancelled` — intentional won't-do. **Terminal.** `notes` is **required** and must explain why it was intentionally skipped.
- **Deep's old `abandoned` outcome maps to Task Relay `cancelled`. Do NOT introduce `abandoned`.** `cancelled` is already wired into `/task-relay learn` skip rules and delta-removal behavior — zero new wiring.

### Rules
- **Every item has ≥1 task.** A trivial item is just an item with a single task.
- **Item completion rollup:** an item may be set `completed` only when **every task is either `completed` or `cancelled`** AND the item-level `validation_steps` all pass. Every `cancelled` task must carry a `notes` explanation. This prevents "item done with pending/blocked tasks" while allowing intentionally-skipped tasks.
- **Resume / ordering invariants (user-driven task order — Option B):**
  - Exactly **one** `in_progress` item at any time.
  - **At most one** `in_progress` task within that item.
  - **Task execution order is user-chosen, NOT sequential.** `TASK-NNN-MM` numbering is identity only — it encodes the ITEM↔TASK relationship, not a mandated run order.
  - **Resume point:** if a task is `in_progress` (overflow mid-task), the agent proposes resuming *that* task. If no task is `in_progress`, the agent does **NOT** auto-pick — it lists remaining `pending` tasks and the **user chooses** the next one. (No `current_task` field: `in_progress` status is the pointer; user choice covers the rest.)
  - **A `blocked` task does NOT block the item** (user can pick another task). An item is `blocked` only when **every** non-terminal task is `blocked`, or the user explicitly blocks the item.
  - `cancelled` tasks are skipped/ignored in selection.
- **Per-task state must be flushed to `item-list.json` before the session ends** — the existing "NEVER skip state updates" rule, applied one level down.
- `metadata` stays item-level (no task counts). **Decision: do NOT add `total_tasks`/`completed_tasks`** — no automated count validation exists, so they would drift.
- **`metadata.cancelled` added.** Item metadata becomes `total_items, completed, in_progress, blocked, pending, cancelled`. Counts must always sum to `total_items`.

### Whole-item `cancelled` lifecycle

A `cancelled` item is **terminal and archived exactly like a `completed` item** (it must not linger in active `items[]`, or delta-created cancellations will accumulate and drift):

- **Who can cancel:** user-initiated, or agent-proposed → **user-confirmed** (cancelling work is consequential; require confirmation, same discipline as memory capture). Delta batches may also cancel via `remove`-equivalent op (see §6).
- **`notes` required** on the item, explaining why.
- **Task cascade:** when an item is cancelled, every non-`completed` task is auto-set to `cancelled` with `notes` referencing the item cancellation. Already-`completed` tasks stay `completed` (preserve audit trail).
- **Archival:** move the full item record to `item-list-archive.json`; append a compact entry to the terminal-summary list with `status: cancelled`; remove from active `items[]`; decrement `pending`/`blocked`/`in_progress` and increment `metadata.cancelled`.
- **`/task-relay learn` skips `cancelled` items** (existing skip rule covers `blocked`/`cancelled` — no rewiring).

### Terminal summary (schema rename)

`completed_summary[]` → **`terminal_summary[]`**, where each entry carries `status: completed | cancelled` plus `id`, `description`, terminal timestamp. Single list for all terminal items keeps archival uniform and avoids a parallel `cancelled_summary`. Touches schema, `item-list.template.json`, `state-file-specs.md`, `execution-phase.md`, examples (added to §6).

### Selection gate (confirm before execution)

Selection is read-only; execution is the consequential step. Task Relay **identifies the next candidate and stops** — it does **not** auto-execute.

- **Trigger points:** on a status check, and after an item becomes terminal/blocked (`completed` / `cancelled` / `blocked`), and at the start of any execution session.
- **Selection logic when NO item is `in_progress`:** suggest `next_override` if set, else the lowest-`priority` `pending` item. If no in_progress item, no `next_override`, and all pending are `blocked` → report **"nothing actionable"** and stop (never pick a blocked item).
- **Resume case (item already `in_progress` from a prior overflow):** do **NOT** run item selection and do **NOT** pick a different item. If a task is `in_progress`, propose resuming that task; else present remaining `pending` tasks for the user to choose.
- **Per-task confirmation (Option B — chosen).** Confirmation is required at **two** levels: (a) once before marking a new item `in_progress`; then (b) before **each task**, the agent presents the remaining `pending` tasks and the **user selects** which task runs next. The agent never auto-advances to the next task. After a task completes/cancels/blocks (state flushed), the agent stops and asks again. Loop ends when the user stops or all tasks are terminal.
  - *Trade-off recorded:* this trades the zero-overhead implicit-resume property for explicit user control of task ordering. Accepted by user decision.
- **`next_override` clearing:** cleared **only** when the user confirms and the item is marked `in_progress`. If the user rejects the suggestion, `next_override` stays set.
- **Status check is strictly read-only:** report state + suggested next; never mark anything `in_progress`.

Touches `SKILL.md` (Execution Phase + Core Rules), `references/execution-phase.md` (Step 2), `references/workflow-checklists.md`, `assets/AGENTS.template.md` (added to §6).

---

## 4. Zone / folder changes

| Zone | Before | After |
|---|---|---|
| `20-working/` | "temporary drafts, experiments, disposable" | **Per-item workspaces.** `20-working/<ITEM-ID>/` holds all files for that item incl. its detailed log. **Durable across item completion/cancellation; manual cleanup only** (no auto-move on terminal status). Redefine the zone description accordingly. |
| `30-logs/` | Project-wide session logs with frontmatter | **Removed.** Detailed logs move into `20-working/<ITEM-ID>/log.md`. Non-item sessions (init, batch ingest, backlog triage, "status?") log to `progress.log` only. |
| `00-current/progress.log` | Session history spine | **Unchanged role, now the *single* global narrative.** Every session appends here, including a handoff note when ending mid-item. |
| `00-current/progress.log` rotation | `rotate-progress-log.sh` → `30-logs/progress-archive-*.log` | Archive target becomes **`90-archive/progress-log/progress-archive-YYYY-MM-DD.log`** + manifest `90-archive/progress-log/PROGRESS-ARCHIVE-MANIFEST.md`. **State-recovery rule: only ever read `00-current/progress.log`; NEVER auto-read `90-archive/`** (keeps state recovery bounded). |
| `90-archive/` | Obsolete files | Per-item folders do **NOT** auto-move here on completion (see §6 stale-path resolution). Manual cleanup only. |

Zones not mentioned (`05-plans/`, `10-reference/`, `50-drafts/`, `60-handoffs/`, `80-issues/`) are unchanged. **`60-handoffs/` is kept** — it serves external handoff packages, a different purpose from session handoff.

---

## 5. `/task-relay deep` removal

**Delete:**
- `references/deep-adapter.md`
- `assets/task-input.template.yaml` (Interface 4 — deep input)
- The "Deep-Task Adapter" section in `SKILL.md`
- Deep references in `assets/AGENTS.template.md`, `references/learn-workflow.md` (deep-fed lessons path), `references/state-file-specs.md`, `references/workflow-checklists.md`, `references/execution-phase.md`, `references/initialization-phase.md`, `user-guide.md`, `design/structured-doc-generator-design.md`
- Frontmatter `description` triggers: `/task-relay deep`, `deep-task adapter`, `complex item handoff`

**MUST NOT touch (different feature, keep intact):**
- `assets/task-input-batch.template.yaml` (Interface 3 — batch ingest)
- `references/batch-ingest.md`
- The "Ingesting a Batch" SKILL.md section

**Preserve from deep, relocated:**
- **Deep's old `abandoned` outcome maps to Task Relay `cancelled`. Do NOT introduce `abandoned`.** A given-up task is `status: cancelled` with a required `notes` explanation (see §3 Status model).
- `/task-relay learn` stays and stands alone (it diffs plan vs. source, independent of deep). Its existing `blocked`/`cancelled` skip rules already cover the mapped outcome — no rewiring.

---

## 6. File-by-file change list

| File | Change |
|---|---|
| `SKILL.md` | Bump `version: 1.3`; rewrite frontmatter `description` (drop deep triggers); delete Deep-Task Adapter section; rewrite Project Folder Structure (drop `30-logs/`, redefine `20-working/`); add Tasks-under-Items + status-model subsection; update Execution Phase steps for per-task status + resume invariants + lazy item folder creation; update Core Rules (per-task state flush, item completion rollup incl. `cancelled`, lazy folder creation, `validation_steps` canonical, **selection gate / confirm-before-execution**); update Resources/References lists; update State File Specs table (drop `30-logs/*.md`); add a "v1.2 → v1.3" troubleshooting note + old-project validation checklist. |
| `references/item-list-schema.json` | Add `working_dir`, `files[]`, `tasks[]` (task `id` pattern `^TASK-[0-9]{3,}-[0-9]{2,}$`; `status` enum `pending\|in_progress\|completed\|blocked\|cancelled`; `validation_steps`, `completed_at`, `notes`). Add `cancelled` to item `status` enum. Add `tasks` to item required (minItems 1). **Rename `completed_summary` → `terminal_summary`** with required `status: completed\|cancelled`. **Add `metadata.cancelled`** (required); counts sum to `total_items`. **Global: `validation_steps` is canonical** — sweep docs replacing `validation_criteria`. |
| `assets/item-list.template.json` | Rename `completed_summary` → `terminal_summary`; add `cancelled: 0` to `metadata`. Items still `[]`; example item with tasks goes in `references/examples.md`. |
| `references/execution-phase.md` | Rewrite: **Step 2 becomes a selection gate** — identify candidate item (resume in_progress item, else `next_override`, else lowest-priority pending, else "nothing actionable"), stop, confirm before marking item in_progress; `next_override` cleared only on confirm; status check read-only. **Step 3 task loop is user-driven (Option B):** present remaining `pending` tasks → user picks one → mark task `in_progress` → work → validate → mark `completed`/`blocked`/`cancelled` → flush JSON → **stop and ask again** (never auto-advance); resume = `in_progress` task else user picks; add overflow/handoff procedure; replace `30-logs/` session-log creation with `20-working/<ITEM-ID>/log.md`; item-completion rollup; **terminal archival for both `completed` and `cancelled` items** (full → `item-list-archive.json`, compact → `terminal_summary` with `status`, update `metadata`); whole-item cancellation procedure incl. user-confirm + task cascade. |
| `references/initialization-phase.md` | Drop `30-logs/` from folder creation; note items get tasks at decomposition; per-item folder created lazily at execution, not init. |
| `references/decomposition-rules.md` | Add item-sizing rule ("an item must be completable in ~one session; if not, split"); add task-sizing guidance (how to break an item into `TASK-NN-MM`). This is now load-bearing — no deep escape hatch. |
| `references/state-file-specs.md` | Update item-list spec for tasks/working_dir/files; `terminal_summary` + `metadata.cancelled`; whole-item `cancelled` lifecycle (archive like completed, task cascade, user-confirm); remove `30-logs/` spec; per-task flush invariant + completion rollup. |
| `references/workflow-checklists.md` | Update both phase checklists: selection gate (stop + confirm), per-task steps, item-folder creation, drop deep + 30-logs. |
| `references/examples.md` | Replace/extend examples with item+tasks shape; remove deep examples. |
| `references/learn-workflow.md` | Remove deep-fed lessons path; keep plan-vs-source diff (re-point any `30-logs` plan path to `20-working/<ITEM-ID>/`). |
| `references/issues-backlog.md` | Promote-to-item flow: ensure promoted items get ≥1 task. |
| `references/batch-ingest.md` | **Interface 3 tasks contract:** `tasks[]` optional per batch item; if absent, auto-derive single `TASK-<NNN>-01` from item description. Task IDs assigned at ingest from the ITEM number. **Explicit task-level delta ops** (item-level delta ops stay as-is): `op: add_task` (target: ITEM-005 → append next task number), `op: modify_task` (target: ITEM-005, task: TASK-005-02 → description/status), `op: remove_task` (target + task → set task `cancelled` with notes, never hard-delete). **Item-level `op: remove` = whole-item cancellation** (item → `cancelled`, task cascade, archived per §3). Add session-size sanity note. Interface 3 otherwise intact. |
| `assets/AGENTS.template.md` | Remove deep instructions; describe item/task model + per-item folder + progress.log handoff + **selection gate: never auto-execute; confirm before item in_progress; per-task user selection (never auto-advance to next task)**. |
| `assets/progress.template.log` | Remove deep references; add handoff-note example (mid-item end). |
| `assets/session-log.template.md` | **Repurpose** as the per-item `log.md` template (lives in `20-working/<ITEM-ID>/`). |
| `assets/init.template.sh` | Update folder references: drop `30-logs/`; reflect lazy per-item `20-working/<ITEM-ID>/` creation; current 9-zone structure. |
| `assets/init.template.md` | Same as above for non-code assignments. |
| `scripts/rotate-progress-log.sh` | Archive target → `90-archive/progress-log/progress-archive-YYYY-MM-DD.log`; manifest → `90-archive/progress-log/PROGRESS-ARCHIVE-MANIFEST.md`. Remove all `30-logs/` references. `--manifest-only` still supported. |
| `assets/task-input.template.yaml` | Delete. |
| `references/deep-adapter.md` | Delete. |
| `user-guide.md` | Rewrite affected sections (deep removal, tasks, folder model, 30-logs removal). |
| `design/structured-doc-generator-design.md` | Update or mark superseded where it references deep/30-logs. |

---

## 7. Resolved decisions (review closed)

1. **Status set:** `pending | in_progress | completed | blocked | cancelled`. No `abandoned`. Deep's `abandoned` → `cancelled`. `cancelled` requires `notes`. Applies to both items and tasks. Completion rollup: all tasks `completed` or `cancelled` + item-level validation passes.
2. **`session-log.template.md`:** repurpose as `20-working/<ITEM-ID>/log.md` template.
3. **`60-handoffs/`:** kept (external handoff packages — different purpose).
4. **`metadata` task counts:** not added (no automated validation → would drift).
5. **Migration:** clean break. Add a short "v1.2 → v1.3" troubleshooting note **and** an old-project validation checklist (verify: items have `tasks[]`; no `30-logs/` dependency; statuses within new enum; per-item folders exist for in-progress items).
6. **Progress archive:** `90-archive/progress-log/`; never auto-read during state recovery.
7. **Stale archived paths:** per-item folders stay **stable in `20-working/<ITEM-ID>/`** even after completion. `item-list-archive.json` records that stable path. No auto-move to `90-archive/`. Only manual cleanup moves them, and must rewrite the recorded `working_dir`/`files` paths.
8. **`validation_steps`** is the canonical field name (matches schema); global sweep replaces `validation_criteria`.

---

## 8. Out of scope

- The external `deep-task` skill itself (separate repo/skill; we only sever task-relay's side).
- Batch-ingest Interface 3 core semantics (kept intact; only the `tasks[]` contract in §6 is added — optional with single-task auto-derive).
- Memory capture / `/task-relay learn` core logic (only deep-coupling removed).

---

## 9. Suggested execution order

1. Schema + templates (`item-list-schema.json`, examples) — establishes the contract.
2. `SKILL.md` (version, frontmatter, structure, deep removal, tasks section, rules).
3. Core reference rewrites (`execution-phase.md`, `initialization-phase.md`, `decomposition-rules.md`, `state-file-specs.md`, `workflow-checklists.md`).
4. Asset templates (`AGENTS`, `progress`, item `log.md`).
5. Script (`rotate-progress-log.sh`).
6. Deletions (`deep-adapter.md`, `task-input.template.yaml`).
7. Peripheral (`user-guide.md`, `examples.md`, `learn-workflow.md`, `issues-backlog.md`, `batch-ingest.md`, `design/`).
8. Grep sweep for residual `deep` / `30-logs` references; final consistency pass.
