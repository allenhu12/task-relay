---
name: task-relay
description: Manage complex, multi-session assignments using persistent state files, like a relay race where each session picks up where the last left off. This skill should be used when users need to work on assignments that span multiple sessions, require tracking progress, or involve many discrete items. Triggers include keywords like "task relay", "multi-session", "track progress", "continue work", "manage items", "incremental progress", "/task-relay deep", "/task-relay learn", "task-relay retrospective", "deep-task adapter", "complex item handoff", "task-input-batch.yaml", "batch ingest items".
license: MIT
version: 1.2
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
│   ├── progress.log          # Progress status and session history
│   ├── item-list.json        # Active items + compact completed summaries
│   ├── item-list-archive.json # Full records of completed items (read on demand)
│   ├── memory.md             # Curated insights captured via "remember this" / "don't forget"
│   └── user-decision.md      # User comments and decisions (READ-ONLY)
├── 05-plans/                 # THE BLUEPRINT (Implementation plans, design docs, planning artifacts)
├── 10-reference/             # Reference materials (progressive disclosure via MANIFEST.md)
│   ├── MANIFEST.md           # Auto-generated index of all reference files (always read)
│   └── 000_YYYY-MM-DD_spec.md # Project spec with paths and URLs (always read)
├── 20-working/               # THE WORKBENCH (Temporary drafts, experiments, work-in-progress)
├── 30-logs/                  # THE HISTORY (Session logs)
├── 50-drafts/                # THE LONG-FORM (Drafts being prepared toward a final deliverable)
├── 60-handoffs/              # THE HANDOFFS (Session-to-session or external handoff packages)
├── 80-issues/                # THE BACKLOG (Ideas, bugs, improvements)
└── 90-archive/               # Obsolete files
```

### Zone Access Rules

| Zone | Purpose | Access |
|------|---------|--------|
| `00-current/` | Current truth - state, tasks, decisions | Read for context; Update (except `user-decision.md`) |
| `05-plans/` | Implementation plans, design docs, planning artifacts | Read/Write |
| `10-reference/` | Reference documents, specs, external materials. Uses MANIFEST.md for progressive disclosure | Read-only (except MANIFEST.md which agent may regenerate) |
| `20-working/` | Temporary drafts, experiments, work-in-progress | Read/Write |
| `30-logs/` | Session logs with YAML frontmatter | Write-only (append) |
| `50-drafts/` | Long-form drafts being prepared toward a final deliverable | Read/Write |
| `60-handoffs/` | Session-to-session or external handoff packages | Read/Write |
| `80-issues/` | Backlog of ideas, bugs, and improvements | Read/Write (on user request only) |
| `90-archive/` | Obsolete/superseded files | Move files here when obsolete |

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
- **Step 0** — Create the 9-zone folder structure (`00-current/`, `05-plans/`, `10-reference/`, `20-working/`, `30-logs/`, `50-drafts/`, `60-handoffs/`, `80-issues/`, `90-archive/`); copy `AGENTS.md`, `user-decision.md`, `memory.md`, spec template; run `scripts/generate-manifest.sh ./10-reference`.
- **Step 1** — Analyze the user's requirements; clarify scope; record reference paths in `10-reference/000_*_spec.md`.
- **Step 1.5** — *Knowledge Front-Loading* (highly recommended): structured Q&A, one question at a time, update reference docs after each answer. Highest-ROI activity at project start.
- **Step 2** — Decompose into items **only if the user explicitly asks** ("generate items", "decompose the project", "fill in the item list"). Otherwise leave `item-list.json` with an empty `items: []` array — the user will populate it later (manually, via `/task-relay` batch ingestion, or by asking to decompose in a later session). When you do decompose, apply the **five decomposition rules** (see `references/decomposition-rules.md`).
- **Step 3** — Create state files from `assets/` templates: `item-list.json` (starts empty unless Step 2 produced items), `item-list-archive.json`, `progress.log`, `init.sh`/`init.md`, initialization session log.
- **Step 4** — Verify baseline (folders, state files, spec, run `init.sh`).
- **Step 5** — Handoff: summarize Session 1; if items exist, recommend the first; otherwise note that the item list is empty pending user direction. Write a session log.

Full procedure with all commands, templates, and acceptance criteria: see `references/initialization-phase.md`.

**Initialization Complete**: ready for execution-phase sessions.

## Ingesting a Batch (`task-input-batch.yaml`)

**When to use.** A decomposer (task-relay Step 2, `/project decompose`, or any external tool) produced a `task-input-batch.yaml` (Interface 3) and you need to load it into `00-current/item-list.json`.

**Procedure (summary).**
1. Validate `schema_version: 1`; assign ITEM-XXX ids; verify required fields per item.
2. Append items, update metadata counts, log to `progress.log`, archive the batch file to `90-archive/`.
3. For delta batches (`delta: true`), apply add/modify/remove ops; never touch completed items.

Full procedure, delta semantics, validation failures, and acceptance criteria: see `references/batch-ingest.md`. Template: `assets/task-input-batch.template.yaml`.

## Execution Phase Workflow

Run this workflow when CONTINUING an existing assignment (state files exist).

**Steps (summary).**
- **Step 1 — State Recovery** (CRITICAL): `tail -100 00-current/progress.log`; read `item-list.json`, `user-decision.md`, `memory.md`, spec file, and `10-reference/MANIFEST.md`. Do **NOT** load `item-list-archive.json` or progress-archive files speculatively. Run `./init.sh`. Full checklist: `references/execution-phase.md` § State Recovery.
- **Step 2 — Item Selection**: pick exactly **one** item. Honor `next_override` if set (then clear); otherwise lowest `priority` pending. Mark `in_progress`; update metadata.
- **Insert mid-execution** (when needed): new item with full v1.1 schema (`complexity`, `rationale_for_order`, etc.); optionally set `next_override`.
- **Step 3 — Execution**: do the work, stay scoped to the one item. For `complexity: complex` items, consider `/task-relay deep` instead of inline execution.
- **Step 4 — Validation** (CRITICAL): run every entry in `validation_criteria`. ONLY mark `completed` if ALL pass; otherwise fix or mark `blocked`.
- **Step 5 — State Update** (MANDATORY): for completed items, move full record to `item-list-archive.json` and append a compact summary to `completed_summary` in `item-list.json`; for blocked, update in place. Append a session entry to `progress.log`. Create the `30-logs/` session log. Commit if using Git.
- **Step 6 — Session Summary**: report progress, files updated, next item.

Full procedure with all commands, examples, algorithms, and acceptance criteria: see `references/execution-phase.md`.


## Deep-Task Adapter (`/task-relay deep ITEM-XXX`)

**When to use.** Item has `complexity: complex`, or the user explicitly requests deeper treatment on a `simple` item. Otherwise execute inline — do not route every item through deep-task. This is the **only** coupling between task-relay and deep-task; all contact is via the file-shaped contract in `INTERFACES.md`.

**Procedure (summary).**
1. Materialize `20-working/<ITEM_ID>/task-input.yaml` (Interface 4) from the item; mark item `in_progress`; log session start.
2. Invoke `/deep-task <WORKDIR>`. Task-relay stays out of the workdir until deep-task exits.
3. Ingest `task-result.yaml` (Interface 5): branch on `status` (completed → archive workdir; blocked → leave in place; abandoned → confirm then archive). Propose `lessons[]` to `memory.md` per-lesson. Write a session log. Optionally suggest `/task-relay learn`.

Full procedure, failure modes, anti-patterns, and acceptance criteria: see `references/deep-adapter.md`. Template: `assets/task-input.template.yaml`.

## Issues Backlog (`80-issues/`)

Lightweight backlog for ideas, bugs, and improvements discovered during work. Issues are separate from items — unstructured markdown, NOT tracked in `item-list.json`, accessed only on explicit user request.

**Do NOT read `80-issues/` during State Recovery.**

**Trigger phrases → workflow**:
- "log this issue" / "record this idea" / "add to backlog" → **Capture**: create `80-issues/<seq>_issue_<name>.md` from `assets/issue.template.md`; fill frontmatter; resume current work.
- "review backlog" / "show issues" → **Review**: list open issues in a table; user decides promote / dismiss / defer per issue.
- "promote issue NNN to an item" → **Promote**: create new item in `item-list.json` (full v1.1 schema); update issue frontmatter `Status: promoted`, `Promoted_to: ITEM-XXX`; log to `progress.log`.
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
1. Diff `02_execution.md` plan vs. current source code; filter out fixing-attempts and documented updates; what remains is user hand-edits.
2. Categorize each hand-edit (Gotcha / Decision / Preference / Fact); build a candidate lessons list with evidence.
3. Per user confirmation, write each lesson to `memory.md` (via capture workflow with `[N=k]` counter) and append `[LEARNED ...]` notes to semantically-relevant pending items.

Full procedure, categorization rules, anti-patterns, and acceptance criteria: see `references/learn-workflow.md`.

## Core Rules (NEVER Violate)

🚫 **NEVER modify item definitions**
- Do NOT change: id, category, description, priority, validation_steps
- ONLY change: status, completed_at, notes, metadata

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

🚫 **NEVER mark completed without validation**
- ALL validation_steps must pass
- Document validation results
- If any fail, fix or mark blocked

🚫 **NEVER skip state updates**
- Always update `00-current/item-list.json`
- Always update `00-current/item-list-archive.json` when completing an item
- Always append to `00-current/progress.log`
- Always create session log in `30-logs/`
- Do this BEFORE session ends

🚫 **NEVER delete items from item-list.json**
- If item is no longer needed, add note explaining why
- Mark as completed or blocked, don't delete
- Maintains audit trail

## State File Specifications

| File | Purpose | Template |
|---|---|---|
| `00-current/item-list.json` | Active items + compact completed summaries | `assets/item-list.template.json` |
| `00-current/item-list-archive.json` | Full records of completed items (read on demand) | `assets/item-list-archive.template.json` |
| `00-current/progress.log` | Session history | `assets/progress.template.log` |
| `00-current/user-decision.md` | User decisions (**read-only** for agents) | `assets/user-decision.template.md` |
| `00-current/memory.md` | Captured insights with `[N=k]` counters | `assets/memory.template.md` |
| `10-reference/MANIFEST.md` | Index of reference files (auto-generated) | `scripts/generate-manifest.sh` |
| `10-reference/000_YYYY-MM-DD_spec.md` | Project spec / reference paths | `assets/spec.template.md` |
| `30-logs/*.md` | Per-session detailed logs | `assets/session-log.template.md` |
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
| `Active` | Keep in `20-working/` or promote to `00-current/` if finalized |

### When Replacing Documents

1. Update old document's frontmatter: set `Status: Superseded` and add `Superseded_by` path
2. Move old document to `90-archive/` if obsolete
3. Create new document with `Status: Active`

### Wiki Linking

Use `[[document-name]]` syntax to link related documents:
- Link session logs from progress.log entries
- Reference related working documents
- Create interconnected knowledge base

## Resources

This skill includes bundled resources to make implementation easier:

### assets/
Template files for creating new task relay assignments:
- `AGENTS.template.md` - Agent instructions copied to project root
- `item-list.template.json` - Template for 00-current/item-list.json (active items + completed summaries)
- `item-list-archive.template.json` - Template for 00-current/item-list-archive.json (completed item full records)
- `progress.template.log` - Template for 00-current/progress.log
- `user-decision.template.md` - Template for 00-current/user-decision.md
- `memory.template.md` - Template for 00-current/memory.md (curated insights captured via "remember this")
- `session-log.template.md` - Template for session logs in 30-logs/
- `spec.template.md` - Template for 10-reference/000_YYYY-MM-DD_spec.md
- `issue.template.md` - Template for backlog issues in 80-issues/
- `init.template.sh` - Template for code projects
- `init.template.md` - Template for non-code assignments
- `task-input.template.yaml` - Interface 4 shape (consumed by `/task-relay deep`)
- `task-input-batch.template.yaml` - Interface 3 shape (consumed by batch ingestion)

### scripts/
Executable utilities:
- `generate-manifest.sh` - Generates / regenerates `10-reference/MANIFEST.md` from file frontmatters
- `rotate-progress-log.sh` - Rotates `00-current/progress.log` to `30-logs/progress-archive-YYYY-MM-DD.log` when it grows past thresholds (default 1000 lines / 200 KB), seeds a fresh log with a continuity header, and regenerates `30-logs/PROGRESS-ARCHIVE-MANIFEST.md`. Run with `--manifest-only` to rebuild the manifest only.

### references/
Additional documentation:
- `item-list-schema.json` - JSON schema for validation
- `workflow-checklists.md` - Detailed checklists for both phases
- `examples.md` - Real-world examples of item decomposition
- `decomposition-rules.md` - The five v1.1 decomposition rules + examples
- `initialization-phase.md` - Full Initialization Phase procedure
- `execution-phase.md` - Full Execution Phase procedure
- `state-file-specs.md` - Full per-file rules and invariants
- `issues-backlog.md` - Full Issues Backlog workflows
- `batch-ingest.md` - Full batch-ingestion procedure (Interface 3)
- `learn-workflow.md` - Full `/task-relay learn` retrospective
- `deep-adapter.md` - Full `/task-relay deep` adapter procedure

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
      (skipped validation steps)

GOOD: "Ran all 3 validation steps, all passed. Marking
       ITEM-003 as completed"
```

❌ **Vague Progress Notes**
```
BAD:  "Worked on some items, made progress"

GOOD: "Completed ITEM-003 (login page). Validation: all
       tests pass, UI renders correctly, auth flow works"
```

❌ **Ignoring Blockers**
```
BAD:  "Can't get API credentials, but I'll mark this done
       and move on"

GOOD: "Marking ITEM-005 as blocked: need production API
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
# Mark as blocked in 00-current/item-list.json
{
  "status": "blocked",
  "notes": "Detailed explanation of blocker and what's needed to unblock"
}

# Document in 00-current/progress.log
# Select next item that isn't blocked
select-next-item --skip-blocked ./00-current/item-list.json
```

### Problem: "State files got corrupted or deleted"

**Solution**:
```bash
# If using Git, restore from last commit
git checkout -- 00-current/item-list.json 00-current/item-list-archive.json 00-current/progress.log

# If no Git, reconstruct manually:
# 1. Review session logs in 30-logs/ for history
# 2. Review recent work (check files modified, git log, etc.)
# 3. Recreate 00-current/item-list.json as best as possible
# 4. Document the incident in 00-current/progress.log
# 5. Mark uncertain items as "pending" to be safe
```

### Problem: "Using legacy flat structure (no 9-zone folders)"

**Solution**: Migrate to the 9-zone structure:
```bash
# 1. Create the folder structure
mkdir -p 00-current 10-reference 20-working 30-logs 80-issues 90-archive

# 2. Move state files to 00-current/
mv item-list.json 00-current/
mv progress.log 00-current/

# 3. Create user-decision.md
cp {SKILL_ASSETS_PATH}/user-decision.template.md ./00-current/user-decision.md

# 4. Copy AGENTS.md to project root
cp {SKILL_ASSETS_PATH}/AGENTS.template.md ./AGENTS.md

# 4b. Do not create a new spec file during migration unless the user requests it

# 5. Document migration in progress.log
```

## References

- [Anthropic Blog: Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Task Relay Framework Document](../task-relay-framework.md) - Comprehensive technical documentation
