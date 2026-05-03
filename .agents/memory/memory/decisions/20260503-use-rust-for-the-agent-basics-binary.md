---
id: decision-20260503-use-rust-for-the-agent-basics-binary
type: decision
title: Use Rust for the agent-basics binary
status: accepted
created: 2026-05-03
updated: 2026-05-03
tags: [agent-basics, rust, cli, distribution]
summary: agent-basics is distributed as a Rust binary that embeds the setup, memory CLI, and MCP server while setup internals are still being ported.
---

# Use Rust for the agent-basics binary

## Decision

Use Rust for the systemwide agent-basics binary from the start. The binary embeds the current setup script, memory CLI, and memory MCP server so Homebrew installs one command while we can port internals gradually. Keep the repo-local Bash and Python scripts as embedded implementation details and fallbacks until native Rust replacements are ready.

## Rationale

Rust gives agent-basics a single distributable binary with predictable startup behavior and no need to ship a loose command wrapper as the primary install artifact. Embedding the existing scripts lets distribution improve now without blocking on a full native rewrite.

## Consequences

Homebrew builds agent-basics with Cargo. The Rust entrypoint must preserve the existing command surface while setup, memory CLI, and MCP internals are migrated behind it over time.

## Related

- None.
