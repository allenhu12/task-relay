# Decomposition Rules

Canonical rules for breaking an assignment into items and tasks. Cited from
`SKILL.md` Initialization Phase / Step 2 and from any external decomposer
that produces a `task-input-batch.yaml` (Interface 3).

The discipline is borrowed from VlppParser2's scrum prompt: loose granularity
guidance is not enough — without these rules, decomposition drifts and items
become unreliable.

## The rules

### 1. One idea per item

A single feature, refactor, or test category. If you can't summarize the
item in one short sentence, split it.

✅ "Implement password reset email template."
❌ "Implement password reset and validate it across the auth module."

### 2. Functionality and tests are separate items

Never mix code change and test-writing in the same item. Split test items
by category (e.g. `TEST_CATEGORY` or feature area).

✅ ITEM-007: Implement JWT refresh endpoint.
   ITEM-008: Test JWT refresh endpoint (happy path + 3 error cases).
❌ ITEM-007: Implement JWT refresh endpoint and write tests for it.

### 3. Ordering guarantees compilability

At the end of each item, the project must compile and pass existing tests.
Order is a contract, not a hint. If completing ITEM-N breaks something that
ITEM-N+1 fixes, the split is wrong — merge them, or re-order.

### 4. Every item cites why it comes here

The item's rationale must reference KB entries, source files, or prior items
— not hand-waving. If you can't justify the order, the order is wrong.

✅ "Comes after ITEM-005 because the schema migration in 005 introduces the
    `users.refresh_token` column this endpoint reads."
❌ "Seems like the next logical step."

### 5. Every item is session-sized

An item must be completable in roughly one session (~30–90 minutes). If an
item would take more, split it into smaller items. **This rule replaces the
old `complexity: complex` / deep-task escape hatch.** Good decomposition is
the only defense against oversized items.

Rule of thumb:
- **Fits one session** — single file or two; obvious validation; no design phase needed.
- **Needs splitting** — touches ≥3 files, or needs a written plan, or has subtle
  invariants the executor must reason about. Split into 2–3 items instead.

### 6. Every item has ≥1 task

A trivial item is an item with a single task (mirroring its description).
Larger items get 2–5 tasks in `tasks[]`. Tasks are the checkpoint and
resumability mechanism — they let a session overflow gracefully if context
fills before the item is done.

**Task sizing guidance**:
- Each task should be a concrete, independently validatable sub-step (~10–30 minutes).
- Tasks within an item may be worked in any order (user-chosen); do not encode mandatory sequencing into the numbering.
- If a task would still take more than one session, it is too large — split the item.

## Item Granularity (advisory)

| Assignment scope | Typical item count |
|---|---|
| Whole application | 30–80 |
| Feature / module | 10–30 |
| Small enhancement | 3–10 |

If your project produces fewer than 3 items, you probably don't need
task-relay — drive the work directly.

## Item schema (v1.3)

Full canonical schema (matches `references/item-list-schema.json`):

```json
{
  "id": "ITEM-XXX",
  "category": "setup|implementation|testing|documentation|refactor|bugfix",
  "description": "<imperative phrase>",
  "priority": 1,
  "validation_steps": ["<item-level rollup check>", "..."],
  "status": "pending",
  "completed_at": null,
  "notes": "",
  "working_dir": null,
  "files": [],
  "tasks": [
    {
      "id": "TASK-XXX-01",
      "description": "<concrete sub-step>",
      "status": "pending",
      "validation_steps": ["<task-level check>"],
      "completed_at": null,
      "notes": ""
    }
  ]
}
```

**Field notes**:
- `validation_steps` is the canonical field name at both item and task level.
- `working_dir` is null until the item first goes `in_progress`; set by the agent lazily.
- `files` is agent-maintained; tracks files inside `working_dir`.
- Item status enum: `pending | in_progress | completed | blocked | cancelled`.

## Working from an existing design

When a `<n>_design.md` (Interface 2) exists, read it first and emit items
that match the design's interfaces and tech-stack choices. The design is
the source of truth; your decomposition is its execution plan.

## Legacy items

Existing items without `tasks[]` are treated as having a single task
auto-derived from the item description. Consumers must accept legacy items
unmodified. Do not retroactively re-decompose unless the user explicitly requests it.

## Citing this document

From `SKILL.md`:
> Decomposition rules — see `references/decomposition-rules.md`.

From `task-input-batch.yaml` producers:
> Items conform to `references/decomposition-rules.md` (six rules).
