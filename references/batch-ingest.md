# Batch Ingestion (`task-input-batch.yaml`)

Full procedure for ingesting an Interface 3 batch into
`00-current/item-list.json`. Routed from `SKILL.md` § Ingesting a Batch.

## When to use

- After running `/project decompose`.
- When the user hands you a `task-input-batch.yaml` produced elsewhere.
- When applying a delta batch from a `## CHANGES` section in an updated
  `<n>_design.md`.

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
   completed_summary`, +1).
2. Verify required fields per Interface 3: `title`, `description`,
   `complexity`, `priority`, `depends_on`, `validation_criteria` (≥1),
   `rationale_for_order`.
3. Map to `00-current/item-list.json` item format:
   - Copy `id`, `category`, `description`, `priority`, `complexity`,
     `depends_on`, `rationale_for_order`.
   - `validation_steps = validation_criteria` (aliasing).
   - `status: pending`, `completed_at: null`, `notes: ""`.
4. **Resolve in-batch `depends_on` references** — items may refer to siblings
   in the same batch; substitute the assigned IDs once known.
5. Append to the `items` array.

### 3. Update metadata counts

- `total_items += <batch length>`
- `pending += <batch length>`

### 4. Log ingestion in `00-current/progress.log`

```markdown
## Session N - YYYY-MM-DD HH:MM
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

When the batch has top-level `delta: true` (designer flow on `## CHANGES`),
apply surgical updates:

| Operation | How |
|---|---|
| `add` | Same as full ingestion — append new items. |
| `modify` | Replace the named item's fields. Preserve `id`; preserve `status` if non-pending. |
| `remove` | Mark the named item `status: cancelled`, note `"removed by delta batch <date>"`. Never delete (audit trail). |

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
  fully-populated items in `item-list.json`.
- Metadata counts match the new state.
- The batch file is archived, not left in the working folder.
- Delta batches preserve completed items.
- Schema-version mismatches are refused, not silently coerced.

## Template

See `assets/task-input-batch.template.yaml` for the expected shape.
