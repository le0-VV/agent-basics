---
id: procedure-20260503-agent-memory-cli
type: procedure
title: Use the agent-basics memory CLI
status: active
created: 2026-05-03
updated: 2026-05-03
tags: [agent-basics, memory, rag, cli]
summary: Use `.agents/memory/rag/agent-memory.py` to validate, rebuild, search, record, and install hooks for repo-local memory.
---

# Use the agent-basics memory CLI

## When To Use

Use this whenever an agent needs to validate memory files, rebuild the generated RAG index, search prior context, or record a new structured entry.

## Steps

1. Run `.agents/memory/rag/agent-memory.py validate` before committing memory changes.
2. Run `.agents/memory/rag/agent-memory.py rebuild` after memory or documentation entries change.
3. Run `.agents/memory/rag/agent-memory.py search "<query>"` when the user refers to vague or previous context.
4. Run `.agents/memory/rag/agent-memory.py record <type> <title> --content "<content>"` to create a structured entry and rebuild the index.
5. Run `.agents/memory/rag/agent-memory.py install-hooks` to install local git hooks in a repo.

## Verification

Run `.agents/memory/rag/agent-memory.py doctor` to check layout, config, manifest, and index status. Add `--online` when the embedding API should be checked too.

## Related

- `.agents/memory/SCHEMA.md`
- `.agents/memory/rag/agent-memory.py`
