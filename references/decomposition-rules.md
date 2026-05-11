# Decomposition Rules

Canonical rules for breaking an assignment into items. Cited from `SKILL.md`
Initialization Phase / Step 2 and from any external decomposer that produces
a `task-input-batch.yaml` (Interface 3).

The discipline is borrowed from VlppParser2's scrum prompt: loose granularity
guidance is not enough — without these five rules, decomposition drifts and
items become unreliable.

## The five rules

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

The item's `rationale_for_order` must reference KB entries, source files,
or prior items — not hand-waving. If you can't justify the order, the
order is wrong.

✅ "Comes after ITEM-005 because the schema migration in 005 introduces the
    `users.refresh_token` column this endpoint reads."
❌ "Seems like the next logical step."

### 5. Every item carries a `complexity` flag

Either `simple` (handled inline by the base agent) or `complex` (handed off
to `deep-task` via the deep adapter). This drives the execution path
automatically.

Rule of thumb:
- **simple** — single file or two; obvious validation; no design phase needed.
- **complex** — touches ≥3 files, or needs a written plan, or has subtle
  invariants the executor must reason about.

## Granularity (advisory, not mandatory)

| Assignment scope | Typical item count |
|---|---|
| Whole application | 30–80 |
| Feature / module | 10–30 |
| Small enhancement | 3–10 |

If your project produces fewer than 3 items, you probably don't need
task-relay — drive the work directly.

## Item schema

Full canonical schema (matches `references/item-list-schema.json`):

```json
{
  "id": "ITEM-XXX",
  "category": "setup|implementation|testing|documentation|refactor|bugfix",
  "description": "<imperative phrase>",
  "complexity": "simple | complex",
  "priority": 1,
  "depends_on": ["ITEM-YYY"],
  "validation_criteria": ["<objective check>", "..."],
  "validation_steps": ["<alias for validation_criteria>"],
  "rationale_for_order": "<why this comes here, citing evidence>",
  "status": "pending",
  "completed_at": null,
  "notes": ""
}
```

> **Field aliasing.** `validation_steps` and `validation_criteria` are
> aliases for one major version. Producers may emit either; consumers must
> accept both. `validation_criteria` is the canonical name going forward
> (aligns with Interface 4).

## Working from an existing design

When a `<n>_design.md` (Interface 2) exists, read it first and emit items
that match the design's interfaces and tech-stack choices. The design is
the source of truth; your decomposition is its execution plan.

## Legacy items

Existing items without `complexity` or `rationale_for_order` are treated as:

- `complexity: simple`
- `rationale_for_order: "(legacy item, no rationale recorded)"`

Consumers must accept legacy items unmodified. Do not retroactively
re-decompose unless the user explicitly requests it.

## Citing this document

From `SKILL.md`:
> Decomposition rules — see `references/decomposition-rules.md`.

From `task-input-batch.yaml` producers:
> Items conform to `references/decomposition-rules.md` (five rules).
