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

# 4. Load item list from 00-current/ (active items + compact terminal summaries)
cat 00-current/item-list.json
# NOTE: Do NOT read item-list-archive.json here — only on demand when you must
# reference detailed history of a specific terminal item.

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
[ -f 90-archive/progress-log/PROGRESS-ARCHIVE-MANIFEST.md ] && \
  cat 90-archive/progress-log/PROGRESS-ARCHIVE-MANIFEST.md
# Pull a specific archive ONLY when the current item needs context (decisions,
# blockers, narrative) outside the fresh progress.log AND the JSON state files
# don't already have it. NEVER load archives speculatively.

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
- Read `00-current/item-list.json` (active items with tasks[] + compact terminal summaries)
- Do **NOT** read `00-current/item-list-archive.json` (only on demand)
- Read `00-current/user-decision.md` (user context — **DO NOT MODIFY**)
- Read `00-current/memory.md` if it exists
- Read `10-reference/000_YYYY-MM-DD_spec.md` (reference paths and URLs)
- If the spec file is missing in an existing project, ask the user for it; do not create it during execution
- Read `10-reference/MANIFEST.md` (discover available reference files); run `ls 10-reference/` and update MANIFEST if files added/removed
- If `90-archive/progress-log/PROGRESS-ARCHIVE-MANIFEST.md` exists, read it. Pull a specific archive only on demand — never speculatively
- Based on the current item's category and description, load only relevant reference files (progressive disclosure)
- Check metadata counts (progress overview); note any blockers from prior sessions
- Verify environment initialized successfully

## Step 2: Selection Gate

**This step is read-only + a single confirmation gate. Never auto-execute.**

### Resume case (item already `in_progress` from a prior overflow)

If `item-list.json` contains an item with `status: in_progress`:
- Do **NOT** run item selection — that item is already chosen.
- If a task within that item is `in_progress`: propose resuming that specific task (the overflow resume point).
- If no task is `in_progress` in the item: list remaining `pending` tasks and **ask the user to choose** which one to run next.
- Do NOT mark anything new `in_progress` until the user responds.

### Selection case (no item currently `in_progress`)

```python
def select_candidate(data):
    """Identify (but do not mark) the next candidate item."""

    # 1. Check for next_override
    override_id = data.get("next_override")
    if override_id:
        override_item = next(
            (item for item in data["items"]
             if item["id"] == override_id and item["status"] == "pending"),
            None
        )
        if override_item:
            return override_item  # cleared only on user confirm
        else:
            data["next_override"] = None  # target not found — clear, fall through

    # 2. Normal selection: lowest-priority pending item
    pending = [item for item in data["items"] if item["status"] == "pending"]
    if not pending:
        return None  # "nothing actionable" — report and stop
    pending.sort(key=lambda x: x["priority"])
    return pending[0]

    # NOTE: NEVER pick a blocked item. If all pending are blocked → return None.
```

### Confirmation protocol

1. Present the candidate item (id, description, tasks overview) to the user.
2. **STOP and wait for confirmation.**
3. On confirm:
   - Mark item `in_progress`; update `metadata`.
   - Clear `next_override` (if it was set).
   - Create `20-working/<ITEM-ID>/` folder if it does not exist yet.
   - Initialize `20-working/<ITEM-ID>/log.md` from `assets/session-log.template.md`.
4. On reject: leave state unchanged; `next_override` stays set if it was set.

### "Nothing actionable" path

If no pending items exist (all blocked or all terminal):
- Report "nothing actionable: all remaining items are blocked (or there are none)."
- List blocked items if any so the user can unblock.
- Do NOT auto-select a blocked item.

## Step 3: Task Loop (User-Driven)

After the item is confirmed `in_progress`, enter the task loop.

### Task loop protocol

1. Read the item's `tasks[]` from `item-list.json`.
2. List all `pending` tasks (do NOT show completed/cancelled unless the user asks).
3. Ask the user: "Which task should we work on? [list]"
4. **Wait for user selection.** The agent does not auto-pick.
5. Mark the selected task `in_progress`; flush `item-list.json` immediately through the state writer (§ Step 3.5).
6. Do the work for that task.
7. Run the task's `validation_steps`.
8. Mark the task `completed` / `blocked` / `cancelled`; flush `item-list.json` through the state writer (§ Step 3.5). For `blocked`, classify the blocker first — see § Step 3.5.
9. Append progress note to `20-working/<ITEM-ID>/log.md`.
10. **STOP. Go back to step 2 of this loop** (list remaining tasks, ask again).

The loop ends when:
- The user says to stop (end session / context overflow).
- No `pending` tasks remain (all `completed` or `cancelled`) → proceed to Item Completion.

### Task state rules

- Exactly **one** `in_progress` task at a time within the `in_progress` item.
- A `blocked` task does NOT block the item — user can pick another task.
- `cancelled` tasks require `notes`; they are skipped in selection.
- The agent NEVER auto-advances to the next task.

### Overflow / mid-session handoff

If context fills before the item is done:
1. Ensure the current task's state is flushed (`in_progress` or `completed` in JSON).
2. Append a handoff note to `00-current/progress.log`:
   ```markdown
   ### Session N - YYYY-MM-DD HH:MM
   **Phase**: Execution (overflow / mid-item)
   **Item**: ITEM-003 - <description>
   **Task in progress**: TASK-003-02 - <task description> (left in_progress)
   **Tasks completed this session**: TASK-003-01
   **Tasks remaining**: TASK-003-02 (in_progress), TASK-003-03 (pending)
   **Handoff note**: Context limit reached. Resume with TASK-003-02 next session.
   ```
3. End the session. Do NOT clear `in_progress` on item or task.

## Step 3.5: State Write via the State Writer

All state writes go through the **`task-relay-state-writer`** subagent (D1, D12). The subagent
owns `item-list.json`, `item-list-archive.json` and `progress.log`, and it re-renders
`00-current/dashboard.html` after every write. Instruction text, the full update-request
grammar, and install notes: `references/state-writer-contract.md`.

Install once per machine, if it is not already there:

```bash
bash {SKILL_SCRIPTS_PATH}/install-state-writer.sh
```

### How to call it

| CLI | Call |
|---|---|
| Claude Code | Agent/Task tool, subagent `task-relay-state-writer`, update request as the prompt |
| Codex CLI | `spawn_agent` with `agent_type = "task-relay-state-writer"` and the update request as `message`. Do **not** pass `model` or `reasoning_effort` — the role pins them (`gpt-6-luna`, medium). |

### The update request

Send one plain-text message. Include every op for this flush, plus the `progress.log` lines:

```
PROJECT_ROOT: /abs/path/to/project
RENDER_SCRIPT: /abs/path/to/skill/scripts/render-dashboard.sh
I18N_SCRIPT: /abs/path/to/skill/scripts/dashboard-i18n.py
CHECK_SCRIPT: /abs/path/to/skill/scripts/state-check.py
OPS:
1. task TASK-003-02 status=completed completed_at=2026-09-28T10:00:00Z
2. task TASK-003-03 status=blocked blocker.type=external blocker.summary=... blocker.waiting_on=... blocker.since=2026-09-28T10:05:00Z
3. item ITEM-003 status=in_progress
4. progress.log:
   TASK-003-02 completed; validation passed.
NOTE: batch of 4 ops from session 7
```

Supported ops: task status / notes / completed_at; set or clear a task `blocker`
(`blocker=none` clears it); item status; `archive <ITEM-ID>` for a terminal item (moves the full
record and writes the compact `terminal_summary` entry); `progress.log:` bullets.

The writer then runs, in order: the ops, `state-check.py --fix` (metadata counts and the item
rollup), the translation refresh when `DASHBOARD_LANGUAGE` is present, `state-check.py` (which
must exit 0), and finally the renderer. **Item rollup** is therefore automatic: an item becomes
`blocked` when every non-terminal task is blocked, and returns to `in_progress` when one is no
longer blocked — the main agent does not track that by hand.

The subagent replies with exactly one line:
`STATE-WRITER OK <n> ops; dashboard rendered` or
`STATE-WRITER ERROR <step>: <message>`.

### Blocked tasks: classify the blocker (D6, D7, D14)

When a task becomes `blocked`, the update request must carry a `blocker` object:

| Type | Required | Use when |
|---|---|---|
| `needs_user` | `question` (+ optional `default_action`) | only the user can answer or decide |
| `external` | `waiting_on` | an outside system, person, or event must act first |

Both carry `type`, `summary`, `since`. Clear the blocker with `blocker=none` when the task
leaves `blocked` — a blocker must never survive on a non-blocked task.

For `needs_user`: **stop and ask the user**. `default_action` is a suggestion shown on the
dashboard; never continue on it automatically (D7).

Legacy data (D14): a `blocked` task with no `blocker` renders under "需要你处理" as 未分类 with
its `notes`. Do not migrate in bulk — the next time the user says which kind it is, add the
`blocker` in that update request.

### If the state writer fails (D11)

Detection signals:

- Claude Code: subagent not found, or the Agent/Task call fails to spawn.
- Codex CLI: `spawn_agent` fails with `unknown agent_type 'task-relay-state-writer'`, the model
  is unavailable, or the spawn errors. If `spawn_agent` exposes **no** `agent_type` parameter,
  no agent definition is installed.
- Either CLI: a `STATE-WRITER ERROR <step>: <message>` reply, or a non-zero render exit.

Then, in order:

1. **Stop.** Do not start the next task. Do not write the state files by hand yet.
2. Report the failed step, the exact error, and the fix — usually
   `bash {SKILL_SCRIPTS_PATH}/install-state-writer.sh`, then restart the CLI.
3. Offer exactly three choices and wait for the user:
   - ① retry the subagent after the fix;
   - ② the main agent writes the state itself this time and runs the render script;
   - ③ write nothing and end the session.

## Step 4: Validation

**Rule**: only mark a task `completed` if ALL its `validation_steps` pass.
**Rule**: only mark an item `completed` if ALL tasks are `completed` or `cancelled` AND all item-level `validation_steps` pass.

For each validation entry:

1. Execute the step exactly as written.
2. Document the result (pass / fail).
3. If ANY step fails:
   - Do NOT mark `completed`.
   - Fix and re-validate, OR
   - Mark as `blocked` with detailed notes.

### Example validation execution

```
Task TASK-001-02 validation_steps:
  "Run npm test and verify all tests pass"
  "Start the app and verify /login loads"

✅ npm test - All 24 tests passed
✅ Navigate to /login - Page loads correctly
→ All task validations passed → mark TASK-001-02 completed
```

## Step 5: Item Completion and Archival

### 5.1 Item completion rollup check

Before marking an item `completed`, verify:
1. Every task is `completed` or `cancelled`.
2. Every `cancelled` task has a non-empty `notes` field.
3. Every item-level `validation_steps` entry passes.

If any check fails, do NOT mark completed. Fix or mark `blocked`.

### 5.2 Whole-item `cancelled` procedure

If the user wants to cancel an entire item:
1. **Require user confirmation** (cancelling work is consequential).
2. Set item `status: cancelled`; fill `notes` with reason.
3. Task cascade: set every non-`completed` task to `cancelled` with `notes: "Item ITEM-XXX cancelled: <reason>"`. Leave already-`completed` tasks as-is (preserve audit trail).
4. Proceed to archival (step 5.3).

### 5.3 Terminal archival (completed or cancelled)

Run this for any item that just became terminal (`completed` or `cancelled`):

> **Send this as one update request** (§ Step 3.5): `archive <ITEM-ID> status=... completed_at=...`
> plus the `progress.log:` bullets for the session. The state writer performs steps A–D below and
> re-renders `00-current/dashboard.html`. Do not edit the three state files by hand while the
> subagent is available.

```json
// Step A: Append the FULL item record to 00-current/item-list-archive.json
{
  "id": "ITEM-003",
  "category": "implementation",
  "description": "Implement user login page",
  "priority": 3,
  "validation_steps": ["Run npm test...", "Navigate to /login..."],
  "status": "completed",
  "completed_at": "2025-12-10T14:45:00Z",
  "notes": "All tests passing, validated in dev environment",
  "working_dir": "20-working/ITEM-003",
  "files": ["20-working/ITEM-003/log.md"],
  "tasks": [
    {
      "id": "TASK-003-01", "description": "...", "status": "completed",
      "validation_steps": ["..."], "completed_at": "...", "notes": ""
    }
  ]
}

// Step B: REMOVE the full record from items[] in item-list.json

// Step C: ADD a compact entry to terminal_summary in item-list.json
{
  "terminal_summary": [
    {
      "id": "ITEM-003",
      "description": "Implement user login page",
      "status": "completed",
      "completed_at": "2025-12-10T14:45:00Z"
    }
  ]
}

// Step D: Update metadata
{
  "metadata": {
    "total_items": 15,
    "completed": 4,     // or cancelled++
    "in_progress": 0,
    "blocked": 0,
    "pending": 10,
    "cancelled": 1      // only if item was cancelled
  }
}
```

**For blocked items** — keep in `items[]` (no archival):

```json
{
  "id": "ITEM-005",
  "status": "blocked",
  "completed_at": null,
  "notes": "Blocked: Waiting for API credentials from user."
}
```

### 5.4 Update progress.log

Append a new session entry:

```markdown
### Session N - 2025-12-10 14:00
**Phase**: Execution
**Duration**: ~45 minutes
**Agent**: [Claude Code / ChatGPT / Gemini / etc.]

**Item**: ITEM-003 - Implement user login page
**Status**: ✅ Completed

**Tasks completed this session**: TASK-003-01, TASK-003-02
**Work Performed**:
1. Created login.tsx component with form validation
2. Integrated with authentication API
3. Added error handling for invalid credentials
4. Implemented redirect to dashboard on success

**Validation Results**:
- ✅ npm test - All 24 tests passed
- ✅ Navigate to /login - Page loads correctly
- ✅ Submit valid credentials - Redirects to dashboard

**State Updates**:
- ITEM-003: in_progress → completed (archived to item-list-archive.json)
- terminal_summary: added ITEM-003 (status: completed)
- metadata.completed: 3 → 4

**Item Log**: [[20-working/ITEM-003/log.md]]

**Next Session Recommendation**: ITEM-004 - Implement password reset flow

---
```

### 5.5 Commit changes (if using Git)

```bash
git add 00-current/item-list.json 00-current/item-list-archive.json \
        00-current/progress.log 20-working/ITEM-003/
git commit -m "Complete ITEM-003: Implement user login page

- Created login component with validation
- Integrated authentication API
- All tests passing"
```

## Step 6: Session Summary

Report to user:

```markdown
✅ **Session Complete**

**Item**: ITEM-003 - Implement user login page
**Status**: Completed
**Tasks**: TASK-003-01 ✅, TASK-003-02 ✅
**Validation**: All checks passed

**Progress**:
- Completed: 4/15 (26.7%)
- Remaining: 11 items
- Blocked: 0 items

**Files Updated**:
- 00-current/item-list.json
- 00-current/item-list-archive.json
- 00-current/progress.log
- 00-current/dashboard.html (re-rendered by the state writer)
- 20-working/ITEM-003/log.md

**Next Session**: Start with ITEM-004 - Implement password reset flow

📖 See 00-current/progress.log for session history
📊 Open 00-current/dashboard.html for the visual status page
📁 See 20-working/ITEM-003/ for item artifacts
```

## Inserting Items During Execution

Users may need to add urgent items mid-assignment.

**Procedure**:

1. Determine the next item ID (highest existing in both `items` and `terminal_summary`, +1).
2. Create the item with full v1.3 schema fields including `tasks[]` (≥1 task).
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
  "priority": 48,
  "validation_steps": [
    "Login no longer enters redirect loop",
    "Session token is set correctly after login"
  ],
  "status": "pending",
  "completed_at": null,
  "notes": "Discovered during ITEM-012.",
  "working_dir": null,
  "files": [],
  "tasks": [
    {
      "id": "TASK-048-01",
      "description": "Identify root cause of redirect loop in auth middleware",
      "status": "pending",
      "validation_steps": ["Root cause documented in ITEM-048/log.md"],
      "completed_at": null,
      "notes": ""
    },
    {
      "id": "TASK-048-02",
      "description": "Apply fix and verify session token is set correctly",
      "status": "pending",
      "validation_steps": ["Login no longer loops", "Session token valid after login"],
      "completed_at": null,
      "notes": ""
    }
  ]
}
```

```json
{ "next_override": "ITEM-048" }
```
