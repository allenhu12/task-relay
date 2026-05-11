# Task Relay Examples

Real-world examples of item decomposition for different types of assignments.

## Example 1: Build a Todo App

**Assignment**: Build a full-stack todo application with user authentication

**Total Items**: 45
**Estimated Sessions**: 30-45

### Categories:
- Setup (5 items)
- Data Models (8 items)
- API Endpoints (12 items)
- UI Components (15 items)
- Testing (5 items)

### Sample Items:

```json
{
  "id": "ITEM-001",
  "category": "setup",
  "description": "Initialize Next.js project with TypeScript and Tailwind CSS",
  "priority": 1,
  "validation_steps": [
    "Run npm install with no errors",
    "Start dev server successfully on port 3000",
    "Verify TypeScript compilation works",
    "Verify Tailwind CSS applies styling"
  ],
  "status": "pending",
  "completed_at": null,
  "notes": ""
}
```

```json
{
  "id": "ITEM-002",
  "category": "setup",
  "description": "Set up PostgreSQL database with Prisma ORM",
  "priority": 2,
  "validation_steps": [
    "Database server running and accessible",
    "Prisma schema file created",
    "Run prisma migrate dev successfully",
    "Prisma client generates without errors"
  ],
  "status": "pending",
  "completed_at": null,
  "notes": "Depends on ITEM-001"
}
```

```json
{
  "id": "ITEM-005",
  "category": "data-models",
  "description": "Create Todo model with CRUD operations",
  "priority": 5,
  "validation_steps": [
    "Create todo.ts with Todo interface",
    "Implement createTodo, readTodo, updateTodo, deleteTodo functions",
    "Write unit tests for all CRUD operations",
    "All tests pass with 100% coverage"
  ],
  "status": "pending",
  "completed_at": null,
  "notes": "Depends on ITEM-002 (database setup)"
}
```

```json
{
  "id": "ITEM-020",
  "category": "ui",
  "description": "Create TodoListItem component with delete functionality",
  "priority": 20,
  "validation_steps": [
    "Component renders todo text and checkbox",
    "Clicking checkbox toggles completed state",
    "Delete button removes item from list",
    "Visual feedback on hover and click",
    "Responsive design works on mobile"
  ],
  "status": "pending",
  "completed_at": null,
  "notes": ""
}
```

## Example 2: Refactor Legacy Codebase

**Assignment**: Refactor a legacy JavaScript codebase to TypeScript with tests

**Total Items**: 60
**Estimated Sessions**: 40-60

### Categories:
- Analysis (10 items)
- Type Safety (15 items)
- Test Coverage (12 items)
- Code Quality (18 items)
- Documentation (5 items)

### Sample Items:

```json
{
  "id": "ITEM-003",
  "category": "analysis",
  "description": "Document all external API dependencies and their usage patterns",
  "priority": 3,
  "validation_steps": [
    "Create api-dependencies.md listing all external APIs",
    "Document authentication methods for each API",
    "Identify which modules call which APIs",
    "Note any deprecated or risky API usage",
    "Review document with senior developer"
  ],
  "status": "pending",
  "completed_at": null,
  "notes": ""
}
```

```json
{
  "id": "ITEM-018",
  "category": "type-safety",
  "description": "Add TypeScript types to user authentication module",
  "priority": 18,
  "validation_steps": [
    "Convert auth.js to auth.ts",
    "Define interfaces for User, AuthToken, LoginRequest, LoginResponse",
    "Add type annotations to all functions",
    "Remove all 'any' types",
    "TypeScript compilation passes with strict mode",
    "All existing tests still pass"
  ],
  "status": "pending",
  "completed_at": null,
  "notes": "Depends on ITEM-015 (core type definitions)"
}
```

## Example 3: Research Project

**Assignment**: Research and write a comprehensive report on AI safety

**Total Items**: 15
**Estimated Sessions**: 10-15

### Categories:
- Research (6 items)
- Analysis (4 items)
- Writing (3 items)
- Review (2 items)

### Sample Items:

```json
{
  "id": "ITEM-001",
  "category": "research",
  "description": "Review and summarize top 10 papers on AI alignment",
  "priority": 1,
  "validation_steps": [
    "Identify top 10 most-cited papers on AI alignment",
    "Read each paper thoroughly",
    "Create summary document with key findings",
    "Extract relevant quotes and citations",
    "Organize summaries by theme"
  ],
  "status": "pending",
  "completed_at": null,
  "notes": ""
}
```

```json
{
  "id": "ITEM-007",
  "category": "analysis",
  "description": "Compare and contrast different AI safety frameworks",
  "priority": 7,
  "validation_steps": [
    "Create comparison table with at least 5 frameworks",
    "Document strengths and weaknesses of each",
    "Identify common themes and divergences",
    "Write analysis section (1000+ words)",
    "Peer review the analysis"
  ],
  "status": "pending",
  "completed_at": null,
  "notes": "Depends on ITEM-001 through ITEM-006 (research items)"
}
```

## Example 4: Data Analysis Pipeline

**Assignment**: Build an automated data processing pipeline

**Total Items**: 25
**Estimated Sessions**: 15-25

### Categories:
- Setup (3 items)
- Data Ingestion (5 items)
- Processing (8 items)
- Validation (4 items)
- Deployment (5 items)

### Sample Items:

```json
{
  "id": "ITEM-004",
  "category": "ingestion",
  "description": "Implement S3 data fetcher with error handling",
  "priority": 4,
  "validation_steps": [
    "Create S3Fetcher class with proper AWS credentials",
    "Implement fetch method with retry logic",
    "Add error handling for network failures",
    "Write unit tests for success and failure cases",
    "Test with production S3 bucket",
    "All tests pass"
  ],
  "status": "pending",
  "completed_at": null,
  "notes": ""
}
```

```json
{
  "id": "ITEM-012",
  "category": "processing",
  "description": "Create data cleaning module with outlier detection",
  "priority": 12,
  "validation_steps": [
    "Implement outlier detection using IQR method",
    "Add missing value handling",
    "Create data validation rules",
    "Test with sample dataset",
    "Verify output data quality",
    "Document cleaning steps in README"
  ],
  "status": "pending",
  "completed_at": null,
  "notes": "Depends on ITEM-008 (data schema definition)"
}
```

## Example 5: Small Bug Fix

**Assignment**: Fix authentication timeout issue in web app

**Total Items**: 8
**Estimated Sessions**: 5-8

### Categories:
- Investigation (3 items)
- Fix (3 items)
- Testing (2 items)

### Sample Items:

```json
{
  "id": "ITEM-001",
  "category": "investigation",
  "description": "Reproduce authentication timeout bug in dev environment",
  "priority": 1,
  "validation_steps": [
    "Set up dev environment with production-like data",
    "Follow steps from bug report",
    "Confirm timeout occurs consistently",
    "Document exact reproduction steps",
    "Capture relevant logs and error messages"
  ],
  "status": "pending",
  "completed_at": null,
  "notes": ""
}
```

```json
{
  "id": "ITEM-004",
  "category": "fix",
  "description": "Implement session refresh mechanism",
  "priority": 4,
  "validation_steps": [
    "Add refresh token endpoint to API",
    "Implement client-side token refresh logic",
    "Test automatic refresh before timeout",
    "Verify user stays logged in",
    "No authentication errors in logs"
  ],
  "status": "pending",
  "completed_at": null,
  "notes": "Depends on ITEM-002 (identify root cause)"
}
```

## Item Sizing Guidelines

### Too Large (needs splitting):
```json
{
  "description": "Build complete user authentication system with login, registration, password reset, email verification, and OAuth integration"
}
```

**Better** (split into multiple items):
- ITEM-010: Implement user login with email/password
- ITEM-011: Implement user registration with email verification
- ITEM-012: Implement password reset flow
- ITEM-013: Add OAuth integration for Google
- ITEM-014: Add OAuth integration for GitHub

### Too Small (consider merging):
```json
{
  "description": "Import React"
}
```

**Better** (merge with related work):
```json
{
  "description": "Set up React project with necessary dependencies and initial configuration"
}
```

### Just Right:
```json
{
  "description": "Create user profile component with edit functionality",
  "validation_steps": [
    "Component renders user data correctly",
    "Edit button enables form fields",
    "Save button updates user data",
    "Form validation works",
    "Success message displays after save"
  ]
}
```

## Common Patterns

### Pattern 1: Setup → Implementation → Testing
Good for feature development:
- ITEM-001: Set up test environment
- ITEM-002: Implement core functionality
- ITEM-003: Write comprehensive tests

### Pattern 2: Research → Analysis → Writing
Good for documentation or reports:
- ITEM-001: Research existing solutions
- ITEM-002: Analyze pros and cons
- ITEM-003: Write recommendation document

### Pattern 3: Spike → Design → Implement
Good for uncertain requirements:
- ITEM-001: Spike to understand feasibility
- ITEM-002: Design approach based on findings
- ITEM-003: Implement chosen solution

### Pattern 4: Break → Fix → Verify
Good for debugging:
- ITEM-001: Reproduce bug consistently
- ITEM-002: Identify root cause
- ITEM-003: Implement fix
- ITEM-004: Add regression tests

## Validation Step Best Practices

### Good Validation Steps (Objective):
- ✅ "All tests pass"
- ✅ "Server starts without errors"
- ✅ "API returns 200 status code"
- ✅ "UI renders correctly on mobile"
- ✅ "Performance benchmark under 100ms"

### Bad Validation Steps (Subjective):
- ❌ "Code looks good"
- ❌ "Seems to work"
- ❌ "Should be fine"
- ❌ "Appears correct"
- ❌ "Probably ready"

### Adding Specificity:
**Vague**: "Test the feature"
**Better**: "Run npm test and verify all 12 tests pass"

**Vague**: "Check if it works"
**Better**: "Navigate to /login, enter credentials, verify redirect to /dashboard"

**Vague**: "Make sure it's fast"
**Better**: "Run performance test, verify response time < 200ms"
