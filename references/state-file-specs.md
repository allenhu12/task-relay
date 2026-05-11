# State File Specifications

Routed from `SKILL.md` § State File Specifications. Full schemas live in
`assets/*.template.*` and `references/item-list-schema.json`; this file
documents the rules and invariants around each.

## 00-current/item-list.json

Template: `assets/item-list.template.json`. Schema:
`references/item-list-schema.json`.

**Key rules**:
- Contains only **active items** (`pending`, `in_progress`, `blocked`) with full records.
- `completed_summary` holds compact references to completed items (`id`, `description`, `completed_at`).
- When an item completes, its full record moves to `item-list-archive.json` and a compact entry is added to `completed_summary`.
- All items start with `status: "pending"`.
- `validation_criteria` (alias `validation_steps`) must have at least 1 step.
- `priority`: lower number = higher priority (1 is highest).
- `complexity`: `simple` or `complex`. Legacy items without the field default to `simple`.
- `rationale_for_order`: required for v1.1 items; legacy items get `"(legacy item, no rationale recorded)"`.
- `metadata` must match actual item counts (`total_items` = active items + `completed_summary` count).

## 00-current/item-list-archive.json

Template: `assets/item-list-archive.template.json`.

**Key rules**:
- Contains full records of all completed items (append-only).
- Do **NOT** read during State Recovery — only on demand when detailed history of a specific completed item is needed.
- Never delete entries.

## 00-current/progress.log

Template: `assets/progress.template.log`.

**Required per session entry**:
- Session header (number, date, time)
- Phase indicator (initialization or execution)
- Item ID and description (for execution phase)
- Work performed summary
- Validation results
- State updates made
- Wiki link to session log in `30-logs/`
- Next session recommendation

> Use `###` (level 3) for session headings in `progress.log` to keep them
> from polluting any document outline that includes this file.

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

## 30-logs/ Session Logs

Template: `assets/session-log.template.md`.

**Key rules**:
- Naming convention: `XXX_YYYY-MM-DD_<author>_session-log-<description>.md`.
- Include YAML frontmatter (`Type: session-log`, `Status: Active`, `Author`, `Created`).
- One log per session.
- Include full validation results and work performed.
- Use wiki links to reference other documents.

## init.sh / init.md (project root)

Templates: `assets/init.template.sh`, `assets/init.template.md`.

**Must include**:
- Environment setup steps
- Dependency installation
- Service startup (if applicable)
- Health check verification
- Success/failure indicators
