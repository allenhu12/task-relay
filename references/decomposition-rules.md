# Decomposition Rules

Canonical rules for breaking an assignment into items and tasks. Cited from
`SKILL.md` Initialization Phase / Step 2 and from any external decomposer
that produces a `task-input-batch.yaml` (Interface 3).

The discipline is borrowed from VlppParser2's scrum prompt: loose granularity
guidance is not enough — without these rules, decomposition drifts and items
become unreliable.

## The rules

### 1. One milestone per item

An item is a milestone. It may have several outcomes, but they all serve one
milestone that you can name in one short sentence. If you need two sentences
for two unrelated goals, split the item.

✅ "Password reset works end to end: email template, token endpoint, reset page."
❌ "Password reset works, and the admin dashboard gets a new layout."

### 2. Functionality and tests are separate tasks

Inside an item, write code and tests in different tasks, so each one is a
checkpoint. The item's `validation_steps` include the tests, so the item
closes with real proof. A broad test effort that serves several milestones
(for example a regression suite) may still be its own item.

✅ ITEM-007: JWT refresh works end to end.
   TASK-007-01: Implement the refresh endpoint.
   TASK-007-02: Test the endpoint (happy path + 3 error cases).
   Item validation: all refresh-endpoint tests pass.
❌ ITEM-007: Implement the refresh endpoint. ITEM-008: Test it.
   (ITEM-007 cannot prove its milestone.)
❌ TASK-007-01: Implement the refresh endpoint and write its tests.
   (No checkpoint between code and tests.)

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

### 5. Every item has a clear finish line

Size an item by its outcome, not by time. A session is the vehicle for the
work, not its unit of size: an item may take one session or many. Tasks and
handoffs carry the work across sessions.

Split an item when:
- it holds two milestones (rule 1), or
- its `validation_steps` cannot show that the milestone is reached.

### 6. Every item has ≥1 task

A trivial item is an item with a single task (mirroring its description).
Larger items get 2–5 tasks in `tasks[]`. Tasks are the checkpoints: each one
ends in a state that the next session can verify and trust.

**Task sizing guidance**:
- Each task is a small goal that ends in a verifiable state.
- A task may take one session or several. Session length does not limit task size.
- Split a task when it holds two goals, not when it is long.
- A long task (one expected to cross a handoff) should have a rulebook that states its objective, deliverables, acceptance, boundaries and stop point.
- Tasks within an item may be worked in any order (user-chosen); do not encode mandatory sequencing into the numbering.

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
