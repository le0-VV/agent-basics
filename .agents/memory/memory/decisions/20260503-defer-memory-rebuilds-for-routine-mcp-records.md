---
id: decision-20260503-defer-memory-rebuilds-for-routine-mcp-records
type: decision
title: Defer memory rebuilds for routine MCP records
status: accepted
created: 2026-05-03
updated: 2026-05-03
tags: [agent-basics, memory, mcp, approvals]
summary: MCP memory_record defers RAG rebuilds by default so agents can write memory markdown without embedding API approval on every record.
---

# Defer memory rebuilds for routine MCP records

## Decision

Set MCP memory_record to pass --no-rebuild by default for routine memory and documentation records.

## Rationale

Markdown writes do not need the local embedding API, but rebuilding the RAG index does. Deferring rebuilds lets agents record context freely, then rebuild once after a batch or before search/commit.

## Consequences

New entries are immediately present in markdown and INDEX.md but are not searchable through embeddings until memory_rebuild runs. Agents must call memory_rebuild before relying on newly recorded entries in search or before committing memory changes.

## Related

- memory/decisions/20260503-polish-memory-recorder-output.md
