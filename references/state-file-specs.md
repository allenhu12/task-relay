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
- **`files`**: agent-maintained list of files inside `working_dir`.

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
