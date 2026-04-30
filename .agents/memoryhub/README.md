# MemoryHub

This directory contains repo-local markdown source for the central MemoryHub installation used by agent-basics.

The central hub should be configured with `MEMORYHUB_CONFIG_DIR`, usually `$HOME/.memoryhub`. Its `projects/` directory links back to this directory so the project owns its memory files while the hub owns the runtime, database, embeddings, and MCP/API surface.

Suggested categories:

- `user/memories/`: user profile, preferences, entities, and events
- `agent/memories/`: agent-learned cases, patterns, tools, and skills
- `agent/skills/`: reusable workflows and capabilities
- `resources/`: static project documents and documentation source records

