---
Type: session-log
Status: Active
Author: {AUTHOR}
Created: {YYYY-MM-DD}
---

# Session Log: {ITEM_ID} - {ITEM_DESCRIPTION}

## Session Info

| Field | Value |
|-------|-------|
| Session # | {SESSION_NUMBER} |
| Date | {YYYY-MM-DD} |
| Time | {HH:MM} |
| Duration | ~{XX} minutes |
| Phase | Execution |
| Agent | {claude / cursor / gemini / etc.} |

---

## Item Details

**Item ID**: {ITEM_ID}
**Description**: {ITEM_DESCRIPTION}
**Category**: {CATEGORY}
**Priority**: {PRIORITY}

---

## Work Performed

1. {Step 1 description}
2. {Step 2 description}
3. {Step 3 description}

---

## Validation Results

| Step | Result | Notes |
|------|--------|-------|
| {Validation step 1} | Pass/Fail | {Details} |
| {Validation step 2} | Pass/Fail | {Details} |
| {Validation step 3} | Pass/Fail | {Details} |

**Overall Result**: {All Passed / X of Y Passed / Blocked}

---

## State Updates

| File | Change |
|------|--------|
| `item-list.json` | {ITEM_ID}: {old_status} → {new_status} |
| `item-list.json` | metadata.completed: {X} → {Y} |
| `item-list.json` | metadata.in_progress: {X} → {Y} |

---

## Blockers

{None encountered / List any blockers}

---

## Related Documents

- [[progress.log]] - Updated with session summary
- [[item-list.json]] - Updated item status
- {Other related documents}

---

## Next Session Recommendation

**Recommended Item**: {NEXT_ITEM_ID} - {NEXT_ITEM_DESCRIPTION}
**Reason**: {Why this item is next priority}

---

## Notes

{Any additional context, observations, or information for future sessions}
