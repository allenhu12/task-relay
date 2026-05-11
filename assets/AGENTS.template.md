# AI Agent Instructions

You are working in a project workspace with a structured folder system. This guide establishes the protocols for how you interact with project files, create documentation artifacts, and maintain project organization.

---

## Project Folder Structure

This project uses a 9-zone folder system:

```
{PROJECT_NAME}/
├── AGENTS.md                  # Instructions for the Agent (Read this first!)
├── 00-current/               # THE TRUTH (State files)
│   ├── progress.log          # Progress status
│   ├── item-list.json        # Active items + compact completed summaries
│   ├── item-list-archive.json # Full records of completed items (read on demand)
│   ├── memory.md             # Curated insights captured via "remember this" / "don't forget"
│   └── user-decision.md      # User comments and decisions (DO NOT modify)
├── 05-plans/                 # THE BLUEPRINT (Implementation plans, design docs, planning artifacts)
├── 10-reference/             # Reference materials (progressive disclosure via MANIFEST.md)
│   ├── MANIFEST.md           # Auto-generated index of all reference files (always read)
│   └── 000_YYYY-MM-DD_spec.md # Project spec with paths and URLs (always read)
├── 20-working/               # THE WORKBENCH (Temporary drafts, experiments, work-in-progress)
├── 30-logs/                  # THE HISTORY (Session logs + rotated progress.log archives)
│   ├── PROGRESS-ARCHIVE-MANIFEST.md     # Index of rotated progress.log archives (on-demand)
│   └── progress-archive-YYYY-MM-DD.log  # Rotated snapshots of progress.log
├── 50-drafts/                # THE LONG-FORM (Drafts being prepared toward a final deliverable)
├── 60-handoffs/              # THE HANDOFFS (Session-to-session or external handoff packages)
├── 80-issues/                # THE BACKLOG (Ideas, bugs, improvements - on user request only)
└── 90-archive/               # Obsolete files
```

### Zone Descriptions

| Zone | Purpose | Access |
|------|---------|--------|
| `00-current/` | The current truth - state, tasks, decisions | Read for context; Update (except `user-decision.md`) |
| `05-plans/` | Implementation plans, design docs, planning artifacts | Read/Write |
| `10-reference/` | Reference documents, specs, external materials. Uses MANIFEST.md for progressive disclosure | Read-only (except MANIFEST.md which agent may regenerate) |
| `20-working/` | Temporary drafts, experiments, work-in-progress | Read/Write |
| `30-logs/` | Session logs, conversation history | Write-only (append) |
| `50-drafts/` | Long-form drafts being prepared toward a final deliverable | Read/Write |
| `60-handoffs/` | Session-to-session or external handoff packages | Read/Write |
| `80-issues/` | Backlog of ideas, bugs, improvements | Read/Write (on user request only) |
| `90-archive/` | Obsolete/superseded files | Move files here when obsolete |

### Critical Rules

1. **NEVER modify `00-current/user-decision.md`** - This file contains user comments and decisions and is maintained exclusively by the user.
2. **ALWAYS read `10-reference/000_YYYY-MM-DD_spec.md`** - Use it to find reference paths and URLs.
   - If it is missing in an existing project, ask the user and do not create it outside initialization.
3. **ALWAYS read `10-reference/MANIFEST.md`** during State Recovery. Use it to discover available reference files. Only open files relevant to the current item. Check staleness by comparing `ls 10-reference/` against entries; update MANIFEST if files were added or removed.
4. **NEVER work on multiple items per session** - ONE item per session, no exceptions.
5. **NEVER mark completed without validation** - ALL validation_steps must pass.
6. **NEVER skip state updates** - Update `item-list.json`, `item-list-archive.json` (when completing items), and `progress.log` before ending session.
7. **Rotate `progress.log` when it gets large.** Before ending the session, if `wc -l 00-current/progress.log` exceeds ~1000 lines (or the file exceeds ~200 KB), run `bash {SKILL_SCRIPTS_PATH}/rotate-progress-log.sh`. This archives the current log to `30-logs/progress-archive-YYYY-MM-DD.log`, starts a fresh `progress.log` with a continuity header, and regenerates `30-logs/PROGRESS-ARCHIVE-MANIFEST.md`. Never truncate `progress.log` by hand — always rotate.

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

**Examples:**
- `000_2025-12-17_claude_session-log-initialization.md`
- `001_2025-12-18_cursor_api-authentication-notes.md`
- `002_2025-12-18_claude_session-log-item-003.md`

**Note**: State files (`item-list.json`, `item-list-archive.json`, `progress.log`, `user-decision.md`) keep their standard names.

**Exception**: `10-reference/000_YYYY-MM-DD_spec.md` is required and does not include an author segment.

---

## YAML Frontmatter

All AI-generated markdown documents must include YAML frontmatter at the beginning:

```yaml
---
Type: working | spec | decision | note | session-log
Status: Active | Superseded | Obsolete
Author: claude | cursor | gemini | user
Created: YYYY-MM-DD
Superseded_by: (optional path to replacement document)
---
```

**Field Descriptions:**
- **Type**: Document category
  - `working` - Work in progress, drafts
  - `spec` - Specifications, requirements
  - `decision` - Decision records
  - `note` - General notes, observations
  - `session-log` - Session transcript or summary
- **Status**: Current state of the document
  - `Active` - Currently valid and in use
  - `Superseded` - Replaced by a newer version (link in `Superseded_by`)
  - `Obsolete` - No longer relevant
- **Author**: Who created the document
- **Created**: Date of creation in YYYY-MM-DD format
- **Superseded_by**: Path to the document that replaces this one (only if Status is Superseded)

---

## Housekeeping Rules

The AI agent should actively maintain project organization based on document status:

| Status | Action |
|--------|--------|
| `Obsolete` | Move file to `90-archive/` |
| `Superseded` | Keep in place, but ensure `Superseded_by` links to replacement |
| `Active` | Keep in `20-working/` or promote to `00-current/` if finalized |

When creating new documents that replace existing ones:
1. Update the old document's frontmatter: set `Status: Superseded` and add `Superseded_by` path
2. Move the old document to `90-archive/` if it's now obsolete
3. Create the new document with `Status: Active`

---

## Session-End Protocol

At the end of every session, produce two outputs:

### 1. Session Log (goes to `30-logs/`)

Save a session log using the standard naming convention:
- Use format: `XXX_YYYY-MM-DD_<author>_session-log-<item-or-description>.md`
- Include:
  - Item ID and description worked on
  - Work performed summary
  - Validation results (ALL steps documented)
  - Blockers encountered
  - Key decisions made
- Example: `002_2025-12-18_claude_session-log-item-003-login-page.md`

### 2. Update Pack (updates `00-current/`)

Update the following files in `00-current/` to reflect the session outcomes:
- `progress.log` - Append session summary
- `item-list.json` - Update item status, notes, and metadata; on completion, move full record to archive and add compact entry to `completed_summary`
- `item-list-archive.json` - Append full record of completed items

**Remember:** Never modify `user-decision.md` - this is user-maintained only.

---

## Document Relationships and Wiki Linking

### Establishing Connections

When creating documents, identify relationships with existing documents and create wiki-style links using the `[[document-name]]` syntax.

### Inline Linking

Place wiki links inline within the natural flow of text where the reference is most relevant.

**Example:**
> "This implementation follows the approach documented in [[001_2025-12-16_cursor_architecture-overview]] and addresses the issues raised in [[user-decision]]."

The goal is to create a web of interconnected knowledge where readers can navigate naturally between related topics.

---

## Item Workflow (Task Relay Core)

### Execution Workflow

1. **State Recovery**: Read the last 100 lines of `00-current/progress.log`, `00-current/item-list.json` (active items + completed summaries), `00-current/user-decision.md` (read-only), `00-current/memory.md` (curated insights from prior sessions, if it exists), `10-reference/000_YYYY-MM-DD_spec.md`, and `10-reference/MANIFEST.md`. Check MANIFEST staleness via `ls 10-reference/`. Load only reference files relevant to the current item. Do NOT read `item-list-archive.json` unless you need detailed history of a completed item. **Progress-log archives**: if `30-logs/PROGRESS-ARCHIVE-MANIFEST.md` exists, read it (cheap, one table). Pull a specific `30-logs/progress-archive-*.log` ONLY when the current item references context (decisions, blockers, narrative) outside the fresh progress.log AND the JSON state files don't have it. Match by date / item ID / milestone keyword from the manifest table; do not load archives speculatively.
2. **Item Selection**: Check `next_override` first; if set, select that item and clear the override. Otherwise pick ONE pending item (lowest priority number)
3. **Execution**: Do the work, stay scoped to this item only
4. **Validation**: Run ALL validation steps (CRITICAL - all must pass)
5. **State Update**: Update `item-list.json` and append to `progress.log`
6. **Session Log**: Save detailed log to `30-logs/`
7. **Session Summary**: Report completion and recommend next item

### Item Status Values

- `pending` - Not yet started
- `in_progress` - Currently being worked on (max 1 at a time)
- `completed` - All validation steps passed
- `blocked` - Cannot proceed, documented reason in notes

---

## Memory Capture (00-current/memory.md)

When the user says "remember this", "remember that", "don't forget", "note for later", "add to memory", "记一下", "记住", or "别忘了":

1. Extract the candidate insight from surrounding conversation.
2. Propose a section (`Gotchas` / `Decisions` / `Preferences` / `Facts`) and a one-line phrasing.
3. Wait for user approval / edits.
4. On approval, append a bullet under the chosen `##` heading in `00-current/memory.md`:
   `- [YYYY-MM-DD] <phrasing>`
5. Echo the entry written. No `progress.log` update needed.

`memory.md` is auto-loaded during State Recovery so insights persist across sessions.

---

## Operating Principles

1. **Read First**: Always read `AGENTS.md`, the current state files (`item-list.json`, `user-decision.md`, `memory.md` if present, and only the last 100 lines of `progress.log`), `10-reference/000_YYYY-MM-DD_spec.md`, and `10-reference/MANIFEST.md` before starting work
2. **Maintain Structure**: Follow the folder structure and naming conventions strictly
3. **Track Status**: Keep frontmatter status updated as documents evolve
4. **Link Knowledge**: Create meaningful connections between related documents
5. **Clean Up**: Actively archive obsolete files and maintain organization
6. **Respect Boundaries**: Never modify user-maintained files (`user-decision.md`)
7. **One Item Per Session**: Focus on a single item to ensure quality
8. **Progressive Reference Disclosure**: Read MANIFEST.md to discover references. Match file descriptions/tags against the current item's category and description. Only load files that are clearly relevant. When in doubt, skip — you can always load a file later during execution

Your goal is not just to complete tasks, but to build an interconnected, well-organized knowledge base that grows more valuable over time.
