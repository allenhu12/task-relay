# State File Specifications

Routed from `SKILL.md` § State File Specifications. Full schemas live in
`assets/*.template.*` and `references/item-list-schema.json`; this file
documents the rules and invariants around each.

## 00-current/item-list.json

Template: `assets/item-list.template.json`. Schema:
`references/item-list-schema.json`.

**Key rules**:
- Contains only **active items** (`pending`, `in_progress`, `blocked`) with full records including `tasks[]`.
- `terminal_summary` holds compact references to terminal items (`id`, `description`, `status`, `completed_at`). Status is `completed` or `cancelled`.
- When an item becomes terminal, its full record moves to `item-list-archive.json` and a compact entry (with `status`) is added to `terminal_summary`.
- All items start with `status: "pending"`.
- `validation_steps` is the canonical field name at both item and task level.
- `priority`: lower number = higher priority (1 is highest).
- `metadata` must match actual item counts (`total_items` = active items + `terminal_summary` count). **All status counts must sum to `total_items`**: `completed + in_progress + blocked + pending + cancelled = total_items`.
- `metadata.cancelled` is required (added in v1.3).
- **Every item has ≥1 task** in `tasks[]`. A trivial item has one task.
- **Per-task state must be flushed to `item-list.json` immediately after each task status change** — do not wait for item completion.
- **At most one `in_progress` task** within the `in_progress` item at any time.
- **Item completion rollup**: item may be set `completed` only when every task is `completed` or `cancelled` AND every `cancelled` task has a non-empty `notes`, AND all item-level `validation_steps` pass.
- **`working_dir`**: null until the item first transitions to `in_progress`. Set to `20-working/<ITEM-ID>` lazily.
- **`files`**: agent-maintained list of files inside `working_dir`. This is the **output** of the work.
- **`rulebook`** (optional, item and task): one path, relative to the project root, or
  `null`. The rulebook states the objective, deliverables, acceptance, boundaries and
  stop point. The agent reads it before work and checks it before closing. A task also
  uses its item's rulebook. File name: `20-working/<ITEM-ID>/<TASK-ID>-rulebook.md` or
  `20-working/<ITEM-ID>/<ITEM-ID>-rulebook.md`.
- **`context`** (optional, item and task): a list of paths, relative to the project root.
  The agent reads them before work. They are the **input** of the work and are not
  checked at closing. A task also reads its item's context.
- **Path rules** for `rulebook` and `context`: relative to the project root, never
  absolute, never containing `..`. Only the state writer writes these fields.
  `state-check.py` reports a bad path as a problem and a missing file as a warning.
- **Task `blocker`** (optional, v1.3+): a structured record of *why* a task is
  `blocked`. Only set while the task is blocked, and removed as soon as the task
  leaves `blocked`. See "Task `blocker`" below.

### Task `blocker`

`blocker` is an optional object on a **task** (never on an item; an item's blocked
state is the rollup of its tasks). Set it only while that task's `status` is
`blocked`, and delete the whole object when the task leaves `blocked` — for example
when the user answers the question or the external dependency clears.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `type` | `needs_user` \| `external` | yes | Who or what can clear the blocker. |
| `summary` | string | yes | One short line naming what is blocked. |
| `question` | string | when `type == needs_user` | The question the user must answer. |
| `default_action` | string | no | Suggested action if the user does not answer. Advice only — see D7 (the agent still stops and asks). |
| `waiting_on` | string | when `type == external` | What the task waits for. |
| `since` | date-time string | yes | When the task first became blocked by this cause. |

Conditional requirements are machine-checked by `references/item-list-schema.json`
using JSON-Schema `if`/`then`, so the `question` requirement fires only for
`needs_user` and the `waiting_on` requirement only for `external`.

**Legacy data (D14)**: a task with `status: "blocked"` and no `blocker` object is
valid. The dashboard shows it under "需要你处理" as **未分类** and displays its
`notes`, with a hint asking the user to say which kind of blocker it is. There is
no one-time migration: the state writer adds the `blocker` object the next time it
writes state for that task, after the user answers.

**Dashboard view**: `needs_user` blockers (plus legacy unclassified blockers) appear
under "需要你处理"; `external` blockers appear under "等外部".

### Whole-item `cancelled` lifecycle

- **Requires user confirmation** — cancelling work is consequential.
- `notes` required on the item, explaining why.
- **Task cascade**: every non-`completed` task is auto-set to `cancelled` with `notes` referencing the item cancellation. Already-`completed` tasks stay `completed` (preserve audit trail).
- **Archival**: move full item record to `item-list-archive.json`; append compact entry to `terminal_summary` with `status: cancelled`; remove from active `items[]`; update `metadata.cancelled`.

### Status enum (items and tasks)

`pending | in_progress | completed | blocked | cancelled`

- `blocked` — not terminal; can be resumed.
- `cancelled` — terminal; `notes` is REQUIRED explaining why.
- `abandoned` is NOT a valid status. Map old `abandoned` → `cancelled`.

## 00-current/item-list-archive.json

Template: `assets/item-list-archive.template.json`.

**Key rules**:
- Contains full records of all terminal items (`completed` or `cancelled`), append-only.
- Do **NOT** read during State Recovery — only on demand when detailed history of a specific terminal item is needed.
- Never delete entries.
- Archived records include `working_dir` and `files` paths (stable; no auto-move on completion).
- Archived records keep `rulebook` and `context` (item and task) for history. They are not copied into `terminal_summary`.

## 00-current/dashboard.html (derived, generated)

Generator: `scripts/render-dashboard.py` (thin wrapper: `scripts/render-dashboard.sh`).
Skeleton: `assets/dashboard.template.html`.

Usage: `python3 scripts/render-dashboard.py <project_root>` reads
`<project_root>/00-current/item-list.json` and
`<project_root>/00-current/item-list-archive.json` (the archive may be missing or
empty) and writes `<project_root>/00-current/dashboard.html`.

**Key rules**:
- **Derived file — never hand-edited.** Every value on the page comes from the two
  JSON files plus the template. Edit the JSON, then re-render.
- **Rewritten in full on every state write** (D8): after any task status change,
  item archival, or `progress.log` append, the state writer re-runs the renderer.
  The renderer never appends.
- **Atomic write**: the renderer writes a temporary file in the same directory and
  renames it over `dashboard.html`, so a reader never sees a half-written page.
- **Failure is non-destructive**: if `item-list.json` is missing or is not valid
  JSON, the renderer exits non-zero with a clear message on stderr and leaves any
  existing `dashboard.html` untouched.
- **Pure static HTML** (D9): no JavaScript, expand/collapse via `<details>`,
  colours follow the system through `prefers-color-scheme`, CSS is inline, and the
  page loads no external resource (no fonts, CDNs, or images).
- **Deterministic** (D15 A4): the "更新于" line comes from
  `assignment.last_updated` in `item-list.json`, never from the current clock, so
  the same input always produces byte-identical output.
- **Bounded size** (D4): the full page is rewritten each time; recent activity is
  capped at 5 entries and latest deliverables at 5 entries; finished items are
  collapsed; each task shows only id, description, status, and a one-line note.
- **No `python3`** (D13): the wrapper prints `render-dashboard: python3 not found;
  install Python 3 or ask the main agent to stop (D11)` on stderr and exits 127.

Layering note: `dashboard.html` is a derived view, not a source of truth. State
recovery still reads `item-list.json`, `progress.log`, and the other documented
files only.

## 00-current/dashboard-translations.json (derived, generated)

Maintainer: `scripts/dashboard-i18n.py`. Reader: `scripts/render-dashboard.py`.

Optional cache that lets the dashboard show a translated page while the stored
text stays as written (D16). It exists only when the project turns translation on
with `Dashboard language:` in the spec file.

```json
{
  "language": "zh-CN",
  "entries": {
    "0f1e2d3c4b5a6978": "支付网关对接与订单导出重构"
  }
}
```

**Key rules**:
- **Derived file — never hand-edited.** The state-writer subagent fills it with
  `list-missing` → translate → `apply`; `apply` also prunes entries whose original
  text is gone.
- The key is the first 16 hex characters of the SHA-256 of the **exact original
  UTF-8 string**, so identical text shares one entry and changed text gets a new key.
- Keys are sorted when the file is written, and the write is atomic.
- Translatable fields (D16): `assignment.description`; item `description`; task `description`
  and `notes`; blocker `summary`, `question`, `default_action`, `waiting_on` — for
  active and archived items. **Not** translated: ids, `assignment.name`,
  timestamps, statuses, `validation_steps`, `files`, paths, commit SHAs, code,
  command names, model names.
- `apply` rejects keys that are not in the current data (exit non-zero, cache
  untouched). `prune` drops stale entries only.
- The renderer reads the cache if it exists: a translation wins, otherwise the
  original is shown. Truncation applies to the shown text, and the hover `title`
  always holds the **original** full text.
- A missing cache means "no translations" and is not an error. A malformed cache
  prints one warning on stderr and the page renders with the original text, exit 0.

## 00-current/progress.log

Template: `assets/progress.template.log`.

**Required per session entry**:
- Session header (number, date, time)
- Phase indicator (initialization / execution / batch-ingest / status-check / etc.)
- Item ID and description (for execution phase)
- Tasks completed this session
- Work performed summary
- Validation results
- State updates made
- Wiki link to item log in `20-working/<ITEM-ID>/log.md` (for execution sessions)
- Next session recommendation or handoff note (if mid-item overflow)

> Use `###` (level 3) for session headings in `progress.log` to keep them
> from polluting any document outline that includes this file.

**Non-item sessions** (init, batch ingest, backlog triage, status checks):
log to `progress.log` only — no separate item log needed.

**Rotation target**: `90-archive/progress-log/progress-archive-YYYY-MM-DD.log`.
Manifest: `90-archive/progress-log/PROGRESS-ARCHIVE-MANIFEST.md`.
**State-recovery rule: only ever read `00-current/progress.log`; NEVER auto-read `90-archive/`.**

## 00-current/user-decision.md

Template: `assets/user-decision.template.md`.

**Key rules**:
- **READ-ONLY for agents** — never modify this file.
- Contains user decisions, preferences, and context.
- Maintained exclusively by the user.
- Check during State Recovery for important context.

## 00-current/memory.md

Template: `assets/memory.template.md`.

**Key rules**:
- Auto-loaded during State Recovery on every session start.
- Agent-writable, but ONLY via the confirmed capture workflow (see `SKILL.md` § Memory Capture).
- Categorized into `## Gotchas`, `## Decisions`, `## Preferences`, `## Facts`.
- Entries are `- [N=k] [YYYY-MM-DD] <text>`; sections sorted descending by `k`, ties by date. Legacy uncounted entries are treated as `[N=1]`.
- No rotation — user prunes manually.

## 10-reference/MANIFEST.md

Auto-generated index of all reference files. Generator: `scripts/generate-manifest.sh`.

**Key rules**:
- Read at the start of every session (after the spec file).
- Use for discovery without loading all reference files.
- Agent maintains staleness: compare `ls 10-reference/` against entries each session.
- New file found → read frontmatter, append entry.
- Listed file no longer exists → remove entry.
- New non-markdown file → ask user for a description.
- The spec file (`000_YYYY-MM-DD_spec.md`) is NOT listed in MANIFEST — it's always loaded separately.
- Run `generate-manifest.sh` for bulk regeneration during initialization or manual resync.

## 10-reference/000_YYYY-MM-DD_spec.md

Template: `assets/spec.template.md`.

**Key rules**:
- Read at the start of every session.
- Treat all paths as project-specific placeholders to update during initialization.
- For code projects, initialization must resolve `PROJECT_ROOT`; source edits, git commands, and rsync commands must not use unresolved placeholders.
- For remote compile/sync workflows, resolve `TARGET_ROOT` before generating rsync commands.
- For multi-repo checkouts, record `REPO_PROFILE_ROOT` only after explicit user confirmation during first initialization. Keep repo local paths portable as `{PROJECT_ROOT}/<checkout_path>`.
- Use for progressive disclosure — only open related documents when needed.

## 20-working/<ITEM-ID>/ — Per-item workspace

**Key rules**:
- Created **lazily** when the item first transitions to `in_progress`. Never created at batch ingest or decomposition time.
- Folder name is the item ID (e.g. `20-working/ITEM-001/`). Stable — never auto-moved on completion or cancellation. Manual cleanup only.
- Contains `log.md` (the per-item detailed log) and any other files produced while working the item.
- `log.md` is initialized from `assets/session-log.template.md` when the folder is created.
- `working_dir` in `item-list.json` is set to `"20-working/ITEM-XXX"` when the folder is created.
- `files[]` in `item-list.json` is updated as files are added to the folder.
- The archived item record in `item-list-archive.json` preserves the stable `working_dir` and `files` paths.

## init.sh / init.md (project root)

Templates: `assets/init.template.sh`, `assets/init.template.md`.

**Must include**:
- Environment setup steps
- Dependency installation
- Service startup (if applicable)
- Health check verification
- Success/failure indicators
