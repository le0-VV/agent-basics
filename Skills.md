# Skills

This file indexes repo-local agent workflows. Skills reduce repeated prompt overhead; baseline behavior still depends on root instructions and MCP tools.

## Available Skills

- [Prework](.agents/skills/prework.md): establish context and plan before editing.
- [Memory Update](.agents/skills/memory-update.md): record durable decisions, preferences, facts, cases, resources, and skills through OpenViking.
- [Finish Work](.agents/skills/finish-work.md): verify, ingest, summarize, and commit completed work.

## Command Surface

Prefer these stable command prefixes:

```bash
agent-basics ov
agent-basics verify
agent-basics commit
```

Agents should use the OpenViking-backed MCP server when available and fall back to the same `agent-basics ov ...` commands when MCP is unavailable.
