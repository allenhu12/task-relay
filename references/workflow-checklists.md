# Task Relay Workflow Checklists

This document provides detailed checklists for both initialization and execution phases.

## Initialization Phase Checklist

### Step 0: Folder Structure Creation
- [ ] Create project directory (if needed)
- [ ] Create 9-zone folder structure (NO 30-logs/ in v1.3):
  - [ ] `00-current/` - State files (the truth)
  - [ ] `05-plans/` - Implementation plans, design docs, planning artifacts
  - [ ] `10-reference/` - Reference materials
  - [ ] `20-working/` - Per-item workspaces (subfolders created lazily)
  - [ ] `50-drafts/` - Long-form drafts toward final deliverables
  - [ ] `60-handoffs/` - Handoff packages (session-to-session or external)
  - [ ] `80-issues/` - Backlog (on-request)
  - [ ] `90-archive/` - Obsolete files; `90-archive/progress-log/` for rotated logs
- [ ] Copy AGENTS.template.md to project root as `AGENTS.md`
- [ ] Copy user-decision.template.md to `00-current/user-decision.md`
- [ ] Do **NOT** create any `20-working/<ITEM-ID>/` subfolders yet (lazy creation)

### Step 1: Requirements Analysis
- [ ] Read user's assignment description thoroughly
- [ ] Ask clarifying questions about scope
  - [ ] What is the final deliverable?
  - [ ] Are there specific requirements or constraints?
  - [ ] What does "done" look like?
- [ ] Understand the domain (code/research/writing/data/etc.)
- [ ] Identify any dependencies or prerequisites

### Step 2: Item Decomposition (opt-in only)
- [ ] Only decompose if the user explicitly asks ("generate items", "decompose", etc.)
- [ ] Break down assignment into discrete items
- [ ] Apply decomposition rules (six rules — see `references/decomposition-rules.md`):
  - [ ] One idea per item
  - [ ] Functionality and tests are separate items
  - [ ] Ordering guarantees compilability
  - [ ] Every item cites why it comes here
  - [ ] Every item is session-sized (~one session)
  - [ ] Every item has ≥1 task in `tasks[]`
- [ ] Apply appropriate granularity:
  - [ ] Large project: 30–80 items
  - [ ] Medium project: 10–30 items
  - [ ] Small task: 3–10 items
- [ ] For each item, ensure:
  - [ ] Independently completable in one session
  - [ ] Has ≥1 item-level `validation_steps`
  - [ ] Description starts with action verb
  - [ ] Has `tasks[]` with ≥1 task; each task has `validation_steps`
  - [ ] `working_dir: null`, `files: []` at creation
- [ ] Assign priorities (dependencies first)
- [ ] Group items by category

### Step 3: State File Creation
- [ ] Copy item-list.template.json to `./00-current/item-list.json`
- [ ] Fill in assignment name and description
- [ ] Add all items with proper structure (including `tasks[]`, `working_dir: null`, `files: []`)
- [ ] Set all items to status: "pending"; all tasks to status: "pending"
- [ ] Calculate and set metadata counts (including `cancelled: 0`)
- [ ] Set `terminal_summary: []` (not `completed_summary`)
- [ ] Set created and last_updated timestamps
- [ ] Copy progress.template.log to `./00-current/progress.log`
- [ ] Add Session 1 initialization entry to progress.log
- [ ] Copy init.template.sh or init.template.md to project root
- [ ] Customize initialization script for project

### Step 4: Baseline Verification
- [ ] Verify 9-zone folder structure exists (no 30-logs/)
- [ ] Validate JSON syntax in `00-current/item-list.json`
- [ ] Verify `terminal_summary` (not `completed_summary`) is present
- [ ] Verify `metadata.cancelled` field exists
- [ ] Run init script to test environment setup
- [ ] Verify all items have required fields including `tasks[]`
- [ ] Verify metadata counts are correct (sum to total_items)
- [ ] Check that all `validation_steps` are clear (item-level and task-level)
- [ ] Verify `00-current/user-decision.md` exists (read-only for agents)

### Step 5: Handoff Documentation
- [ ] Update `00-current/progress.log` with Session 1 summary
- [ ] List all created artifacts
- [ ] Recommend first item to work on
- [ ] Report initialization completion to user
- [ ] Provide clear instructions for next session
- [ ] Remind user about `00-current/user-decision.md` for their notes

## Execution Phase Checklist

### Start of Session — State Recovery
- [ ] Read `AGENTS.md` for workflow instructions
- [ ] Read `00-current/progress.log` (last 100 lines only)
  - [ ] Understand what was done previously
  - [ ] Note any blockers
  - [ ] Note any handoff instructions (overflow mid-item)
  - [ ] Review recommendations
- [ ] Read `00-current/item-list.json` (active items with tasks[] + compact terminal summaries)
  - [ ] Check overall progress (metadata)
  - [ ] Identify pending items and their tasks
  - [ ] Check for blocked items and blocked tasks
  - [ ] Do NOT read `00-current/item-list-archive.json` (only on demand for terminal item details)
- [ ] Read `00-current/user-decision.md` for user context (DO NOT MODIFY)
- [ ] Run init.sh or follow init.md
  - [ ] Verify environment initialized successfully
  - [ ] Run health checks
  - [ ] Confirm no regressions

### Selection Gate (read-only + confirm before action)

**Resume case** (item already `in_progress`):
- [ ] Do NOT run item selection — item is already chosen
- [ ] If a task is `in_progress`: propose resuming that specific task
- [ ] If no task is `in_progress`: list remaining `pending` tasks and ask user to choose
- [ ] Wait for user response before marking anything

**Selection case** (no item `in_progress`):
- [ ] Check `next_override` field first
  - [ ] If set to a valid pending item ID, identify that as candidate
  - [ ] Clear `next_override` to `null` ONLY after user confirms
  - [ ] If override target is invalid (not found, blocked, completed), clear and fall through
- [ ] If no override: identify EXACTLY ONE pending item by priority (lowest number first)
- [ ] NEVER pick a blocked item; if all pending are blocked → report "nothing actionable"
- [ ] **STOP: present candidate to user and wait for confirmation**
- [ ] On confirm:
  - [ ] Mark item `in_progress`; update `metadata.in_progress` (+1), `metadata.pending` (-1)
  - [ ] Create `20-working/<ITEM-ID>/` folder if it does not exist
  - [ ] Initialize `20-working/<ITEM-ID>/log.md` from `assets/session-log.template.md`
  - [ ] Set `working_dir: "20-working/<ITEM-ID>"` in item-list.json
  - [ ] Clear `next_override` (if it was the trigger)

### Inserting Items Mid-Execution (when user requests)
- [ ] Determine next item ID (highest existing ID + 1, check both `items` and `terminal_summary`)
- [ ] Create full item record including `tasks[]` (≥1 task), `working_dir: null`, `files: []`
- [ ] Add to `items` array in `item-list.json`
- [ ] Update metadata: total_items (+1), pending (+1)
- [ ] If item should be handled first: set `next_override` to the new item ID
- [ ] Log insertion reason in `progress.log`

### Task Loop (user-driven — Option B)
- [ ] List remaining `pending` tasks in the current item
- [ ] **Ask user which task to run next** — do NOT auto-pick
- [ ] Wait for user selection
- [ ] Mark selected task `in_progress`; flush `item-list.json`
- [ ] Perform the work for that task
- [ ] Stay scoped (resist scope creep; do not work on other items or tasks)
- [ ] Run ALL task-level `validation_steps`
- [ ] Mark task `completed` / `blocked` / `cancelled`; flush `item-list.json`
- [ ] Append task result to `20-working/<ITEM-ID>/log.md`
- [ ] Update `files[]` in item-list.json if new files were created
- [ ] **STOP: go back to top of task loop** — present remaining tasks, ask again

### Overflow / Mid-Item Session End
- [ ] If context fills before item is done:
  - [ ] Ensure current task state is flushed (in_progress or completed in JSON)
  - [ ] Append handoff note to `00-current/progress.log`:
    - [ ] Item ID, which task is in_progress, which tasks remain
    - [ ] Explicit note: "Resume with TASK-XXX-YY next session"
  - [ ] Leave item `in_progress` (do NOT clear)
  - [ ] Leave `in_progress` task as `in_progress` (do NOT clear)

### Item Completion Rollup
- [ ] Check: every task is `completed` or `cancelled`
- [ ] Check: every `cancelled` task has a non-empty `notes` field
- [ ] Check: every item-level `validation_steps` entry passes
- [ ] Only proceed if ALL checks pass; otherwise fix or mark blocked

### Whole-Item Cancellation (when user requests)
- [ ] Require explicit user confirmation
- [ ] Set item `status: cancelled`; fill `notes` with reason
- [ ] Task cascade: set every non-`completed` task to `cancelled` with notes referencing item cancellation
- [ ] Leave already-`completed` tasks as `completed`
- [ ] Proceed to terminal archival

### Terminal Archival (completed or cancelled)
- [ ] Append full item record to `00-current/item-list-archive.json` (include `tasks[]`, `working_dir`, `files`)
- [ ] Remove full record from `items` array in `00-current/item-list.json`
- [ ] Add compact entry to `terminal_summary` (with `status: completed | cancelled`)
- [ ] Set `completed_at` timestamp on item
- [ ] Update metadata counts:
  - [ ] `completed` (+1 if completed) or `cancelled` (+1 if cancelled)
  - [ ] `in_progress` → 0
  - [ ] `pending` (already decremented when item went in_progress)
- [ ] Update `assignment.last_updated` timestamp
- [ ] Append session entry to `00-current/progress.log` (see format in execution-phase.md)
- [ ] If using Git:
  - [ ] Stage `00-current/` and `20-working/<ITEM-ID>/`
  - [ ] Stage any code changes
  - [ ] Commit with descriptive message referencing item ID

### End of Session
- [ ] Report session completion to user
- [ ] Summarize what was accomplished (tasks completed, item status)
- [ ] Show updated progress statistics (use metadata counts)
- [ ] Recommend next item or task, or note "nothing actionable"
- [ ] Provide clear handoff (especially if mid-item)

## Common Validation Patterns

### Code Implementation
- [ ] All tests pass
- [ ] Code compiles/runs without errors
- [ ] Functionality works as specified
- [ ] Edge cases handled
- [ ] Code reviewed (if applicable)

### Documentation
- [ ] Document created at specified path
- [ ] All required sections included
- [ ] Information is accurate
- [ ] Examples provided (if needed)
- [ ] Reviewed for clarity

### Testing
- [ ] Test cases cover requirements
- [ ] All tests pass
- [ ] Coverage meets threshold
- [ ] Edge cases tested
- [ ] Tests are repeatable

### Setup/Configuration
- [ ] Installation completes without errors
- [ ] Configuration files created
- [ ] Services start successfully
- [ ] Health checks pass
- [ ] Dependencies verified

## Error Recovery Checklist

### If task validation fails:
- [ ] Do NOT mark task as completed
- [ ] Identify specific failures
- [ ] Decide: fix now or mark blocked?
- [ ] If fixing:
  - [ ] Make necessary changes
  - [ ] Re-run ALL task validation steps
  - [ ] Only mark completed when all pass
- [ ] If blocking:
  - [ ] Mark task status as blocked
  - [ ] Add detailed notes about why
  - [ ] Explain what's needed to unblock
  - [ ] Flush item-list.json; pick another task or end session

### If multiple items in progress (ERROR):
- [ ] Find all in_progress items
- [ ] Decide which ONE to continue
- [ ] Mark others back to pending (reset tasks to pending too)
- [ ] Update metadata counts
- [ ] Document the mistake in progress.log
- [ ] Return to one-item-per-session discipline

### If state files corrupted:
- [ ] If using Git: `git checkout -- 00-current/item-list.json 00-current/progress.log`
- [ ] If no Git:
  - [ ] Check `20-working/<ITEM-ID>/log.md` files for item history
  - [ ] Recreate `00-current/item-list.json` as accurately as possible
  - [ ] Mark uncertain items as pending
  - [ ] Document incident in `00-current/progress.log`
  - [ ] Verify metadata counts

### If blocker encountered (task or item):
- [ ] Mark the task (or item) as blocked immediately
- [ ] Document blocker in notes field
- [ ] Explain what's needed to unblock
- [ ] Flush item-list.json
- [ ] For a blocked task: pick another task in the same item (if available) or end session
- [ ] For a blocked item: select a different item to work on
- [ ] Address blocker when possible

## Quality Checks

Before ending ANY session, verify:
- [ ] Exactly 0 or 1 items are in_progress (1 during session, 0 at session end — unless mid-item overflow)
- [ ] At most 1 task is in_progress within the in_progress item
- [ ] Metadata counts match actual item statuses (items array + terminal_summary count = total_items)
- [ ] All terminal items have `completed_at` timestamps
- [ ] All `cancelled` items and tasks have non-empty `notes`
- [ ] `00-current/progress.log` has entry for this session
- [ ] `20-working/<ITEM-ID>/log.md` updated for this session (execution sessions only)
- [ ] No item definition fields were modified (id, description, priority, validation_steps, tasks[].id, tasks[].description)
- [ ] `00-current/user-decision.md` was NOT modified (read-only for agents)
- [ ] Next recommendation is clear

## Anti-Pattern Warnings

Watch out for these common mistakes:

⚠️ **Auto-advancing tasks**: Agent picks the next task without asking the user
- Check: Did I stop after each task and ask which task to run next?

⚠️ **Auto-executing without confirm**: Agent marks item `in_progress` without user approval
- Check: Did I present the candidate item and wait for confirmation?

⚠️ **Scope Creep**: Working on more than assigned item
- Check: Did I only work on the selected item?

⚠️ **Validation Shortcuts**: Skipping validation steps
- Check: Did I run ALL task validation steps AND all item-level validation steps before marking item completed?

⚠️ **Skipping task flush**: Not writing task status to JSON immediately
- Check: Did I flush item-list.json after every task status change (not just at item completion)?

⚠️ **Vague Documentation**: Unclear progress notes
- Check: Can someone else understand what I did and which tasks were completed?

⚠️ **Modifying User Decisions**: Editing `00-current/user-decision.md`
- Check: Did I accidentally modify the user's decision file?
- This file is READ-ONLY for agents - NEVER modify it!

⚠️ **Missing 30-logs/ session log**: Creating session logs in 30-logs/ (removed in v1.3)
- Check: Did I update `20-working/<ITEM-ID>/log.md` instead?

## Issues Backlog Checklists (80-issues/)

### Capture an Issue
- [ ] User explicitly requests to log an issue/idea
- [ ] Determine next sequence number (`ls 80-issues/ | wc -l` + 1)
- [ ] Create file: `<seq>_issue_<meaningful-name>.md`
- [ ] Fill frontmatter: Type: issue, Status: open, Priority, Category, Created
- [ ] Write description and context (which item was being worked on)
- [ ] Resume current work immediately

### Review Backlog
- [ ] User explicitly requests to review backlog
- [ ] Read frontmatter of all `.md` files in `80-issues/`
- [ ] Filter to `Status: open` issues
- [ ] Present summary table (file, priority, category, title)
- [ ] Wait for user decision per issue: promote, dismiss, defer, or leave open

### Promote Issue to Item
- [ ] Read full issue file
- [ ] Generate next ITEM-XXX ID (check `items` + `terminal_summary`)
- [ ] Create item in `item-list.json` with full fields including ≥1 task
- [ ] Ask user for `validation_steps` if not derivable from issue
- [ ] Update metadata: total_items (+1), pending (+1)
- [ ] If user wants it next: set `next_override` to new item ID
- [ ] Update issue frontmatter: Status → promoted, Promoted_to → ITEM-XXX
- [ ] Log promotion in `progress.log`

### Dismiss Issue
- [ ] Update issue frontmatter: Status → dismissed
- [ ] Add reason in Notes section
- [ ] File stays in `80-issues/`

### Defer Issue
- [ ] Update issue frontmatter: Status → deferred
- [ ] Optionally add target date or condition in Notes
- [ ] File stays in `80-issues/`
