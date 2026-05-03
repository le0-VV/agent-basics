---
id: decision-20260503-retire-the-agent-mailbox
type: decision
title: Retire the agent mailbox
status: accepted
created: 2026-05-03
updated: 2026-05-03
tags: [agent-basics, memory, coordination, cleanup]
summary: The MemoryHub-era agent-mailbox folder is retired; durable coordination belongs in .agents/memory and operational handoffs use git.
---

# Retire the agent mailbox

## Decision

Remove `.agents/agent-mailbox/` from this repository.

## Rationale

The mailbox was created for cross-sandbox coordination with MemoryHub. MemoryHub is no longer part of the agent-basics direction, so the mailbox would be an unindexed side channel outside the structured memory and RAG flow.

## Consequences

Durable coordination should be recorded under `.agents/memory/`. Operational handoffs should use git status, commits, branches, and pull requests.

## Related

- None.
