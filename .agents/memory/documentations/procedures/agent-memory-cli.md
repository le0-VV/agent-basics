---
id: procedure-20260503-agent-memory-cli
type: procedure
title: Use the agent-basics memory CLI
status: active
created: 2026-05-03
updated: 2026-05-03
tags: [agent-basics, memory, rag, cli]
summary: Use `.agents/memory/rag/agent-memory.py` for setup, git hooks, manual recovery, and fallback memory operations.
---

# Use the agent-basics memory CLI

## When To Use

Use this when installing git hooks, running setup, repairing memory manually, or when the memory MCP server is unavailable.

## Steps

1. Run `.agents/memory/rag/agent-memory.py validate` before committing memory changes.
2. Run `.agents/memory/rag/agent-memory.py rebuild` after memory or documentation entries change.
3. Run `.agents/memory/rag/agent-memory.py search "<query>"` only as a fallback when MCP `memory_search` is unavailable.
4. Run `.agents/memory/rag/agent-memory.py record <type> <title> --content "<content>"` only as a fallback when MCP `memory_record` is unavailable.
5. Run `.agents/memory/rag/agent-memory.py install-hooks` to install local git hooks in a repo.

## Verification

Run `.agents/memory/rag/agent-memory.py doctor` to check layout, config, manifest, and index status. Add `--online` when the embedding API should be checked too.

## Related

- `.agents/memory/SCHEMA.md`
- `.agents/memory/rag/agent-memory.py`
- `.agents/memory/rag/memory-mcp.py`
