# Task Relay User Guide

A complete guide to using the Task Relay skill for managing complex, multi-session assignments with AI agents.

> **What's new in v1.3.** Tasks-under-items, per-item workspaces, and deep-adapter removal:
>
> 1. **Tasks under items.** Every item now has `tasks[]` (≥1). Tasks are the checkpoint/resumability mechanism — they let sessions overflow gracefully without losing progress. Task IDs are `TASK-NNN-MM`; order is user-chosen, not sequential.
> 2. **Per-item workspaces.** `20-working/<ITEM-ID>/` is created lazily when an item first goes `in_progress`. Each item's detailed log lives at `20-working/<ITEM-ID>/log.md`. The folder is stable (never auto-moved on completion).
> 3. **`30-logs/` removed.** Session logs now live in the per-item folder. Non-item sessions (init, batch ingest, status checks) log to `progress.log` only. Rotated progress logs go to `90-archive/progress-log/`.
> 4. **`/task-relay deep` removed.** The deep-task adapter is gone. Good decomposition (session-sized items with tasks) replaces it as the overflow mechanism.
> 5. **Schema changes.** `completed_summary` → `terminal_summary` (with `status: completed|cancelled`); `metadata.cancelled` added; `cancelled` is a valid status for items and tasks (replaces `abandoned`).
> 6. **Selection gate.** Item selection now requires explicit user confirmation before the item is marked `in_progress`. Task advancement also requires explicit user selection after each task.
>
> See the "v1.2 → v1.3 migration" note in SKILL.md Troubleshooting for a validation checklist.

> **What's new in v1.2.** Two parts:
>
> 1. **Cleanup**: `SKILL.md` shrunk from ~1,290 → ~520 lines by extracting full phase procedures, state-file specs, and issues-backlog workflows into `references/`. Five phantom top-level headings fixed (better routing). Shell utilities (`generate-manifest.sh`, `rotate-progress-log.sh`) moved from `assets/` to `scripts/`. Trigger phrases tightened.
> 2. **Structure & workflow**: folder structure expanded from 6 zones to **9 zones** — added `05-plans/` (implementation plans, design docs), `50-drafts/` (long-form drafts), `60-handoffs/` (handoff packages). `item-list.json` now starts **empty by default** at init — the agent only decomposes the project into items when you explicitly ask ("generate items", "decompose the project").
>
> Backwards-compatible: all v1.0/v1.1 projects keep working unchanged.

> **What's new in v1.1.** Tighter decomposition rules (one-idea-per-item, func/test separation, `complexity` flag, `rationale_for_order`); `[N=k]` frequency counters on memory entries; batch ingestion of pre-decomposed item lists; `/task-relay learn` retrospective; `/task-relay deep` adapter for routing complex items to the `deep-task` skill. See the "New in v1.1" section below.

## What is Task Relay?

Task Relay is a skill that enables AI agents (Claude, ChatGPT, Gemini, etc.) to work on complex projects across multiple sessions by maintaining persistent state in simple files. Think of it like a relay race where each session picks up exactly where the last one left off.

**The Problem It Solves**: AI agents have no memory between sessions. Without Task Relay, when you start a new conversation, the agent has forgotten everything about your project.

**The Solution**: A 9-zone folder structure with persistent state files:

```
Project/
├── AGENTS.md                  # Instructions for the AI agent
├── 00-current/               # THE TRUTH (State files)
│   ├── progress.log          # Single global narrative — every session appends here
│   ├── item-list.json        # Items (with tasks[]) + compact terminal summaries
│   ├── memory.md             # Captured insights ("remember this")
│   └── user-decision.md      # Your decisions (agent can't modify)
├── 05-plans/                 # THE BLUEPRINT (implementation plans, design docs)
├── 10-reference/             # Reference materials (includes 000_YYYY-MM-DD_spec.md)
├── 20-working/               # PER-ITEM WORKSPACES
│   └── ITEM-001/             # Created lazily when item first goes in_progress
│       └── log.md            # Detailed log for this item
├── 50-drafts/                # Long-form drafts toward a final deliverable
├── 60-handoffs/              # External handoff packages
├── 80-issues/                # Backlog (ideas, bugs, improvements)
├── 90-archive/               # Old/obsolete files; rotated progress logs at 90-archive/progress-log/
└── init.sh or init.md        # How to set up the environment
```

### Reference Spec File

During initialization, the agent creates `10-reference/000_YYYY-MM-DD_spec.md`. Edit this file with project-specific reference paths and URLs. The agent will read it at the start of every session and only open related documents when needed.

## Prerequisites

### Required
- An AI agent (Claude Code, ChatGPT, Gemini, or any LLM client)
- The `task-relay` skill installed (if using Claude Code)
- A text editor to view the state files

### Optional but Recommended
- Git for version control of state files
- A project directory to keep everything organized

## Quick Start: Your First Assignment

### Step 1: Start with a Clear Request

Tell your AI agent what you want to accomplish and ask it to use Task Relay:

```
I want to build a personal blog website with the following features:
- Homepage with recent posts
- Individual post pages
- About page
- Contact form
- Responsive design

Please use Task Relay to manage this project across multiple sessions.
```

### Step 2: Initialization Phase

The agent will:
1. Ask clarifying questions about your requirements
2. **By default, leave `item-list.json` empty.** The agent will only decompose the project into items if you explicitly ask ("generate items", "decompose the project", "fill in the item list"). Otherwise, you populate items later (manually, via a `task-input-batch.yaml`, or by asking the agent to decompose in a future session).
3. Create the 9-zone folder structure with state files:
   - `00-current/item-list.json` (starts with `items: []` unless you opted into decomposition)
   - `00-current/progress.log`
   - `00-current/user-decision.md` (for your notes)
   - `00-current/memory.md` (captured insights)
   - `05-plans/`, `50-drafts/`, `60-handoffs/`, `80-issues/`, `90-archive/`, `20-working/`, `10-reference/`
   - `10-reference/000_YYYY-MM-DD_spec.md` (reference paths and URLs)
   - `AGENTS.md` (instructions for the agent)
   - `init.sh` (or `init.md` for non-code projects)
   - Per-item `20-working/<ITEM-ID>/` folders are created lazily at execution time

**What you'll see** (when you DID opt into decomposition):
```
✅ Assignment initialized: Personal Blog Website
📋 Created 42 items in item-list.json
📝 Next session: Start with ITEM-001 - Initialize Next.js project
📁 Created 9-zone folder structure
📁 Files created:
   - AGENTS.md (agent instructions)
   - 00-current/item-list.json (track progress)
   - 00-current/progress.log (session history)
   - 00-current/user-decision.md (your notes)
   - 10-reference/000_YYYY-MM-DD_spec.md (reference paths and URLs)
   - init.sh (environment setup)
```

**What you'll see** (default — no decomposition opt-in):
```
✅ Assignment initialized: Personal Blog Website
📋 item-list.json starts empty — add items by asking me to decompose,
   hand-editing the file, or feeding a task-input-batch.yaml
📁 Created 9-zone folder structure
```

### Step 3: Review the Plan (Recommended)

Before continuing, review what the agent created:

```bash
# See all the items
cat 00-current/item-list.json | grep description

# Read recent progress context
tail -100 00-current/progress.log

# Check your decisions file (you can add notes here)
cat 00-current/user-decision.md

# Update reference paths and URLs
cat 10-reference/000_YYYY-MM-DD_spec.md
```

**If something doesn't look right**, tell the agent immediately:
```
The items look too granular. Can we combine ITEM-005 through ITEM-010
into fewer items?
```

### Step 4: First Work Session

When you're ready to start, tell the agent:

```
Continue working on the blog project
```

The agent will:
1. Read the state files to understand where things are, including only the last 100 lines of `00-current/progress.log`
2. Read `10-reference/000_YYYY-MM-DD_spec.md` for reference paths and URLs
3. Select the first pending item (ITEM-001)
4. Complete the work
5. Validate that it's done correctly
6. Update the state files
7. Tell you what was accomplished

**What you'll see**:
```
=� Resuming assignment...
<� Working on: ITEM-001 - Initialize Next.js project

[Agent does the work...]

 Item completed and validated
=� Updated progress files
= Next session: ITEM-002 - Set up Tailwind CSS
```

## Complete Workflow Example

Let's walk through a realistic multi-day project to see how Task Relay works in practice.

### Monday - Session 1: Initialization (30 minutes)

**You**: "Build a todo app with user authentication. Use Task Relay."

**Agent**: Creates initial structure
- Breaks project into 35 items
- Categories: Setup (3), Auth (8), Todo Features (15), Testing (9)
- Creates state files

**You**: Review items, ask questions
```
Why are there 8 items for auth? That seems like a lot.
```

**Agent**: Explains reasoning
```
Auth items include:
- User model and database
- Registration endpoint
- Login endpoint
- Password hashing
- JWT token generation
- Protected route middleware
- Email verification
- Password reset flow

Each is a discrete, testable piece. We can combine some if you prefer.
```

**You**: "That makes sense. Let's proceed."

### Monday - Session 2: First Work (45 minutes)

**You**: "Continue working on the todo app"

**Agent**:
```
=� Reading state files...
=� Progress: 0/35 items completed (0%)
<� Working on: ITEM-001 - Initialize Next.js project with TypeScript
```

**Agent**: Does the work
- Creates Next.js project
- Installs dependencies
- Configures TypeScript
- Sets up ESLint

**Agent**: Validates
```
**Validation Results**:
-  npm install completes without errors
-  Dev server starts on port 3000
-  TypeScript compiles with no errors
-  ESLint runs with no warnings
```

**Agent**: Updates state
```
 **Session Complete**

**Item**: ITEM-001 - Initialize Next.js project
**Status**: Completed

**Progress**: 1/35 (2.9%)
**Next Session**: ITEM-002 - Set up Tailwind CSS
```

**You**: End session, come back later

### Tuesday - Session 3: Continue (60 minutes)

**You**: "Continue the todo app"

**Agent**: Recovers state
```
=� Resuming from Session 2...
=� Progress: 1/35 items completed (2.9%)
<� Working on: ITEM-002 - Set up Tailwind CSS
```

**Agent**: Completes ITEM-002, validates, updates state

**Your project now has**:
-  ITEM-001: Next.js initialized
-  ITEM-002: Tailwind configured
- � ITEM-003: Database setup (next up)

### Wednesday - Session 4: Hit a Blocker (30 minutes)

**You**: "Continue"

**Agent**:
```
<� Working on: ITEM-003 - Set up PostgreSQL database
```

**Agent**: Encounters blocker
```
=� Item blocked

**Blocker**: Need database connection string.
Cannot complete setup without production database credentials.

**What's needed**:
- PostgreSQL host URL
- Database name
- Username and password
```

**You**: Provide credentials
```
Here are the DB credentials:
Host: db.example.com
Database: todo_app
User: app_user
Password: [password]
```

**Agent**: Unblocks and continues
```
 Unblocked ITEM-003
 Completed database setup
 All connection tests pass
```

### Friday - Session 8: Check Progress (5 minutes)

**You**: "What's our progress on the todo app?"

**Agent**:
```
=� **Todo App Progress Report**

**Overall**: 12/35 items completed (34%)

**By Category**:
- Setup: �������������������� 100% (3/3)
- Auth: �������������������� 50% (4/8)
- Todo Features: �������������������� 0% (0/15)
- Testing: �������������������� 25% (5/9)

**Recent Sessions**:
- Session 7: Completed ITEM-012 - JWT middleware
- Session 6: Completed ITEM-011 - Login endpoint
- Session 5: Completed ITEM-010 - Password hashing

**Blockers**: None
**Next Item**: ITEM-013 - Registration endpoint
**Estimated Remaining**: ~23 sessions (at current velocity)
```

**You**: "Great! Let's continue."

### Two Weeks Later - Session 30: Completion

**Agent**:
```
<� **Assignment Complete!**

**Total Items**: 35
**Completed**: 35 (100%)
**Sessions**: 30
**Total Time**: ~25 hours over 14 days

**Final Deliverables**:
- Full-stack todo app with Next.js
- User authentication (register, login, logout)
- CRUD operations for todos
- Responsive UI with Tailwind
- 98% test coverage
- Production-ready deployment config

All items validated and tested. Ready for deployment!
```

## Day-to-Day Usage Patterns

### Starting a Work Session

**Simple continuation**:
```
Continue working on [project name]
```

**Check progress first**:
```
What's the current status of [project]? Then continue with the next item.
```

**Work on specific item**:
```
I want to work on ITEM-025 (the reporting feature) next, even though
it's not the highest priority. Is that okay?
```

### During a Session

**Checking what's being done**:
```
What item are you working on now?
```

**Requesting validation details**:
```
Can you show me the validation results in detail?
```

**Asking about dependencies**:
```
Does this item depend on any other items that aren't done yet?
```

### Ending a Session

The agent should automatically:
- Update `00-current/item-list.json` with the completed item and tasks
- Append a session entry to `00-current/progress.log`
- Update `20-working/<ITEM-ID>/log.md` with task details
- Commit changes if using Git
- Provide a summary and next recommendation

**You don't need to do anything special** - just end the conversation when ready.

### Between Sessions

**Review progress** (optional but recommended):
```bash
# Quick status check
cat 00-current/item-list.json | grep -c '"status": "completed"'
cat 00-current/item-list.json | grep -c '"status": "pending"'

# Read recent history
tail -50 00-current/progress.log

# See what's next
cat 00-current/item-list.json | grep -A 3 '"status": "pending"' | head -20

# Review per-item logs
ls -la 20-working/
```

**Track in Git** (highly recommended):
```bash
git add 00-current/ 20-working/ITEM-012/
git commit -m "Session 5: Completed ITEM-012 - Authentication middleware"
```

**Add your decisions** (the agent can't modify this file):
```bash
# Edit 00-current/user-decision.md with your notes, preferences, and context
```

## The Status Dashboard

Task Relay keeps a visual status page at **`00-current/dashboard.html`**. It is written for you,
not for the agent.

**How to open it**: double-click the file, or open it in any app that previews HTML (Safari,
DEVONthink, an editor's preview pane). It is one self-contained file — inline CSS, system fonts,
**no JavaScript, no external resources, no auto-refresh**. It follows your system light/dark
setting. Because nothing is scripted, it renders even where scripts are blocked. Reload it (⌘R)
after the agent finishes a state write to see the current page (D8, D9).

**What each section means**

| Section | Meaning |
|---|---|
| KPI row | How many blockers need you, how many wait on something external, how many items are in progress, completed items / total |
| 需要你处理 | Tasks blocked on **you** — the question, where it sits (item → task), the suggested default action, and how long it has been waiting. Anything marked 未分类 is old data: tell the agent whether it is a question for you or an external wait |
| 等外部 | Tasks blocked on something outside your control — what they wait for and since when |
| 进行中和待办的 Items | Active items, expanded by default. Each shows its status, a progress bar (done + cancelled / all tasks), and every task with a one-line note |
| 最近动态 | The 5 most recent state changes, taken from the JSON timestamps |
| 最新交付物 | Up to 5 files from your most recently completed items |
| 已结束的 Items | Every finished item, collapsed by default. Click to expand its tasks |

Long descriptions are shortened on the page; hover one to see the full text.

**Install the state-writer subagent** (once per machine). It is the lightweight model that
applies state updates and re-renders the page:

```bash
bash scripts/install-state-writer.sh            # run inside the task-relay skill folder
bash scripts/install-state-writer.sh --dry-run  # preview
bash scripts/install-state-writer.sh --help     # all options
```

Use `--claude-only` or `--codex-only` if you work with a single client. The installer refuses to
overwrite a file you edited; add `--force` to replace it.

**Run the renderer by hand** (for example after editing `item-list.json` yourself):

```bash
bash scripts/render-dashboard.sh .        # from the project root
# writes 00-current/dashboard.html
```

If `python3` is missing the wrapper prints a clear message and exits 127 instead of writing a
broken page. If `item-list.json` is missing or invalid, the render fails and your existing
`dashboard.html` is left untouched.

## Working Across Different AI Clients

Task Relay works across different AI agents because state is in files, not memory.

### Scenario: Start with Claude, Continue with ChatGPT

**Monday (Claude Code)**:
```
You: "Build a finance tracker with Task Relay"
Claude: [Creates state files]
Claude: [Completes ITEM-001, ITEM-002]
```

**Tuesday (ChatGPT - File Access)**:
```
You: "Continue working on finance tracker using Task Relay"
ChatGPT: [Reads item-list.json and the last 100 lines of progress.log]
ChatGPT: [Continues with ITEM-003]
```

**Wednesday (ChatGPT - No File Access)**:
```
You: "Continue finance tracker using Task Relay. Here's the current state:

item-list.json:
[paste entire file]

Last 100 lines of progress.log:
[paste last 100 lines]

Please read these, then continue with the next item."

ChatGPT: [Parses state, continues work, gives you updated files to copy back]
```

**Thursday (Back to Claude)**:
```
You: "Continue finance tracker"
Claude: [Reads updated state files, continues seamlessly]
```

## Tips and Best Practices

### 1. Trust the Process

**Don't**: "Can we just quickly finish all the remaining items today?"

**Do**: Let the agent work one item at a time. Quality > Speed.

**Why**: Rushing leads to:
- Skipped validation
- Buggy code
- Context exhaustion
- More debugging later

### 2. Review the Initial Breakdown

Always review the items created during initialization.

**Good questions to ask**:
- "Are any of these items too large?"
- "Do we need all of these items?"
- "Can we simplify the approach?"

**When to push back**:
- Items seem redundant
- Too much boilerplate work
- Over-engineered solution
- Not aligned with your goals

### 3. Keep State Files Safe

**Use Git**:
```bash
# After each session
git add item-list.json progress.log
git commit -m "Session N: [item completed]"

# Benefits:
# - Full history
# - Easy rollback if files corrupted
# - Can see progress over time
```

**Backup important sessions**:
```bash
# Before major changes
cp item-list.json item-list.backup.json
cp progress.log progress.backup.log
```

### 4. Intervene When Needed

**Agent marks item complete without showing validation**:
```
I don't see the validation results. Can you run all validation steps
and show me the results before marking this complete?
```

**Agent tries to work on multiple items**:
```
Let's focus on just ITEM-015 first. We can do ITEM-016 in the next session.
```

**You need to change priorities**:
```
I need the reporting feature (ITEM-030) urgently. Can we work on that
next, even if it's lower priority?
```

### 5. Handle Blockers Promptly

**When an item gets blocked**, address it quickly:

```
Agent: "ITEM-010 is blocked - needs API key for Stripe integration"

You: "Here's the API key: sk_test_..."

Agent: [Unblocks and continues]
```

**If you can't unblock immediately**:
```
You: "I'll get that API key tomorrow. Can you work on a different
item that doesn't need it?"

Agent: "Yes, moving to ITEM-011 which doesn't depend on the API."
```

### 6. Check Progress Regularly

**Every 5-10 sessions**, check overall progress:

```
What's our overall progress? Show me completion rate by category.
```

This helps you:
- Spot if certain categories are lagging
- Adjust priorities if needed
- Estimate time to completion

### 7. Provide Feedback Early

**If the agent makes a mistake**, correct it immediately:

```
You marked ITEM-015 as complete, but the tests are still failing.
Let's mark it back as in_progress and fix the issues.
```

**If you see a pattern of mistakes**:
```
I've noticed you've been marking items complete without running all
validation steps. Please make sure to run ALL validation steps for
every item going forward.
```

## Troubleshooting

### Problem: "The agent isn't reading the state files"

**Symptoms**: Agent acts like it's starting fresh, doesn't know what was done

**Solution**:
```
Please read AGENTS.md, 00-current/item-list.json and only the last 100 lines of
00-current/progress.log to see the current state, then continue with the next
pending item using Task Relay.
```

### Problem: "Multiple items marked in_progress"

**Symptoms**: 00-current/item-list.json shows 2+ items with status: "in_progress"

**Solution**:
```bash
# Find all in-progress items
cat 00-current/item-list.json | grep -B 5 '"status": "in_progress"'

# Tell agent to fix
```

```
I see both ITEM-010 and ITEM-012 are marked in_progress. That violates
the one-item-per-session rule. Please:
1. Choose which one you're actually working on
2. Mark the other as pending
3. Update metadata counts
```

### Problem: "Validation was skipped"

**Symptoms**: Item marked complete but no validation results in progress.log

**Solution**:
```
I don't see validation results for ITEM-015. Please:
1. Mark it back as in_progress
2. Run ALL validation steps
3. Show me the results
4. Only mark complete if all pass
```

### Problem: "State files got corrupted or deleted"

**Symptoms**: Files are missing or have invalid JSON

**Solution with Git**:
```bash
# Restore from last commit
git checkout -- 00-current/item-list.json 00-current/progress.log
```

**Solution without Git**:
```
I lost the state files. Here's what I remember was completed:
- ITEM-001 through ITEM-008
- ITEM-010 and ITEM-011

Can you help me reconstruct 00-current/item-list.json based on this?
Also check 20-working/ for per-item log.md files that may help recover state.
```

### Problem: "Progress feels slow"

**Symptoms**: 20 sessions in, only 5 items done

**Solution**: This might be normal! Check:

1. **Are items too large?**
   ```
   The items seem very large. Can we break ITEM-012 into 3 smaller items?
   ```

2. **Is validation too thorough?**
   ```
   Do we really need 10 validation steps for this item?
   Can we simplify to the 3 most important checks?
   ```

3. **Are there blockers?**
   ```
   How many items are blocked? What's blocking them?
   ```

**Remember**: One quality item per session is better than 5 rushed items.

### Problem: "How do I know what's next?"

**Symptoms**: Session ended but you're not sure what to work on next

**Solution**: Check the last entry in progress.log:

```bash
tail -20 00-current/progress.log
```

Look for "Next Session Recommendation"

Or ask the agent:
```
What should we work on next?
```

## New in v1.1

Task Relay v1.1 adds five capabilities. None of them break v1.0 projects — legacy item-lists and memory files continue to work unchanged.

### 1. Stricter decomposition rules

When initializing or adding new items, the agent now follows five rules (full reference: `references/decomposition-rules.md`):

1. **One idea per item.** If you can't summarize it in one short sentence, split it.
2. **Functionality and tests are separate items.** Never bundle code + tests in one item.
3. **Ordering guarantees compilability.** At the end of every item, the project must still compile and pass existing tests.
4. **Every item cites why it comes here.** New `rationale_for_order` field — references a KB entry, source file, or prior item.
5. **Every item carries a `complexity` flag.** Either `simple` (handled inline) or `complex` (needed deeper treatment). *Note: in v1.3, the `complexity` flag is deprecated — use item sizing (session-sized items + tasks[]) instead.*

**New item fields** (v1.1): `complexity`, `depends_on`, `rationale_for_order`. The `validation_steps` field is canonical (deprecated alias `validation_criteria` still accepted for backwards compatibility).

**Legacy items** without these fields default to `complexity: simple` and `rationale_for_order: "(legacy item, no rationale recorded)"`. No migration required.

**Granularity guidance** (advisory, refined):
| Assignment scope | Typical item count |
|---|---|
| Whole application | 30–80 |
| Feature / module | 10–30 |
| Small enhancement | 3–10 |

### 2. Memory frequency counters (`[N=k]`)

`00-current/memory.md` entries are now prefixed with a frequency counter. When a recurring lesson is captured, the counter increments instead of creating a duplicate.

**Old format**:
```
- [2026-04-29] JsonWriter::writer is private — use this->writer.
- [2026-04-30] JsonWriter::writer is private; must use this->writer.
```

**New format** (sorted descending by counter; ties by recent date):
```
- [N=2] [2026-04-30] JsonWriter::writer is private in base; use this->writer in derived members.
- [N=1] [2026-04-27] Test fixture cleanup must run even on failure (use RAII guard).
```

Trigger phrases are unchanged ("remember this", "don't forget", "记一下", etc.). The agent now checks for semantically-similar entries before appending; on a match it increments and updates the date instead of duplicating. You'll see confirmations like `"Incremented Gotchas entry to N=3"` or `"Added new Decisions entry"`.

Legacy uncounted entries are auto-promoted to `[N=1]` on first capture in their section.

### 3. Batch ingestion (`task-input-batch.yaml`)

You (or a future decomposer skill) can hand the agent a YAML file containing many items at once, and the agent will ingest them into `00-current/item-list.json` in one shot. Useful when:

- You've designed the decomposition externally (e.g. from a design document).
- A `/project decompose` orchestrator produced a batch.
- You need to apply a **delta batch** of changes (`add` / `modify` / `remove` ops) against an existing item-list — without disturbing completed items.

**Example prompt**:
```
I've drafted 20-working/task-input-batch.yaml. Please ingest it into the item-list.
```

The agent will validate the schema, assign `ITEM-XXX` ids, append items, update metadata counts, log to `progress.log`, and archive the batch file to `90-archive/`. See `assets/task-input-batch.template.yaml` for the expected shape; full procedure: `references/batch-ingest.md`.

**Delta batches** protect completed items: if a delta tries to modify or remove an already-completed item, the agent logs a warning and skips it.

### 4. `/task-relay learn` — post-task retrospective

After an item completes, run a retrospective to extract lessons from any **user hand-edits** you made to the executor's code. The intuition: the diff between *what the executor planned to write* and *what the file currently says* is the highest-signal indicator of your preferences.

**Usage**:
```
/task-relay learn
```
Or target a specific completed item:
```
/task-relay learn ITEM-007
```

The agent will:
1. Diff the executor's plan in `02_execution.md` against the current source.
2. Filter out executor self-corrections and already-documented updates — what remains is *your* hand-edits.
3. Categorize each edit (Gotcha / Decision / Preference / Fact) and present a candidate-lessons list.
4. **For each lesson, ask for your confirmation.** Confirmed lessons land in `memory.md` (via the counter-aware capture flow) and propagate as `[LEARNED ...]` notes into semantically-relevant pending items.

Skipped automatically for items that ended `blocked` or `cancelled` (those need direct attention, not retrospection).

Full procedure: `references/learn-workflow.md`.

### 5. Tasks under items — overflow-safe execution

Items now have `tasks[]` (≥1). Tasks are the checkpoint and resumability mechanism — if context fills before an item finishes, completed tasks stay recorded and the next session resumes exactly where you left off. This replaces the old `/task-relay deep` adapter.

**How it works:**
- Decompose each item into 2–5 concrete tasks at the time you create the item.
- Each session works through tasks one at a time — the **user selects** which task to do next after each one completes.
- If context fills mid-item, the agent writes a handoff note to `progress.log` and the next session picks up the `in_progress` task.
- Task IDs: `TASK-<item-number>-<task-number>` (e.g. `TASK-005-01`).

**Key rules:**
- The agent never auto-advances to the next task — it always asks you.
- A `blocked` task doesn't block the item; you can pick another task.
- A `cancelled` task is terminal and requires a `notes` explanation.

## Advanced Patterns

### Pattern 1: Parallel Work with Multiple Agents

If you have access to multiple AI agents, you can work on different items in parallel (carefully):

**Setup**:
1. Assign items to different agents
2. Update item status before starting
3. Commit frequently to avoid conflicts

**Agent 1** (Claude):
```
Work on ITEM-005. Mark it in_progress before you start.
```

**Agent 2** (ChatGPT):
```
Work on ITEM-007. Mark it in_progress before you start.
```

**After both complete**:
```bash
# Merge the changes
git pull
# Resolve any conflicts in metadata counts
# Commit merged state
```

� **Warning**: This is advanced! Only do this if items are truly independent.

### Pattern 2: Rapid Prototyping Then Refinement

**Phase 1**: Create items for quick prototype (10-15 items)
```
Let's build a quick prototype first. Create items just for the
core features, skip testing and polish for now.
```

**Phase 2**: After prototype works, add refinement items
```
Now that the prototype works, add items for:
- Comprehensive testing
- Error handling
- Performance optimization
- Documentation
```

### Pattern 3: Spike-and-Pivot

If you're unsure about approach:

**ITEM-001**: Spike to evaluate approach A (time-boxed)
**ITEM-002**: Spike to evaluate approach B (time-boxed)
**ITEM-003**: Based on spikes, design chosen approach
**ITEM-004+**: Implement chosen approach

## FAQ

### Q: How many items should an assignment have?

**A**: Depends on size (v1.1 guidance):
- Small enhancement: 3–10 items
- Feature / module: 10–30 items
- Whole application: 30–80 items

**Rule of thumb**: Each item should take 30–60 minutes including validation. If you'd produce fewer than 3 items, you probably don't need Task Relay — drive the work directly.

### Q: Can I modify items after initialization?

**A**: Yes, but carefully:
- Can change: `status`, `notes`, `completed_at`
- Don't change: `id`, `description`, `priority`, `validation_steps`, `category`, `tasks[].id`, `tasks[].description`

If you need to change item definitions, tell the agent:
```
I realized ITEM-020 is no longer needed. Can we mark it as completed
with a note that it's been skipped?
```

### Q: What if I want to add new items mid-project?

**A**: Tell the agent:
```
We need to add a new item for [feature]. Can you:
1. Add it to item-list.json as ITEM-036
2. Set appropriate priority
3. Update metadata counts
```

### Q: Can I use this for non-coding projects?

**A**: Absolutely! Use `init.md` instead of `init.sh`. Examples:
- Research papers
- Content writing
- Data analysis
- Design projects
- Any multi-step work

### Q: How do I know when the assignment is complete?

**A**: When `metadata.pending = 0` and `metadata.blocked = 0` and `metadata.in_progress = 0`.

The agent should announce completion:
```
<� Assignment Complete!
All 35 items completed and validated.
```

### Q: What if I disagree with the agent's approach?

**A**: Speak up immediately:
```
I don't think we should use approach X for this item.
Let's use approach Y instead because [reasons].
```

You're in control. The agent should follow your guidance.

## Example Prompts

### Starting an assignment
```
I need to [goal]. This will take multiple sessions.
Please use Task Relay to manage this work.

Requirements:
- [requirement 1]
- [requirement 2]
- [requirement 3]
```

### Continuing work
```
Continue working on [project name]
```

### Checking progress
```
What's our current progress on [project]?
```

### Working on specific item
```
Let's work on ITEM-[number] next
```

### Handling blockers
```
ITEM-[number] is blocked because [reason].
Here's the information needed: [info]
Please unblock and continue.
```

### Adjusting the plan
```
The items for [category] seem too granular.
Can we consolidate them into fewer, larger items?
```

### Debugging issues
```
I see [issue] in the state files.
Can you help me fix this?
```

## Next Steps

Now that you understand Task Relay:

1. **Try it on a small project first** (10-15 items)
2. **Get comfortable with the workflow**
3. **Graduate to larger projects** (30+ items)
4. **Experiment with different agents** (Claude, ChatGPT, etc.)
5. **Develop your own patterns** based on your work style

Happy building! =�

---

## Additional Resources

- **Framework Documentation**: See `task-relay-framework.md` for complete technical details
- **SKILL.md**: See `SKILL.md` for agent-focused instructions
- **Examples**: See `references/examples.md` for real-world item breakdowns
- **Checklists**: See `references/workflow-checklists.md` for detailed checklists
- **Schema**: See `references/item-list-schema.json` for JSON validation
- **Decomposition rules** (v1.3): See `references/decomposition-rules.md` for six rules + examples (including session-sizing and task-sizing)
- **Batch ingestion** (v1.1/v1.3): See `references/batch-ingest.md` and `assets/task-input-batch.template.yaml`
- **Learn workflow** (v1.1): See `references/learn-workflow.md`
- **Initialization Phase** (v1.2): See `references/initialization-phase.md` for the full Steps 0–5 procedure
- **Execution Phase** (v1.3): See `references/execution-phase.md` for the full Steps 1–6 procedure (selection gate, task loop, archival)
- **State File Specifications** (v1.3): See `references/state-file-specs.md`
- **Issues Backlog workflows** (v1.2): See `references/issues-backlog.md`
- **Scripts**: `scripts/generate-manifest.sh`, `scripts/rotate-progress-log.sh` (archives to `90-archive/progress-log/`)

## Getting Help

If you run into issues:

1. Check the troubleshooting section above
2. Review the framework documentation
3. Ask the agent: "What does Task Relay recommend for [situation]?"
4. File an issue in the skill repository

Remember: The agent is your partner in this process. Don't hesitate to give feedback, ask questions, or request changes!
