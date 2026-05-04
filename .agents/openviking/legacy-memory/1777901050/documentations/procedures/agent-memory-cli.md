---
id: procedure-1777766400-agent-memory-cli
type: procedure
title: Use the compatibility agent-basics memory CLI
status: compatibility
created: 1777766400
updated: 1777827387
tags: [agent-basics, memory, rag, cli, compatibility]
summary: Use `agent-basics memory` or `.agents/memory/rag/agent-memory.py` for fallback memory operations while OpenViking integration is unavailable.
---

# Use the compatibility agent-basics memory CLI

## When To Use

Use this when installing compatibility git hooks, repairing `.agents/memory/` manually, or when the OpenViking gateway and compatibility memory MCP server are unavailable.

## Steps

1. Prefer `agent-basics ov ...` or OpenViking-backed MCP tools when they exist.
2. Run `agent-basics memory validate` before committing compatibility memory changes when the systemwide command is installed, or `.agents/memory/rag/agent-memory.py validate` from a source checkout.
3. Run `agent-basics memory rebuild` after compatibility memory or documentation entries change.
4. Run `agent-basics memory search "<query>"` only as a fallback when OpenViking search and MCP `memory_search` are unavailable.
5. Run `agent-basics memory record <type> <title> --content "<content>" --no-rebuild` only as a fallback when OpenViking recording and MCP `memory_record` are unavailable.
6. Prefer structured fields such as `--rationale`, `--consequences`, `--notes`, `--steps`, and `--related` instead of patching generated memory markdown by hand.
7. Run `agent-basics memory install-hooks` to install compatibility local git hooks in a repo. Hooks validate memory before commit and warn when the generated index is stale; set `AGENT_BASICS_HOOK_AUTO_REBUILD=1` only when hook-triggered embedding calls are acceptable.

## Verification

Run `agent-basics memory doctor` to check compatibility layout, config, manifest, and index status. Add `--online` when the embedding API should be checked too.

## Related

- `.agents/memory/documentations/procedures/openviking-gateway.md`
- `.agents/memory/SCHEMA.md`
- `.agents/memory/rag/agent-memory.py`
- `.agents/memory/rag/memory-mcp.py`
