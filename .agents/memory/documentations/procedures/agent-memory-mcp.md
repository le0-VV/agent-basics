---
id: procedure-20260503-agent-memory-mcp
type: procedure
title: Use the agent-basics memory MCP server
status: active
created: 2026-05-03
updated: 2026-05-03
tags: [agent-basics, memory, rag, mcp]
summary: Use `.agents/memory/rag/memory-mcp.py` as the primary agent-facing memory interface.
---

# Use the agent-basics memory MCP server

## When To Use

Use this whenever an MCP-capable agent needs to retrieve prior project context, record durable memory, validate memory, rebuild the generated RAG index, or check memory health.

## Steps

1. Configure the agent's MCP client to run `.agents/memory/rag/memory-mcp.py` from the repository root.
2. Call `memory_search` before answering requests that depend on prior project context.
3. Call `memory_record` when the user asks to remember something or when a durable decision, fact, preference, gotcha, event, source, or procedure should be preserved.
4. Call `memory_validate` before committing memory changes.
5. Call `memory_doctor` to inspect layout, config, index freshness, and embedding endpoint health.

## Verification

Send `initialize`, `tools/list`, and a `tools/call` request for `memory_doctor`. The server should return the `memory_search`, `memory_record`, `memory_doctor`, `memory_rebuild`, and `memory_validate` tools.

## Related

- `.agents/memory/rag/memory-mcp.py`
- `.agents/memory/rag/agent-memory.py`
- `.agents/memory/SCHEMA.md`
