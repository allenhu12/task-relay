# Learn Workflow (`/task-relay learn`)

Full procedure for the post-task retrospective. Routed from `SKILL.md`
§ Learn Workflow.

## When to use

- User invokes `/task-relay learn` (or `/task-relay learn ITEM-XXX`) after
  an item is marked `completed`.

**Do NOT run** when the item ended `blocked` or `cancelled`. Those need
separate user attention, not a retrospective.

## Inputs

- The most-recently-completed item from `00-current/item-list.json` (or
  the one named in the command).
- Its item log: `20-working/<ITEM-XXX>/log.md` (what was planned and how
  each task was executed).
- The current source-code state of the files the executor touched.

## Step 1 — Identify the last completed item

Find the most recent item where status flipped to `completed` (check
`progress.log` or the `terminal_summary` in `item-list.json`). If the user
passed an explicit ITEM-XXX, use that.

## Step 2 — Identify user hand-edits

Read `20-working/<ITEM-XXX>/log.md` to understand what the agent planned to
do vs. what actually happened. Then compare logged work against the current
source code:

1. For each file referenced in the item log's task entries, read current contents.
2. Compute the diff between *log-said-to-write* and *file-currently-says*.
3. Filter the diff:
   - **Ignore** changes documented under task validation results (executor self-corrections).
   - **Ignore** changes already captured in the log's "Work performed" sections.
   - **Anything else** is a user hand-edit — the signal we care about.

> **Why not `git diff`?** Because the user often commits intermediate
> states. The trustworthy comparison is *log vs. current state*, not
> *initial vs. current state*.

## Step 3 — Categorize the hand-edits

| Edit type | Lesson section |
|---|---|
| Renamed a variable / refactored naming | Preferences |
| Replaced one API call with another | Decisions or Preferences |
| Removed a comment / changed comment style | Preferences |
| Fixed a bug the executor introduced | Gotchas |
| Added a new helper / refactored shape | Decisions |
| Changed a hard-coded value / config | Facts (if stable constant) or Decisions |

If you can't categorize a hand-edit, propose it as a Decision with the
note "user adjusted X — pending classification."

## Step 4 — Propose lessons

Build a candidate list:

```yaml
candidate_lessons:
  - section: preferences
    text: "User prefers `auto&&` over explicit type for collection-typed locals."
    evidence:
      file: Source/Json/JsonWriter.cpp
      excerpt: |
        - vint count = items.Count();
        + auto&& count = items.Count();
  - section: gotchas
    text: "JsonWriter::writer is private in base class; must use this->writer in derived members."
    evidence: ...
```

Present this list to the user. **Require per-lesson confirmation.** Default
is interactive confirm-each; `--auto-confirm` flag allows low-risk patterns
to apply without prompting.

## Step 5 — Apply confirmed lessons

For each confirmed lesson:

1. **Update `00-current/memory.md`** via the capture workflow with
   `[N=k]` frequency counters (see `SKILL.md` § Memory Capture). Pass the
   lesson `text` and `section`.

2. **Update not-yet-started items** in `00-current/item-list.json`:
   - For each pending item where the lesson is semantically relevant,
     append to its `notes` field:
     ```
     [LEARNED YYYY-MM-DD from ITEM-007] <lesson text>
     ```
   - Use semantic judgement — only attach to items where the lesson
     plausibly applies. If unclear, skip; do not pollute every item.

3. **Log to `progress.log`:**
   ```markdown
   ### Session N - YYYY-MM-DD
   **Phase**: Learn Retrospective
   **From**: ITEM-007
   **Lessons applied**:
     - Preferences: "User prefers auto&& over explicit type..."
       → memory.md (N=1 → N=2)
       → ITEM-009.notes (semantic relevance: refactor task)
     - Gotchas: "JsonWriter::writer is private..."
       → memory.md (new)
   ```

## Anti-patterns

- ❌ **Auto-applying lessons without confirmation.** The signal can be
  noisy — a "preference" may be the user fixing a typo. Always confirm.
- ❌ **Editing completed items.** Lessons propagate forward only; pending
  items are fair game, completed ones are immutable.
- ❌ **Batching many tasks at once.** Run `learn` per-task while context
  is fresh. Five tasks of unprocessed lessons buries the signal.

## Acceptance criteria

- Running the command after a completed task produces a candidate
  lessons list with categorization and evidence.
- User confirms per-lesson; only confirmed ones land in `memory.md` and
  `item-list.json`.
- `progress.log` records the retrospective transparently.
- Items that ended `blocked` or `cancelled` are skipped, not retrospected.
- Falsely-attributed hand-edits (caused by fixing attempts) are filtered
  out.
