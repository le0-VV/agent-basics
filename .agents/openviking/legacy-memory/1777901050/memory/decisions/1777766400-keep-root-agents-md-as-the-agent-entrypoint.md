---
id: decision-1777766400-keep-root-agents-md-as-the-agent-entrypoint
type: decision
title: Keep root Agents.md as the agent entrypoint
status: accepted
created: 1777766400
updated: 1777766400
tags: [agent-basics, instructions, setup]
summary: agent-basics keeps Agents.md at the project root because agents reliably discover root instruction files
---

# Keep root Agents.md as the agent entrypoint

## Decision

agent-basics keeps Agents.md at the project root because agents reliably discover root instruction files. Detailed agent-basics operating rules live in .agents/AGENT-BASICS.md, which Agents.md references. setup-macos.sh treats legacy .agents/INSTRUCTIONS.md as migration input and seeds .agents/AGENT-BASICS.md from it when needed.

## Related

- None.

