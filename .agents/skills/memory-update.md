---
name: agent-basics-memory-update
description: Record durable project context through the OpenViking-backed agent-basics gateway.
---

# Memory Update Skill

Use this whenever durable project context should survive the current session.

## Record

Record through the OpenViking MCP server when available. Otherwise use `agent-basics ov record`.

Use OpenViking memory categories:

- `profile`
- `preferences`
- `entities`
- `events`
- `cases`
- `patterns`
- `tools`
- `skills`

Use resources for external documentation, URLs, references, and larger source material.

## Steps

1. Decide whether the information is durable enough to keep.
2. Split mixed information into one independently updatable idea per record.
3. Avoid secrets and local-only credentials.
4. Record memory with `agent-basics ov record` or ingest resources with `agent-basics ov add-resource`.
5. Run `agent-basics ov ingest-changed` after editing `.agents/memory/` source-store files.
6. Verify retrieval with `agent-basics ov search "<query>"` when the record matters for future work.

## Commands

```bash
agent-basics ov record <category> "<title>" --content "<content>"
agent-basics ov add-resource <path-or-url>
agent-basics ov add-skill <path>
agent-basics ov ingest-changed
agent-basics ov search "<query>"
```
