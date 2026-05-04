---
id: procedure-1777766400-agent-memory-mcp
type: procedure
title: Use the compatibility agent-basics memory MCP server
status: compatibility
created: 1777766400
updated: 1777827387
tags: [agent-basics, memory, rag, mcp, compatibility]
summary: Use `agent-basics mcp` or `.agents/memory/rag/memory-mcp.py` only while the OpenViking gateway is unavailable.
---

# Use the compatibility agent-basics memory MCP server

## When To Use

Use this only when the OpenViking-backed `agent-basics mcp` or `agent-basics ov ...` gateway is unavailable and work must continue through the transitional `.agents/memory/` mini-RAG.

## Steps

1. Prefer the OpenViking gateway procedure first.
2. Configure the agent's MCP client to run `agent-basics mcp` from the repository root when the installed command is still backed by the compatibility memory server.
3. If the systemwide command is unavailable, configure the client to run the absolute repo-local `.agents/memory/rag/memory-mcp.py` path from the repository root.
4. Call `memory_search` before answering requests that depend on prior project context.
5. Call `memory_record` when the user asks to remember something or when a durable decision, fact, preference, gotcha, event, source, or procedure should be preserved before OpenViking migration.
6. Pass structured fields such as `rationale`, `consequences`, `notes`, `steps`, and `related` when they apply, so the recorder can generate polished markdown without manual edits.
7. Leave `no_rebuild` at its default `true` for routine records so writes do not call the embedding API every time.
8. Call `memory_rebuild` once after a batch of memory changes, before relying on new entries in search, or before committing.
9. Call `memory_validate` before committing memory changes.
10. Call `memory_doctor` to inspect layout, config, index freshness, and embedding endpoint health.

## Codex Desktop Configuration

In Settings -> MCP servers -> Connect to a custom MCP, use these fields when the OpenViking gateway is not available:

- Name: `agent-basics-memory`
- Transport: `STDIO`
- Command to launch: `agent-basics` when installed, otherwise the absolute path to `.agents/memory/rag/memory-mcp.py`
- Arguments: `mcp` when using `agent-basics`; none when using the repo-local fallback script
- Environment variables: leave blank unless `.agents/memory/rag/config.json` names an API key variable in `embedding.api_key_env`
- Environment variable passthrough: same API key variable only when needed
- Working directory: absolute path to the repository root

For this repository:

- Command to launch: `agent-basics` with argument `mcp` after Homebrew install, or `/Users/leonardw/Projects/agent-basics/.agents/memory/rag/memory-mcp.py` from the checkout
- Working directory: `/Users/leonardw/Projects/agent-basics`

## Verification

Send `initialize`, `tools/list`, and a `tools/call` request for `memory_doctor`. The compatibility server should return `memory_search`, `memory_record`, `memory_doctor`, `memory_rebuild`, and `memory_validate`.

## Related

- `.agents/memory/documentations/procedures/openviking-gateway.md`
- `.agents/memory/rag/memory-mcp.py`
- `.agents/memory/rag/agent-memory.py`
- `.agents/memory/SCHEMA.md`
