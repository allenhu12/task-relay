---
Type: decision
Status: accepted
Author: claude
Created: 2026-09-28
---

# 1. Render the status dashboard with a script and a fixed template

## Context

Task Relay stores the state of an assignment in files that are written for agents to read. A
person who wants to know where the work stands has to open those files and rebuild the picture in
their head, so we decided to publish a status dashboard the user can simply open. That raised the
question of who writes the page. The reference workflow we studied answered it the opposite way: a
dedicated "dashboard-builder" agent chose its own panels for the current task and explicitly did
not use a template.

## Decision

A deterministic Python 3 script, using only the standard library, renders the page from a fixed
HTML template and rewrites it in full after every state write. The lightweight state-writer
subagent still drives the change: it applies the state operations, appends the session narrative,
and then calls the render script. The HTML itself is never composed free-form by a language model.

## Considered Options

- **An LLM writes the page free-form on each update.** Rejected: the output would differ run to
  run, cost tokens on every state flush, grow without a bound, and could quietly contradict the
  state files it is supposed to display.
- **An LLM fills a fixed template.** Rejected: for a mechanical mapping from data to fields the
  model adds nothing over a script, while keeping the same instability and token cost.
- **A script renders a fixed template (chosen).** The same input always produces byte-identical
  output, rendering costs no tokens, the page size stays bounded, and the result is static HTML
  with no JavaScript, so it opens in viewers that block scripts (DEVONthink, for example).

## Consequences

- The dashboard is a **derived** file: never hand-edited, always regenerated from the state files.
- Changing what the page shows means changing the template, not prompting a model.
- The page can only present what the state files already contain, which keeps it honest.
- If rendering fails, the previous page is left untouched, so a reader never sees a half-written
  dashboard.
