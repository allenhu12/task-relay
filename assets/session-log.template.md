---
Type: session-log
Status: Active
Author: {AUTHOR}
Created: {YYYY-MM-DD}
Item: {ITEM_ID}
---

# Item Log: {ITEM_ID} - {ITEM_DESCRIPTION}

This file lives at `20-working/{ITEM_ID}/log.md`. It is initialized when the
item first transitions to `in_progress` and updated after each task.

---

## Item Details

| Field | Value |
|-------|-------|
| **Item ID** | {ITEM_ID} |
| **Description** | {ITEM_DESCRIPTION} |
| **Category** | {CATEGORY} |
| **Priority** | {PRIORITY} |
| **Started** | {YYYY-MM-DD} |

---

## Tasks

| Task ID | Description | Status | Completed |
|---------|-------------|--------|-----------|
| TASK-{NNN}-01 | {task description} | pending | — |

---

## Session Entries

<!-- Append a new entry after each work session. -->

### {YYYY-MM-DD} — {AGENT}

**Tasks worked this session**: TASK-{NNN}-01

**Work performed**:
1. {Step 1 description}
2. {Step 2 description}

**Task validation results**:

| Task | Step | Result | Notes |
|------|------|--------|-------|
| TASK-{NNN}-01 | {Validation step 1} | Pass/Fail | {Details} |

**Task outcome**: TASK-{NNN}-01 → {completed / blocked / cancelled}

**Blockers**: {None encountered / List any blockers}

**Files created/modified**:
- `{file path}`

---

## Item Validation Results

<!-- Fill in when all tasks are done and item-level validation is run. -->

| Step | Result | Notes |
|------|--------|-------|
| {Item-level validation step 1} | Pass/Fail | {Details} |

**Overall Result**: {All Passed / X of Y Passed / Blocked}

---

## Item Outcome

**Status**: {completed / blocked / cancelled}
**Completed at**: {YYYY-MM-DDTHH:MM:SSZ}
**Notes**: {Any additional context or reason for cancellation}

---

## Related Documents

- [[00-current/progress.log]] - Session history
- [[00-current/item-list.json]] - Item status
- {Other related documents}
