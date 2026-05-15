# Structured Document Generator - Design Specification

**Version:** 1.0
**Date:** 2025-12-25
**Status:** Design Phase

> **v1.3 note:** This design predates task-relay v1.3. References to `30-logs/`
> session logs are superseded — detailed item logs now live in
> `20-working/<ITEM-ID>/log.md`. References to `/task-relay deep` or
> `task-result.yaml` are superseded — the deep adapter was removed in v1.3.
> The core structured-doc-generator design remains valid for future implementation.

---

## Executive Summary

Create a standalone, generic document generator skill that:
- Saves context tokens by delegating document generation to sub-agents (when available)
- Supports multiple workflow profiles (extensible architecture)
- Adapts detail level based on main agent's token usage
- Auto-validates and corrects documents before writing

**V1 Scope**: Task-relay profile with session-log generation only

---

## Problem Statement

In the task-relay workflow, document generation (session logs, progress updates, etc.) consumes significant context tokens in the main agent. By delegating this work to a sub-agent:
- Main agent tokens are preserved for core workflow logic
- Document generation follows strict rules and templates consistently
- The solution is reusable across multiple workflows

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ Caller Skill (e.g., task-relay)                             │
│ - Ask user approval before generating document              │
│ - Invoke: Skill("structured-doc-generator", args="{...}")   │
│ - Receive: "✅ Generated..." or "❌ Validation failed..."   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Structured-Doc-Generator Skill (orchestrator)               │
│ - Try to use Task tool for sub-agent delegation             │
│ - If Task tool fails → execute directly in main agent       │
│ - Parse args, determine profile & doc type                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
         ▼                           ▼
┌──────────────────┐        ┌──────────────────┐
│ Sub-Agent        │        │ Main Agent       │
│ (Claude Code)    │        │ (Other clients)  │
│ - Load profile   │        │ - Load profile   │
│ - Check tokens   │        │ - Check tokens   │
│ - Generate doc   │        │ - Generate doc   │
│ - Validate       │        │ - Validate       │
│ - Auto-correct   │        │ - Auto-correct   │
│ - Write file     │        │ - Write file     │
└──────────────────┘        └──────────────────┘
```

---

## Design Decisions Summary

| Decision Point | Choice | Rationale |
|---------------|---------|-----------|
| Sub-agent delegation | Try-and-adapt pattern | Portable across Claude Code and other clients |
| Context passing | Full context (Option B) | Sub-agent needs complete state to make decisions |
| Responsibility | Generator + Validator + Writer (Option C) | Ensures compliance before persisting |
| Error handling | Hybrid auto-correction | Auto-fix obvious issues, fail on critical violations |
| Rules access | Bundled knowledge (Option A) | Self-contained, token-efficient |
| Integration | New standalone skill (Option A) | Reusable, decoupled from task-relay |
| Invocation interface | Profile-based (Option A) | Easy to call, extensible |
| V1 Scope | Task-relay only with extensible design | Proven use case, clear requirements |
| Args format | Structured JSON (Option A) | Reliable parsing, well-defined |
| V1 Document types | Session-log only (Option C) | Most complex, validates architecture |
| Token optimization | Adaptive detail level (Option A) | Smart optimization without complexity |
| Detail threshold | 70% binary threshold (Option A) | Simple, effective |
| Detail mode difference | Section inclusion (Option A) | Clear distinction between modes |

---

## Detailed Design

### 1. Skill Interface

#### Skill Name
`structured-doc-generator`

#### Invocation Pattern
```javascript
Skill("structured-doc-generator", args='{"profile": "task-relay", "doc_type": "session-log", "token_usage_pct": 65, "data": {...}}')
```

#### Args Structure
```json
{
  "profile": "task-relay",           // Which workflow profile to use
  "doc_type": "session-log",         // Document type within profile
  "token_usage_pct": 65,             // Main agent's current token usage %
  "data": {                          // Document-specific data
    "item_id": "ITEM-003",
    "description": "Implement user authentication",
    "work_performed": [
      "Created login component",
      "Added JWT token handling",
      "Implemented session management"
    ],
    "validation_results": [
      {"step": "Login form renders correctly", "status": "pass"},
      {"step": "Token stored securely", "status": "pass"},
      {"step": "Session persists on refresh", "status": "pass"}
    ],
    "state_updates": [
      {"file": "item-list.json", "change": "ITEM-003 status: in_progress → completed"},
      {"file": "progress.log", "change": "Added session entry"}
    ],
    "blockers": [],
    "related_docs": ["001_2025-12-20_claude_session-log-item-001"],
    "next_recommendation": "ITEM-004",
    "notes": "Authentication working well, ready for testing",
    "author": "claude",
    "date": "2025-12-25"
  }
}
```

#### Return Values

**Success:**
```
"✅ Generated session-log: 30-logs/003_2025-12-25_claude_session-log-item-003.md"
```

**Failure:**
```
"❌ Validation failed: missing required field 'item_id'"
"❌ Validation failed: invalid status 'done' (must be: pending|in_progress|completed|blocked)"
```

---

### 2. Profile System

#### Profile Structure

Each profile is bundled in the SKILL.md file with three components:

```markdown
## Profile: {profile-name}

### Templates

#### {doc-type}.template.md
[Full template content with {{placeholders}}]

### Schemas

#### {doc-type}.schema.json
{
  "required": ["field1", "field2"],
  "properties": {
    "field1": {"type": "string"},
    "field2": {"type": "array"}
  }
}

### Rules

- File naming convention
- Location/directory requirements
- YAML frontmatter specifications
- Detail mode definitions
- Validation rules
- Auto-correction rules
```

#### Task-Relay Profile Specification

**Profile Name:** `task-relay`

**Supported Document Types (V1):**
- `session-log`: Detailed session work log

**Future Document Types (V2+):**
- `progress-update`: Progress log entry
- `init-script`: Initialization script (bash or markdown)
- `spec-file`: Reference specification document

**Templates:**
- See section "Task-Relay Profile Templates" below

**Schemas:**
- See section "Task-Relay Profile Schemas" below

**Rules:**
- File naming: `XXX_YYYY-MM-DD_<author>_session-log-<description>.md`
  - `XXX`: 3-digit sequence number (000, 001, 002...)
  - `YYYY-MM-DD`: ISO date format
  - `<author>`: Creator (claude, cursor, gemini, user, etc.)
  - `<description>`: Hyphenated lowercase description derived from item_id
- Location: `30-logs/` directory relative to project root
- YAML frontmatter required with fields: Type, Status, Author, Created
- Detail modes:
  - **Full detail** (token_usage_pct ≤ 70%): Include all sections
  - **Concise** (token_usage_pct > 70%): Skip Notes, Related Documents sections; brief Next Session Recommendation

**Extensibility:**
Future profiles can be added by appending new profile sections to SKILL.md following the same structure.

---

### 3. Token-Aware Adaptive Detail

#### Purpose
When the main agent is approaching token limits, generated documents should be more concise to preserve context space while still capturing essential information.

#### Logic

```
IF token_usage_pct > 70:
  detail_mode = "concise"

  Sections to INCLUDE:
  - Session Info (table)
  - Item Details
  - Work Performed (concise bullet points)
  - Validation Results (table)
  - State Updates (table)
  - Blockers (if any)
  - Next Session Recommendation (1 sentence only)

  Sections to SKIP:
  - Notes
  - Related Documents

ELSE:
  detail_mode = "full"

  Sections to INCLUDE:
  - All sections from template
  - Full detail in each section
  - Complete Next Session Recommendation
```

#### Threshold Rationale
- 70% allows enough headroom to complete the session and generate the log
- Binary threshold is simple to implement and reason about
- Can be adjusted in future versions based on empirical data

---

### 4. Validation & Auto-Correction

#### Auto-Fix Rules (Applied Automatically)

1. **Date format normalization:**
   - `12/25/2025` → `2025-12-25`
   - `Dec 25, 2025` → `2025-12-25`
   - `2025-12-25` → `2025-12-25` (no change)

2. **Item ID format normalization:**
   - `item-3` → `ITEM-003`
   - `ITEM-3` → `ITEM-003`
   - `Item-003` → `ITEM-003`

3. **Status normalization:**
   - `Complete` → `completed`
   - `Pending` → `pending`
   - `In Progress` → `in_progress`
   - `Blocked` → `blocked`

4. **Author normalization:**
   - `Claude` → `claude`
   - `Cursor` → `cursor`
   - `Gemini` → `gemini`

5. **Add missing optional fields with defaults:**
   - `blockers`: `[]` (empty array)
   - `notes`: `""` (empty string)
   - `related_docs`: `[]` (empty array)

6. **Sequence number calculation:**
   - Read existing files in `30-logs/`
   - Find highest sequence number
   - Increment by 1 for new file

#### Hard Fail Rules (Return Error)

1. **Missing required fields:**
   - `item_id`, `description`, `work_performed`, `validation_results`
   - Error: `"❌ Validation failed: missing required field '{field_name}'"`

2. **Invalid status values:**
   - Must be one of: `pending`, `in_progress`, `completed`, `blocked`
   - Error: `"❌ Validation failed: invalid status '{value}' (must be: pending|in_progress|completed|blocked)"`

3. **Malformed data structures:**
   - `work_performed` not an array
   - `validation_results` not an array of objects
   - Error: `"❌ Validation failed: '{field}' must be an array"`

4. **Invalid date format that cannot be parsed:**
   - Error: `"❌ Validation failed: cannot parse date '{value}'"`

#### Validation Process Flow

```
1. Parse args JSON
2. Extract profile and doc_type
3. Load corresponding schema
4. Check required fields → fail if missing
5. Apply auto-corrections to data
6. Validate corrected data against schema → fail if invalid
7. Generate document from template
8. Write document to file system
9. Return success message
```

---

### 5. Claude Code Detection (Try-and-Adapt Pattern)

#### Purpose
The skill should work seamlessly in Claude Code (with sub-agent delegation for token savings) and in other AI clients (direct execution).

#### Implementation

```markdown
## Step 1: Attempt Sub-Agent Delegation

First, try to use the Task tool to delegate to a sub-agent:

```
Task(
  subagent_type="general-purpose",
  description="Generate structured document",
  prompt="You are a structured document generator sub-agent.

  Profile: {profile}
  Document Type: {doc_type}
  Token Usage: {token_usage_pct}%
  Data: {data}

  [Include full profile templates, schemas, and rules here]

  Instructions:
  1. Load the profile and template for {doc_type}
  2. Validate data against schema
  3. Apply auto-corrections as needed
  4. Determine detail mode based on token usage
  5. Generate document from template
  6. Write to appropriate location
  7. Return success or error message
  "
)
```

## Step 2: Handle Sub-Agent Unavailable

If the Task tool returns an error indicating it's not available:
- Catch the error
- Execute the same document generation logic directly in the main agent
- Use the same profile, templates, schemas, and rules

## Step 3: Return Result

Regardless of execution mode (sub-agent or direct):
- Return the same format success/error message
- Caller doesn't need to know which mode was used
```

#### Benefits
- Automatic adaptation to environment
- Consistent interface for callers
- Token savings when available, functional fallback when not

---

### 6. Task-Relay Integration

#### Modification to Task-Relay SKILL.md

**Location:** Execution Phase, Step 5b (Session Log Creation)

**Current behavior:**
Task-relay includes full session-log template and generation instructions inline.

**New behavior:**

```markdown
## Step 5b: Generate Session Log

**Before generating session-log:**

1. **Ask user for approval:**
   "Session completed. Generate session-log now? (Y/n)"

2. **If user approves (Y or default):**

   a. Calculate current token usage percentage

   b. Prepare data for doc-generator:
      - item_id: [current item ID]
      - description: [item description]
      - work_performed: [list of work done this session]
      - validation_results: [validation steps and results]
      - state_updates: [changes made to state files]
      - blockers: [any blockers encountered]
      - related_docs: [related session logs or documents]
      - next_recommendation: [recommended next item]
      - notes: [any additional notes]
      - author: [current agent name]
      - date: [current date YYYY-MM-DD]

   c. Invoke structured-doc-generator:
      ```
      Skill("structured-doc-generator", args='{
        "profile": "task-relay",
        "doc_type": "session-log",
        "token_usage_pct": [calculated percentage],
        "data": {
          "item_id": "[value]",
          "description": "[value]",
          ...
        }
      }')
      ```

   d. If doc-generator returns success:
      - Confirm to user: "✅ Session log created"
      - Continue to next step

   e. If doc-generator returns error:
      - Show error message to user
      - Ask: "How should we proceed? (retry / skip / manual)"
      - Handle user's choice

3. **If user declines (n):**
   - Skip session log generation
   - Note in progress.log that session-log was skipped
   - Continue to next step
```

**What to remove from task-relay:**
- Detailed session-log template (now in doc-generator profile)
- YAML frontmatter specifications (now in doc-generator profile)
- File naming logic for session logs (now in doc-generator)

**What to keep in task-relay:**
- Overall workflow orchestration
- Item management logic
- Validation step definitions
- State file update logic (item-list.json, progress.log)

---

### 7. Task-Relay Profile Templates

#### session-log.template.md

```markdown
---
Type: session-log
Status: Active
Author: {{author}}
Created: {{date}}
---

# Session Log: {{item_id}} - {{description}}

## Session Info

| Field | Value |
|-------|-------|
| **Item ID** | {{item_id}} |
| **Session Date** | {{date}} |
| **Agent** | {{author}} |
| **Status** | {{final_status}} |
| **Duration** | ~{{duration}} minutes |

## Item Details

**Description:** {{description}}

**Priority:** {{priority}}

**Validation Steps:**
{{#validation_steps}}
- {{.}}
{{/validation_steps}}

## Work Performed

{{#work_performed}}
{{@index}}. {{.}}
{{/work_performed}}

## Validation Results

| Validation Step | Status | Notes |
|----------------|--------|-------|
{{#validation_results}}
| {{step}} | {{status}} | {{notes}} |
{{/validation_results}}

## State Updates

| File | Change |
|------|--------|
{{#state_updates}}
| {{file}} | {{change}} |
{{/state_updates}}

## Blockers

{{#if blockers}}
{{#blockers}}
- {{.}}
{{/blockers}}
{{else}}
None
{{/if}}

{{#if_full_detail}}
## Related Documents

{{#if related_docs}}
{{#related_docs}}
- [[{{.}}]]
{{/related_docs}}
{{else}}
None
{{/if}}

## Notes

{{notes}}
{{/if_full_detail}}

## Next Session Recommendation

{{#if_full_detail}}
**Recommended Next Item:** {{next_recommendation}}

**Reasoning:** {{next_reasoning}}

**Preparation needed:** {{next_preparation}}
{{else}}
**Next:** {{next_recommendation}}
{{/if_full_detail}}
```

---

### 8. Task-Relay Profile Schemas

#### session-log.schema.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": [
    "item_id",
    "description",
    "work_performed",
    "validation_results",
    "author",
    "date"
  ],
  "properties": {
    "item_id": {
      "type": "string",
      "pattern": "^ITEM-[0-9]{3}$",
      "description": "Item ID in format ITEM-XXX"
    },
    "description": {
      "type": "string",
      "minLength": 1,
      "description": "Item description"
    },
    "work_performed": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "minItems": 1,
      "description": "List of work completed"
    },
    "validation_results": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["step", "status"],
        "properties": {
          "step": {
            "type": "string"
          },
          "status": {
            "type": "string",
            "enum": ["pass", "fail", "skip"]
          },
          "notes": {
            "type": "string"
          }
        }
      },
      "minItems": 1,
      "description": "Validation results"
    },
    "state_updates": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["file", "change"],
        "properties": {
          "file": {
            "type": "string"
          },
          "change": {
            "type": "string"
          }
        }
      },
      "description": "State file changes made"
    },
    "blockers": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Any blockers encountered"
    },
    "related_docs": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Related documents"
    },
    "next_recommendation": {
      "type": "string",
      "description": "Next recommended item ID"
    },
    "next_reasoning": {
      "type": "string",
      "description": "Reasoning for next recommendation"
    },
    "next_preparation": {
      "type": "string",
      "description": "Preparation needed for next item"
    },
    "notes": {
      "type": "string",
      "description": "Additional notes"
    },
    "author": {
      "type": "string",
      "enum": ["claude", "cursor", "gemini", "user", "chatgpt"],
      "description": "Agent or user who performed the work"
    },
    "date": {
      "type": "string",
      "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$",
      "description": "Date in YYYY-MM-DD format"
    },
    "final_status": {
      "type": "string",
      "enum": ["pending", "in_progress", "completed", "blocked"],
      "description": "Final status of the item"
    },
    "priority": {
      "type": "integer",
      "minimum": 1,
      "description": "Item priority (1 = highest)"
    },
    "duration": {
      "type": "integer",
      "minimum": 1,
      "description": "Session duration in minutes"
    },
    "validation_steps": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Validation steps defined for item"
    }
  }
}
```

---

## Implementation Plan

### Phase 1: Core Infrastructure

**Tasks:**
1. Create `structured-doc-generator/` directory
2. Create `SKILL.md` file with skill metadata
3. Define skill description and trigger conditions
4. Implement Claude Code detection logic (try Task tool, fallback to direct)
5. Implement args parsing (JSON from string parameter)

**Deliverable:** Basic skill skeleton that can be invoked and detects execution environment

---

### Phase 2: Task-Relay Profile

**Tasks:**
6. Extract session-log template from task-relay
7. Define session-log schema with all required and optional fields
8. Document task-relay profile rules (naming, location, frontmatter, detail modes)
9. Bundle profile into SKILL.md with clear section markers

**Deliverable:** Complete task-relay profile embedded in skill file

---

### Phase 3: Document Generation Logic

**Tasks:**
10. Implement template rendering engine (replace {{placeholders}} with data)
11. Implement token-aware detail level logic (70% threshold, section inclusion/exclusion)
12. Implement YAML frontmatter generation with proper formatting
13. Implement file naming logic:
    - Find existing files in target directory
    - Calculate next sequence number
    - Format: `XXX_YYYY-MM-DD_author_session-log-description.md`

**Deliverable:** Working document generator that produces correctly formatted markdown

---

### Phase 4: Validation System

**Tasks:**
14. Implement schema validation against required fields
15. Implement auto-correction rules:
    - Date format normalization
    - Item ID format normalization
    - Status normalization
    - Author normalization
    - Missing optional field defaults
16. Implement hard-fail detection:
    - Missing required fields
    - Invalid enum values
    - Malformed data structures
17. Implement error message formatting (clear, actionable)

**Deliverable:** Robust validation system that ensures document quality

---

### Phase 5: File Operations

**Tasks:**
18. Implement file path resolution:
    - Determine project root
    - Resolve target directory (e.g., `30-logs/`)
    - Generate full file path
19. Implement Write tool invocation with generated content
20. Implement success/failure response formatting:
    - Success: file path relative to project
    - Failure: validation error with details
21. Handle file system errors gracefully

**Deliverable:** End-to-end document generation and persistence

---

### Phase 6: Task-Relay Integration

**Tasks:**
22. Update task-relay SKILL.md execution phase (Step 5b)
23. Add user approval prompt before document generation
24. Add doc-generator invocation with all required data
25. Add error handling and retry logic
26. Remove redundant session-log template from task-relay
27. Test task-relay → doc-generator flow manually

**Deliverable:** Task-relay integrated with doc-generator

---

### Phase 7: Testing & Validation

**Tasks:**
28. Test end-to-end workflow: task-relay → doc-generator → session-log created
29. Test validation: missing required fields, invalid data
30. Test auto-correction: date formats, ID formats, status values
31. Test token-aware detail: >70% vs ≤70% token usage
32. Test Claude Code detection: verify sub-agent delegation works
33. Test error cases: invalid profile, invalid doc_type, file write failures
34. Verify token savings in main agent (compare before/after)

**Deliverable:** Verified, working system with proven token savings

---

### Phase 8: Documentation

**Tasks:**
35. Document profile extension guide:
    - How to add a new profile
    - Profile structure requirements
    - Template syntax and placeholders
    - Schema definition guidelines
36. Add usage examples for caller skills
37. Document args interface with all parameters
38. Document return value formats
39. Add troubleshooting guide

**Deliverable:** Complete documentation for maintenance and extension

---

## Success Criteria

### Functional Requirements

✅ Task-relay can generate session-logs via doc-generator
✅ Generated documents pass all validation rules (schema, formatting, naming)
✅ Works in Claude Code with sub-agent delegation
✅ Works in other AI clients with direct execution
✅ Adaptive detail level works (concise mode triggered above 70% tokens)
✅ Auto-correction fixes common data issues automatically
✅ Hard validation errors are caught and reported clearly

### Non-Functional Requirements

✅ Token usage in main agent reduced by offloading document generation
✅ Profile system is extensible (clear pattern for adding new profiles)
✅ Error messages are actionable and helpful
✅ Skill is self-contained (no external dependencies)
✅ Documentation is complete and clear

### Quality Metrics

- **Token Savings:** Main agent saves at least 1000+ tokens per session-log generation
- **Validation Accuracy:** 100% of invalid documents are caught before writing
- **Auto-Correction Rate:** At least 80% of common issues are auto-fixed
- **Error Clarity:** All error messages explain what's wrong and how to fix it

---

## Future Enhancements (V2+)

### Additional Task-Relay Document Types

- Progress log updates (`progress-update`)
- Init scripts (`init-script-bash`, `init-script-markdown`)
- Spec file generation (`spec-file`)
- Item list updates (`item-list-update`)

### New Workflow Profiles

- Profile for other multi-session workflows
- Profile for research/analysis workflows
- Profile for code review workflows

### Advanced Features

- Custom profiles: caller provides template/schema paths at runtime
- Token usage analytics: measure and report actual token savings
- Profile versioning: support multiple versions of a profile
- Template inheritance: base templates that profiles can extend
- Validation webhooks: call external validation services
- Document diff/history: track changes to generated documents

### Performance Optimizations

- Caching: cache parsed templates and schemas
- Lazy loading: load profiles on-demand rather than all upfront
- Parallel validation: run schema and rule validation concurrently

---

## Appendices

### A. Design Discussion Summary

This design emerged from a comprehensive Q&A discussion that explored:

1. **Document generation scope** - Understanding what task-relay generates
2. **Rules and templates** - Where they're defined and how they're structured
3. **Sub-agent architecture** - Generic vs specific, standalone vs integrated
4. **Interface design** - Profile-based invocation pattern
5. **Error handling** - Auto-correction with hard-fail boundaries
6. **Token optimization** - Adaptive detail levels based on usage
7. **Integration approach** - Minimal modification to task-relay
8. **Extensibility** - Profile system for future workflows

Key principles that guided the design:
- **Token efficiency** - Primary goal of saving context tokens
- **Portability** - Works across Claude Code and other clients
- **Simplicity** - Avoid over-engineering, solve current need first
- **Extensibility** - Design for future workflows without implementing them now
- **Reliability** - Validation and auto-correction ensure quality

### B. Glossary

- **Profile:** A bundle of templates, schemas, and rules for a specific workflow
- **Detail Mode:** Full or concise document generation based on token usage
- **Auto-correction:** Automatic fixing of common data issues (dates, IDs, etc.)
- **Hard fail:** Validation error that cannot be auto-corrected
- **Sub-agent:** A Task tool delegation in Claude Code that runs in separate context
- **Token-aware:** Adapting behavior based on main agent's token usage percentage

### C. References

- Task-relay skill: `/SKILL.md`
- Session-log template: `/assets/session-log.template.md`
- Item-list schema: `/references/item-list-schema.json`

---

**Document Control**

- **Created:** 2025-12-25
- **Last Updated:** 2025-12-25
- **Version:** 1.0
- **Status:** Approved for Implementation
- **Next Review:** After V1 implementation complete
