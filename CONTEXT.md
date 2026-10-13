# Task Relay

Task Relay is a file-based way to run long assignments with a coding agent across many sessions.
Work is broken into items and tasks, and the state of that work lives in files, so any agent or
client can pick up where the last session stopped.

## Language

### Work structure

**Item**:
A milestone in the assignment. It can have several outcomes, and it holds one or more tasks plus
the validation that proves the milestone is reached.
_Avoid_: ticket, issue, job, story

**Task**:
A small goal inside an item that ends in a state anyone can verify. A task can take one session
or several.
_Avoid_: step, subtask, checklist entry

**Session**:
One agent run that moves an item or task forward. Compaction keeps the same session. A session
never defines how big the work is.
_Avoid_: chat, conversation, run

**Handoff**:
Ending a session so that a new session, maybe with a different model, can continue from the state
files and the session narrative alone.
_Avoid_: transfer, resume note

**Terminal item**:
An item that has finished — completed or cancelled — and will not be worked on again. Its full
record is kept for history.
_Avoid_: closed item, done item, archived item

**Rulebook**:
A file linked to an item or task that sets its objective, deliverables, acceptance, boundaries
and stop point. The agent reads it before the work and checks it before closing.
_Avoid_: guide, spec

**Context file**:
A file pinned to an item or task that the agent must read before working on it. It informs the
work but is not checked at closing. A task also reads the context files of its item.
_Avoid_: guide, attachment, reference

### State and views

**State file**:
A file that holds the current truth about an assignment: which items are active, what each task's
status is, the compact record of finished items, and the running session narrative. State files
are the source of truth; every other view is derived from them.
_Avoid_: database, ledger, tracker

**Status dashboard**:
The page a person opens to see where the assignment stands: what needs their answer, what is
waiting on something external, what is in progress, and what has finished. It is generated from
the state files and is meant for reading, never for editing.
_Avoid_: report, board, UI, screen

**State writer**:
A lightweight subagent that applies state changes and then regenerates the status dashboard. It
does the bookkeeping so the main agent can keep its context on the actual work.
_Avoid_: updater, scribe, state machine, backend

**Update request**:
The single message the main agent sends to the state writer. It lists the operations to apply, in
order, together with the session narrative lines to append.
_Avoid_: diff, patch, command, job

### Blockers

**Blocker**:
A recorded reason why a task cannot proceed. A blocker names who or what can clear it and when it
started, and it exists only while the task is blocked.
_Avoid_: impediment, obstacle, dependency

**Needs-user blocker**:
A blocker that only the user can clear, usually because a question needs an answer. It may carry
a suggested default action, which is advice for the user and never permission to continue.
_Avoid_: approval, decision request, user input

**External blocker**:
A blocker that clears when something outside the agent and the user acts — a credential, a
delivery, or another team's decision.
_Avoid_: dependency, third party, wait

**Unclassified blocker**:
A blocked task from older data that carries no blocker type. It is shown to the user as needing
attention until someone says whether it is a needs-user or an external blocker.
_Avoid_: unknown blocker, legacy blocker, misc blocker
