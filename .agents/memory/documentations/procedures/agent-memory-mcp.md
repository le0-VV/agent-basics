---
id: procedure-20260503-agent-memory-mcp
type: procedure
title: Use the agent-basics memory MCP server
status: active
created: 2026-05-03
updated: 2026-05-03
tags: [agent-basics, memory, rag, mcp]
summary: Use `agent-basics-memory-mcp` or `.agents/memory/rag/memory-mcp.py` as the primary agent-facing memory interface.
---

# Use the agent-basics memory MCP server

## When To Use

Use this whenever an MCP-capable agent needs to retrieve prior project context, record durable memory, validate memory, rebuild the generated RAG index, or check memory health.

## Steps

1. Configure the agent's MCP client to run `agent-basics-memory-mcp` from the repository root when the systemwide command is installed.
2. If the systemwide command is unavailable, configure the client to run the absolute repo-local `.agents/memory/rag/memory-mcp.py` path from the repository root.
3. Call `memory_search` before answering requests that depend on prior project context.
4. Call `memory_record` when the user asks to remember something or when a durable decision, fact, preference, gotcha, event, source, or procedure should be preserved.
5. Call `memory_validate` before committing memory changes.
6. Call `memory_doctor` to inspect layout, config, index freshness, and embedding endpoint health.

## Codex Desktop Configuration

In Settings -> MCP servers -> Connect to a custom MCP, use these fields:

- Name: `agent-basics-memory`
- Transport: `STDIO`
- Command to launch: `agent-basics-memory-mcp` when installed, otherwise the absolute path to `.agents/memory/rag/memory-mcp.py`
- Arguments: none
- Environment variables: leave blank unless `.agents/memory/rag/config.json` names an API key variable in `embedding.api_key_env`
- Environment variable passthrough: same API key variable only when needed
- Working directory: absolute path to the repository root

For this repository:

- Command to launch: `agent-basics-memory-mcp` after Homebrew install, or `/Users/leonardw/Projects/agent-basics/.agents/memory/rag/memory-mcp.py` from the checkout
- Working directory: `/Users/leonardw/Projects/agent-basics`

Keep this guidance in agent-basics docs and memory procedures. Do not rely on a separate `Skills.md` for baseline setup because skills are optional client-side additions, while repo-local memory MCP setup is part of the agent-basics contract.

## Verification

Send `initialize`, `tools/list`, and a `tools/call` request for `memory_doctor`. The server should return the `memory_search`, `memory_record`, `memory_doctor`, `memory_rebuild`, and `memory_validate` tools.

## Related

- `.agents/memory/rag/memory-mcp.py`
- `.agents/memory/rag/agent-memory.py`
- `.agents/memory/SCHEMA.md`
