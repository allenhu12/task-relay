# Issues Backlog (`80-issues/`)

Routed from `SKILL.md` § Issues Backlog. The `80-issues/` folder is a
lightweight backlog for ideas, bugs, and improvements discovered during
project work. Issues are separate from items — unstructured markdown,
not tracked in `item-list.json`, only accessed on explicit user request.

**Do NOT read `80-issues/` during State Recovery.** It is not part of the
active state.

## Issue file format

**Naming**: `<seq>_issue_<meaningful-name>.md`

Examples:
- `001_issue_login-redirect-bug.md`
- `002_issue_add-dark-mode-toggle.md`
- `003_issue_refactor-api-error-handling.md`

**Template** (see `assets/issue.template.md`):

```markdown
---
Type: issue
Status: open
Priority: low | medium | high | critical
Category: bug | feature | improvement | idea | debt
Created: YYYY-MM-DD
Promoted_to: null
---

# Issue Title

Brief description of the issue, idea, bug, or improvement.

### Context

Discovered during [ITEM-XXX / general usage / user request].

### Notes

- Additional details
- Related items or references
```

> Use `###` (level 3) for `Context` / `Notes` so issue files don't pollute
> the outline of any document that includes them.

**Status values**:
- `open` — Active backlog item, not yet acted upon
- `promoted` — Converted to an item in `item-list.json` (see `Promoted_to` field)
- `dismissed` — Decided not to pursue (add reason in Notes)
- `deferred` — Postponed for later consideration

## Workflow: Capture an issue

**Trigger phrases**: "log this issue", "record this idea", "add to backlog", or similar.

1. Determine next sequence number: `ls 80-issues/ | wc -l` + 1.
2. Create issue file using the template.
3. Fill in frontmatter (`Status: open`, `Priority`, `Category`, `Created`).
4. Write the user's idea into the body with context about what item was being worked on.
5. Resume current work — no state-file updates needed.

```bash
# Example
cat > 80-issues/004_issue_api-rate-limiting.md << 'EOF'
---
Type: issue
Status: open
Priority: medium
Category: feature
Created: 2026-03-17
Promoted_to: null
---

# Add API rate limiting

The public API endpoints have no rate limiting. Could be abused.

### Context

Discovered while working on ITEM-012 (API authentication).

### Notes

- Affects all /api/v1/* endpoints
- Consider using express-rate-limit or similar middleware
EOF
```

## Workflow: Review backlog

**Trigger phrases**: "review backlog", "show issues", "what's in the backlog", or similar.

1. Read all `.md` files in `80-issues/` with `Status: open` (read frontmatter).
2. Present a summary table to the user:

```markdown
| # | File | Priority | Category | Title |
|---|------|----------|----------|-------|
| 1 | 001_issue_login-redirect-bug.md | high | bug | Login redirect bug |
| 2 | 002_issue_add-dark-mode-toggle.md | low | feature | Add dark mode toggle |
| 3 | 003_issue_refactor-api-error-handling.md | medium | debt | Refactor API error handling |
```

3. User decides per issue: **promote**, **dismiss**, **defer**, or **leave open**.

## Workflow: Promote issue to item

**Trigger**: user selects an issue during review, or says "promote issue 003 to an item".

1. Read the full issue file.
2. Create a proper item in `item-list.json` per the v1.1 schema:
   - Generate next ITEM-XXX ID (check both `items` array and `completed_summary`).
   - Map issue Category → item category.
   - Derive description from issue title/body.
   - Ask user for `validation_criteria` (or derive from issue content if clear).
   - Set `complexity` (`simple` or `complex`); set `rationale_for_order`.
   - Set `status: pending`.
3. Update `item-list.json` metadata (`total_items` +1, `pending` +1).
4. Optionally set `next_override` if the user wants to handle it next session.
5. Update the issue file frontmatter:
   - `Status: promoted`
   - `Promoted_to: ITEM-XXX`
6. Log the promotion in `progress.log`.

## Workflow: Dismiss / defer

- **Dismiss**: update frontmatter to `Status: dismissed`. Add reason in Notes. File stays in `80-issues/`.
- **Defer**: update frontmatter to `Status: deferred`. Optionally add a target date or condition in Notes. Reviewed again later.
