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

# Write AGENTS.md from the template: fills in the project name and the real
# skill paths, so no {SKILL_*} placeholder is left. Add --name "<name>" to
# choose the title (default: the folder name).
python3 {SKILL_SCRIPTS_PATH}/agents-md.py write .

# Create empty user-decision.md (user-maintained file)
cp {SKILL_ASSETS_PATH}/user-decision.template.md ./00-current/user-decision.md

# Create empty memory.md (curated insights captured during sessions)
cp {SKILL_ASSETS_PATH}/memory.template.md ./00-current/memory.md

# Create reference spec file (fill in placeholder paths)
cp {SKILL_ASSETS_PATH}/spec.template.md ./10-reference/000_$(date +%Y-%m-%d)_spec.md

# REQUIRED before you finish initialization: ask the user which language the
# dashboard page should show. Propose the language the user writes in
# (for example `zh-CN` when the request is in Chinese) as the default.
# Then write the answer as an explicit line in the spec file:
#   - Dashboard language: `zh-CN`    -> dashboard shows Chinese, stored text unchanged
#   - Dashboard language: `none`     -> dashboard shows the stored text as written
# Write it even when you author a custom spec instead of copying this template.

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
3. For code projects, resolve source roots before finalizing the spec:
   - `PROJECT_ROOT`: active checkout root on the local workstation.
   - `TARGET_ROOT`: matching remote compile-server checkout root, if source sync/compile is needed.
   - `REPO_PROFILE_ROOT`: profile folder containing `manifest.xml`, `metadata.json`, `repo_map.txt`, and `repo_map_upstream.txt`, if this is a multi-repo checkout.
   - `REPO_PROFILE_ROOT` must be confirmed by the user the first time the skill initializes a project. The agent may propose an inferred value, but must not write it to the spec until the user confirms it.
   - For `PROJECT_ROOT` and `TARGET_ROOT`, use user-provided values when available. If absent, infer only when obvious from the current working directory or repo metadata. If inference is uncertain, ask the user.
   - Replace `{PROJECT_ROOT}`, `{TARGET_ROOT}`, and `{REPO_PROFILE_ROOT}` in `10-reference/000_YYYY-MM-DD_spec.md`. Do not leave `{PROJECT_ROOT}` unresolved in a live project spec.
4. Update `10-reference/000_YYYY-MM-DD_spec.md` with project-specific reference paths
5. Understand the domain (code project, research, writing, data analysis, etc.)
6. Ask which language the dashboard page should show, then record the answer in the spec as
   `Dashboard language: <code>` — or `Dashboard language: none` to show the stored text as
   written. Propose the language the user writes in as the default. Never omit this line and
   never leave the template placeholder, even when you author a custom spec.

### Multi-Repo Source Map Handling

When `REPO_PROFILE_ROOT` contains a manifest:

1. Read `metadata.json` and `manifest.xml`.
2. Replace the placeholder repo table in the spec with rows generated from the manifest.
3. Generate each row from manifest fields:
   - repo name = `project/@name`
   - checkout path = `project/@path`, or `project/@name` when `path` is absent
   - local path = `{PROJECT_ROOT}/<checkout_path>`
   - upstream branch = `project/@upstream`
   - pinned revision = `project/@revision`
4. Set remote fields from the manifest `remote` element (`name`, `fetch`, `review`) when present.
5. Keep paths portable. Do not replace repo table paths with one hardcoded checkout path; only set `PROJECT_ROOT` once.
6. For future source edits, use the table to identify the owning repo before running git commands or preparing rsync commands.

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

1. **One milestone per item.** An item may have several outcomes, but they serve one milestone you can name in one short sentence. Split unrelated goals.
2. **Functionality and tests are separate tasks.** Inside an item, code and tests are different tasks; the item's `validation_steps` include the tests. A broad test suite may be its own item.
3. **Ordering guarantees compilability.** At the end of each item, the project must compile and pass existing tests.
4. **Every item cites why it comes here.** Reference KB entries, source files, or prior items in your rationale.
5. **Every item has a clear finish line.** Size an item by its outcome, not by time; it may take one session or many. Split it when its `validation_steps` cannot show the milestone is reached.
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

### 3.1b First dashboard render (empty state)

Initialization renders the first dashboard so the user has a page from day one:

```bash
bash {SKILL_SCRIPTS_PATH}/install-state-writer.sh --dry-run   # show where the subagent will go
bash {SKILL_SCRIPTS_PATH}/install-state-writer.sh             # install once per machine (D10)
bash {SKILL_SCRIPTS_PATH}/render-dashboard.sh .               # writes 00-current/dashboard.html
```

`00-current/dashboard.html` is a **derived** file: generated from `item-list.json` and
`item-list-archive.json`, never hand-edited, and rewritten in full on every state write (D8).
During execution the state writer re-renders it after each update request, so initialization is
the only time the main agent runs the renderer directly
(`references/state-writer-contract.md`, `references/state-file-specs.md`).

Before this first render, the spec must already carry `Dashboard language:`. When the value is a
language code instead of `none`, refresh the translation cache first — `python3
{SKILL_SCRIPTS_PATH}/dashboard-i18n.py list-missing .`, translate the strings, then `apply` — so
the first page is not left in the stored language (D16).

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

# Verify the dashboard rendered (empty state is fine)
ls -la 00-current/dashboard.html

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
