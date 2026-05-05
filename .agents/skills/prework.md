---
name: agent-basics-prework
description: Establish context, run state, and a concrete plan before editing an agent-basics repository.
---

# Prework Skill

Use this before non-trivial repository work.

## Steps

1. Read `Agents.md`, `.agents/AGENT-BASICS.md`, `ROADMAP.md`, `.agents/TODO.md`, and `Skills.md` when they exist.
2. Start or inspect run state with `agent-basics run start --task "<task>"` or `agent-basics run status`.
3. Verify or start the user-level OpenViking service with `agent-basics ov status --offline`, `agent-basics ov doctor`, or `agent-basics ov service install` when live retrieval is needed. Use `agent-basics ov server` only for foreground debugging.
4. Search prior context through the OpenViking MCP server or `agent-basics ov search "<query>"`.
5. Inspect the git state before editing.
6. Write or update the concrete checklist in `.agents/TODO.md`.

## Commands

```bash
agent-basics run status
agent-basics run start --task "<task>"
agent-basics ov status --offline
agent-basics ov search "<query>"
```

## Output

Proceed only when the current task, prior context, and planned file scope are clear.
