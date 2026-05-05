---
name: agent-basics-finish-work
description: Verify, ingest, summarize, and commit completed agent-basics repository work.
---

# Finish Work Skill

Use this before handing work back to the user or another agent.

## Steps

1. Run `agent-basics verify` or the narrowest reliable validation for the changed surface.
2. Record durable decisions, gotchas, and follow-up context through the memory update workflow.
3. Run `agent-basics ov ingest-changed` after source-store, instruction, documentation, or skill changes.
4. Update `.agents/TODO.md` by ticking completed items and recording blockers.
5. Check `git status --short`.
6. Stage intentional changes.
7. Commit with `agent-basics commit "type(scope): description"` when a commit is expected.

## Commands

```bash
agent-basics verify
agent-basics ov ingest-changed
agent-basics commit "feat(scope): description"
```

## Output

Report changed files, validation results, memory/ingest status, commit hash when created, and any residual risk.
