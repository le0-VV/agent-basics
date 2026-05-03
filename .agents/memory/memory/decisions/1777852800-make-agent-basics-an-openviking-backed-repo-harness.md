---
id: decision-1777852800-make-agent-basics-an-openviking-backed-repo-harness
type: decision
title: Make agent-basics an OpenViking-backed repo harness
status: accepted
created: 1777852800
updated: 1777852800
tags: [roadmap, openviking, harness, memory]
summary: agent-basics should focus on repo harness responsibilities while OpenViking owns memory, resources, skills, semantic organization, and retrieval.
---

# Make agent-basics an OpenViking-backed repo harness

## Decision

agent-basics should focus on repo harness responsibilities while OpenViking owns memory, resources, skills, semantic organization, and retrieval.

## Rationale

The custom mini-RAG work overlaps with OpenViking. The more useful product boundary is for agent-basics to install, configure, wrap, and enforce repo workflows around OpenViking instead of becoming a second memory engine.

## Consequences

OpenViking becomes the required memory/context backend target. Custom .agents/memory RAG files are transitional until migration is proven. agent-basics should prioritize setup/upgrade, MCP gateway, stable commands, run state, skills, hooks, and migration UI.

## Related

- `ROADMAP.md`
- `.agents/AGENT-BASICS.md`
- `.agents/memory/documentations/procedures/openviking-gateway.md`
- `.agents/memory/memory/decisions/repo-local-memory-rag.md`
