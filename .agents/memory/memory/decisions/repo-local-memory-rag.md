---
id: decision-20260503-repo-local-memory-rag
type: decision
title: Use repo-local structured memory with generated RAG support
status: accepted
created: 2026-05-03
updated: 2026-05-03
tags: [agent-basics, memory, rag, embeddings]
summary: agent-basics keeps memory as repo markdown and uses generated embedding/RAG support for vague recall.
---

# Use repo-local structured memory with generated RAG support

## Decision

agent-basics uses `.agents/memory/` as the canonical project-owned memory and documentation source tree.

RAG indexes, embedding databases, model caches, and local embedding APIs are generated support layers that must be rebuildable from the markdown source.

## Rationale

Structured markdown gives agents a predictable place to record durable context. A generated RAG layer helps with vague user requests and fuzzy recall without making a separate memory runtime the source of truth.

## Consequences

- Setup must create the memory schema, templates, and directory layout.
- Setup must validate an existing embedding API or install a repo-local HuggingFace embedding API.
- Durable RAG provider and runtime settings belong in `.agents/memory/rag/config.json`; environment variables are setup inputs, secret pointers, or one-off overrides.
- Agents must wait when `.agents/memory/rag/write.lock/` exists.
- Future MCP/RAG tooling should cite markdown source files for every returned result.

## Related

- `.agents/memory/SCHEMA.md`
- `.agents/memory/rag/config.json`
