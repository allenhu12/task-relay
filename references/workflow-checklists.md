# Task Relay Workflow Checklists

This document provides detailed checklists for both initialization and execution phases.

## Initialization Phase Checklist

### Step 0: Folder Structure Creation
- [ ] Create project directory (if needed)
- [ ] Create 9-zone folder structure:
  - [ ] `00-current/` - State files (the truth)
  - [ ] `05-plans/` - Implementation plans, design docs, planning artifacts
  - [ ] `10-reference/` - Reference materials
  - [ ] `20-working/` - Work in progress
  - [ ] `30-logs/` - Session logs
  - [ ] `50-drafts/` - Long-form drafts toward final deliverables
  - [ ] `60-handoffs/` - Handoff packages (session-to-session or external)
  - [ ] `80-issues/` - Backlog (on-request)
  - [ ] `90-archive/` - Obsolete files
- [ ] Copy AGENTS.template.md to project root as `AGENTS.md`
- [ ] Copy user-decision.template.md to `00-current/user-decision.md`

### Step 1: Requirements Analysis
- [ ] Read user's assignment description thoroughly
- [ ] Ask clarifying questions about scope
  - [ ] What is the final deliverable?
  - [ ] Are there specific requirements or constraints?
  - [ ] What does "done" look like?
- [ ] Understand the domain (code/research/writing/data/etc.)
- [ ] Identify any dependencies or prerequisites

### Step 2: Item Decomposition
- [ ] Break down assignment into discrete items
- [ ] Apply appropriate granularity:
  - [ ] Large project: 50-100+ items
  - [ ] Medium project: 20-50 items
  - [ ] Small task: 5-20 items
- [ ] For each item, ensure:
  - [ ] Independently completable
  - [ ] Has clear validation steps (at least 1)
  - [ ] Description starts with action verb
  - [ ] Validation steps are objective (pass/fail)
- [ ] Assign priorities (dependencies first)
- [ ] Group items by category

### Step 3: State File Creation
- [ ] Copy item-list.template.json to `./00-current/item-list.json`
- [ ] Fill in assignment name and description
- [ ] Add all items with proper structure
- [ ] Set all items to status: "pending"
- [ ] Calculate and set metadata counts
- [ ] Set created and last_updated timestamps
- [ ] Copy progress.template.log to `./00-current/progress.log`
- [ ] Add Session 1 initialization entry
- [ ] Copy init.template.sh or init.template.md to project root
- [ ] Customize initialization script for project
- [ ] Create session log in `./30-logs/` with YAML frontmatter:
  - [ ] Use naming: `000_YYYY-MM-DD_<agent>_session-log-initialization.md`
  - [ ] Include Type: session-log, Status: Active, Author, Created

### Step 4: Baseline Verification
- [ ] Verify 9-zone folder structure exists
- [ ] Validate JSON syntax in `00-current/item-list.json`
- [ ] Run init script to test environment setup
- [ ] Verify all items have required fields
- [ ] Verify metadata counts are correct
- [ ] Check that all validation_steps are clear
- [ ] Verify `00-current/user-decision.md` exists (read-only for agents)

### Step 5: Handoff Documentation
- [ ] Update `00-current/progress.log` with Session 1 summary
- [ ] Ensure session log saved in `30-logs/`
- [ ] List all created artifacts
- [ ] Recommend first item to work on
- [ ] Report initialization completion to user
- [ ] Provide clear instructions for next session
- [ ] Remind user about `00-current/user-decision.md` for their notes

## Execution Phase Checklist

### Start of Session
- [ ] Read `AGENTS.md` for workflow instructions
- [ ] Read `00-current/progress.log` (last 100 lines only)
  - [ ] Understand what was done previously
  - [ ] Note any blockers
  - [ ] Review recommendations
- [ ] Read `00-current/item-list.json` (active items + compact completed summaries)
  - [ ] Check overall progress (metadata)
  - [ ] Identify pending items
  - [ ] Check for blocked items
  - [ ] Do NOT read `00-current/item-list-archive.json` (only on demand for completed item details)
- [ ] Read `00-current/user-decision.md` for user context (DO NOT MODIFY)
- [ ] Run init.sh or follow init.md
  - [ ] Verify environment initialized successfully
  - [ ] Run health checks
  - [ ] Confirm no regressions

### Item Selection
- [ ] Check `next_override` field first
  - [ ] If set to a valid pending item ID, select that item
  - [ ] Clear `next_override` to `null` after selection
  - [ ] If override target is invalid (not found, blocked, completed), clear and fall through
- [ ] If no override: select EXACTLY ONE pending item by priority (lowest number first)
- [ ] Skip blocked items
- [ ] Consider dependencies (check notes)
- [ ] Update item status: pending → in_progress
- [ ] Update metadata.in_progress count (+1)
- [ ] Update metadata.pending count (-1)

### Inserting Items Mid-Execution (when user requests)
- [ ] Determine next item ID (highest existing ID + 1, check both `items` and `completed_summary`)
- [ ] Create full item record (id, category, description, priority, validation_steps, status: pending)
- [ ] Add to `items` array in `item-list.json`
- [ ] Update metadata: total_items (+1), pending (+1)
- [ ] If item should be handled first: set `next_override` to the new item ID
- [ ] Log insertion reason in `progress.log`

### Execution
- [ ] Read item description carefully
- [ ] Review validation steps (know how to verify)
- [ ] Perform the work
- [ ] Stay scoped (resist scope creep)
- [ ] Do NOT work on other items

### Validation (CRITICAL)
- [ ] Execute EVERY validation step
- [ ] Document each result (pass/fail)
- [ ] If ANY validation fails:
  - [ ] Do NOT mark completed
  - [ ] Either fix and re-validate
  - [ ] Or mark as blocked with detailed notes
- [ ] Only proceed if ALL validations pass

### State Update (MANDATORY)
- [ ] If item completed:
  - [ ] Append full item record to `00-current/item-list-archive.json`
  - [ ] Remove full record from `items` array in `00-current/item-list.json`
  - [ ] Add compact entry (id, description, completed_at) to `completed_summary` in `00-current/item-list.json`
- [ ] If item blocked: update status and notes in place in `00-current/item-list.json`
- [ ] Set completed_at timestamp (if completed)
- [ ] Add notes if blocked or noteworthy
- [ ] Update metadata counts:
  - [ ] completed (+1 if completed)
  - [ ] in_progress (back to 0)
  - [ ] blocked (+1 if blocked)
  - [ ] pending (-1 if moved from pending)
- [ ] Update assignment.last_updated timestamp
- [ ] Append session entry to `00-current/progress.log`:
  - [ ] Session number and timestamp
  - [ ] Phase (execution)
  - [ ] Item ID and description
  - [ ] Work performed summary
  - [ ] Validation results (detailed)
  - [ ] State updates made
  - [ ] Wiki link to session log in 30-logs/
  - [ ] Next session recommendation
- [ ] Create detailed session log in `30-logs/`:
  - [ ] Use naming: `XXX_YYYY-MM-DD_<agent>_session-log-<item>.md`
  - [ ] Include YAML frontmatter (Type, Status, Author, Created)
  - [ ] Full validation results
  - [ ] Wiki links to related documents
- [ ] If using Git:
  - [ ] Stage `00-current/` and `30-logs/`
  - [ ] Stage any code changes
  - [ ] Commit with descriptive message
  - [ ] Reference item ID in commit

### End of Session
- [ ] Report session completion to user
- [ ] Summarize what was accomplished
- [ ] Show updated progress statistics
- [ ] Recommend next item
- [ ] Provide clear handoff

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

### If validation fails:
- [ ] Do NOT mark as completed
- [ ] Identify specific failures
- [ ] Decide: fix now or mark blocked?
- [ ] If fixing:
  - [ ] Make necessary changes
  - [ ] Re-run ALL validation steps
  - [ ] Only mark completed when all pass
- [ ] If blocking:
  - [ ] Mark status as blocked
  - [ ] Add detailed notes about why
  - [ ] Explain what's needed to unblock
  - [ ] Update metadata counts

### If multiple items in progress (ERROR):
- [ ] Find all in_progress items
- [ ] Decide which ONE to continue
- [ ] Mark others back to pending
- [ ] Update metadata counts
- [ ] Document the mistake in progress.log
- [ ] Return to one-item-per-session discipline

### If state files corrupted:
- [ ] If using Git: `git checkout -- 00-current/item-list.json 00-current/progress.log`
- [ ] If no Git:
  - [ ] Check `30-logs/` for session logs to help reconstruct state
  - [ ] Review recent work to understand state
  - [ ] Recreate `00-current/item-list.json` as accurately as possible
  - [ ] Mark uncertain items as pending
  - [ ] Document incident in `00-current/progress.log`
  - [ ] Verify metadata counts

### If blocker encountered:
- [ ] Mark item as blocked immediately
- [ ] Document blocker in notes field
- [ ] Explain what's needed to unblock
- [ ] Update progress.log with blocker details
- [ ] Select different item to work on
- [ ] Address blocker when possible

## Quality Checks

Before ending ANY session, verify:
- [ ] Exactly 0 or 1 items are in_progress (1 during session, 0 at end)
- [ ] Metadata counts match actual item statuses (items array + completed_summary count)
- [ ] All completed items have completed_at timestamps
- [ ] All completed items have validation results documented
- [ ] `00-current/progress.log` has entry for this session
- [ ] Session log created in `30-logs/` with YAML frontmatter
- [ ] No item definition fields were modified
- [ ] `00-current/user-decision.md` was NOT modified (read-only for agents)
- [ ] Next recommendation is clear

## Anti-Pattern Warnings

Watch out for these common mistakes:

⚠️ **Scope Creep**: Working on more than assigned item
- Check: Did I only work on the selected item?

⚠️ **Validation Shortcuts**: Skipping validation steps
- Check: Did I run ALL validation steps?

⚠️ **Vague Documentation**: Unclear progress notes
- Check: Can someone else understand what I did?

⚠️ **Ignoring Blockers**: Marking blocked items as completed
- Check: Did all validations actually pass?

⚠️ **Batch Updates**: Not updating state until multiple items done
- Check: Did I update state files THIS session?

⚠️ **Modifying User Decisions**: Editing `00-current/user-decision.md`
- Check: Did I accidentally modify the user's decision file?
- This file is READ-ONLY for agents - NEVER modify it!

⚠️ **Skipping Session Logs**: Not creating detailed logs in `30-logs/`
- Check: Did I create a session log with proper naming and YAML frontmatter?

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
- [ ] Generate next ITEM-XXX ID (check `items` + `completed_summary`)
- [ ] Create item in `item-list.json` with full fields
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
