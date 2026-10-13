# Batch Ingestion (`task-input-batch.yaml`)

Full procedure for ingesting an Interface 3 batch into
`00-current/item-list.json`. Routed from `SKILL.md` § Ingesting a Batch.

## When to use

- After running `/project decompose`.
- When the user hands you a `task-input-batch.yaml` produced elsewhere.
- When applying a delta batch of changes against an existing item-list.

## Inputs

- `task-input-batch.yaml` at a known path (typically
  `20-working/task-input-batch.yaml`).
- Existing `00-current/item-list.json` (may be empty or already populated).

## Procedure

### 1. Validate schema

Read the batch file. Confirm `schema_version: 1`. If unknown, refuse and
alert the user.

### 2. For each item in `items[]`

1. Assign next `ITEM-XXX` id (highest existing id in `items ∪
   terminal_summary`, +1).
2. Verify required fields per Interface 3: `title`, `description`,
   `priority`, `validation_steps` (≥1), and optionally `tasks[]`.
3. **Tasks contract:**
   - If the batch item has `tasks[]`, ingest them as-is. Assign task IDs as
     `TASK-<item-number>-01`, `TASK-<item-number>-02`, etc. in order.
   - If `tasks[]` is absent, **auto-derive a single task** from the item:
     ```json
     {
       "id": "TASK-001-01",
       "description": "<item description>",
       "status": "pending",
       "validation_steps": ["<same as item validation_steps>"],
       "completed_at": null,
       "notes": ""
     }
     ```
4. Map to `00-current/item-list.json` item format:
   - Copy `id`, `category`, `description`, `priority`.
   - `validation_steps` is the canonical field name.
   - `status: pending`, `completed_at: null`, `notes: ""`, `working_dir: null`, `files: []`.
   - Include the resolved `tasks[]`.
5. **Resolve in-batch `depends_on` references** — items may refer to siblings
   in the same batch; substitute the assigned IDs once known.
6. Append to the `items` array.

**Milestone sanity note:** if any item's description joins unrelated goals
(e.g. "Implement password reset and redesign the billing page"), flag it to
the user with a suggestion to split before ingesting. Length alone is not a
reason to split.

### 3. Update metadata counts

- `total_items += <batch length>`
- `pending += <batch length>`

### 4. Log ingestion in `00-current/progress.log`

```markdown
### Session N - YYYY-MM-DD HH:MM
**Phase**: Ingestion (batch)
**Source**: <path to task-input-batch.yaml>
**Items added**: ITEM-AAA through ITEM-ZZZ (<count> total)
**Notes**: <any validation issues, dropped items, etc.>
```

### 5. Archive the batch file

Move `task-input-batch.yaml` to
`90-archive/<YYYY-MM-DD>_task-input-batch.yaml` once successfully ingested.
Prevents accidental re-ingestion; preserves audit trail.

## Delta batches

When the batch has top-level `delta: true`, apply surgical updates.

### Item-level delta ops

| Operation | How |
|---|---|
| `op: add` | Same as full ingestion — append new items (with tasks[]). |
| `op: modify` | Replace the named item's fields. Preserve `id`; preserve `status` if non-pending. |
| `op: remove` | **Whole-item cancellation**: mark item `status: cancelled`, `notes: "removed by delta batch <date>"`. Cascade: set every non-completed task to `cancelled`. Archive to `terminal_summary`. Never hard-delete. |

### Task-level delta ops

| Operation | How |
|---|---|
| `op: add_task` | Target: `ITEM-XXX`. Append a new task with the next sequential task number. |
| `op: modify_task` | Target: `ITEM-XXX`, task: `TASK-XXX-YY`. Replace description or status fields. |
| `op: remove_task` | Target: `ITEM-XXX`, task: `TASK-XXX-YY`. Set task `status: cancelled`, `notes: "removed by delta batch <date>"`. Never hard-delete tasks. |

**Completed items (`status: completed`) MUST NEVER be modified or removed
by a delta.** If a delta would change a completed item, log a warning and
skip it.

## Validation failures

- **Missing required field on any item** → refuse the entire batch; alert
  user with the offending item index.
- **Duplicate `title` against existing pending items** → flag for user
  confirmation; do not auto-merge.
- **`depends_on` referencing unknown ITEM-ID** → flag, but allow ingestion
  (mark item as having a forward-reference; resolve later).

## Acceptance criteria

- A valid `task-input-batch.yaml` produces correctly-numbered,
  fully-populated items in `item-list.json`, each with ≥1 task.
- Items without `tasks[]` get a single auto-derived task.
- Metadata counts match the new state (including `cancelled` if any removals).
- The batch file is archived, not left in the working folder.
- Delta batches preserve completed items and use the new task-level ops.
- Schema-version mismatches are refused, not silently coerced.

## Template

See `assets/task-input-batch.template.yaml` for the expected shape.
