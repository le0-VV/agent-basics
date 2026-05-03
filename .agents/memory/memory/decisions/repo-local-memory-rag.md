---
id: decision-1777766400-repo-local-memory-rag
type: decision
title: Use repo-local structured memory with generated RAG support as compatibility
status: superseded
created: 1777766400
updated: 1777827387
tags: [agent-basics, memory, rag, embeddings, compatibility]
summary: agent-basics keeps the custom markdown mini-RAG only as compatibility while OpenViking becomes the required backend.
---

# Use repo-local structured memory with generated RAG support as compatibility

## Decision

agent-basics used `.agents/memory/` as the canonical project-owned memory and documentation source tree.

This decision is now superseded by the OpenViking-backed harness direction. The `.agents/memory/` tree, generated RAG indexes, embedding databases, model caches, and local embedding APIs remain compatibility support until migration is implemented.

## Rationale

Structured markdown gave agents a predictable place to record durable context. A generated RAG layer helped with vague user requests and fuzzy recall without making a separate memory runtime the source of truth.

OpenViking overlaps with this custom layer and should own memory, resources, skills, semantic organization, and retrieval instead.

## Consequences

- Existing compatibility setup may still create the memory schema, templates, and directory layout.
- Compatibility setup may still validate an existing embedding API or install a repo-local HuggingFace embedding API.
- Compatibility RAG provider and runtime settings remain in `.agents/memory/rag/config.json`.
- Agents must wait when `.agents/memory/rag/write.lock/` exists while using the compatibility layer.
- Future OpenViking tooling should cite source records and keep repo-specific config under `.agents/`.

## Related

- `.agents/memory/memory/decisions/1777852800-make-agent-basics-an-openviking-backed-repo-harness.md`
- `.agents/memory/SCHEMA.md`
- `.agents/memory/rag/config.json`
