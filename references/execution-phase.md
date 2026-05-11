# Execution Phase — Full Procedure

Routed from `SKILL.md` § Execution Phase Workflow. Run this workflow when
**continuing** an existing assignment (state files exist).

The summary in `SKILL.md` lists the steps + the State Recovery checklist.
This file holds the full procedure, examples, and acceptance criteria.

## Step 1: State Recovery

**CRITICAL**: start every execution session by recovering state.

```bash
# 1. Confirm working directory
pwd

# 2. Read AGENTS.md for workflow instructions
cat AGENTS.md

# 3. Read recent progress log context from 00-current/
tail -100 00-current/progress.log

# 4. Load item list from 00-current/ (active items + compact completed summaries)
cat 00-current/item-list.json
# NOTE: Do NOT read item-list-archive.json here — it contains full records of
# completed items and is only needed when you must reference detailed history
# of a specific completed item.

# 5. Check user decisions (read-only!)
cat 00-current/user-decision.md

# 5b. Read curated memory (insights captured via "remember this" / "don't forget")
[ -f 00-current/memory.md ] && cat 00-current/memory.md

# 6. Read reference spec file (always)
SPEC_FILE=$(ls -t 10-reference/*_spec.md 2>/dev/null | head -1)
cat "$SPEC_FILE"

# 7. Read reference manifest and check for staleness
cat 10-reference/MANIFEST.md
ls 10-reference/

# 7b. If progress-log archives exist, read the manifest (cheap; one table)
[ -f 30-logs/PROGRESS-ARCHIVE-MANIFEST.md ] && cat 30-logs/PROGRESS-ARCHIVE-MANIFEST.md
# Pull a specific 30-logs/progress-archive-*.log ONLY when the current item
# needs context (decisions, blockers, narrative) outside the fresh progress.log
# AND the JSON state files don't already have it.

# 8. Load relevant reference files (progressive disclosure)
# Based on the current item's category/description and MANIFEST entries,
# decide which reference files to fully read. Only load what's relevant.

# 9. Initialize environment
./init.sh  # or follow init.md

# 10. Run health checks (if applicable)
npm test  # or equivalent
```

### State Recovery Checklist

- Read AGENTS.md (understand workflow rules)
- Read the last 100 lines of `00-current/progress.log`
- Read `00-current/item-list.json` (active items + compact completed summaries)
- Do **NOT** read `00-current/item-list-archive.json` (only on demand)
- Read `00-current/user-decision.md` (user context — **DO NOT MODIFY**)
- Read `00-current/memory.md` if it exists
- Read `10-reference/000_YYYY-MM-DD_spec.md` (reference paths and URLs)
- If the spec file is missing in an existing project, ask the user for it; do not create it during execution
- Read `10-reference/MANIFEST.md` (discover available reference files); run `ls 10-reference/` and update MANIFEST if files added/removed
- If `30-logs/PROGRESS-ARCHIVE-MANIFEST.md` exists, read it. Pull a specific archive only on demand — never speculatively
- Based on the current item's category and description, load only relevant reference files (progressive disclosure)
- Check metadata counts (progress overview); note any blockers from prior sessions
- Verify environment initialized successfully

## Step 2: Item Selection

Select exactly **one** item to work on this session.

### Selection algorithm

```python
def select_next_item(data):
    """Select the next item to work on."""

    # 1. Check for next_override (user-requested priority item)
    override_id = data.get("next_override")
    if override_id:
        override_item = next(
            (item for item in data["items"]
             if item["id"] == override_id and item["status"] == "pending"),
            None
        )
        if override_item:
            data["next_override"] = None  # Clear after selecting
            return override_item
        else:
            data["next_override"] = None  # Target not found — clear, fall through

    # 2. Normal selection: pending items, sort by priority (lowest = highest priority)
    pending = [item for item in data["items"] if item["status"] == "pending"]
    if not pending:
        return None
    pending.sort(key=lambda x: x["priority"])
    return pending[0]
```

### Override behaviour

- If `next_override` is a valid pending item ID, that item is selected regardless of priority.
- The override is automatically cleared (set to `null`) after selection.
- If the override target is not found, blocked, or already completed, clear it and resume normal selection.

### Update state on selection

In `00-current/item-list.json`:

```json
{
  "id": "ITEM-003",
  "status": "in_progress",
  ...
}
```

And:

```json
{ "next_override": null }
```

Update metadata:

```json
{
  "metadata": {
    "in_progress": 1,
    "pending": 12
  }
}
```

## Inserting Items During Execution

Users may need to add urgent items mid-assignment.

**When to insert**:
- User explicitly requests: "add a new item for X" or "I need to handle X first"
- A discovered dependency or bug requires immediate attention
- Scope change from user decisions

**Procedure**:

1. Determine the next item ID (highest existing in both `items` and `completed_summary`, +1).
2. Create the item with full fields per the v1.1 schema (`complexity`, `depends_on`, `validation_criteria`, `rationale_for_order`, `status: pending`, etc.).
3. Append to `items` array.
4. Update metadata: increment `total_items` and `pending`.
5. If the item should be handled first: set `next_override` to the new item's ID.
6. Log the insertion in `progress.log` with reason.

### Example — insert and prioritize

```json
{
  "id": "ITEM-048",
  "category": "bugfix",
  "description": "Fix critical login redirect loop discovered during ITEM-012 work",
  "complexity": "simple",
  "priority": 48,
  "depends_on": [],
  "validation_criteria": [
    "Login no longer enters redirect loop",
    "Session token is set correctly after login"
  ],
  "rationale_for_order": "Hot-patch discovered during ITEM-012; blocks user testing.",
  "status": "pending",
  "completed_at": null,
  "notes": "Discovered during ITEM-012."
}
```

```json
{ "next_override": "ITEM-048" }
```

Update metadata:

```json
{
  "metadata": {
    "total_items": 48,
    "pending": 13
  }
}
```

### Example — insert without priority override

Add the item as above, but leave `next_override` as `null`. The item will be picked up based on its priority.

## Step 3: Execution

Perform the work for the selected item.

1. Read the item description — understand exactly what needs to be done.
2. Check validation criteria — know how you'll verify completion.
3. Do the work — implement, write, code, analyze, etc.
4. Stay scoped — only work on **this** item; resist scope creep.

**Anti-patterns to avoid**:
- ❌ Working on multiple items simultaneously
- ❌ Adding "just one more thing" beyond item scope
- ❌ Modifying other items while working on this one
- ❌ Skipping validation "to save time"

For `complexity: complex` items, consider invoking `/task-relay deep ITEM-XXX`
(see `references/deep-adapter.md`) rather than executing inline.

## Step 4: Validation (CRITICAL)

**Rule**: only mark an item `completed` if ALL validation steps pass.

For each entry in `validation_criteria`:

1. Execute the step exactly as written.
2. Document the result (pass / fail).
3. If ANY step fails:
   - Do NOT mark `completed`.
   - Fix and re-validate, OR
   - Mark as `blocked` with detailed notes.

### Example validation execution

```json
[
  "Run npm test and verify all tests pass",
  "Start the app and navigate to /login",
  "Submit login form and verify redirect to dashboard"
]
```

```
✅ npm test - All 24 tests passed
✅ Navigate to /login - Page loads correctly
✅ Submit form - Redirects to dashboard, session persists
→ All validations passed → OK to mark completed
```

## Step 5: State Update (MANDATORY)

**CRITICAL**: update state files BEFORE ending the session.

### 5.1 Update item-list.json (archive if completed)

**For completed items** — archive the full record to keep `item-list.json` lean:

```json
// Step A: Append the FULL item record to 00-current/item-list-archive.json
{
  "id": "ITEM-003",
  "category": "implementation",
  "description": "Implement user login page",
  "complexity": "simple",
  "priority": 3,
  "validation_criteria": ["Run npm test...", "Navigate to /login...", "Submit form..."],
  "rationale_for_order": "Comes after auth scaffold (ITEM-002).",
  "status": "completed",
  "completed_at": "2025-12-10T14:45:00Z",
  "notes": "All tests passing, validated in dev environment"
}

// Step B: REMOVE the full record from the items array in item-list.json

// Step C: ADD a compact summary to completed_summary in item-list.json
{
  "completed_summary": [
    { "id": "ITEM-003", "description": "Implement user login page", "completed_at": "2025-12-10T14:45:00Z" }
  ]
}

// Step D: Update metadata
{
  "metadata": {
    "total_items": 15,
    "completed": 4,
    "in_progress": 0,
    "blocked": 0,
    "pending": 10
  }
}
```

**For blocked items** — keep in `item-list.json` (no archival):

```json
{
  "id": "ITEM-005",
  "status": "blocked",
  "completed_at": null,
  "notes": "Blocked: Waiting for API credentials from user."
}
```

```json
{
  "metadata": {
    "total_items": 15,
    "completed": 3,
    "in_progress": 0,
    "blocked": 1,
    "pending": 11
  }
}
```

### 5.2 Update progress.log

Append a new session entry (note the `###` heading to avoid polluting
document outline when this template is rendered as docs):

```markdown
### Session N - 2025-12-10 14:00
**Phase**: Execution
**Duration**: ~45 minutes
**Agent**: [Claude Code / ChatGPT / Gemini / etc.]

**Item**: ITEM-003 - Implement user login page
**Status**: ✅ Completed

**Work Performed**:
1. Created login.tsx component with form validation
2. Integrated with authentication API
3. Added error handling for invalid credentials
4. Implemented redirect to dashboard on success

**Validation Results**:
- ✅ npm test - All 24 tests passed
- ✅ Navigate to /login - Page loads correctly
- ✅ Submit valid credentials - Redirects to dashboard
- ✅ Submit invalid credentials - Shows error message

**State Updates**:
- ITEM-003: in_progress → completed
- metadata.completed: 3 → 4
- metadata.in_progress: 1 → 0

**Session Log**: [[002_2025-12-10_claude_session-log-item-003]]

**Next Session Recommendation**: ITEM-004 - Implement password reset flow

---
```

### 5.3 Create session log in 30-logs/

```bash
# Naming: XXX_YYYY-MM-DD_<agent>_session-log-<item-description>.md
touch 30-logs/002_2025-12-10_claude_session-log-item-003-login-page.md
```

Include:
- YAML frontmatter (`Type: session-log`, `Status: Active`, `Author`, `Created`)
- Full session details
- Work performed
- All validation results
- Blockers encountered
- Wiki links to related documents

See `assets/session-log.template.md` for the complete format.

### 5.4 Commit changes (if using Git)

```bash
git add 00-current/item-list.json 00-current/item-list-archive.json \
        00-current/progress.log 30-logs/
git commit -m "Complete ITEM-003: Implement user login page

- Created login component with validation
- Integrated authentication API
- All tests passing
- Validated in dev environment"
```

## Step 6: Session Summary

Report to user:

```markdown
✅ **Session Complete**

**Item**: ITEM-003 - Implement user login page
**Status**: Completed
**Validation**: All checks passed

**Progress**:
- Completed: 4/15 (26.7%)
- Remaining: 11 items
- Blocked: 0 items

**Files Updated**:
- 00-current/item-list.json
- 00-current/item-list-archive.json (if item completed)
- 00-current/progress.log
- 30-logs/002_2025-12-10_claude_session-log-item-003-login-page.md

**Next Session**: Start with ITEM-004 - Implement password reset flow

📖 See 00-current/progress.log for detailed session history
📖 See 30-logs/ for full session logs
```

For `complexity: complex` items completed via `/task-relay deep`, consider
suggesting `/task-relay learn` to extract lessons from any user hand-edits.
