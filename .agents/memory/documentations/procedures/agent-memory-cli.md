---
id: procedure-20260503-agent-memory-cli
type: procedure
title: Use the agent-basics memory CLI
status: active
created: 2026-05-03
updated: 2026-05-03
tags: [agent-basics, memory, rag, cli]
summary: Use `agent-basics memory` or `.agents/memory/rag/agent-memory.py` for setup, git hooks, manual recovery, and fallback memory operations.
---

# Use the agent-basics memory CLI

## When To Use

Use this when installing git hooks, running setup, repairing memory manually, or when the memory MCP server is unavailable.

## Steps

1. Run `agent-basics memory validate` before committing memory changes when the systemwide command is installed, or `.agents/memory/rag/agent-memory.py validate` from a source checkout.
2. Run `agent-basics memory rebuild` after memory or documentation entries change.
3. Run `agent-basics memory search "<query>"` only as a fallback when MCP `memory_search` is unavailable.
4. Run `agent-basics memory record <type> <title> --content "<content>" --no-rebuild` only as a fallback when MCP `memory_record` is unavailable and you are recording multiple entries.
5. Prefer structured fields such as `--rationale`, `--consequences`, `--notes`, `--steps`, and `--related` instead of patching generated memory markdown by hand.
6. Run `agent-basics memory install-hooks` to install local git hooks in a repo.

## Verification

Run `agent-basics memory doctor` to check layout, config, manifest, and index status. Add `--online` when the embedding API should be checked too.

## Related

- `.agents/memory/SCHEMA.md`
- `.agents/memory/rag/agent-memory.py`
- `.agents/memory/rag/memory-mcp.py`
