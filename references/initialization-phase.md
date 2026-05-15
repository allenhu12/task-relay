# Initialization Phase — Full Procedure

Routed from `SKILL.md` § Initialization Phase Workflow. Run this workflow
when starting a **new** assignment (no state files exist).

The summary in `SKILL.md` lists the step titles; this file holds the full
procedure, commands, and acceptance criteria.

## Step 0: Create Folder Structure

Create the 9-zone folder structure:

```bash
# Create project directory (if user hasn't specified one)
PROJECT_DIR="task-relay-project"  # or user-specified name
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Create 9-zone folders (no 30-logs/ — removed in v1.3)
mkdir -p 00-current 05-plans 10-reference 20-working 50-drafts 60-handoffs 80-issues 90-archive

# Per-item 20-working/<ITEM-ID>/ folders are created LAZILY at execution,
# not here. Do NOT pre-create them.

# Copy AGENTS.md template to project root
cp {SKILL_ASSETS_PATH}/AGENTS.template.md ./AGENTS.md
# Edit AGENTS.md to replace {PROJECT_NAME} with actual project name

# Create empty user-decision.md (user-maintained file)
cp {SKILL_ASSETS_PATH}/user-decision.template.md ./00-current/user-decision.md

# Create empty memory.md (curated insights captured during sessions)
cp {SKILL_ASSETS_PATH}/memory.template.md ./00-current/memory.md

# Create reference spec file (fill in placeholder paths)
cp {SKILL_ASSETS_PATH}/spec.template.md ./10-reference/000_$(date +%Y-%m-%d)_spec.md

# Generate initial MANIFEST.md for reference files (empty at start)
bash {SKILL_SCRIPTS_PATH}/generate-manifest.sh ./10-reference

# Verify structure
ls -la
ls -la 00-current/
ls -la 10-reference/
```

## Step 1: Analyze Requirements

1. Read the user's assignment description carefully
2. Ask clarifying questions if scope is unclear:
   - What is the final deliverable?
   - Are there specific requirements or constraints?
   - What does "done" look like?
3. Update `10-reference/000_YYYY-MM-DD_spec.md` with project-specific reference paths
4. Understand the domain (code project, research, writing, data analysis, etc.)

## Step 1.5: Knowledge Front-Loading (Recommended)

Before decomposing items, conduct a structured Q&A session to capture tribal knowledge into project docs. This is especially valuable when:
- The assignee is new to the task domain
- Requirements are scattered across emails, wiki pages, or colleagues' heads
- The project involves institutional knowledge that isn't in the codebase

**How it works:**
1. The agent prepares a list of clarifying questions based on the initial requirements analysis
2. The user answers questions **one by one** (not all at once — this keeps each answer focused)
3. After **each answer**, the agent immediately updates the relevant project documents (`10-reference/000_*_spec.md`, `00-current/item-list.json`, working notes in `20-working/`)
4. Continue until the agent has enough context to decompose items confidently

**Why this matters:** Most project knowledge lives in people's heads. A deliberate front-loading phase converts scattered tribal knowledge into structured, persistent reference material before implementation begins. Future sessions (even with a fresh context window) can recover full state from these docs without re-asking the user. This is the single highest-ROI activity at project start — it compounds across every subsequent session.

**Keep the item list minimal** during this phase if requirements are still being clarified. It's better to have 5 well-understood items than 20 vague ones. Items can be expanded later as understanding deepens.

## Step 2: Decompose into Items (opt-in)

**Default behaviour: skip this step.** At project initialization, leave
`item-list.json` with an empty `items: []` array unless the user
**explicitly** asks the agent to decompose.

Trigger phrases that opt-in to decomposition at init time:
- "generate items"
- "decompose the project (now)"
- "fill in the item list"
- "create the items from this spec"

If the user does not opt in, complete initialization with an empty item
list. They can populate later by:
- Asking the agent to decompose in a future session.
- Hand-writing items into `item-list.json`.
- Producing a `task-input-batch.yaml` and using the batch-ingestion
  workflow (see `references/batch-ingest.md`).
- Promoting an issue from `80-issues/` to an item.

When the user *does* opt in, break the assignment into discrete, testable
items per the decomposition rules below.

**Decomposition Rules** (full reference + examples: `references/decomposition-rules.md`):

1. **One idea per item.** A single feature, refactor, or test category. If you can't summarize the item in one short sentence, split it.
2. **Functionality and tests are separate items.** Never mix code change and test-writing in the same item.
3. **Ordering guarantees compilability.** At the end of each item, the project must compile and pass existing tests.
4. **Every item cites why it comes here.** Reference KB entries, source files, or prior items in your rationale.
5. **Every item is session-sized.** An item must be completable in roughly one session. If it would take more, split it into smaller items.
6. **Every item has ≥1 task.** A trivial item is an item with a single task. Decompose larger items into 2–5 tasks in `tasks[]`.

**Granularity** (advisory):
| Assignment scope | Typical item count |
|---|---|
| Whole application | 30–80 |
| Feature / module | 10–30 |
| Small enhancement | 3–10 |

If fewer than 3 items result, you probably don't need task-relay — drive the work directly.

**Template for Each Item** (full schema: `references/item-list-schema.json`):
```json
{
  "id": "ITEM-XXX",
  "category": "setup|implementation|testing|documentation|refactor|bugfix",
  "description": "Action verb + specific outcome",
  "priority": 1,
  "validation_steps": ["Item-level rollup check 1", "Item-level rollup check 2"],
  "status": "pending",
  "completed_at": null,
  "notes": "",
  "working_dir": null,
  "files": [],
  "tasks": [
    {
      "id": "TASK-XXX-01",
      "description": "First concrete sub-step",
      "status": "pending",
      "validation_steps": ["Task-level check"],
      "completed_at": null,
      "notes": ""
    }
  ]
}
```

**Note**: Per-item `20-working/<ITEM-ID>/` folders are **NOT created at decomposition time**. They are created lazily when each item first transitions to `in_progress`.

## Step 3: Create State Files

Use the templates from `assets/` to create state files in `00-current/`.

### 3.1 item-list.json and item-list-archive.json

```bash
cp {SKILL_ASSETS_PATH}/item-list.template.json ./00-current/item-list.json
cp {SKILL_ASSETS_PATH}/item-list-archive.template.json ./00-current/item-list-archive.json
```

Fill in `item-list.json`:
- `assignment.name`
- `assignment.description`
- `items` array — **empty `[]` by default**; populate only if Step 2 was opted into.
- `terminal_summary` array (empty at initialization)
- `metadata` counts — set all to `0` (including `cancelled: 0`) when items are empty.

`item-list-archive.json` starts empty.

### 3.2 progress.log

```bash
cp {SKILL_ASSETS_PATH}/progress.template.log ./00-current/progress.log
```

Add Session 1 entry documenting initialization. Non-item sessions (init, batch ingest, backlog triage, status checks) log to `progress.log` only.

### 3.3 init.sh or init.md

```bash
# For code projects:
cp {SKILL_ASSETS_PATH}/init.template.sh ./init.sh
chmod +x init.sh

# For non-code assignments:
cp {SKILL_ASSETS_PATH}/init.template.md ./init.md
```

Customize with project-specific setup steps.

## Step 4: Verify Baseline

```bash
# Verify folder structure exists (no 30-logs/)
ls -la 00-current/ 10-reference/ 20-working/ 80-issues/ 90-archive/

# Verify state files exist
ls -la 00-current/item-list.json 00-current/item-list-archive.json \
       00-current/progress.log 00-current/user-decision.md

# Verify reference spec exists
ls -la 10-reference/*_spec.md

# Validate JSON structure (if validate-state tool is available)
validate-state ./00-current/item-list.json

# Test initialization script
./init.sh  # or follow init.md manually
```

## Step 5: Handoff Documentation

1. Update `00-current/progress.log` with Session 1 summary.
2. Recommend the first item to work on (lowest priority number).
3. Report to user:
   ```
   ✅ Assignment initialized with 9-zone folder structure
   📁 Created: 00-current/, 05-plans/, 10-reference/, 20-working/, 50-drafts/, 60-handoffs/, 80-issues/, 90-archive/
   📋 item-list.json — empty by default (ask to "decompose" when ready) OR X items created (with tasks[])
   📝 Next session: Start with ITEM-001 - [description]
   📖 Read the last 100 lines of 00-current/progress.log for recent context
   📖 Read AGENTS.md for workflow instructions
   ```

**Initialization complete** — the assignment is now ready for execution-phase sessions.
