---
id: decision-20260503-polish-memory-recorder-output
type: decision
title: Polish memory recorder output
status: accepted
created: 2026-05-03
updated: 2026-05-03
tags: [agent-basics, memory, mcp, usability]
summary: memory_record and agent-basics memory record now support structured fields so generated entries need less manual cleanup.
---

# Polish memory recorder output

## Decision

Generate more complete markdown entries from the memory recorder instead of requiring agents to patch the files by hand after recording.

## Rationale

Agent memory should be written through the CLI or MCP path, and the tool should own schema, section structure, INDEX.md insertion, locking, validation, and rebuild behavior.

## Consequences

The CLI and MCP server accept structured fields such as rationale, consequences, notes, steps, and related. The recorder preserves blank lines between INDEX.md sections.

## Related

- memory/decisions/20260503-use-rust-for-the-agent-basics-binary.md
